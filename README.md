# ScopeKeeper 🛡️

> **Autonomous multi-agent client desk and scope-to-delivery governance on Switch.**  
> Built for the **[Flip the Switch Hackathon](https://www.wemakedevs.org/hackathons/switch)** (Track 1: Best Business Workflow).

[![ScopeKeeper CI](https://github.com/scopekeeper/scopekeeper/actions/workflows/ci.yml/badge.svg)](https://github.com/scopekeeper/scopekeeper/actions/workflows/ci.yml)
[![Switch Protocol 0.31](https://img.shields.io/badge/Switch%20Protocol-0.31.0-4F46E5.svg)](https://github.com/sandbox-quantum/switch)
[![Python 3.12](https://img.shields.io/badge/Python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📺 Demonstration Video

[![ScopeKeeper Demo](https://img.shields.io/badge/Demo%20Video-Watch%20on%20YouTube-red?style=for-the-badge&logo=youtube)](https://youtu.be/placeholder-scopekeeper-demo)

> *3-minute walk-through showing cross-company chat on Discord and Slack, autonomous shift handovers at 19:00 and 09:30 IST, sub-minute contract classification, $140 overnight autonomous change orders, git-history grounded estimation, and zero-dollar scope swaps.*

---

## 💸 The Problem in Two Numbers

According to **Ignition's 2025 State of Client Engagement Report**:
1. **57% of software and digital agencies lose between $1,000 and $5,000 every single month** to unbilled scope creep ($12,000 – $60,000 annually per agency).
2. **78% of agency leads rarely or only sometimes charge clients for out-of-scope requests** because scope conversations happen inside informal chat channels where account managers fear client friction, lead times are slow, and delivery teams default to working nights for free.

When an agency in Mumbai (`Asia/Kolkata`) builds for a client in New York (`America/New_York`), a **14.5-hour timezone blackout** leaves client requests unanswered overnight or builds unplanned features without pricing approval.

---

## ⚡ What ScopeKeeper Does That Scope Bots Don't

Typical AI chat bots either summarize transcripts after the damage is done or naively hallucinate fixed price quotes without checking codebase git history or contractual commitments. ScopeKeeper is different:

| Capability | Generic Scope Bot | ScopeKeeper |
| :--- | :--- | :--- |
| **Cross-Company Chat** | Single bot in one Slack channel | Bridges **Discord (Acme client)** with **Slack (Pixel & Co agency)** using Switch Room Groups. |
| **Shift Handovers ("The Flip")** | Static 24/7 bot or human only | Autonomous **`assume_role` / `release_role`** handovers at 19:00 IST (evening autopilot) and 09:30 IST (morning copilot). |
| **Contract Boundaries** | LLM guesses scope loosely | Multi-tier classification: pre-checks (duplicate candidates & contradiction log) + LLM + warranty post-rules. |
| **Pricing Engine** | Hallucinated ranges ($500 - $5,000) | **Deterministic rate-card calculation**: blended rate × hours × confidence contingency + milestone buffer. |
| **Estimation Grounding** | LLM predicts arbitrary hours | Reads **41 commits and 8 `Effort-Hours:` merge trailers** from `acme-portal` git history. |
| **Zero-Dollar Scope Swaps** | "Pay us or don't get it" | Automatically identifies unstarted deliverable items with matching effort for a **$0, 0-day milestone impact swap**. |
| **Governance Envelopes** | Zero autonomy or unsafe autonomy | Autonomous approval for asks under **$250 with HIGH confidence**; human approval required for high-impact changes. |
| **Code & Preview Delivery** | Just text recommendations | Branches `sk/*`, runs test suite, opens pull request, and serves live worktree preview on `http://localhost:4300`. |

---

## 🏛️ Architecture & Room Topology

ScopeKeeper organizes agents and team members into a single **Switch Room Group** (`Acme Web Portal`), enforcing strict boundary isolation across organizations:

```mermaid
flowchart LR
    subgraph Discord["Acme Inc. (Client on Discord)"]
        ClientUser["Sam (Client)"]
        RoomClient["#acme-client"]
    end

    subgraph Switch["Switch Agent Protocol Mesh"]
        direction TB
        Scout(["@acme-scout<br/>Client Desk"])
        Clerk(["@clerk<br/>Contract & Pricing Engine"])
        Estimator(["@acme-estimator<br/>Git History Estimator"])
        Builder(["@acme-builder<br/>Branch Implementation"])
    end

    subgraph Slack["Pixel & Co (Agency on Slack)"]
        RoomIntake["#acme-intake"]
        RoomDelivery["#acme-delivery"]
        RoomCR["#acme-cr-NNN (Ephemeral)"]
        Priya["Priya (@account-manager)"]
        Ravi["Ravi (@delivery-lead)"]
    end

    ClientUser <--> RoomClient
    RoomClient <--> Scout
    Scout <--> RoomIntake
    RoomIntake <--> Clerk
    Clerk <--> RoomDelivery
    Clerk <--> RoomCR
    Estimator <--> RoomCR
    Builder <--> RoomDelivery
    Priya <--> RoomIntake
    Priya <--> RoomDelivery
    Ravi <--> RoomDelivery
```

### Room Membership & Isolation Table

A core architectural principle of ScopeKeeper is that **internal rates, margin discussions, and code work are never exposed to the client room**:

| Room | Bridge App | Purpose | Human Members | Agent Members | Roles Configured |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`acme-client`** | Discord | Public client support & requests | Sam (`client`), Priya (`agency`) | `@acme-scout` | `@client-desk` (exclusive) |
| **`acme-intake`** | Slack | Triage & handoff between Scout and Clerk | Priya (`account-manager`) | `@acme-scout`, `@clerk` | *(None)* |
| **`acme-delivery`** | Slack | Agency team governance & work orders | Priya, Ravi (`delivery-lead`), Aisha | `@clerk`, `@acme-estimator`, `@acme-builder` | `@account-manager`, `@delivery-lead` |
| **`acme-cr-NNN`** | Slack | Ephemeral room for 1 out-of-scope Change Request | Priya, Ravi | `@clerk`, `@acme-estimator` | *(None)* |

> 🔒 **Strict Isolation Guarantee:** `@clerk`, `@acme-estimator`, and `@acme-builder` **never join `acme-client`**. Scout never sees pricing models, rates, or internal margin formulas.

---

## 🔄 Roles and "The Flip"

Because the agency is based in Mumbai (`Asia/Kolkata`) and the client in New York (`America/New_York`), ScopeKeeper manages shift handovers automatically using Switch Room Roles:

```mermaid
stateDiagram-v2
    direction LR
    COPILOT: ☀️ Copilot Mode (09:30 - 19:00 IST)<br/>Priya holds @client-desk<br/>Scout drafts replies for Priya in #acme-intake
    AUTOPILOT: 🌙 Autopilot Mode (19:00 - 09:30 IST)<br/>Scout assumes @client-desk<br/>Autonomous envelope approvals (<$250, HIGH conf)

    [*] --> COPILOT: Morning Handover (09:30 IST)
    COPILOT --> AUTOPILOT: 19:00 IST Evening Handover ("The Flip")
    AUTOPILOT --> COPILOT: 09:30 IST Morning Brief & Handover
```

1. **Evening Handover (19:00 IST / 09:30 ET):**
   - Clerk emits `MODE autopilot` in `#acme-intake`.
   - Scout invokes Switch protocol `assume_role(role="client-desk")`.
   - Scout greets Sam on Discord: *"Good morning Sam! I am covering client desk until 11 PM ET while Mumbai is offline."*
   - Asks within the autonomous envelope (< $250, HIGH confidence) are priced, approved, and built overnight.
2. **Morning Brief & Handover (09:30 IST / 23:00 ET):**
   - Clerk posts the **Morning Brief** in `#acme-delivery` summarizing overnight asks, revenue billed, and pending approvals.
   - Clerk emits `MODE copilot` in `#acme-intake`.
   - Scout releases `@client-desk` (`release_role()`) back to Priya.

---

## 📖 The Life of an Ask

When Sam posts a message containing multiple requests, ScopeKeeper executes a deterministic pipeline:

```text
1. Client Message       -> "1. Login button broken on Safari, 2. Dark mode, 3. Excel export, 4. Android app"
2. Scout Relay          -> Numbered split asks relayed to #acme-intake in exact JSON/YAML format
3. Clerk Classification -> Multi-tier classifier runs pre-checks, LLM, and warranty post-rules:
                           - Ask 1: DEFECT (Contract clause 1.1) -> Free warranty fix
                           - Ask 2: IN_SCOPE (Clause 2.4)        -> Work order dispatched to Builder
                           - Ask 3: UNCLEAR (Clause 3.2)         -> Clarifying question generated (Q-0001)
                           - Ask 4: OUT_OF_SCOPE (Clause 1.3)    -> Change Room #acme-cr-004 opened
4. Estimation (CR-004)  -> Estimator scans acme-portal git history trailers:
                           - Full: 200 hours ($10,350)
                           - Smaller dashboard: 56 hours ($2,650)
5. Delivery Confirmation-> Ravi confirms 200 hours in #acme-cr-004
6. Pricing & Options    -> Clerk presents 4 standardized client options:
                           - Option A: 200h full scope ($10,350, +12 milestone days)
                           - Option B: 200h with contingency buffer
                           - Option C: 56h board-meeting dashboard ($2,650, +3 milestone days)
                           - Option D: Scope Swap (56h mobile dashboard swapped for unstarted I9, $0, +0 days)
7. Client Acceptance    -> Sam selects Option D; Clerk updates the Scope Ledger and plan in database.
```

---

## 🚀 Quickstart: Clone to Demo in 10 Minutes

### Prerequisites
- Python 3.12+ and [`uv`](https://docs.astral.sh/uv/) installed.
- Git and Node.js 18+ (for running the demo app).
- [Switch CLI / Switch Console](https://github.com/sandbox-quantum/switch) (optional for local mock; fake adapters included).

### 1. Clone & Setup Environment
```bash
git clone https://github.com/scopekeeper/scopekeeper.git
cd scopekeeper
cp .env.example .env
```

### 2. Install Dependencies & Initialize Database
```bash
# Using just
just setup
just seed

# Or manually:
cd clerk
uv sync --all-extras
python ../demo-app/seed/seed_history.py
uv run python -m clerk.cli seed
```

### 3. Run Clerk Backend & Preview Server
```bash
# Run Clerk backend (FastAPI + SSE Broadcaster on port 8080)
uv run --directory clerk python -m clerk.cli serve --port 8080

# In a separate terminal, run the local preview server (port 4300)
python scripts/preview_server.py
```

### 4. Replay the Overnight Demo Story
```bash
# Run the golden-path integration test that replays the full 14.5-hour demo story
uv run --directory clerk pytest tests/integration/test_overnight_story.py -v
```

### 5. Interactive Demo Controls
When `DEMO_MODE=true` is enabled in `.env`:
```bash
# Trigger the 19:00 IST evening handover (Scout assumes @client-desk)
just flip

# Trigger the 09:30 IST morning brief and copilot handover
just morning

# Advance simulated clock by 2 hours
uv run --directory clerk python -m clerk.cli clock +2h

# Reset database, change rooms, git branches, and clock back to seed state in <60s
just reset
```

---

## 🔌 One-Click Switch Template Import

ScopeKeeper includes a verified, self-contained Switch template: [`switch/templates/scopekeeper.template.yaml`](file:///f:/2026%20-%20Projects/scopekeeper/switch/templates/scopekeeper.template.yaml).

To import into Switch Console:
1. Open **Switch Console** (`http://localhost:8000`).
2. Navigate to **Templates** → **Import Template**.
3. Select `switch/templates/scopekeeper.template.yaml`.
4. Fill in the bridge parameters (Discord bridge for `client_bridge`, Slack bridge for `agency_bridge`).
5. Click **Deploy**. Switch will instantiate all 3 core rooms, assign roles, attach scope documents, and launch agents.

---

## 🏆 Hackathon Judging Criteria Alignment

### 1. Use of Switch
- Uses Switch **Room Groups** to bundle cross-company chat spaces across Discord and Slack.
- Employs **Switch Room Roles** (`assume_role`, `release_role`, `client-desk`, `exclusive: true`) to implement human-agent shift handovers.
- Implements custom agent protocol adapter over **Switch WebSocket Streams** (`SwitchProtocolAdapter`) with independent 2-second `ping`/`pong` heartbeats, session placements, `gap` sequence re-sync, and `evicted` recovery.
- Uses **Switch Documents** (`scope-summary`, `ledger-summary`) for persistent, room-scoped reference data.

### 2. Real-World Usefulness
- Directly addresses the **$1,000 – $5,000 monthly unbilled revenue leak** experienced by 57% of software agencies.
- Solves the timezone blackout between Western clients and offshore agency delivery teams.
- Eliminates client friction through **Scope Swaps (Option D)**: giving clients flexibility while protecting agency team capacity and margins.

### 3. Working Demo
- Includes an end-to-end integration test (`test_overnight_story.py`) verifying all 7 beats of the overnight story matching Section 2 number for number.
- `reset_demo.py` cleans databases, archives open change rooms, resets git tags, and rewinds the clock in **under 20 seconds**.
- Web Dashboard API with 19 REST endpoints and a real-time Server-Sent Events (SSE) event stream (`/api/stream`).

### 4. Clarity & Replicability
- Fully deterministic: `demo-app/seed/seed_history.py` regenerates `acme-portal` with exactly 41 backdated commits, 8 `Effort-Hours:` merge trailers, and tag `seed-v1`.
- Single command execution with `justfile` targets (`setup`, `seed`, `dev`, `test`, `eval`, `reset`, `flip`, `morning`).
- Step-by-step setup guide in [`docs/switch-setup.md`](file:///f:/2026%20-%20Projects/scopekeeper/docs/switch-setup.md).

### 5. Technical Depth
- **Zero hallucinations on numbers:** Clerk verifies every number, money amount, and date against `facts` JSON before posting.
- **Strict type safety:** 100% `mypy --strict` compliance across all 71 Python source files; 0 ruff lint errors.
- **Multi-provider LLM support:** Production adapters for Google Gemini, Anthropic Claude, OpenAI, and offline Scripted LLM with automatic repair retry and SHA-256 caching.
- **Planted real-world defect:** Session expiry date parsing bug (`new Date("2026-11-04 10:00")`) replicating Safari's strict ISO parser defect with accompanying Vitest test.

---

## ⚠️ Known Limits & Boundaries

1. **Switch Tasks Deprecation:** Switch tasks were deprecated in version 0.31.0; ScopeKeeper uses GitHub Issues and local markdown tickets (`tickets/ASK-NNNN.md`).
2. **Room Documents on Bridged Chats:** Switch room documents cannot be opened from bridged Discord/Slack clients; Clerk mirrors key updates as standard chat messages.
3. **Agent-Only Room Roles:** In Switch, only agents can hold room roles (`assume_role`), while humans hold governance roles defined in `config/rooms.yaml`; Clerk reconciles both seamlessly.
4. **Offline Fallback:** If Switch Console is offline or `SCOUT_MODE=builtin`, Clerk activates an embedded, sandboxed Scout process (`BuiltinScout`) maintaining full functionality.

---

## 📄 License

ScopeKeeper is open-source software licensed under the [MIT License](LICENSE).
