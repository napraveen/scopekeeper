---
title: "How We Built ScopeKeeper: Stopping Agency Scope Creep with Switch Protocol and Multi-Agent AI"
description: "A complete technical walkthrough of ScopeKeeper, built for the WeMakeDevs 'Flip the Switch' Hackathon. Learn how 4 AI agents collaborate across Discord, Telegram, and Slack with Day/Night role leases, Jira Cloud, Google Sheets, and GitHub to eliminate unbilled agency scope creep."
date: "2026-11-07"
author: "Praveen Natarajan & The ScopeKeeper Team"
canonical_url: "https://dev.to/napraveen/how-we-built-scopekeeper-stopping-agency-scope-creep-with-switch-protocol-and-multi-agent-ai"
tags: ["switchai", "wemakedevs", "hackathon", "ai-agents", "python", "automation", "devops"]
cover_image: "https://raw.githubusercontent.com/napraveen/scopekeeper/main/dashboard/public/01-scopekeeper-banner.png"
image: "https://raw.githubusercontent.com/napraveen/scopekeeper/main/dashboard/public/01-scopekeeper-banner.png"
cover: "https://raw.githubusercontent.com/napraveen/scopekeeper/main/dashboard/public/01-scopekeeper-banner.png"
series: "Flip the Switch Hackathon 2026"
reading_time: "11 min read"
---

# How We Built ScopeKeeper: Stopping Agency Scope Creep with Switch Protocol and Multi-Agent AI

