"""Adapter contract tests for SwitchProtocolAdapter (WebSocket control frames & HTTP ops)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx

from clerk.adapters.clock import SimulatedClock
from clerk.adapters.llm_scripted import ScriptedLLM
from clerk.adapters.local_git import LocalGitHost
from clerk.adapters.preview_local import FakePreview
from clerk.adapters.switch_protocol import SwitchBudgetExceededError, SwitchProtocolAdapter
from clerk.db.repositories import LedgerRepository
from clerk.db.session import create_db_engine, create_session_factory, reset_and_seed_db
from clerk.ports.protocols import Reference, RoomDocumentSpec, RoomRoleSpec, RoomSpec
from clerk.services.workflow import WorkflowOrchestrator
from clerk.settings import ConfigBundle
from clerk.workers.switch_consumer import SwitchConsumerWorker

IST = ZoneInfo("Asia/Kolkata")


class FakeWebSocketConnection:
    """In-memory WebSocket connection yielding scripted server frames and recording client sends."""

    def __init__(self, frames: list[dict[str, Any] | float]) -> None:
        self._frames = list(frames)
        self.sent: list[dict[str, Any]] = []
        self.closed = False

    def __aiter__(self) -> AsyncIterator[str]:
        return self._iter_frames()

    async def _iter_frames(self) -> AsyncIterator[str]:
        for item in self._frames:
            if isinstance(item, (int, float)):
                await asyncio.sleep(float(item))
            else:
                yield json.dumps(item)
                await asyncio.sleep(0)

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))

    async def close(self) -> None:
        self.closed = True

    async def __aenter__(self) -> FakeWebSocketConnection:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.closed = True


class ScriptedWebSocketFactory:
    """Factory returning a sequence of FakeWebSocketConnections across reconnects."""

    def __init__(self, connections: list[FakeWebSocketConnection]) -> None:
        self.connections = list(connections)
        self.urls: list[str] = []
        self.headers: list[dict[str, str]] = []
        self._idx = 0

    def __call__(self, url: str, headers: dict[str, str]) -> FakeWebSocketConnection:
        self.urls.append(url)
        self.headers.append(headers)
        conn = self.connections[min(self._idx, len(self.connections) - 1)]
        self._idx += 1
        return conn


@pytest.fixture()
def clock() -> SimulatedClock:
    return SimulatedClock("2026-11-05T19:00:00+05:30")


@pytest.mark.asyncio
async def test_ws_connection_state_and_independent_ping_pong_during_slow_consumer(
    config_bundle: ConfigBundle,
    clock: SimulatedClock,
) -> None:
    """Verify ping/pong replies immediately even while consumer is blocked on a slow operation."""
    frames: list[dict[str, Any] | float] = [
        {
            "event": "connection_state",
            "data": {
                "connection_id": "conn-123",
                "agent_id": "clerk-uuid",
                "generation": 3,
                "scope": "all",
                "filter": "all",
                "rooms": ["room-acme-intake", "room-acme-delivery"],
                "cursor": 41,
                "heartbeat_interval_seconds": 2.0,
            },
        },
        {
            "event": "message",
            "id": 42,
            "data": {
                "type": "message",
                "room_id": "room-acme-delivery",
                "sequence": 42,
                "payload": {
                    "addressed": True,
                    "sender": "user-priya",
                    "sender_name": "priya",
                    "sender_kind": "user",
                    "message_id": "msg-42",
                    "body": "@clerk status CR-003",
                    "timestamp": 1762349400000,
                },
            },
        },
        0.02,
        {"event": "ping", "data": {}},
        0.02,
        {"event": "ping", "data": {}},
        {
            "event": "evicted",
            "data": {"code": "taken_over", "reason": "test complete"},
        },
    ]
    ws_conn = FakeWebSocketConnection(frames)
    ws_factory = ScriptedWebSocketFactory([ws_conn])

    async with respx.mock(base_url="http://switch.local") as respx_mock:
        respx_mock.post("/agents/clerk-uuid/connection/placements").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        adapter = SwitchProtocolAdapter(
            base_url="http://switch.local",
            ws_url="ws://switch.local",
            agent_id="clerk-uuid",
            api_key="secret-key",
            rooms_config=config_bundle.rooms,
            clock=clock,
            connection_id="conn-123",
            ws_factory=ws_factory,
        )
        await adapter.connect()

        received_events = []
        async for ev in adapter.events():
            received_events.append(ev)
            # Simulate a slow LLM/git call in the consumer while pings arrive on WS
            await asyncio.sleep(0.08)
        await adapter.close()

    assert adapter.generation == 3
    assert adapter.cursor == 42
    assert adapter.pongs_sent == 2
    assert ws_conn.sent == [
        {"type": "pong", "cursor": 42},
        {"type": "pong", "cursor": 42},
    ]
    assert len(received_events) == 1
    assert received_events[0].id == "msg-42"
    assert received_events[0].room_name == "acme-delivery"
    assert received_events[0].sender_name == "priya"


@pytest.mark.asyncio
async def test_ws_evicted_taken_over_vs_heartbeat_lapsed_reconnect(
    config_bundle: ConfigBundle,
    clock: SimulatedClock,
) -> None:
    """Verify heartbeat_lapsed reconnects with cursor+generation, while taken_over stops."""
    conn1 = FakeWebSocketConnection(
        [
            {
                "event": "connection_state",
                "data": {"generation": 5, "cursor": 100, "rooms": ["room-acme-intake"]},
            },
            {
                "event": "evicted",
                "data": {"code": "heartbeat_lapsed", "reason": "missed pong"},
            },
        ]
    )
    conn2 = FakeWebSocketConnection(
        [
            {
                "event": "connection_state",
                "data": {"generation": 6, "cursor": 105, "rooms": ["room-acme-intake"]},
            },
            {
                "event": "evicted",
                "data": {"code": "taken_over", "reason": "another instance connected"},
            },
        ]
    )
    ws_factory = ScriptedWebSocketFactory([conn1, conn2])

    async with respx.mock(base_url="http://switch.local") as respx_mock:
        respx_mock.post("/agents/clerk-uuid/connection/placements").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        adapter = SwitchProtocolAdapter(
            base_url="http://switch.local",
            agent_id="clerk-uuid",
            api_key="secret-key",
            rooms_config=config_bundle.rooms,
            clock=clock,
            connection_id="conn-reconnect",
            reconnect_base_delay=0.01,
            ws_factory=ws_factory,
        )
        await adapter.connect()
        async for _ in adapter.events():
            pass
        await adapter.close()

    assert adapter.reconnect_count == 1
    assert adapter.stopped is True
    assert adapter.last_eviction is not None
    assert adapter.last_eviction["code"] == "taken_over"
    assert len(ws_factory.urls) == 2
    assert "start_from=head" in ws_factory.urls[0]
    assert "start_from=100" in ws_factory.urls[1]
    assert "expected_generation=5" in ws_factory.urls[1]


@pytest.mark.asyncio
async def test_ws_gap_frame_triggers_read_context(
    config_bundle: ConfigBundle,
    clock: SimulatedClock,
) -> None:
    """Verify a `gap` control frame calls `ops/read_context` and yields missed messages."""
    conn = FakeWebSocketConnection(
        [
            {
                "event": "connection_state",
                "data": {"generation": 1, "cursor": 10, "rooms": ["room-acme-intake"]},
            },
            {
                "event": "gap",
                "data": {
                    "from_sequence": 10,
                    "to_sequence": 12,
                    "rooms": ["room-acme-intake"],
                    "all_rooms": False,
                    "reason": "buffer rotated",
                },
            },
            0.05,
            {
                "event": "evicted",
                "data": {"code": "taken_over", "reason": "done"},
            },
        ]
    )
    ws_factory = ScriptedWebSocketFactory([conn])

    async with respx.mock(base_url="http://switch.local") as respx_mock:
        respx_mock.post("/agents/clerk-uuid/connection/placements").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        read_ctx_route = respx_mock.post("/agents/clerk-uuid/ops/read_context").mock(
            return_value=httpx.Response(
                200,
                json={
                    "result": {
                        "threads": [
                            {
                                "root": {
                                    "message_id": "missed-msg-11",
                                    "sender_name": "acme-scout",
                                    "body": (
                                        'ASK client="Sam" link="https://discord.com/1"\n'
                                        '"Fix Safari"'
                                    ),
                                    "timestamp": 1762349400000,
                                },
                                "replies": [],
                            }
                        ],
                        "truncated": False,
                    }
                },
            )
        )

        adapter = SwitchProtocolAdapter(
            base_url="http://switch.local",
            agent_id="clerk-uuid",
            api_key="secret-key",
            rooms_config=config_bundle.rooms,
            clock=clock,
            ws_factory=ws_factory,
        )
        await adapter.connect()
        events = [ev async for ev in adapter.events()]
        await adapter.close()

    assert read_ctx_route.called
    assert len(events) == 1
    assert events[0].id == "missed-msg-11"
    assert events[0].room_name == "acme-intake"


@pytest.mark.asyncio
async def test_http_operations_and_placements_fallback_contract(
    config_bundle: ConfigBundle,
    clock: SimulatedClock,
) -> None:
    """Verify placements fallback, post_message, send_targeted_message, roles, and docs."""
    async with respx.mock(base_url="http://switch.local") as respx_mock:
        # 1. Registration
        reg_route = respx_mock.post("/agents").mock(
            return_value=httpx.Response(
                200, json={"id": "clerk-registered-id", "api_key": "clerk-live-key"}
            )
        )

        # 2. Placements: return 422 on dict shape first, then 200 on list shape fallback
        placement_calls: list[dict[str, Any]] = []

        def placement_handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content.decode("utf-8"))
            placement_calls.append(body)
            if isinstance(body.get("placements"), dict):
                return httpx.Response(422, json={"detail": "Expected list of placements"})
            return httpx.Response(200, json={"ok": True})

        respx_mock.post("/agents/clerk-registered-id/connection/placements").mock(
            side_effect=placement_handler
        )

        # 3. post_message
        post_route = respx_mock.post("/agents/clerk-registered-id/ops/post_message").mock(
            return_value=httpx.Response(200, json={"result": {"event_id": "evt-post-1"}})
        )

        # 4. send_targeted_message
        targeted_route = respx_mock.post(
            "/agents/clerk-registered-id/ops/send_targeted_message"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "result": {
                        "event_id": "evt-targ-1",
                        "target_statuses": {"acme-estimator": "live"},
                    }
                },
            )
        )

        # 5. Room creation, links, references, room documents, and archiving
        create_room_route = respx_mock.post("/agents/clerk-registered-id/ops/create_room").mock(
            return_value=httpx.Response(
                200, json={"result": {"id": "uuid-cr-004", "name": "acme-cr-004"}}
            )
        )
        link_route = respx_mock.post("/agents/clerk-registered-id/ops/link_rooms").mock(
            return_value=httpx.Response(
                200, json={"result": {"target_room_id": "uuid-cr-004", "label": "linked"}}
            )
        )
        ref_route = respx_mock.post(
            "/agents/clerk-registered-id/ops/attach_reference_to_room"
        ).mock(return_value=httpx.Response(200, json={"result": {"ok": True}}))
        create_doc_route = respx_mock.post(
            "/agents/clerk-registered-id/ops/create_room_document"
        ).mock(return_value=httpx.Response(200, json={"result": {"document_id": "doc-123"}}))
        update_doc_route = respx_mock.post(
            "/agents/clerk-registered-id/ops/update_room_document"
        ).mock(
            return_value=httpx.Response(
                200, json={"result": {"document_id": "doc-123", "status": "ok"}}
            )
        )
        archive_route = respx_mock.post("/agents/clerk-registered-id/ops/archive_room").mock(
            return_value=httpx.Response(200, json={"result": {"archived": True}})
        )

        # 6. get_role_detail, assume_role, release_role, runtime-state, leases/renew
        role_detail_route = respx_mock.post(
            "/agents/clerk-registered-id/ops/get_role_detail"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "result": {
                        "name": "client-desk",
                        "exclusive": True,
                        "instructions": "Cover desk",
                        "held_by": [{"name": "acme-scout", "present_here": True}],
                        "assumable_by_me": False,
                    }
                },
            )
        )
        assume_route = respx_mock.post("/agents/clerk-registered-id/ops/assume_role").mock(
            return_value=httpx.Response(
                200, json={"result": {"role": "delivery-lead", "instructions": "..."}}
            )
        )
        release_route = respx_mock.post("/agents/clerk-registered-id/ops/release_role").mock(
            return_value=httpx.Response(200, json={"result": {"status": "released"}})
        )
        runtime_route = respx_mock.post("/agents/clerk-registered-id/runtime-state").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        lease_route = respx_mock.post("/agents/clerk-registered-id/leases/renew").mock(
            return_value=httpx.Response(200, json={"renewed": 1})
        )

        adapter = SwitchProtocolAdapter(
            base_url="http://switch.local",
            agent_id="initial-id",
            api_key="initial-key",
            rooms_config=config_bundle.rooms,
            clock=clock,
            connection_id="conn-ops-test",
        )

        # Register agent
        agent_id, api_key = await adapter.register_agent(registration_key="reg-boot-key")
        assert agent_id == "clerk-registered-id"
        assert api_key == "clerk-live-key"
        assert reg_route.called

        delivery_room = adapter.get_room_ref("acme-delivery")
        client_room = adapter.get_room_ref("acme-client")

        # Post message (triggers placement dict->list fallback)
        msg_ref = await adapter.post(delivery_room, "Morning brief ready.")
        assert msg_ref.id == "evt-post-1"
        assert len(placement_calls) == 2
        assert isinstance(placement_calls[0]["placements"], dict)
        assert isinstance(placement_calls[1]["placements"], list)
        post_req = post_route.calls.last.request
        assert post_req.headers["X-Switch-Connection-Id"] == "conn-ops-test"
        assert post_req.headers["X-Switch-Session-Id"] == f"sess-{delivery_room.id}"
        assert json.loads(post_req.content) == {"body": "Morning brief ready.", "thread_id": None}

        # Send targeted message (strips leading @ from target_names)
        targ_ref = await adapter.send_targeted(
            delivery_room,
            targets=["@acme-estimator", "acme-builder"],
            text="Estimate CR-004",
            target_roles=["@delivery-lead"],
        )
        assert targ_ref.id == "evt-targ-1"
        targ_payload = json.loads(targeted_route.calls.last.request.content)
        assert targ_payload == {
            "body": "Estimate CR-004",
            "target_names": ["acme-estimator", "acme-builder"],
            "target_roles": ["delivery-lead"],
            "thread_id": None,
        }

        # Create room, link, attach reference, upsert document twice (create then update), archive
        doc_spec = RoomDocumentSpec(
            name="cr-004-brief",
            description="CR-004 brief",
            instructions="Updated by Clerk",
            content="# CR-004 v1",
        )
        cr_room = await adapter.create_room(
            RoomSpec(
                name="acme-cr-004",
                description="Android app CR",
                agent_names=["@acme-estimator"],
                user_names=["@priya"],
                roles=[RoomRoleSpec(name="estimator", instructions="Size ask")],
                references=[Reference(id="ref-sow", title="SOW", url="config/sow/SOW.md")],
                docs=[doc_spec],
            )
        )
        assert cr_room.id == "uuid-cr-004"
        assert create_room_route.called
        assert create_doc_route.called

        # Second upsert updates existing document_id
        await adapter.upsert_document(
            cr_room,
            RoomDocumentSpec(
                name="cr-004-brief",
                description="CR-004 brief",
                instructions="Updated by Clerk",
                content="# CR-004 v2",
            ),
        )
        assert update_doc_route.called
        upd_payload = json.loads(update_doc_route.calls.last.request.content)
        assert upd_payload["document_id"] == "doc-123"
        assert upd_payload["content"] == "# CR-004 v2"

        await adapter.link(delivery_room, cr_room, "one change request")
        assert link_route.called

        await adapter.attach_reference(
            cr_room, Reference(id="ref-plan", title="Plan", url="config/plan.yaml")
        )
        assert ref_route.called

        # Role holder check on acme-client works via get_role_detail without joining acme-client
        holder = await adapter.role_holder(client_room, "@client-desk")
        assert holder == "acme-scout"
        assert role_detail_route.called

        # Assume & release role in acme-delivery
        await adapter.assume_role(delivery_room, "delivery-lead")
        assert assume_route.called
        renewed = await adapter.renew_leases()
        assert renewed == 1
        assert lease_route.called
        await adapter.release_role(delivery_room, "delivery-lead")
        assert release_route.called

        # Runtime state indicator
        await adapter.set_runtime_state(
            delivery_room, "working", detail="Classifying ASK-0007"
        )
        assert runtime_route.called
        rt_payload = json.loads(runtime_route.calls.last.request.content)
        assert rt_payload["room_id"] == delivery_room.id
        assert rt_payload["state"] == "working"
        assert rt_payload["detail"] == "Classifying ASK-0007"

        await adapter.archive_room(cr_room)
        assert archive_route.called
        await adapter.close()


@pytest.mark.asyncio
async def test_create_room_pool_fallback_and_guardrails(
    config_bundle: ConfigBundle,
    clock: SimulatedClock,
) -> None:
    """Verify pre-created room pool fallback on create_room error and acme-client guardrails."""
    async with respx.mock(base_url="http://switch.local") as respx_mock:
        respx_mock.post("/agents/clerk/connection/placements").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        respx_mock.post("/agents/clerk/ops/create_room").mock(
            return_value=httpx.Response(403, json={"detail": "Room creation disabled"})
        )
        invite_user_route = respx_mock.post("/agents/clerk/ops/add_users_to_room").mock(
            return_value=httpx.Response(200, json={"result": {"ok": True}})
        )
        invite_agent_route = respx_mock.post("/agents/clerk/ops/invite_agent_to_room").mock(
            return_value=httpx.Response(200, json={"result": {"ok": True}})
        )
        respx_mock.post("/agents/clerk/ops/post_message").mock(
            return_value=httpx.Response(429, json={"detail": "BudgetExceeded"})
        )

        adapter = SwitchProtocolAdapter(
            base_url="http://switch.local",
            agent_id="clerk",
            api_key="key",
            rooms_config=config_bundle.rooms,
            clock=clock,
        )

        # 1. Guardrail: Clerk cannot touch acme-client
        client_room = adapter.get_room_ref("acme-client")
        with pytest.raises(PermissionError, match="acme-client"):
            await adapter.post(client_room, "Hello client")
        with pytest.raises(PermissionError, match="acme-client"):
            await adapter.send_targeted(client_room, ["sam"], "Hello")
        with pytest.raises(PermissionError, match="acme-client"):
            await adapter.read_context(client_room)
        with pytest.raises(PermissionError, match="acme-client"):
            await adapter.assume_role(client_room, "client-desk")
        with pytest.raises(PermissionError, match="acme-client"):
            await adapter.set_runtime_state(client_room, "working")

        # 2. Guardrail: acknowledgement-only message rejected
        delivery_room = adapter.get_room_ref("acme-delivery")
        with pytest.raises(ValueError, match="acknowledgement-only"):
            await adapter.post(delivery_room, "ok!")

        # 3. BudgetExceeded (HTTP 429) mapped to SwitchBudgetExceededError
        with pytest.raises(SwitchBudgetExceededError):
            await adapter.post(delivery_room, "Real message")

        # 4. create_room falls back to pre-created pool and invites members
        fallback_ref = await adapter.create_room(
            RoomSpec(
                name="acme-cr-004",
                description="Fallback test",
                agent_names=["acme-estimator"],
                user_names=["priya"],
            )
        )
        assert fallback_ref.name == "acme-cr-004"
        assert invite_user_route.called
        assert invite_agent_route.called
        await adapter.close()


@pytest.mark.asyncio
async def test_consumer_worker_answers_clerk_status_over_protocol_adapter(
    config_bundle: ConfigBundle,
    clock: SimulatedClock,
) -> None:
    """Verify SwitchConsumerWorker consumes WS event, reports runtime-state, and replies."""
    conn = FakeWebSocketConnection(
        [
            {
                "event": "connection_state",
                "data": {"generation": 1, "cursor": 1, "rooms": ["room-acme-delivery"]},
            },
            {
                "event": "message",
                "id": 2,
                "data": {
                    "type": "message",
                    "room_id": "room-acme-delivery",
                    "sequence": 2,
                    "payload": {
                        "sender": "user-priya",
                        "sender_name": "priya",
                        "sender_kind": "user",
                        "message_id": "msg-status-1",
                        "body": "@clerk status CR-003",
                        "timestamp": 1762349400000,
                    },
                },
            },
            0.05,
            {"event": "evicted", "data": {"code": "taken_over", "reason": "done"}},
        ]
    )
    ws_factory = ScriptedWebSocketFactory([conn])

    engine = create_db_engine("sqlite:///:memory:")
    reset_and_seed_db(engine, config_bundle.seed_ledger, config_bundle.plan)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=config_bundle.plan)

    async with respx.mock(base_url="http://switch.local") as respx_mock:
        respx_mock.post("/agents/clerk/connection/placements").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        rt_route = respx_mock.post("/agents/clerk/runtime-state").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        post_route = respx_mock.post("/agents/clerk/ops/post_message").mock(
            return_value=httpx.Response(200, json={"result": {"event_id": "evt-reply-1"}})
        )

        adapter = SwitchProtocolAdapter(
            base_url="http://switch.local",
            agent_id="clerk",
            api_key="key",
            rooms_config=config_bundle.rooms,
            clock=clock,
            ws_factory=ws_factory,
        )
        orchestrator = WorkflowOrchestrator(
            config=config_bundle,
            repo=repo,
            switch=adapter,
            llm=ScriptedLLM(),
            git_host=LocalGitHost(),
            preview=FakePreview(),
            clock=clock,
        )
        worker = SwitchConsumerWorker(
            switch=adapter,
            orchestrator=orchestrator,
            poll_interval_seconds=0.0,
        )
        await worker.start()
        await asyncio.sleep(0.12)
        await worker.stop()

    assert rt_route.call_count >= 2
    states_sent = [json.loads(c.request.content)["state"] for c in rt_route.calls]
    assert "working" in states_sent
    assert states_sent[-1] == "idle"
    assert post_route.called
    reply_body = json.loads(post_route.calls.last.request.content)["body"]
    assert "CR-003" in reply_body
