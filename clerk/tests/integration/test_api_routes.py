"""Integration tests for all Section 10 FastAPI routes, CORS, auth, and SSE stream."""

from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest

from clerk.adapters.clock import SimulatedClock
from clerk.adapters.llm_scripted import ScriptedLLM
from clerk.adapters.local_git import LocalGitHost
from clerk.adapters.preview_local import FakePreview
from clerk.adapters.switch_inmemory import InMemorySwitch
from clerk.db.repositories import LedgerRepository
from clerk.db.session import create_db_engine, create_session_factory, reset_and_seed_db
from clerk.domain.models import Confidence, Estimate, EstimateVersion
from clerk.main import create_app
from clerk.settings import ConfigBundle, Settings

IST = ZoneInfo("Asia/Kolkata")


@pytest.mark.asyncio
async def test_all_section_10_api_routes_cors_and_sse(
    config_bundle: ConfigBundle,
    tmp_path: Path,
) -> None:
    """Verify every Section 10 REST endpoint, camelCase data contract, CORS, and SSE stream."""
    import dataclasses
    import shutil

    temp_cfg_dir = tmp_path / "config"
    shutil.copytree(config_bundle.config_dir, temp_cfg_dir)
    test_bundle = dataclasses.replace(config_bundle, config_dir=temp_cfg_dir)

    clock = SimulatedClock("2026-11-05T19:00:00+05:30")
    engine = create_db_engine("sqlite:///:memory:")
    reset_and_seed_db(engine, test_bundle.seed_ledger, test_bundle.plan)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=test_bundle.plan)

    switch = InMemorySwitch(rooms_config=test_bundle.rooms, clock=clock)
    await switch.connect()

    settings = Settings(admin_token="test-secret-token", demo_mode=True)
    app = create_app(
        settings=settings,
        config=test_bundle,
        repo=repo,
        switch=switch,
        llm=ScriptedLLM(),
        git_host=LocalGitHost(),
        preview=FakePreview(),
        clock=clock,
        start_workers=False,
    )

    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": "Bearer test-secret-token"}

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. GET /api/health (no auth required) & CORS preflight for http://localhost:5173
        health_resp = await client.get(
            "/api/health", headers={"Origin": "http://localhost:5173"}
        )
        assert health_resp.status_code == 200
        assert health_resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
        health_data = health_resp.json()
        assert health_data["status"] == "ok"
        assert health_data["switchConnected"] is True

        # 2. Protected route without token returns 401 with standard error envelope
        unauth_resp = await client.get("/api/overview")
        assert unauth_resp.status_code == 401
        assert unauth_resp.json()["error"]["code"] == "unauthorized"

        # 3. GET /api/overview (camelCase KPIs)
        ov_resp = await client.get("/api/overview?month=2026-11", headers=headers)
        assert ov_resp.status_code == 200
        ov = ov_resp.json()
        assert ov["revenueProtectedCents"] == 189000
        assert ov["goodwill"]["usedHours"] == 2.0
        assert ov["goodwill"]["bucketHours"] == 8.0

        # 4. GET /api/desk
        desk_resp = await client.get("/api/desk", headers=headers)
        assert desk_resp.status_code == 200
        desk = desk_resp.json()
        assert desk["holder"] in {"priya", "scout"}
        assert "nextHandoverAt" in desk
        assert "clockIst" in desk
        assert "clockEt" in desk

        # 5. GET /api/asks & GET /api/asks/{id}
        asks_resp = await client.get("/api/asks", headers=headers)
        assert asks_resp.status_code == 200
        asks = asks_resp.json()
        assert len(asks) == 6
        assert "createdAt" in asks[0]

        ask_detail_resp = await client.get("/api/asks/ASK-0006", headers=headers)
        assert ask_detail_resp.status_code == 200
        ask_detail = ask_detail_resp.json()
        assert ask_detail["id"] == "ASK-0006"
        assert "events" in ask_detail

        # 6. POST /api/asks/{id}/goodwill
        orch = app.state.orchestrator
        new_ask = repo.create_ask(
            quote="Add a small tooltip on the export button",
            requester="Sam",
            created_at=clock.now().isoformat(),
        )
        gw_resp = await client.post(
            f"/api/asks/{new_ask.id}/goodwill",
            headers=headers,
            json={"hours": 1.0, "reason": "Quick UI polish"},
        )
        assert gw_resp.status_code == 200
        assert gw_resp.json()["status"] == "accepted"
        delivery_msgs = [m.text for m in switch.messages_in("acme-delivery")]
        assert any("goodwill" in m.lower() for m in delivery_msgs)

        # 7. Open CR-004, estimate, confirm, override price, approve from dashboard
        oos_ask = repo.create_ask(
            quote="We need an Android app for the board meeting on the 20th",
            requester="Sam",
            created_at=clock.now().isoformat(),
        )
        cr = await orch.cr_service.open_change_request(oos_ask)
        est = Estimate(
            full=EstimateVersion(p50_hours=190, p90_hours=240, confidence=Confidence.MEDIUM),
            smaller=EstimateVersion(
                title="Board-meeting version: view-only dashboards",
                p50_hours=56,
                p90_hours=64,
                confidence=Confidence.HIGH,
            ),
            posted_at=clock.now().isoformat(),
        )
        await orch.cr_service.handle_estimate(cr.id, est)
        await orch.cr_service.confirm_hours(cr.id, hours=200, confirmed_by="ravi")

        crs_resp = await client.get("/api/change-requests", headers=headers)
        assert crs_resp.status_code == 200
        assert any(item["id"] == cr.id for item in crs_resp.json())

        cr_detail_resp = await client.get(f"/api/change-requests/{cr.id}", headers=headers)
        assert cr_detail_resp.status_code == 200
        assert cr_detail_resp.json()["confirmedHours"] == 200

        # PATCH /api/change-requests/{id}/options/A
        patch_resp = await client.patch(
            f"/api/change-requests/{cr.id}/options/A",
            headers=headers,
            json={"priceCents": 980000},
        )
        assert patch_resp.status_code == 200
        opts_after_patch = patch_resp.json()["options"]
        assert opts_after_patch[0]["priceCents"] == 980000

        # POST /api/change-requests/{id}/approve -> posts dashboard approval
        app_resp = await client.post(
            f"/api/change-requests/{cr.id}/approve",
            headers=headers,
            json={"options": ["A", "C", "D"]},
        )
        assert app_resp.status_code == 200
        cr_room_msgs = [m.text for m in switch.messages_in(cr.room.room)]
        assert any("Priya approved A, C, D from the dashboard" in t for t in cr_room_msgs)

        # 8. GET /api/public/co/{id} (no auth required!)
        pub_resp = await client.get(f"/api/public/co/{cr.id}")
        assert pub_resp.status_code == 200
        pub_data = pub_resp.json()
        assert pub_data["id"] == cr.id
        assert pub_data["clientCompany"] == "Acme Inc."
        assert pub_data["agencyCompany"] == "Pixel & Co"

        # 9. POST /api/change-requests/{id}/decline on a second CR
        oos_ask2 = repo.create_ask(
            quote="Build a VR headset client",
            requester="Sam",
            created_at=clock.now().isoformat(),
        )
        cr2 = await orch.cr_service.open_change_request(oos_ask2)
        dec_resp = await client.post(
            f"/api/change-requests/{cr2.id}/decline",
            headers=headers,
            json={"reason": "Out of agency domain"},
        )
        assert dec_resp.status_code == 200
        assert dec_resp.json()["status"] == "closed"

        # 10. GET /api/rooms, /api/ledger, /api/invoice, /api/renewal
        rooms_resp = await client.get("/api/rooms", headers=headers)
        assert rooms_resp.status_code == 200
        assert len(rooms_resp.json()["rooms"]) >= 3

        ledger_resp = await client.get("/api/ledger?month=2026-11", headers=headers)
        assert ledger_resp.status_code == 200
        assert "entries" in ledger_resp.json()

        inv_resp = await client.get("/api/invoice?month=2026-11", headers=headers)
        assert inv_resp.status_code == 200
        assert "date,change,option,hours,price_usd,approved_by,link" in inv_resp.text

        ren_resp = await client.get("/api/renewal", headers=headers)
        assert ren_resp.status_code == 200
        assert "report" in ren_resp.json()

        # 11. GET & PUT /api/config/{name}
        cfg_get = await client.get("/api/config/rate-card", headers=headers)
        assert cfg_get.status_code == 200
        rc_data = cfg_get.json()
        assert float(rc_data["blendedRate"]) == 45.0

        cfg_put = await client.put(
            "/api/config/rate-card",
            headers=headers,
            json={"config": rc_data, "note": "Verified Q4 rate card"},
        )
        assert cfg_put.status_code == 200
        assert any("Verified Q4 rate card" in d.text for d in repo.list_decisions())

        # 12. Demo controls: /api/demo/flip, /api/demo/morning, /api/demo/clock
        flip_resp = await client.post("/api/demo/flip", headers=headers)
        assert flip_resp.status_code == 200

        morn_resp = await client.post("/api/demo/morning", headers=headers)
        assert morn_resp.status_code == 200

        clk_resp = await client.post(
            "/api/demo/clock",
            headers=headers,
            json={"offset": "+2h"},
        )
        assert clk_resp.status_code == 200
        assert "21:00:00" in clk_resp.json()["clock"]

        # 13. GET /api/stream (SSE with max_events=2 so stream closes after 2 events)
        stream_resp = await client.get(
            "/api/stream?limit=2&max_events=2",
            headers=headers,
        )
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers["content-type"]
        assert "data:" in stream_resp.text