*Built for the [WeMakeDevs "Flip the Switch" Hackathon](https://www.wemakedevs.org/hackathons/switch) (November 4–7, 2026) — Track 1: Best Business Workflow & Best Blog.*

![ScopeKeeper Banner](https://raw.githubusercontent.com/napraveen/scopekeeper/main/dashboard/public/01-scopekeeper-banner.png)

---

## ⚡ Key Takeaways (Executive TL;DR)

> [!IMPORTANT]
> - **The Problem:** 57% of software agencies lose \$1,000 to \$5,000 every month to informal, unbilled "quick favor" requests made in chat apps while teams sleep across timezones.
> - **The Solution:** **ScopeKeeper** transforms **Switch Protocol 0.31** into an autonomous agency desk connecting **Discord**, **Telegram**, and **Slack** to enforce contract governance under Statement of Work (SOW) v1.2.
> - **The Shift Flip Protocol (`!flip`):** Switches between Day PM Copilot (**Sakthi**) and Night Autopilot (**Scout**) with an atomic PostgreSQL role lease and a \$2,000 autonomous envelope.
> - **Signer Authority Gate:** Separates requesters (junior devs on Discord) from authorized budget signatories (executives on Telegram) to eliminate the "Rogue Requester" trap.
> - **1-Click Multi-Cloud Cascade:** A single Telegram button tap executes across 4 cloud ecosystems in under 45 seconds: Atlassian Jira Cloud ticket, Google Workspace Sheet & Doc sync, GitHub branch/component/PR with passing CI, and Slack technical review.
> - **Zero Extra Paid Subscriptions:** Designed for a solo builder to demo a multi-timezone agency on free tiers with full local reproducibility.

---

## The 2:00 AM Slack Ping That Destroys Agency Margins

If you have ever worked at or run a software development agency, this scenario will hurt:

It is 2:15 AM in Bengaluru (`Asia/Kolkata`). Your agency delivery squad is fast asleep. Over in San Francisco, an excited client product manager drops a casual message into your shared Discord channel:

> *"Hey team! Urgent ask for Monday's investor demo: Our mobile Safari users hit an 'Invalid Date' crash in the analytics session reports—we need that patched ASAP. Also, our CEO mandated an Enterprise Stripe Checkout Portal with multi-currency subscriptions so we can process live investor payments. Can you push that tonight?"*

Notice what just happened. That single message contains two radically different requests:
1. **A legitimate warranty defect:** A bug in an existing deliverable that the agency is legally obligated to fix under warranty at **\$0.00**.
2. **A massive out-of-scope feature:** A brand-new payment portal requiring ~20 engineering hours (\$1,800+ billable value) that was never in the signed contract.

### The \$60,000 Silent Agency Killer

According to **Ignition's 2025 State of Client Engagement Report**:
- **57% of software agencies lose between \$1,000 and \$5,000 every single month** to unbilled scope creep (\$12,000 to \$60,000 annually per firm).
- **78% of agency leads rarely or only sometimes charge clients for out-of-scope requests** because scope conversations happen inside informal chat channels where account managers fear client friction, proposals take days to draft, and delivery engineers default to working weekends for free.
- **The "Rogue Requester" Trap:** A junior client developer casually requests a complex integration. The agency builds it. At month's end, the client VP refuses the invoice because the requester never had budget commitment authority.

Between an agency in India and a client in the United States, there is a **14.5-hour timezone blackout**. Either client asks sit unacknowledged for half a day, or enthusiastic developers build unplanned features for free.

We built **ScopeKeeper** to solve this once and for all.

---

## What is ScopeKeeper?

**ScopeKeeper** is an autonomous multi-agent agency desk and scope-to-delivery governance system built directly on **Switch Protocol**.

Instead of treating AI agents as isolated chat toys, ScopeKeeper embeds four specialized AI personas into the platforms where real work happens:

![ScopeKeeper Stakeholders and Agents Topology](https://raw.githubusercontent.com/napraveen/scopekeeper/main/dashboard/public/02-personas-and-agents.png)

### The 4 AI Agents on the Switch Mesh

1. **`@acme-scout` (Client Desk Representative):** Monitors Discord and Telegram channels 24/7, acknowledging client asks within seconds, classifying requests against SOW v1.2, and enforcing signer authority.
2. **`@clerk` (Contract & Pricing Governor):** Accesses Switch Core's native document store, audits legal clauses, calculates hourly estimates (\$90/hr blended rate), and formats Change Orders.
3. **`@acme-builder` (Autonomous Engineering Engine):** Clones repositories, checks out git branches, generates customized React components, authors legally binding markdown SOW amendments, and opens GitHub Pull Requests.
4. **`@acme-estimator` (Capacity & Backlog Modeler):** Evaluates deliverable tradeoffs for zero-dollar scope swaps.

---

## System Architecture: How Switch Protocol Powers Everything

Switch Protocol is not just a bot bridge; it is the **event bus, permission boundary, and state engine** of ScopeKeeper.

![ScopeKeeper End-to-End System Architecture](https://raw.githubusercontent.com/napraveen/scopekeeper/main/dashboard/public/03-system-architecture.png)

### The 4 Switch Superpowers Leveraged

![The 4 Switch Protocol Superpowers Leveraged](https://raw.githubusercontent.com/napraveen/scopekeeper/main/dashboard/public/04-switch-superpowers-table.png)

1. **Collaboration Bridges:** Real-time bidirectional message routing across Discord, Telegram, and Slack simultaneously via `switch_core.bridges` socket mode and long-polling adapters.
2. **Role Leases (`role_leases`):** Atomic handoff of `@client-desk` custody between Day PM (Sakthi) and Night Autopilot (Scout) using PostgreSQL optimistic locking and lease expiration.
3. **Native Document Store (`documents`):** Canonical storage of Statement of Work v1.2, hourly blended rates (\$90/hr), and warranty definitions.
4. **Native References Graph (`references`):** Pins live Jira tickets, Google Sheets billing ledger, and GitHub PR links directly into Switch room sidebars.

---

## Step-by-Step Technical Setup Guide

Here is how you can set up and run ScopeKeeper locally in less than 5 minutes.

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+ (for the dashboard)
- Git
- Switch Protocol 0.31.0 installed (via Switch Console)

### 1. Clone the Repository
```bash
git clone https://github.com/napraveen/scopekeeper.git
cd scopekeeper
```

### 2. Configure Environment Variables
Create a `.env` file in the project root:
```env
# Switch Core Configuration
SWITCH_HTTP=http://127.0.0.1:50415
SWITCH_DB_URL=postgresql://postgres:oIYBdLrq3PE6xq_mkrgnLTqmrdsKuRtM@127.0.0.1:50417/switch

# Multi-Platform Tokens
DISCORD_BOT_TOKEN=your_discord_token_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_BOT_USERNAME=AcmeClientDesk_bot
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token

# Atlassian Jira Cloud Integration
JIRA_INSTANCE_URL=https://your-domain.atlassian.net
JIRA_API_EMAIL=your-email@domain.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=KAN

# Google Workspace Apps Script Webhook
GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/your-script-id/exec
GOOGLE_DOCS_WEBHOOK_URL=https://script.google.com/macros/s/your-doc-script-id/exec

# GitHub Integration
GITHUB_TOKEN=your_personal_access_token
GITHUB_REPO=napraveen/scopekeeper
```

### 3. Start PostgreSQL and Switch Core
ScopeKeeper uses Switch's bundled native toolchain:
```powershell
# Terminal 1: Start PostgreSQL
& "$env:APPDATA\switchdash\local-switch-server\native\toolchain\bundle-057e6b8bca99\postgres\bin\postgres.exe" `
  -D "$env:APPDATA\switchdash\local-switch-server\native\pgdata" -p 50417

# Terminal 2: Start Switch Core with Native !flip Dispatcher
& "$env:APPDATA\switchdash\local-switch-server\native\switch-core\0.31.0\venv\Scripts\python.exe" `
  scratch/run_switch_core.py
```

### 4. Start ScopeKeeper Orchestrator & Frontend
```powershell
# Terminal 3: Start ScopeKeeper Multi-Agent Daemon
& "$env:APPDATA\switchdash\local-switch-server\native\switch-core\0.31.0\venv\Scripts\python.exe" -u `
  switch/orchestrator.py

# Terminal 4: Start React 19 Frontend Dashboard
cd dashboard
npm install
npm run dev
```

Visit `http://localhost:5173` to see the live executive command center.

---

## The 5-Act Live Workflow Walkthrough

Here is the exact real-world scenario demonstrated in our 3-minute hackathon video:

- **Act 1 (0:00 - 0:35):** Switch Console & Shift Flip (`!flip night`)
- **Act 2 (0:35 - 1:10):** Harish Double-Ask & Signer Authority Gate
- **Act 3 (1:10 - 1:45):** Telegram Inline $0 Scope Swap
- **Act 4 (1:45 - 2:20):** 1-Click 4-Cloud Cascade
- **Act 5 (2:20 - 3:00):** Morning Brief, Switch Lens & Dashboard

---

### Act 1: The Switch Console & The Shift Flip (`!flip night`)
The scene opens in **Switch Console**. We meet the four personas and our four AI agents.

At 7:00 PM IST, Sakthi (Lead PM) ends her day shift and types into Slack or Switch Console:
```text
!flip night
```

Switch Core intercepts this command natively. It updates PostgreSQL `role_leases`, releasing Sakthi's day lock and assigning `@client-desk` custody to **Scout (Night Autopilot)**:

```sql
UPDATE role_leases 
SET agent_id = '44482fb9-b075-432c-aa85-9abd59758ac2',  -- Scout
    acquired_at = NOW(), 
    last_seen_at = NOW() 
WHERE room_id = '24ccfc18-6ddd-42fa-a1fe-59d48975a828';
```

Clerk broadcasts the overnight briefing to Slack:
> 🌙 **Night Autopilot Engaged by Sakthi**  
> • Autonomous Scope Envelope: Active (≤ \$2,000 auto-approved)  
> • Desk Custody: `@acme-scout` (Autopilot Mode)  
> • On-Call Escalation: Bala (Delivery Lead)

---

### Act 2: Harish's Multi-Ask on Discord & The Signer Gate
At 2:15 AM, junior client developer **Harish** drops his urgent multi-ask into Discord:

> *"Urgent for Monday's board demo: Our mobile Safari users hit an 'Invalid Date' crash in the analytics session reports (`session.ts`)—we need that patched ASAP. Also, our CEO just mandated an Enterprise Stripe Checkout Portal with multi-currency subscriptions so we can process live investor payments. Can you push that tonight?"*

Scout and Clerk analyze the prompt against SOW v1.2 in parallel:

1. **Defect Fast-Path (\$0 Warranty):**
   Clerk matches the Safari crash against **Clause 5.1 (Warranty)**. It immediately calls the Atlassian Jira Cloud API to file a high-priority bug:
   - **Ticket:** `KAN-24`
   - **Title:** `Safari Date Parsing Crash in Session Reports (session.ts)`
   - **Cost:** **\$0.00** (Covered under Warranty)

2. **Out-of-Scope Classification:**
   Clerk evaluates the Stripe Portal against **Clause 6.1 (Change Control — Third-Party Payment Gateways)**:
   - **Effort:** 21 engineering hours
   - **Blended Rate:** \$90.00 / hour
   - **Commercial Value:** **\$1,890.00 USD**
   - **Timeline Impact:** +3 business days

3. **Signer Authority Enforcement:**
   Scout checks `config/people.yaml`. Harish is listed as a **Requester**, not an **Authorized Signatory**:
   ```yaml
   harish:
     name: "Harish"
     role: "Junior Frontend Developer"
     org: "client"
     authority: "requester_only" # Cannot commit budget!
   ```

Scout replies to Harish in Discord within 3 seconds:
> 🛡️ **ScopeKeeper Evaluation:**  
> 1. ✅ **Warranty Defect Logged:** Patched under Clause 5.1 → [Jira Bug KAN-24](https://napraveen.atlassian.net/browse/KAN-24) (\$0.00).  
> 2. ⚠️ **Scope Modification Required:** The Enterprise Stripe Portal is out-of-scope (\$1,890.00 USD).  
> 3. 🚫 **Signer Notice:** Hi Harish, per contract governance, you are designated as a Requester and cannot authorize budget. I have routed Change Order proposal `CR-004` to your Head of Product (**@Dhana**) on Telegram for authorization.

---

### Act 3: The Telegram Win-Win Scope Swap
Over on Telegram, Dhana (Head of Product and authorized signatory with a \$5,000 cap) receives an interactive Telegram card with inline keyboard buttons:

![Telegram Change Order Proposal Card](https://raw.githubusercontent.com/napraveen/scopekeeper/main/dashboard/public/05-telegram-change-order-card.png)

Here is why **Option B ($0 Scope Swap)** is a game changer for client relationships:

Instead of demanding more money (Option A) or refusing the request (Option C), ScopeKeeper queries the project deliverable backlog. It discovers that **Deliverable D3 (CSV Data Export)** is allocated 20 engineering hours and has not been started.

By offering to swap Deliverable D3 for the Stripe Checkout Portal:
- **Client Budget Impact:** **\$0.00**
- **Schedule Slippage:** **0 business days** (D3 hours offset the Stripe hours)
- **Client Happiness:** Harish gets his CEO-mandated payment portal without waiting for procurement red tape!

Dhana taps **`[🔄 Option B: $0 Scope Swap]`** on her phone.

---

### Act 4: The 1-Click Multi-Cloud Cascade
The instant Dhana taps the button, ScopeKeeper's daemon triggers a coordinated 4-cloud cascade in under 45 seconds:

![1-Click 4-Cloud Cascade Flowchart](https://raw.githubusercontent.com/napraveen/scopekeeper/main/dashboard/public/06-cloud-cascade-flowchart.png)

1. **Atlassian Jira Cloud:** Creates Story `KAN-30` (`[CR-004] Enterprise Stripe Checkout Portal`), links it to Epic 1, and marks Deliverable D3 as `Descheduled (Scope Swap)`.
2. **Google Workspace Sheets:** Fires an HTTPS POST to our Apps Script Webhook, appending the financial record to the *Master Billing Ledger*:
   ```csv
   CR-004,Enterprise Stripe Checkout Portal,Scope Swap,0.00,Dhana,AMENDMENT_CR-004.md,2026-11-06T18:26:46Z
   ```
3. **Official SOW Amendment Authored:** Builder generates `contracts/amendments/AMENDMENT_CR-004_stripe-checkout-portal.md`, calculating a cryptographic SHA-256 digital signature:
   ```text
   SHA-256 Audit Digest: 2aab718f775f17cffec0d0b98d02c4b264ed0f1524d5f7c8c3d1a5ccd90af735
   ```
4. **Autonomous GitHub Pull Request:** Builder checks out branch `feature/cr-004-stripe-checkout-portal`, generates the complete interactive React component `dashboard/src/components/StripeCheckoutModal.tsx`, commits, and opens a GitHub PR.
5. **Switch Native References Pinned:** Pins the Jira issue, Google Sheet URL, and GitHub PR into Switch Core PostgreSQL `references` and `room_references` tables.
6. **Slack Review Handshake:** In Slack (`#acme-delivery`), Builder notifies tech lead Bala:
   > 🛠️ **WORK ORDER READY FOR REVIEW (CR-004)**  
   > • Feature: **Enterprise Stripe Checkout Portal** (Scope Swap \$0)  
   > • Client Signatory: Dhana (Acme Head of Product)  
   > • Implementation Branch: `feature/cr-004-stripe-checkout-portal`  
   > • Compare & Merge PR: [GitHub PR Link](https://github.com/napraveen/scopekeeper)  
   > • Bala (Delivery Lead): Please reply `@builder lgtm` here in Slack to confirm review.

Bala reviews the PR and types:
```text
@builder lgtm
```

Antigravity verifies that 91/91 unit tests pass green and confirms:
> ✅ **CODE REVIEW APPROVED BY BALA (REVIEWER)**  
> • Pull Request checks verified: Green (91/91 tests pass)  
> • Branch: `feature/cr-004-stripe-checkout-portal`  
> • Stage: Staged for deployment into production milestone.

---

### Act 5: Morning Brief, Switch Lens & Dashboard
At 9:30 AM IST, Sakthi arrives at the office, opens Slack, and types:
```text
!flip day
```

Clerk delivers the **Morning Brief**:
> ☀️ **MORNING BRIEF — 9:30 AM IST**  
> Welcome back Sakthi! Here is the overnight delivery summary:  
> • **Asks Processed:** 2 (1 Warranty Defect, 1 Change Request)  
> • **Scope Creep Prevented:** **\$1,890.00 USD protected**  
> • **Schedule Slippage:** **0 business days** (Resolved via D3 Scope Swap)  
> • **Contract Status:** Amendment `CR-004` digitally signed & executed  
> • **Sprint Backlog:** Jira Bug & Story logged • PR staged on GitHub

On our frontend dashboard at `http://localhost:5173`, leadership has an executive command center displaying real-time revenue protection, signed audit digests, and live interactive previews of newly built components.

Pressing **`⌘K`** activates **Switch Lens**, revealing the underlying Switch agent rooms, role leases, and cross-channel bridges in an architectural view. Pressing **`D`** opens **Director Mode** for full timeline control and replay.

---

## Hard Engineering Challenges & Lessons Learned

Building a multi-agent system across three live messaging platforms and four enterprise cloud services taught us lessons that you never find in chatbot tutorials:

### 1. The Autonomous Feedback Loop Trap
When Antigravity posted the Slack review prompt:
`"Bala (Delivery Lead): Please reply @builder lgtm here in Slack..."`

Our message ingestion daemon saw `@builder` and `lgtm` in the message content, mistook the bot's own instruction for Bala's approval, and immediately marked the PR approved before a human ever saw it!

**The Fix:** We implemented a strict sender identity filter that checks message metadata against an ignored bot registry (`{"Scout", "Clerk", "Builder", "Estimator", "Antigravity", "admin", "system"}`) before parsing action keywords.

### 2. Telegram Long-Polling Concurrency Conflicts
Switch Core's built-in Telegram bridge uses `python-telegram-bot` to poll Telegram for inbound messages. When our orchestrator daemon started polling Telegram for inline button callback queries (`answerCallbackQuery`), Telegram returned **HTTP 409 Conflict: terminated by other getUpdates request**.

Telegram strictly permits only **one** poller per bot token.

**The Fix:** We decoupled inline button handling into an atomic webhook listener with exponential backoff and coordinated offset management, allowing callback queries and room messages to coexist without dropped packets.

### 3. Native Switch Core Command Dispatching
Switch Core intercepts any message starting with `!` as an internal management command (like `!reset` or `!compact`). Initially, typing `!flip night` returned `Unknown command: flip` because `flip` was not registered in Switch Core's native command table.

**The Fix:** We registered `_cmd_flip` directly inside Switch Core's `commands.py` dispatcher:
```python
Command(
    "flip",
    "Toggle room role lease between Day PM Copilot and Night Autopilot.",
    _cmd_flip,
)
```
This allows Switch Core to execute role handovers natively from any connected bridge (Slack, Discord, or Console) with zero latency.

### 4. Cross-Platform Markdown Incompatibilities
- **Telegram Legacy Markdown:** Does not support `**bold**` (requires single `*bold*`) and crashes if raw underscores in URLs are unescaped.
- **Discord:** Supports full GitHub Flavored Markdown.
- **Slack:** Uses proprietary `mrkdwn` where links must be formatted as `<url|text>` instead of `[text](url)`.

**The Fix:** We built 3 dedicated per-platform string formatters in `switch/orchestrator.py` so every message renders cleanly without broken markup or API rejection.

---

## Why Switch Protocol is the Future of Agentic Workflows

Most "AI agent frameworks" today are glorified Python scripts that make sequential LLM calls and log outputs to a terminal. That doesn't work in enterprise settings because **real work is asynchronous, multi-stakeholder, and multi-platform**.

Switch Protocol solved three problems that would have taken us months to build from scratch:
1. **Unified Identity Across Bridges:** Harish on Discord, Dhana on Telegram, and Bala on Slack are mapped to canonical Switch identities.
2. **Stateful Room Topology:** Agents and humans share stateful rooms with persistent documents, references, and audit trails.
3. **Atomic Role Leases:** The `role_leases` table in PostgreSQL provides provable, race-condition-free handovers between humans and autonomous agents.

---

## Frequently Asked Questions (FAQ)

### Can clients customize the SOW clauses?
Yes. ScopeKeeper reads SOW contract terms from `contracts/SOW_v1.2_Acme_Web_Portal.md` and indexes them into Switch Core's PostgreSQL `documents` table. You can modify hourly rates, warranty definitions, and change control clauses per client contract.

### Does ScopeKeeper require paid enterprise accounts?
No! ScopeKeeper is designed to run completely on **free developer tiers**: Atlassian Jira Cloud (free up to 10 users), Google Workspace Apps Script (free), GitHub (free), and Discord/Telegram/Slack bot APIs (free).

### What AI models does ScopeKeeper support?
ScopeKeeper is powered by the Google Antigravity AI Engine using `gemini-2.5-flash` / `gemini-3.1-flash-lite`, but also supports Anthropic Claude Code, OpenAI GPT-4o, and local models via OpenCode.

---

## Conclusion & Links

ScopeKeeper proves that autonomous multi-agent AI does not replace humans—it protects them. It protects engineers from working unbilled midnight overtime, protects project managers from awkward pricing confrontations, and protects clients from unexpected invoices.

By turning Switch Protocol into an autonomous contract governance desk, we turned the most contentious, money-losing part of agency life into a frictionless, high-margin delivery machine.

- **GitHub Repository:** [https://github.com/napraveen/scopekeeper](https://github.com/napraveen/scopekeeper)
- **Demo Video (3:00):** [https://youtu.be/placeholder-scopekeeper-demo](https://youtu.be/placeholder-scopekeeper-demo)
- **WeMakeDevs Hackathon Submission:** [https://www.wemakedevs.org/hackathons/switch/submit](https://www.wemakedevs.org/hackathons/switch/submit)

*If you found this technical breakdown helpful, star our [GitHub repo](https://github.com/napraveen/scopekeeper) and share your thoughts in the comments!*
