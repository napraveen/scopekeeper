# Switch Agent Protocol — Verified Notes

**Verified on:** 2026-11-04  
**Sources:**
- Official Switch repository: [`github.com/sandbox-quantum/switch`](https://github.com/sandbox-quantum/switch)
  - `core/switch_core/bridges/agent/api/handlers.py`
  - `core/switch_core/bridges/agent/api/operations.py`
  - `core/switch_core/bridges/agent/api/schemas.py`
  - `core/switch_core/bridges/agent/operations/registry.py`
  - `core/switch_core/bridges/agent/operations/definitions.py`
  - `core/switch_core/bridges/agent/operations/context.py`
  - `core/switch_core/bridges/agent/operations/callctx.py`
  - `core/switch_core/bridges/agent/protocol/stream.py`
  - `core/switch_core/bridges/agent/protocol/agent_connections.py`
  - `core/switch_core/bridges/agent/protocol/liveness.py`
  - `core/switch_core/bridges/agent/protocol/types.py`
  - `docs/TEMPLATES.md`
- Official Switch documentation: [`docs.switchagents.ai`](https://docs.switchagents.ai/)

---

## 1. Agent Registration & Authentication

- **Endpoint:** `POST /agents`
  - **Source:** `core/switch_core/bridges/agent/api/handlers.py` (`register_agent_endpoint`), `schemas.py` (`RegisterAgentRequest`, `RegisterAgentResponse`)
  - **Headers:** `Authorization: Bearer <SWITCH_REGISTRATION_KEY>` (registration or bootstrap key)
  - **Request Body (`RegisterAgentRequest`):**
    ```json
    {
      "name": "clerk",
      "description": "ScopeKeeper contract, pricing, ledger, and handover service",
      "display_name": "Clerk",
      "icon_url": null,
      "connector_type": "custom",
      "integration_profile": {
        "connection_model": "always_on",
        "message_exchange": true,
        "pre_invocation_mediation": [],
        "post_invocation_mediation": [],
        "event_reporting": [],
        "command_capabilities": {
          "reset": "unsupported",
          "compact": "unsupported",
          "interrupt": "unsupported"
        }
      },
      "tools": [],
      "models": [],
      "metadata": {},
      "overwrite": true
    }
    ```
  - **Response (`RegisterAgentResponse`):**
    ```json
    {
      "id": "<agent-uuid>",
      "api_key": "<agent-api-key>"
    }
    ```
  - **Subsequent Requests:** All agent API, WebSocket, and operation calls authenticate with `Authorization: Bearer <agent_api_key>`.

---

## 2. Primary Event Stream & Heartbeat (WebSocket)

- **Endpoint:** `GET /agents/{agent_id}/connection/ws` (WebSocket upgrade)
  - **Source:** `core/switch_core/bridges/agent/api/handlers.py` (`connection_socket`), `protocol/stream.py`, `protocol/agent_connections.py`, `protocol/liveness.py`
  - **Query Parameters:**
    - `connection_id` *(required)*: Client-generated UUID string (`<= 64` chars). Reused across reconnects so room slots and role leases survive brief drops.
    - `scope`: `"single"` or `"all"` (Clerk uses `"all"` to monitor `acme-intake`, `acme-delivery`, and all `acme-cr-NNN` rooms on one connection).
    - `filter`: `"all"` or `"addressed"` (Clerk uses `"all"`).
    - `rooms`: Optional comma-separated list of Switch room UUIDs to claim on connect (`takeover=True`).
    - `start_from`: `"head"` or integer sequence/ticket number string (default `"head"`).
    - `start_at`: Optional position JSON/string for protocol revision 9+.
    - `expected_generation`: Optional integer incarnation number from the previous `connection_state` frame to fence reattachments.
    - `spawn_capable`: Boolean (default `false`).
    - `protocol`, `protocol_accepts`, `client`, `client_version`: Optional client declaration fields.

### Server-to-Client WebSocket Frames (`encode_ws`)

Every server frame is JSON: `{"event": "<type>", "data": {...}, "id": <optional int seq>}`.

1. **`connection_state`** (sent immediately upon opening):
   ```json
   {
     "event": "connection_state",
     "data": {
       "connection_id": "<uuid>",
       "agent_id": "<agent_id>",
       "generation": 1,
       "scope": "all",
       "filter": "all",
       "spawn_capable": false,
       "rooms": ["<room_id_1>", "<room_id_2>"],
       "cursor": 42,
       "position": {"s": 42, "r:<room_id_1>": 10},
       "protocol": 9,
       "heartbeat_interval_seconds": 2.0,
       "server": {"version": "0.31.0", "speaks": 9, "accepts": 1},
       "client": {}
     }
   }
   ```
2. **`ping`** (sent every `heartbeat_interval_seconds`: 2s in Switch 0.31 / 10s in latest `main`; TTL is 3 intervals = 6s in 0.31 / 30s in `main`):
   ```json
   {"event": "ping", "data": {}}
   ```
   - **Client Reply Requirement:** Client **must** run an independent async task that immediately replies:
     ```json
     {"type": "pong", "cursor": 42}
     ```
     Verified in `_receive_pongs` (`handlers.py` line 324): `message.get("type") == "pong"`. Running this on an independent task ensures slow LLM or git calls never block the pong and never trigger `heartbeat_lapsed`.
3. **`gap`** (sent when requested cursor expired or missed events occurred):
   ```json
   {
     "event": "gap",
     "data": {
       "from_sequence": 10,
       "to_sequence": 25,
       "rooms": ["<room_id>"],
       "all_rooms": false,
       "reason": "..."
     }
   }
   ```
   - **Client Action:** Call `read_context` for affected rooms before acting.
4. **`subscription_changed`**:
   ```json
   {
     "event": "subscription_changed",
     "data": {"rooms": ["..."], "reason": "subscription updated"}
   }
   ```
5. **`room_released`**:
   ```json
   {
     "event": "room_released",
     "data": {"room_id": "<room_id>", "session_id": "<session_id>"}
   }
   ```
6. **`evicted`**:
   ```json
   {
     "event": "evicted",
     "data": {
       "code": "taken_over",
       "reason": "another stream attached to this connection and took it over",
       "room_id": null
     }
   }
   ```
   - **Close codes (`CloseCode`):** `"taken_over"`, `"heartbeat_lapsed"`, `"closed"`, `"launch_superseded"`.
   - **Client Action:** On `code == "taken_over"`, stop immediately and **do not reconnect** (reconnecting would endlessly fight the new connection). On `"heartbeat_lapsed"`, reconnect with exponential backoff + jitter using `start_from` and `expected_generation`.
7. **`refused`** (when connection open fails validation/fencing):
   ```json
   {
     "event": "refused",
     "data": {"status": 409, "detail": {...}}
   }
   ```
   Followed by WebSocket close code `4000 + status`.
8. **Room Events (`message`, `command`, `room_join`)**:
   - **Source:** `core/switch_core/bridges/agent/protocol/types.py` (`AgentEvent`, `MessagePayload`, `CommandPayload`, `RoomJoinPayload`)
   ```json
   {
     "event": "message",
     "id": 105,
     "data": {
       "type": "message",
       "room_id": "<room_id>",
       "bridge_id": "<bridge_id>",
       "channel_type": "channel_public",
       "sequence": 105,
       "position": {"r:<room_id>": 19},
       "missed": {"count": 0, "reason": null},
       "payload": {
         "addressed": true,
         "sender": "user-priya-id",
         "sender_name": "priya",
         "sender_kind": "user",
         "on_behalf_of": null,
         "message_id": "msg-001",
         "body": "@clerk approve A,C,D",
         "timestamp": 1762402200000,
         "thread_id": null,
         "attachments": [],
         "opening_message": null,
         "sender_role": "owner",
         "switch_notice": null
       }
     }
   }
   ```

### Deprecated SSE Fallback

- `GET /agents/{agent_id}/events` with header `Accept: text/event-stream` and same query parameters as `/connection/ws`.
- Heartbeat via `POST /agents/{agent_id}/connection/beat` with body `{"connection_id": "<uuid>", "generation": 1}`.

---

## 3. Room Session Placements & Operations Dispatch

### Session Placements (`POST /agents/{agent_id}/connection/placements`)

- **Source:** `core/switch_core/bridges/agent/api/handlers.py` (`connection_placements`), `schemas.py` (`ConnectionPlacementsRequest`), `operations/operations.py` (`resolve_caller`)
- Many operations (`post_message`, `send_targeted_message`, `list_participants`, `list_roles`, `define_role`, `assume_role`, `release_role`, `create_room_document`, `update_room_document`, `load_internal_documents`) do **not** take a `room_id` parameter in their JSON body; they resolve their target room from the caller's session placement via `require_connected_room()`.
- **Note on `placements` payload shape across Switch 0.31 and latest `main`:**
  - In `core/switch_core/bridges/agent/api/schemas.py` (`ConnectionPlacementsRequest`), `placements` is `dict[str, str]` mapping `{session_id: room_id}`:
    ```json
    {
      "connection_id": "<conn_id>",
      "placements": {"sess-<room_id>": "<room_id>"},
      "generation": 1
    }
    ```
  - In `BUILD_PROMPT.md` section 8.3 (written against an earlier 0.31 draft), `placements` is shown as a list `[{"session_id": "sess-<room_id>", "room_id": "<room_id>"}]`.
  - **Adapter handling:** `SwitchProtocolAdapter` sends `{"connection_id": conn_id, "placements": {f"sess-{room_id}": room_id}, "generation": generation}` by default, and if the server responds with `HTTP 422`/`400` expecting a list, automatically retries with the list shape `[{"session_id": f"sess-{room_id}", "room_id": room_id}]` (or `connect_to_room`).

### Operations Endpoint (`POST /agents/{agent_id}/ops/{operation}`)

- **Source:** `core/switch_core/bridges/agent/api/operations.py` (`post_operation`, `call_operation`), `operations/registry.py`
- **Headers:**
  - `Authorization: Bearer <CLERK_API_KEY>`
  - `X-Switch-Connection-Id: <conn_id>`
  - `X-Switch-Session-Id: sess-<room_id>` (when calling a room-scoped operation)
- **Argument Validation:** `call_operation` inspects `inspect.signature(fn)` and rejects any unknown argument key with `HTTP 400` (`BadArgumentsError: "<op> does not accept: ..."`).
- **Response Wrapper:** `{"result": <return_value>}`
- **Error HTTP Status Mapping (`refusal_status`):**
  - `400`: `BadArgumentsError` or `ValueError`
  - `403`: `PermissionError`
  - `404`: `UnknownOperationError`
  - `409`: `UnknownConnectionError`
  - `422`: `GuardrailBlockedError`
  - `429`: `BudgetExceeded`

### Verified Operation Signatures (`core/switch_core/bridges/agent/operations/definitions.py`)

| Operation | Exact Arguments (`additionalProperties: false`) | Room Source | Verified Return Shape (`result`) |
| :--- | :--- | :--- | :--- |
| `list_rooms` | `{"include_archived": false}` | Agent-wide | `[{"room_id", "name", "description", "connected", "archived"}]` |
| `connect_to_room` | `{"room_id": "<uuid>", "include_general_instructions": true}` | Explicit `room_id` | `{"agent_id", "room_id", "name", "description", "participants", "instructions", "references", "documents", "linked_rooms", "roles", "warning"}` |
| `post_message` | `{"body": "<text>", "thread_id": null}` | Session placement | `{"event_id": "<id>"}` |
| `send_targeted_message` | `{"body": "<text>", "target_names": ["acme-estimator"], "target_roles": [], "thread_id": null}` | Session placement | `{"event_id": "<id>", "target_statuses": {"acme-estimator": "live"}}` *(Pass bare names without `@`)* |
| `read_context` | `{"limit": 50, "since": "<iso8601>", "before": "<iso8601>", "room_id": "<uuid>"}` | Explicit `room_id` or placement | `{"threads": [{"root": {...}, "replies": [...]}], "truncated": false, "oldest_timestamp": 1762402200000}` |
| `list_participants` | `{}` | Session placement | `[{"id", "name", "type", "status", "alias"}]` *(Also `GET /agents/rooms/{room_id}/participants`)* |
| `create_room` | `{"name": "...", "description": "...", "agent_names": [...], "user_names": [...], "channel_type": "channel_public", "bridge_id": null, "internal_only": false, "admin_mode": false, "instructions": "...", "reference_ids": [...], "linked_rooms": [{"target_room_id": "...", "label": "..."}], "group_name": "Acme Web Portal", "roles": [{"name": "...", "instructions": "...", "exclusive": false}]}` | Agent-wide | `{"id", "name", "transport_room_id", "matrix_room_id", "caller_is_member", "failed_attachments"}` |
| `archive_room` | `{"room_id": "<uuid>"}` | Explicit `room_id` | Full `RoomDetailDescriptor` dict (`archived: true`) |
| `invite_agent_to_room` | `{"room_id": "<uuid>", "agent_name": "<name>", "include_subagents": false}` | Explicit `room_id` | `{"ok": true}` |
| `add_users_to_room` | `{"room_id": "<uuid>", "user_names": ["priya", "ravi"]}` | Explicit `room_id` | `{"ok": true, "added": [...], "unresolved": []}` |
| `link_rooms` | `{"source_room_id": "<uuid_a>", "target_room_id": "<uuid_b>", "label": "..."}` | Explicit room IDs | `{"target_room_id", "target_room_name", "target_room_description", "label"}` |
| `list_reference_types` | `{}` | Agent-wide | `[{"type", "display_name", "instructions", "value_schema", "value_hint", "origin"}]` |
| `create_reference` | `{"type": "...", "name": "...", "description": "...", "instructions": "...", "value": {"urls": ["..."]}, "read_visibility": "private", "write_visibility": "private"}` | Agent-wide | `{"id", "type", "name", "read_visibility", "write_visibility"}` |
| `attach_reference_to_room` | `{"room_id": "<uuid>", "reference_id": "<ref_id>"}` | Explicit `room_id` | `{"ok": true}` |
| `create_room_document` | `{"name": "...", "description": "...", "instructions": "...", "content": "..."}` | Session placement | `{"document_id": "<doc_id>"}` |
| `update_room_document` | `{"document_id": "<doc_id>", "name": null, "description": null, "instructions": null, "content": "..."}` | Session placement | `{"document_id": "<doc_id>", "status": "ok"}` |
| `load_internal_documents` | `{"ids": ["<doc_id>"]}` | Session placement | `[{"id", "description", "content"}]` |
| `list_roles` | `{}` | Session placement | `[{"name", "exclusive", "instructions_preview", "assumable_by_me", "held_by": [{"name", "present_here", "session_room"}]}]` |
| `get_role_detail` | `{"room_id": "<uuid>", "role_name": "client-desk"}` | Explicit `room_id` | `{"name", "exclusive", "instructions", "held_by": [{"name": "acme-scout", "present_here": true, "session_room": "..."}], "assumable_by_me": true}` |
| `define_role` | `{"name": "client-desk", "instructions": "...", "exclusive": true}` | Session placement | `{"status": "defined", "name": "client-desk"}` |
| `assume_role` | `{"role": "client-desk"}` | Session placement | `{"role": "client-desk", "instructions": "..."}` |
| `release_role` | `{}` | Session placement | `{"status": "released"}` |
| `create_room_group` | `{"name": "Acme Web Portal", "description": "...", "color": "#4F46E5", "parent_group_name": null}` | Agent-wide | `{"id", "name", "description", "color", "parent_group_id", "room_count", "path", "member_rooms", "child_groups"}` |
| `update_agent_detail` | `{"agent_id": "<uuid>", "addressing": "anyone", "instructions": "..."}` | Explicit `agent_id` | Agent detail dict + `"addressing"` + `"managed"` |
| `get_template_guide` | `{}` | Agent-wide | `{"guide": "...", "schema": {...}}` |
| `save_template` | `{"name": "...", "description": "...", "yaml": "...", "visibility": "private", "bypass_warnings": false}` | Agent-wide | `{"id", "name", "kind", "visibility", "warnings"}` |

---

## 4. Direct HTTP Endpoints (`core/switch_core/bridges/agent/api/handlers.py`)

1. **Direct Message Send (alternative to `ops/post_message`):**
   - `POST /agents/{agent_id}/message`
   - Body (`SendMessageRequest`): `{"room_id": "<uuid>", "content": "<text>", "metadata": {}}`
2. **Role Lease Renewal:**
   - `POST /agents/{agent_id}/leases/renew`
   - Header: `X-Switch-Connection-Id: <conn_id>`
   - Response: `{"renewed": <int>}`
3. **Live Runtime State Indicator:**
   - `POST /agents/{agent_id}/runtime-state`
   - Body (`RuntimeStateRequest`):
     ```json
     {
       "room_id": "<uuid>",
       "state": "working",
       "thread_id": null,
       "anchor_event_id": null,
       "deeplink_url": null,
       "detail": "Classifying ASK-0007 against SOW v1.2",
       "control_capabilities": null
     }
     ```
4. **Room Participants Lookup:**
   - `GET /agents/rooms/{room_id}/participants`
   - Response (`ParticipantsResponse`):
     ```json
     {
       "participants": [
         {"type": "user", "agent_id": null, "name": "priya", "status": null},
         {"type": "agent", "agent_id": "<uuid>", "name": "clerk", "status": "live"}
       ]
     }
     ```

---

## 5. Templates Specification (`docs/TEMPLATES.md`)

- Verified `version: 1` group template structure for `switch/templates/scopekeeper.template.yaml`:
  - Top-level keys: `version: 1`, `params:`, `agents:`, `group:`, `rooms:`, `links:`, `form:`.
  - Every entry in `agents:` must declare `name`, `display_name`, `description`, `provider` (`opencode`, `claude`, `codex`), `location` (`local` or `{location}`), `directory` (`{$agents_dir}/...` or `{repo_dir}`), `addressing` (`anyone` or `owner-agents`), `allow_existing: true`, and `instructions`.
  - `group:` declares `name: "Acme Web Portal"`, `description`, and `color: "#4F46E5"`.
  - `rooms:` lists `acme-client`, `acme-intake`, and `acme-delivery` with `name`, `description`, `bridge`, `channel_type`, `instructions`, `agents`, `users`, `roles`, and `docs`.
  - `links:` lists bidirectional `{from, to, label}` entries between `acme-client` ↔ `acme-intake` and `acme-intake` ↔ `acme-delivery`.
