# 🎬 ScopeKeeper: 3-Minute Hackathon Demo Video Script
**Track 1:** Best Business Workflow ($2,000 Cash Prize)  
**Event:** WeMakeDevs "Flip the Switch" Hackathon  
**Target Duration:** Exactly 3 minutes (180 seconds)  

---

## ⏱️ Video Timeline Overview

| Section | Timestamp | Focus Area | Key Screen / Visual |
| :--- | :---: | :--- | :--- |
| **1. The $5,000 Problem** | `0:00 - 0:30` | Problem & Agency Pain | Title Slide + Ignition Report Stats |
| **2. Native Switch Doc Store & !flip** | `0:30 - 1:00` | Switch Core Architecture | Discord/Slack (`!flip` & `/documents` query) |
| **3. Client Request on Telegram** | `1:00 - 1:40` | Live Multi-Channel Mesh | Telegram Mobile App (`@AcmeClientDesk_bot`) |
| **4. Autonomous Build, SOW Amendment & 1-Click PR** | `1:40 - 2:30` | Full Autonomous Execution | Git Commit + Signed Amendment + GitHub PR |
| **5. Mission Control Dashboard** | `2:30 - 3:00` | Full Architecture & Recap | React Dashboard (`localhost:5173`) + FastMCP |

---

## 🎙️ Word-for-Word Voiceover & Action Script

### [0:00 - 0:30] The $5,000 Problem
* **Visual:** Clean slide displaying:  
  *"57% of software agencies lose $1,000 to $5,000 every month to unbilled scope creep."*  
  *(Ignition 2025 State of Client Engagement Report)*
* **Voiceover:**  
  > *"Every software agency knows this pain: you sign a fixed Statement of Work for a client project. But as soon as work begins, clients send endless 'quick asks' in chat: 'Can we add Stripe checkout? Can you fix this button? Can we add export to CSV?'*  
  > *Account managers hesitate to push back because they fear client friction. Developers work late nights for free. And the agency bleeds thousands of dollars every month.*  
  > *This is ScopeKeeper: an autonomous multi-agent scope-to-delivery governance system built natively on Switch Protocol for the Flip the Switch Hackathon."*

---

### [0:30 - 1:00] Native Switch Document Store & Interactive !flip Shift Handover
* **Visual:** Discord `#general` (Engineering squad). User types `!documents` and `!flip autopilot`.
* **Prompt to Type on Discord:**  
  `!documents`  
  *then*  
  `!flip autopilot`
* **Voiceover:**  
  > *"ScopeKeeper uses Switch Core's native PostgreSQL Document Store. When we send '!documents', Switch queries our room-linked authoritative SOW v1.2 contract.*  
  > *Now, watch our standout feature: '!flip'!*  
  > *At 7 PM, Priya triggers '!flip autopilot'. Switch immediately updates its 'role_leases' table: the Client Desk lease transfers to Scout AI, and Delivery Lead transfers to Antigravity.*  
  > *Simultaneously, a synchronized night shift briefing broadcasts across Discord, Slack, and Telegram—confirming autonomous coverage until morning!"*

---

### [1:00 - 1:40] Client Request on Telegram & Deterministic Governance
* **Visual:** Screen recording of Telegram (`@AcmeClientDesk_bot`). The client types from their phone.
* **Prompt to Type on Telegram:**  
  `Can we add Stripe checkout for our customers?`
* **Voiceover:**  
  > *"Our client Sam from Acme Corp chats on Telegram. He doesn't need to learn new tools—he talks to our client desk bot.*  
  > *Sam asks: 'Can we add Stripe checkout for our customers?'*  
  > *Behind the scenes, Switch Core routes the message to Scout and Antigravity. It checks Clause 6.1 of our native SOW store, calculates 18 hours at our deterministic $90 rate, and quotes $1,620 under Change Order CR-003 with zero human delay!"*
* **Prompt to Type on Telegram:**  
  `CONFIRM CR-003`

---

### [1:40 - 2:30] Autonomous Git Build, Signed SOW Amendment & 1-Click GitHub PR
* **Visual:** Split-screen showing:  
  1. Terminal checking out dynamic branch `feature/cr-003-stripe-checkout`, writing the component, and committing.  
  2. The generated official legal amendment `contracts/amendments/AMENDMENT_CR-003_stripe-checkout.md`.  
  3. Discord receiving the alert with the **1-Click GitHub PR link**.  
  4. Clicking the link to show GitHub's pre-filled Pull Request comparison page!
* **Voiceover:**  
  > *"The moment Sam types 'CONFIRM CR-003', ScopeKeeper executes the entire delivery pipeline autonomously!*  
  > *Builder checks out a dynamic feature branch, generates the production React component, and produces an Official Signed SOW Amendment with cryptographic SHA-256 audit digest.*  
  > *It commits and pushes directly to GitHub, and generates a pre-filled 1-Click Pull Request Compare URL.*  
  > *In Discord and Slack, engineering and finance get the exact PR link to review and merge in one click, alongside the signed contract amendment.*  
  > *Zero unbilled scope creep. Full legal and technical auditability."*

---

### [2:30 - 3:00] Mission Control Dashboard & Architecture Recap
* **Visual:** Browser showing the live ScopeKeeper Dashboard at `http://localhost:5173/`.  
  Click through Mission Control, Scope Map, and the SOW Ledger.
* **Voiceover:**  
  > *"Finally, here is the ScopeKeeper Mission Control Dashboard.*  
  > *Agency leaders inspect real-time protected revenue, view the active SOW ledger, review change orders, and monitor margin health.*  
  > *Everything you saw runs on 100% free infrastructure: Switch Core 0.31 native server, PostgreSQL, FastMCP (mcp_server.py), and Google's Gemini Flash AI—with zero credit card required.*  
  > *ScopeKeeper turns messy client scope into profitable, autonomous software delivery. Thank you!"*

---

## 📋 Pre-Recording Checklist

- [ ] PostgreSQL running on port `50417`
- [ ] Switch Core running on port `50415`
- [ ] ScopeKeeper Dashboard open at `http://localhost:5173/`
- [ ] Telegram desktop / web open to `@AcmeClientDesk_bot`
- [ ] Discord open to `#general` (guild `1562043658843201609`)
- [ ] Slack open to `#general` (`My Space`)
- [ ] GitHub repository: `https://github.com/napraveen/scopekeeper`
