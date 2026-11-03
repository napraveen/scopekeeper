# Switch Setup Guide — ScopeKeeper

This guide walks through configuring **Switch Console (0.40+)** and **Switch Core (0.31+)** for ScopeKeeper's multi-app, multi-vendor workflow across **Discord** (client desk) and **Slack** (agency workspace).

> **Fast Path (One-Click Template Import):** After completing Steps 1 and 5 (bridges + registering the `clerk` custom agent), you can import [`switch/templates/scopekeeper.template.yaml`](../switch/templates/scopekeeper.template.yaml) directly in Switch Console (**Templates → Import YAML**) to provision Steps 2, 3, 6, and 7 automatically.

---

## Step 1: Install Switch Console, Start the Server, and Connect Bridges

1. **What to click / run:**
   - Install and launch **Switch Console 0.40+** and start the local Switch server (default `http://localhost:8000`, WebSocket `ws://localhost:8000`).
   - In Switch Console, open **Settings → Bridges** and connect:
     - **Discord Bridge** (connected to the client Discord server where Sam is a member).
     - **Slack Bridge** (connected to Pixel & Co.'s agency Slack workspace where Priya, Ravi, and Aisha are members).
   - *Fallback:* If Slack or Discord is unavailable in an offline environment, connect **Mattermost** with two teams (`acme-external` and `pixel-internal`).
2. **What to check after this step:**
   - Both bridges show a green **Connected** badge in Switch Console.
   - `GET http://localhost:8000/health` returns `200 OK`.

---

## Step 2: Create the `"Acme Web Portal"` Room Group and Three Core Rooms

1. **What to click / run:**
   - In Switch Console, click **Room Groups → New Group**:
     - **Name:** `Acme Web Portal`
     - **Color:** `#4F46E5`
   - Create the three rooms inside `Acme Web Portal` and paste each room's instructions from `switch/rooms/`:
     1. **`acme-client`** (Bridge: **Discord**, Channel Type: `channel_public`) — paste [`switch/rooms/acme-client.md`](../switch/rooms/acme-client.md).
     2. **`acme-intake`** (Bridge: **Slack**, Channel Type: `channel_public`) — paste [`switch/rooms/acme-intake.md`](../switch/rooms/acme-intake.md).
     3. **`acme-delivery`** (Bridge: **Slack**, Channel Type: `channel_public`) — paste [`switch/rooms/acme-delivery.md`](../switch/rooms/acme-delivery.md).
   - *(Optional fallback pool)* If dynamic room creation is restricted on your Slack bridge, pre-create `acme-cr-001` through `acme-cr-005` using [`switch/rooms/acme-cr.md`](../switch/rooms/acme-cr.md).
   - Copy the Switch Room UUIDs for `acme-client`, `acme-intake`, and `acme-delivery` into [`config/rooms.yaml`](../config/rooms.yaml).
2. **What to check after this step:**
   - All three rooms appear under the **Acme Web Portal** group in Switch Console and are bridged to their respective Discord/Slack channels.
   - `config/rooms.yaml` has the room IDs and human handles (`sam`, `priya`, `ravi`, `aisha`).

---

## Step 3: Add Console Agents (Scout, Estimator, Builder) and Configure Addressing

1. **What to click / run:**
   - In Switch Console, open **Agents → New Agent** and create the three coding/desk agents:
     1. **Scout (`acme-scout`):**
        - **Provider:** `OpenCode`
        - **Working Directory:** `{$agents_dir}/acme-scout`
        - **Addressing Policy (`update_agent_detail`):** `anyone` (**Anyone**) so external client users (Sam on Discord) and any room participant can reach Scout.
        - **Instructions:** Paste [`switch/agents/scout.md`](../switch/agents/scout.md).
        - **Rooms:** Add to `acme-client` and `acme-intake` **only** (never `acme-delivery`).
     2. **Estimator (`acme-estimator`):**
        - **Provider:** `Claude Code`
        - **Working Directory:** `./demo-app/acme-portal` (read-only permissions; never edits files)
        - **Addressing Policy:** `owner_and_owner_agents` (`owner-agents` in templates) so only the agency owner and Clerk can instruct it.
        - **Instructions:** Paste [`switch/agents/estimator.md`](../switch/agents/estimator.md).
        - **Rooms:** Add to `acme-delivery` (Clerk invites it to `acme-cr-NNN` change rooms dynamically).
     3. **Builder (`acme-builder`):**
        - **Provider:** `Codex`
        - **Working Directory:** `./demo-app/acme-portal` (branch-only; `pre-push` hook blocks `main`)
        - **Addressing Policy:** `owner_and_owner_agents` (`owner-agents` in templates).
        - **Instructions:** Paste [`switch/agents/builder.md`](../switch/agents/builder.md).
        - **Rooms:** Add to `acme-delivery` (and `acme-cr-NNN` change rooms).
2. **What to check after this step:**
   - All three agents show **Live** status in Switch Console.
   - Verify addressing: `acme-scout` is set to **Anyone** (`anyone`), while `acme-estimator` and `acme-builder` are set to **Owner & Owner Agents** (`owner_and_owner_agents`).
   - *Gotcha:* Remember that edited room or agent instructions reach Console agents only after they reconnect—click **Reconnect** on each agent if you edit instructions later.

---

## Step 4: Assign Scout as the Main Agent in `acme-client`

1. **What to click / run:**
   - In the Discord channel bridged to `acme-client` (or the Switch Console room chat for `acme-client`), run the Switch bridge commands:
     ```text
     !assign-agent @acme-scout
     !follow-ups on
     ```
2. **What to check after this step:**
   - Switch confirms that `@acme-scout` is the assigned room agent with follow-ups enabled, so unaddressed messages from Sam in Discord are routed to Scout during autopilot shifts without Sam needing to type `@acme-scout`.

---

## Step 5: Register Clerk as a Custom Agent (`POST /agents`)

1. **What to click / run:**
   - Generate a Registration API Key in Switch Console (**Settings → API Keys → Registration Key**) and set `SWITCH_REGISTRATION_KEY` in `.env`.
   - Register **Clerk** via `POST /agents` (or let `SwitchProtocolAdapter.register_agent` register on startup):
     ```bash
     curl -X POST http://localhost:8000/agents \
       -H "Authorization: Bearer $SWITCH_REGISTRATION_KEY" \
       -H "Content-Type: application/json" \
       -d '{
         "name": "clerk",
         "display_name": "Clerk",
         "description": "ScopeKeeper contract, pricing, ledger, and handover service",
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
         "overwrite": true
       }'
     ```
   - Save the returned `id` and `api_key` into `.env` as `CLERK_AGENT_ID` and `CLERK_API_KEY`.
   - Set Clerk's addressing policy to `anyone` via `ops/update_agent_detail` so any internal team member (`Priya`, `Ravi`, `Aisha`) can run `@clerk` commands.
   - Add `clerk` to **`acme-intake` and `acme-delivery` only** (never `acme-client`).
2. **What to check after this step:**
   - Start Clerk (`just dev`) and verify `/api/health` shows `switchConnected: true`.
   - In `acme-delivery`, type `@clerk status CR-003` and verify Clerk replies within 2 seconds while maintaining its 2-second WebSocket `ping`/`pong` heartbeat.
   - Verify `acme-client` participant list does **not** include `clerk`.

---

## Step 6: Define Room Roles and Verify Human Governance Holders

1. **What to click / run:**
   - In **`acme-client`**, define the exclusive agent shift role `client-desk` (`ops/define_role` with `exclusive: true`) using [`switch/roles/client-desk.md`](../switch/roles/client-desk.md):
     ```json
     {
       "name": "client-desk",
       "exclusive": true,
       "instructions": "You are covering the client desk while the agency team is offline..."
     }
     ```
   - In **`acme-delivery`**, define the governance roles `account-manager` and `delivery-lead` using [`switch/roles/account-manager.md`](../switch/roles/account-manager.md) and [`switch/roles/delivery-lead.md`](../switch/roles/delivery-lead.md).
   - Verify [`config/rooms.yaml`](../config/rooms.yaml) maps `account-manager` to `priya` and `delivery-lead` to `ravi`.
2. **What to check after this step:**
   - Calling `ops/get_role_detail` for `client-desk` in `acme-client` returns `{"name": "client-desk", "exclusive": true, "held_by": []}` during daytime copilot hours.
   - When `@clerk flip now` is run in `acme-delivery`, Scout assumes `client-desk` in `acme-client` and `held_by` shows `[{"name": "acme-scout", ...}]`.

---

## Step 7: Attach References, Create Live Room Documents, and Link Rooms Bidirectionally

1. **What to click / run:**
   - **Room Documents (`ops/create_room_document`):**
     - In `acme-client`: create `scope-summary` (deliverables `1.1`, `2.4`, `3.2`, `4.1` and exclusions `1.3`, `3.5`; no hourly rates or margins).
     - In `acme-delivery`: create `ledger-summary` (live monthly revenue protected, goodwill balance, and active swaps).
   - **References (`ops/create_reference` + `ops/attach_reference_to_room`):**
     - Attach `config/sow/SOW.md`, `config/scope-map.yaml`, and `config/plan.yaml` to `acme-intake`.
     - Attach all five config files (`SOW.md`, `scope-map.yaml`, `plan.yaml`, `rate-card.yaml`, `envelope.yaml`) to `acme-delivery`.
   - **Bidirectional Room Links (`ops/link_rooms`):**
     - Link `acme-client` ↔ `acme-intake` with label `"asks in, client-ready answers out"`.
     - Link `acme-intake` ↔ `acme-delivery` with label `"approved work becomes tickets"`.
2. **What to check after this step:**
   - The Switch Console room graph displays the linked topology (`acme-client` ↔ `acme-intake` ↔ `acme-delivery`).
   - Note that room documents cannot be opened directly inside bridged Slack/Discord clients, so Clerk also posts human-readable summaries in chat whenever it updates `ledger-summary`.

---

## Step 8: Export and Validate `switch/templates/scopekeeper.template.yaml`

1. **What to click / run:**
   - Compare your live workspace configuration with [`switch/templates/scopekeeper.template.yaml`](../switch/templates/scopekeeper.template.yaml).
   - Validate the template against Switch's template validator via `ops/get_template_guide` and `ops/save_template`:
     ```json
     {
       "name": "scopekeeper",
       "description": "ScopeKeeper cross-company agency scope & change-order workflow",
       "yaml": "<contents of switch/templates/scopekeeper.template.yaml>",
       "visibility": "private",
       "bypass_warnings": false
     }
     ```
2. **What to check after this step:**
   - `save_template` returns `warnings: []` and a valid template `id`.
   - A fresh workspace can import `switch/templates/scopekeeper.template.yaml` in one step.
