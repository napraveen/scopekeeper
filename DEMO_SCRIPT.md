# 🎬 ScopeKeeper: 3-Minute Hackathon Demo Video Script
**Track 1:** Best Business Workflow ($2,000 Cash Prize)  
**Event:** WeMakeDevs "Flip the Switch" Hackathon  
**Target Duration:** Exactly 3 minutes (180 seconds)  

---

## ⏱️ Video Timeline Overview

| Section | Timestamp | Focus Area | Key Screen / Visual |
| :--- | :---: | :--- | :--- |
| **1. The $5,000 Problem** | `0:00 - 0:35` | The Problem & Agency Pain | Title Slide + Ignition Report Stats |
| **2. Client Request** | `0:35 - 1:15` | Live Switch Integration | Telegram Mobile App (`@AcmeClientDesk_bot`) |
| **3. SOW Governance** | `1:15 - 1:55` | AI Reasoning & Change Order | Telegram Reply (`CR-003 Quote`) |
| **4. Autonomous Build** | `1:55 - 2:30` | Autonomous Execution | Terminal Git Branch + Discord Alert (`#general`) |
| **5. Mission Dashboard** | `2:30 - 3:00` | Full Architecture & Recap | React Dashboard (`localhost:5173`) + FastMCP |

---

## 🎙️ Word-for-Word Voiceover & Action Script

### [0:00 - 0:35] The $5,000 Problem
* **Visual:** Clean slide displaying:  
  *"57% of software agencies lose $1,000 to $5,000 every month to unbilled scope creep."*  
  *(Ignition 2025 State of Client Engagement Report)*
* **Voiceover:**  
  > *"Every software agency knows this pain: you sign a fixed Statement of Work for a client project. But as soon as the project starts, the client sends 'quick asks' in chat: 'Can we add Stripe checkout? Can you fix this button? Can we add export to CSV?'*  
  > *Account managers hesitate to push back because they fear client friction. Developers end up working nights for free. And the agency bleeds thousands of dollars every month.*  
  > *This is ScopeKeeper: an autonomous multi-agent governance and client desk system built on Switch Protocol for the Flip the Switch Hackathon."*

---

### [0:35 - 1:15] The Client Request on Telegram
* **Visual:** Screen recording of Telegram (`@AcmeClientDesk_bot`). The client types and sends a message from their phone.
* **Prompt to Type on Telegram:**  
  `Can we add Stripe checkout?`
* **Voiceover:**  
  > *"Here, our client Sam from Acme Corp is chatting on Telegram. He doesn't need to join our internal tools—he talks to our client desk bot powered by Switch.*  
  > *Sam asks: 'Can we add Stripe checkout?'*  
  > *Behind the scenes, Switch Core routes this message through our multi-agent orchestrator. Scout—our client desk agent powered by Google Antigravity and Gemini AI—instantly evaluates the request against Acme's signed SOW v1.2 contract."*

---

### [1:15 - 1:55] Deterministic SOW Governance & Approval
* **Visual:** Telegram shows Scout's instant response:  
  - SOW Classification: **Out-of-Scope (Change Order)**  
  - Estimate: **18 hours @ $90.00/hr = $1,620.00**  
  - Change Order ID: **`CR-003`**  
  - Authorization prompt: *"Reply CONFIRM CR-003 to authorize."*
* **Voiceover:**  
  > *"Notice what just happened: Scout didn't hallucinate an arbitrary price. It checked the contract deliverables (D1, D2, D3), confirmed that payment processing is an excluded feature, and applied our deterministic SOW rate card of $90 an hour.*  
  > *It offers Sam a formal quote: 18 hours, $1,620, under Change Order CR-003.*  
  > *Now, Sam authorizes the work directly from Telegram."*
* **Prompt to Type on Telegram:**  
  `CONFIRM CR-003`

---

### [1:55 - 2:30] Autonomous Git Build & Synchronized Cross-Platform Dispatch
* **Visual:** Split-screen showing:  
  1. Terminal showing real Git execution (`git checkout`, file write, `git commit`).  
  2. Discord channel (`#general` in the agency server) receiving an automated engineering work order.  
  3. Slack channel (`#general` in the executive workspace) receiving an automated revenue booking alert.
* **Voiceover:**  
  > *"As soon as Sam replies CONFIRM CR-003, ScopeKeeper flips into autonomous execution mode!*  
  > *Watch the terminal: Builder automatically checks out a new branch: `feature/cr-003-stripe-portal`.*  
  > *It writes the production React component, commits the code with message 'feat(stripe): autonomous CR-003 Stripe Checkout implementation', and grabs the commit hash.*  
  > *Simultaneously, look at Discord and Slack!*  
  > *Our engineering developers in Discord receive an immediate Engineering Work Order notification with the branch name and Git commit hash.*  
  > *At the exact same second, our account executives and finance team in Slack receive an Executive Revenue Alert confirming +$1,620 booked to contract SOW v1.2 at an 82% profit margin!*  
  > *Zero human delays. Zero unbilled scope creep. Full three-way synchronization across Telegram, Discord, and Slack via Switch Core."*

---

### [2:30 - 3:00] Mission Control Dashboard & Architecture Recap
* **Visual:** Browser showing the live ScopeKeeper Dashboard at `http://localhost:5173/`.  
  Click through Mission Control, Scope Map, and the SOW Ledger.
* **Voiceover:**  
  > *"Finally, here is the ScopeKeeper Mission Control Dashboard.*  
  > *Agency leads can view their real-time protected revenue ticker, inspect the active SOW ledger, review change orders, and verify delivery milestones.*  
  > *Everything you saw runs on 100% free infrastructure: Switch Core 0.31 native server, PostgreSQL, our Model Context Protocol server (mcp_server.py), and Google's Gemini Flash AI—with zero credit card required.*  
  > *ScopeKeeper turns messy client scope into profitable, autonomous software delivery. Thank you!"*

---

## 📋 Pre-Recording Checklist

- [ ] PostgreSQL running on port `50417`
- [ ] Switch Core running on port `50415`
- [ ] ScopeKeeper Dashboard open at `http://localhost:5173/`
- [ ] Telegram desktop / web open to `@AcmeClientDesk_bot`
- [ ] Discord open to `#general` (guild `1562043658843201609`)
- [ ] Clean test branch ready (e.g. `git branch -D feature/cr-003-stripe-portal` if rerunning)
