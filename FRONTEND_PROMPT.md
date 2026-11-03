Build this inside the `dashboard/` folder of the existing `scopekeeper` repo.
Don't change anything outside `dashboard/` except the README's dashboard section.
Start in mock mode. The backend will run at `http://localhost:8000`.

# ScopeKeeper — Frontend Prompt

## 1. Your role and the goal
You are a world-class product designer and senior frontend engineer. Build the ScopeKeeper dashboard, the back-office web app for a hackathon project in which people and AI agents from two companies run client work through shared chat rooms on Switch, an open-source framework that brings AI agents into Slack, Discord, Teams, Telegram and Mattermost.

The goal is a dashboard so clear and alive that, in a 3-minute demo video, judges instantly see the workflow, the money it protects and how Switch powers it. It must run on its own with a built-in mock of the whole demo story, and switch to a real backend with one setting.

How to work:
- Write a short plan (pages, components, data flow) before coding, then build in the order of section 12.
- Use the realistic data from section 10 everywhere. No lorem ipsum and no placeholder charts.
- After each phase, open the app in the browser and check every page at 1440 px and 390 px wide, in light and dark themes. Fix anything misaligned, clipped or unclear before moving on.
- Chat is the main interface and the dashboard mirrors it. Any action button shows exactly which room it will post to before it posts.
- Keep components small, typed and tested: strict TypeScript, no `any`.

---

## 2. Product context and the story the UI must tell
ScopeKeeper is a client desk run by people and AI agents. A client asks for things in chat; agents check each ask against the signed scope of work, estimate it from the real code, price it, get the right person's approval, build it and get the client's sign-off. When the agency's day ends, the client-desk role flips from the account manager to an agent, so the client's day is never wasted.

Show the people and agents the same way everywhere:

| Name | Who | Side and app | Shown as |
| :--- | :--- | :--- | :--- |
| **Sam** | Product owner at Acme, the client, New York | Client, Discord | Person avatar "S" |
| **Priya** | Account manager at Pixel & Co, Mumbai | Agency, Slack | Person avatar "P"; holds `@account-manager`, and `@client-desk` by day |
| **Ravi** | Delivery lead | Agency, Slack | Person avatar "R"; holds `@delivery-lead` |
| **Aisha** | Developer | Agency, Slack | Person avatar "A" |
| **Scout** | Client-desk agent | Agency; runs on OpenCode | Agent avatar with an "OpenCode" badge; holds `@client-desk` by night |
| **Clerk** | Contract-keeper agent | Agency; custom code | Agent avatar with a "Custom" badge |
| **Estimator** | Estimates from the code | Agency; Claude Code | Agent avatar with a "Claude Code" badge |
| **Builder** | Builds approved work | Agency; Codex | Agent avatar with a "Codex" badge |

Use text badges for agent vendors, never their logos.

The six ask categories each get a label, an icon and a colour, and colour is never the only signal: **Defect** (always free), **In scope**, **Unclear**, **Out of scope**, **Duplicate**, **Already decided**.

The story, which the UI must make obvious beat by beat:
1. At 7:00 PM IST the desk flips from Priya to Scout.
2. At 8:30 PM IST (10:00 AM ET) Sam asks for four things in one message.
3. Within a minute all four are sorted with clauses. The Safari login bug is a defect (1.1). Dark mode is in scope (2.4). Excel export is unclear (3.2), so Scout asks one question. An Android app is out of scope (1.3), so change request CR-004 opens.
4. Sam wants a native .xlsx file. It is priced at $140, inside the auto-approval envelope, then sent and approved in minutes. Revenue protected ticks up from $1,890 to $2,030.
5. The Estimator sizes the Android app: P50 190 h and P90 240 h (medium) for the full app, and 56 h (high) for a view-only board-meeting version.
6. Pull requests and previews appear, and Sam accepts dark mode.
7. At 9:30 AM IST the desk flips back to Priya, and the morning brief lists what needs a yes.
8. Ravi confirms 200 h. The options: A $10,350, moving milestone M2 from Dec 12 to Dec 24; B $10,350 in the next phase; C $2,650, moving M2 by 3 days; D the view-only version in place of unstarted item I9 (58 h) for $0. Priya approves all four.
9. Sam picks D. The swap animates in the plan, and the ledger shows $2,030 approved this month and one swap.

---

## 3. Tech stack and project structure
Use current stable versions of everything below.

| Concern | Choice |
| :--- | :--- |
| **Build** | Vite, React, TypeScript in strict mode |
| **Styling** | Tailwind CSS, shadcn/ui, CSS variables for design tokens |
| **Routing** | TanStack Router or React Router, code-split per route |
| **Server state** | TanStack Query |
| **UI state** | Zustand for the desk, theme, Director mode and Switch lens |
| **Tables and lists** | TanStack Table and TanStack Virtual |
| **Charts** | Custom SVG with `d3-scale` for the estimate range and the plan timeline; Recharts for simple bars |
| **Graph** | React Flow (`@xyflow/react`) for the Rooms map |
| **Motion** | Motion (formerly Framer Motion), with reduced-motion support |
| **Forms** | `react-hook-form` with `zod` |
| **Editor** | CodeMirror 6 with YAML mode |
| **Feedback** | `sonner` toasts, `cmdk` command palette, `lucide-react` icons |
| **Dates and money** | `date-fns` with time-zone support; `Intl.NumberFormat` |
| **Live stream** | `@microsoft/fetch-event-source`, so the token can travel in a header |
| **Mocks** | MSW (Mock Service Worker) plus an in-browser story engine |
| **Tests** | Vitest, Testing Library, Playwright |

Fonts: Inter for the interface and JetBrains Mono for IDs, hours and code, self-hosted with `@fontsource`.

```text
src/
  app/            # router, providers, layout shell
  pages/          # mission-control, asks, change-requests, change-order-public,
                  # plan, scope, rooms, ledger, settings
  features/       # desk, pipeline, activity, kpis, estimate, options, plan-timeline,
                  # scope-map, rooms-graph, ledger, director, switch-lens, command-palette
  components/ui/  # shadcn components
  components/     # Avatar, AgentBadge, CategoryChip, ClauseBadge, Money, DualTime,
                  # ChatLink, EmptyState, ConfirmPost
  lib/api/        # client, types, adapters, stream
  lib/format/     # money, time zones, hours
  mocks/          # seed data, MSW handlers, story engine
  styles/         # tokens, globals
  tests/          # unit and e2e
```

---

## 4. Design language
The brand idea is a light switch. "Flip the Switch" is the hackathon's name, and the product's key moment is the desk flipping between a person and an agent. Use it with restraint so it feels like a product, not a gimmick.

- **Logo:** an original wordmark, "ScopeKeeper", with a small toggle-switch glyph. Show "Built on Switch" as text in the footer; never copy Switch's own logo.
- **Day and night:** a light theme when Priya holds the desk and a dark theme when Scout holds it, when the "Follow the desk" setting is on (the default). At the handover the whole UI cross-fades over 400 ms.
- **Colour tokens:** CSS variables with light and dark values. Neutral surfaces from a zinc scale, one accent (electric indigo), and status colours. Categories: Defect rose, In scope emerald, Unclear amber, Out of scope violet, Duplicate slate, Already decided sky. Every chip also has an icon and a text label, and all text meets WCAG AA contrast in both themes.
- **Typography:** Inter on a 12, 14, 16, 20, 28 and 40 px scale; tabular figures for money and hours; JetBrains Mono for IDs such as `ASK-0007` and `CR-004`.
- **Layout:** an 8 px spacing grid, rounded-xl cards, 1 px hairline borders, no heavy shadows or gradients, comfortable density, content up to 1440 px wide.
- **Motion:** purposeful only, 150 to 300 ms, ease-out. Cards slide between pipeline stages with layout animation, money uses a number ticker, and new events fade in. Under `prefers-reduced-motion`, changes are instant.
- **Voice:** plain and specific, like a good colleague: *"Scout asked Sam one question about Excel export (clause 3.2)."* No exclamation marks and no jargon.
- **Times:** always both zones, for example `"8:30 PM IST · 10:00 AM ET"`.

---

## 5. App shell and navigation
- **Sidebar, collapsible to icons:** Mission Control, Asks, Change requests, Plan, Scope, Rooms, Ledger, Settings. Badges count what needs attention, such as change requests waiting for approval.
- **Top bar, left to right:** two live clocks (Mumbai and New York), each with a sun or moon and a thin bar marking its working hours; the desk pill (*"Desk: Scout · autopilot until 9:30 AM IST"*); search (⌘K); the Switch lens toggle; the connection dot (Live, Mock or Disconnected); the theme menu (Light, Dark, Follow the desk); the user menu (Priya, account manager).
- **Command palette (⌘K):** jump to any ask, change request, clause or page. Run actions such as "Approve CR-004", with the same confirm dialog as the button, and in demo mode "Flip now" and "Next beat".
- **Switch lens:** when on, small outlined tags appear on elements powered by a Switch building block: "Room", "Role", "Room link", "Reference", "Agent · Claude Code" and "Membership boundary". Each tag has a one-sentence tooltip, such as *"A role reaches whoever holds it, person or agent."* It is meant for judges and is off by default.
- **Banners:** a Disconnected banner with a retry button when the stream drops, and a quiet "Mock data · story mode" ribbon in mock mode.
- **Confirm before posting:** every action that posts to chat opens `ConfirmPost`, a dialog showing the exact message, the room and the app, such as `"#acme-cr-004 in Slack"`.
- **Mobile:** the sidebar becomes a bottom tab bar with five items and a More sheet.

---

## 6. Mission Control
Mission Control is the screen the video lives on. At a glance it answers who is on the desk, what came in, what it is worth and what needs a yes.

- **The Desk (hero, full width):** a large SVG toggle switch with Priya's avatar on the day side and Scout's on the night side, the knob resting on the current holder. Beside it: the holder's name, the mode (copilot by day, autopilot by night), "until 9:30 AM IST · 11:00 PM ET", and a countdown. At a handover the knob slides across, the sun sets or rises, the theme flips when following the desk, and a line appears in the activity feed. In demo mode, show a "Flip now" button.
- **KPI strip:** revenue protected this month as a number ticker ($1,890 to $2,030 during the story); change orders sent, approved, pending and swapped; goodwill as a small gauge (2 of 8 h); median minutes from ask to decision; asks by category as a compact stacked bar.
- **Live pipeline:** columns Received, Sorted, Waiting on client, Change path, Building, Preview and Accepted. Each card shows the ID, a one-line quote, the category chip, the clause badge, the requester's avatar and the time in both zones. Cards animate between columns as events arrive, and a new card glows briefly. Clicking a card opens the ask drawer.
- **Needs a yes:** decisions waiting on Priya or Ravi, each with who must act, what to decide and a primary button that opens `ConfirmPost`.
- **Activity feed (right rail):** human sentences with actor avatars, relative time plus both zones, and an "Open in Slack" or "Open in Discord" link. Group bursts, such as "Scout sorted 4 asks", and expand them on click. Announce new items through an `aria-live="polite"` region.
- **Layout:** the Desk and the KPI strip across the top; the pipeline (two-thirds width) with Needs a yes beneath it; the activity feed on the right. On mobile, stack the Desk, KPIs, Needs a yes, the pipeline as a vertical list, then the feed.

---

## 7. Asks, change requests and the public change-order page
- **Asks page:** a table with ID, quote, requester, category, clause, status, created time in both zones, and links. Filters for category, status and date, a search box, and a saved "This week" view. A row opens a right-hand drawer with:
  - The quote in large type, attributed to Sam, with a link to the Discord message.
  - The verdict: category chip, clause badge with the SOW excerpt on hover, confidence as a thin bar, and the one-line reason.
  - The related plan item or decision, linked.
  - A vertical timeline of every event, each with both times and a chat link.
  - The linked change request, work items, pull requests and preview links.
- **Change requests:** a list of cards (ID, title, status, chosen or best option, value) and a detail page for each one:
  - Header: CR-004, "Android app", the client's quote, the status, and "Open #acme-cr-004 in Slack".
  - Estimate chart: a horizontal hours axis. For each version, a bar from P50 to P90 with a dot at P50, and the three similar past changes as small labelled ticks on the same axis (Reports v2 61 h, Admin users page 52 h, Auth refresh 18 h). Confidence badges, then touches and risks as quiet lists. The point to land: the estimate rests on this codebase's history.
  - Confirmation: "Ravi confirmed 200 h at 9:42 AM IST", or a waiting state with who must act.
  - Options: four cards side by side, stacked on mobile. Each shows the price in large tabular figures, hours, the date effect, a one-line description and envelope chips (passed, or which rule failed). Card D draws the swap as two equal-height bars: "I9 Admin analytics dashboard, 58 h" out and "View-only Android app, 56 h" in. The client's choice gets a check and an accent ring, and the others dim.
  - What-if timeline: a small timeline for milestone M2. Hovering or focusing an option shows a ghost of where Dec 12 would move: Dec 24 for A, Dec 15 for C, unchanged for B and D.
  - Audit trail: every event with actor, both times and chat link.
  - Actions for the account manager: Approve all, Approve selected, Edit a price, Decline and Share change order, each through `ConfirmPost`.
- **Public change-order page at `/co/:id`:** a calm, printable page the client opens from the chat link. It shows both companies' names, the ask, the clause excerpt, the options with prices and dates, the status, and "Reply in Discord with A, B, C or D". It is read-only, because decisions stay in chat. Add a print stylesheet that fits one A4 or Letter page.

---

## 8. Plan, Scope, Rooms, Ledger and Settings
- **Plan:** a custom SVG timeline with a weekly time axis. Milestones M1 (done) and M2 (due Dec 12) each show their items as bars coloured by status, with a "today" line. Pending change-request options can be overlaid as ghosts. After the swap, I9 slides out and the new item slides in, labelled *"Swapped via CR-004, no date change"*.
- **Scope, the contract map:** two columns, In scope and Out of scope. In scope lists deliverables D1 to D4 with clause, title and inclusions; Out of scope lists exclusions 1.3 and 3.5. Each clause carries a small heat strip counting the asks that hit it. Clicking a clause opens its SOW excerpt and those asks. An Edit button opens the YAML in CodeMirror with live validation and a diff before saving.
- **Rooms, the Switch map:** the page that shows judges how Switch is used. Draw it with React Flow:
  - Room nodes: `acme-client` with a Discord badge; `acme-intake`, `acme-delivery` and change rooms such as `acme-cr-004` with Slack badges. Each node shows its members as avatars, its role holders ("@client-desk: Scout") and its references as small chips.
  - Edges: the room links, each labelled with its description, such as "asks in, client-ready answers out".
  - Boundary: a dashed outline around the internal rooms, labelled "Scout never enters here, so internal pricing stays inside."
  - Live pulses: when a message flows in a room, its node pulses and the relevant link animates.
  - Matrix toggle: switch to a members-by-rooms table with ticks, for screen readers and printing.
- **Ledger:** a month picker; summary cards; a table of entries with date, reference, title, kind (change order, swap, goodwill, defect or in scope), hours, amount, approver and chat link; a "Download invoice CSV" button; renewal insight cards, such as *"4 reporting changes asked for this quarter: propose a reporting add-on"*.
- **Settings:** the rate card (blended rate, contingency by confidence, rounding); envelope rules with a live preview (*"A 3 h, high-confidence change priced at $140 would be sent automatically"*); the goodwill bucket; the Flip schedule with time pickers showing both zones; integration status for Switch, the LLM provider and the git host as read-only rows; and the demo mode toggle.

---

## 9. Data contract
Put every type in `src/lib/api/types.ts` and every call in `src/lib/api/client.ts`. If the backend returns a different shape, adapt it in one place, `src/lib/api/adapters.ts`. All times are ISO 8601 strings with offsets; money is integer cents.

```typescript
export type Category = 'DEFECT' | 'IN_SCOPE' | 'UNCLEAR' | 'OUT_OF_SCOPE' | 'DUPLICATE' | 'ALREADY_DECIDED';
export type AskStatus = 'received' | 'classified' | 'question_pending' | 'ticketed' | 'change_open' | 'linked' 
  | 'reminded' | 'change_sent' | 'approved' | 'swapped' | 'declined' | 'building' | 'preview' | 'accepted' | 'invoiced';
export type Confidence = 'high' | 'medium' | 'low';
export type OptionKey = 'A' | 'B' | 'C' | 'D';
export type ChatApp = 'discord' | 'slack' | 'mattermost' | 'teams';
export interface ChatLink { app: ChatApp; room: string; url: string }
export interface Ask { 
  id: string; quote: string; requester: string; createdAt: string; status: AskStatus; 
  category?: Category; clauseIds: string[]; relatedItem?: string; decisionId?: string; 
  confidence?: number; reason?: string; crId?: string; questionId?: string; 
  workItemIds: string[]; source: ChatLink; 
}
export interface Question { id: string; askId: string; text: string; choices: string[]; answer?: string; askedAt: string; answeredAt?: string }
export interface EstimateVersion { title?: string; p50Hours: number; p90Hours: number; confidence: Confidence }
export interface Estimate { 
  full: EstimateVersion; smaller?: EstimateVersion; touches: string[]; 
  similar: { ref: string; hours: number }[]; risks: string[]; assumptions: string[]; postedAt: string; 
}
export interface OptionQuote { 
  key: OptionKey; label: string; description: string; hours: number; priceCents: number; 
  milestoneId?: string; shiftDays: number; newDue?: string; swapOut?: string[]; swapIn?: string; draft?: boolean; 
}
export interface EnvelopeResult { passed: boolean; failedRules: string[] }
export interface ChangeRequest { 
  id: string; askId: string; title: string; room: ChatLink; createdAt: string; 
  status: 'estimating' | 'awaiting_confirmation' | 'awaiting_approval' | 'sent' | 'decided' | 'closed'; 
  estimate?: Estimate; confirmedHours?: number; confirmedBy?: string; options: OptionQuote[]; 
  envelope?: EnvelopeResult; approvedBy?: string; approvedAt?: string; approvedOptions?: OptionKey[]; 
  clientChoice?: OptionKey | 'DECLINE'; decidedAt?: string; 
}
export interface WorkItem { 
  id: string; askId: string; crId?: string; title: string; branch: string; prUrl?: string; previewUrl?: string; 
  status: 'queued' | 'building' | 'pr_open' | 'preview' | 'merged' | 'accepted'; 
}
export interface DeskState { holder: 'priya' | 'scout'; mode: 'copilot' | 'autopilot'; since: string; nextHandoverAt: string; nextHolder: 'priya' | 'scout' }
export interface Overview { 
  month: string; revenueProtectedCents: number; 
  changeOrders: { sent: number; approved: number; pending: number; swaps: number }; 
  goodwill: { usedHours: number; bucketHours: number }; 
  medianAskToDecisionMinutes: number; asksByCategory: Record<Category, number>; 
}
export interface LedgerEntry { 
  date: string; ref: string; title: string; hours: number; amountCents: number; approvedBy?: string; link?: ChatLink; 
  kind: 'change_order' | 'swap' | 'goodwill' | 'defect' | 'in_scope'; 
}
export interface PlanItem { id: string; title: string; deliverable: string; hours: number; status: 'done' | 'in_progress' | 'unstarted'; doneOn?: string; priority?: number }
export interface Milestone { id: string; name: string; due: string; items: PlanItem[] }
export interface Plan { capacityHoursPerWeek: number; milestones: Milestone[] }
export interface Member { id: string; name: string; kind: 'person' | 'agent'; side: 'client' | 'agency'; vendor?: 'OpenCode' | 'Claude Code' | 'Codex' | 'Custom' }
export interface Room { id: string; name: string; app: ChatApp; kind: 'client' | 'intake' | 'delivery' | 'change'; members: Member[]; roles: { name: string; holder?: string }[]; references: string[] }
export interface RoomMap { rooms: Room[]; links: { from: string; to: string; description: string }[] }
export interface StreamEvent { id: string; ts: string; type: string; actor: string; text: string; askId?: string; crId?: string; roomId?: string; link?: ChatLink; data?: unknown }
```

### Endpoints

| Method | Path | Returns |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Liveness, Switch connection state and server time |
| `GET` | `/api/overview?month=2026-11` | Overview |
| `GET` | `/api/desk` | DeskState |
| `GET` | `/api/asks` with filters and a cursor | A page of Ask items |
| `GET` | `/api/asks/:id` | Ask with its question, events and work items |
| `POST` | `/api/asks/:id/goodwill` | The updated Ask |
| `GET` | `/api/change-requests` | ChangeRequest list |
| `GET` | `/api/change-requests/:id` | ChangeRequest with events and work items |
| `POST` | `/api/change-requests/:id/approve` | Body with the approved option keys |
| `POST` | `/api/change-requests/:id/decline` | Body with a reason |
| `PATCH` | `/api/change-requests/:id/options/:key` | Body with the new price in cents |
| `GET` | `/api/ledger?month=2026-11` | Overview plus LedgerEntry rows |
| `GET` | `/api/invoice?month=2026-11` | CSV |
| `GET` | `/api/renewal` | Themes with ask ids, hours and a proposal |
| `GET`, `PUT` | `/api/config/:name` | `scope-map`, `rate-card`, `envelope`, `plan` or `schedule` |
| `GET` | `/api/rooms` | RoomMap |
| `GET` | `/api/public/co/:id` | A read-only change order for the public page |
| `POST` | `/api/demo/flip`, `/api/demo/morning`, `/api/demo/clock` | Demo controls |
| `GET` | `/api/stream` | Server-sent StreamEvent messages |

**Stream event types:** `desk.handover`, `room.message`, `ask.created`, `ask.classified`, `question.asked`, `question.answered`, `cr.created`, `cr.estimated`, `cr.confirmed`, `cr.priced`, `cr.approved`, `co.sent`, `client.decided`, `work.created`, `work.pr_opened`, `work.preview_ready`, `ask.accepted`, `brief.posted`, `plan.updated`, `ledger.updated`. On each event, update the TanStack Query cache directly, then refetch the affected queries in the background.

**Settings:** `VITE_API_MODE` is `mock` (default) or `live`; `VITE_API_BASE_URL` points at the backend (`http://localhost:8000`); the API token is asked for on first load in live mode.

---

## 10. Mock mode, the story engine and Director mode
In mock mode the app must look exactly as it will live. MSW serves every endpoint from an in-memory database, and a story engine replays the demo through the same stream interface the live mode uses, so every page stays consistent.

### Seed data in `src/mocks/seed.ts`:
- **Project:** Acme Web Portal, built by Pixel & Co. Month November 2026. Currency USD, rate $45 an hour, contingency 5%, 15% or 25% for high, medium or low confidence, prices rounded to $10. Envelope: up to $500, high confidence, no milestone impact. Goodwill bucket: 8 hours a month.
- **Scope:** D1, clause 1.1, Responsive web app (browsers including Safari; login). D2, clause 2.4, Theming (light, dark, brand colours, brand typeface). D3, clause 3.2, Reports page (filters, CSV export). D4, clause 4.1, Admin analytics dashboard. Exclusions: 1.3 native mobile apps, 3.5 third-party BI integrations. Warranty 30 days.
- **Plan:** capacity 120 hours a week. M1 Launch, due Oct 25, done: I1 Responsive layout and login, 46 h, done Oct 20; I2 Reports page with filters v1, 40 h, done Oct 25. M2 Reporting release, due Dec 12: I8 CSV export, 12 h, done Oct 28; I9 Admin analytics dashboard, 58 h, unstarted; I10 Report filters v2, 24 h, unstarted.
- **History:** ASK-0001 (Oct 12) logo upload on Settings, in scope, accepted. ASK-0002 (Oct 15) text users when reports are ready, which produced decision DEC-002, "Notifications are email-only; no SMS". ASK-0003 (Oct 22) connect to our Slack, out of scope, CR-001 declined. ASK-0004 (Oct 29) monthly summary email, out of scope, CR-002 approved Oct 30 at 20 h for $950. ASK-0005 (Nov 2) send reports every Monday, out of scope, CR-003 approved Nov 2 at 40 h for $1,890. ASK-0006 (Nov 3) a "last updated" time on reports, out of scope, 2 h of goodwill from Priya.
- **Starting KPIs (Nov 5, 6:59 PM IST):** revenue protected $1,890; change orders sent 1, approved 1, pending 0, swaps 0; goodwill 2 of 8 hours; median ask to decision 52 minutes.

### Story schedule in `src/mocks/story.ts`
Also emit a `room.message` event for every chat message along the way, so the Rooms map pulses.

| Time (IST) | Time (ET) | Events |
| :--- | :--- | :--- |
| Nov 5, 7:00 PM | 8:30 AM | `desk.handover` Priya to Scout, autopilot |
| 8:30 PM | 10:00 AM | Sam's four-ask message in `acme-client` |
| 8:30:20 PM | 10:00 AM | `ask.created` ASK-0007 to ASK-0010 |
| 8:30:40 PM | 10:00 AM | `ask.classified`: 0007 Defect 1.1; 0008 In scope 2.4; 0009 Unclear 3.2; 0010 Out of scope 1.3 |
| 8:30:50 PM | 10:00 AM | `question.asked` Q-0001: "CSV that opens in Excel, or a native .xlsx file with formatting?" |
| 8:31 PM | 10:01 AM | `cr.created` CR-004 in `acme-cr-004`; `work.created` W-0001 Safari fix and W-0002 dark mode |
| 8:32:30 PM | 10:02 AM | `question.answered` "a native .xlsx file"; 0009 reclassified Out of scope 3.2; `cr.created` CR-005 |
| 8:36 PM | 10:06 AM | `cr.estimated` CR-005: 3 h, high |
| 8:37 PM | 10:07 AM | `cr.priced` CR-005 option A $140, envelope passed; `co.sent` |
| 8:41 PM | 10:11 AM | `client.decided` CR-005 A; `ledger.updated` to $2,030; `work.created` W-0003 Excel export |
| 8:44 PM | 10:14 AM | `cr.estimated` CR-004: full P50 190, P90 240, medium; smaller 56 and 64, high; similar 61, 52 and 18 h |
| 8:45 PM | 10:15 AM | `cr.priced` CR-004 draft at 190 h; envelope failed on price, confidence and milestone impact; waiting for `@delivery-lead` |
| 9:20 PM to 10:12 PM | 10:50 to 11:42 AM | Pull requests #12 (Safari fix) and #13 (dark mode) open; previews ready |
| 11:40 PM | 1:10 PM | `ask.accepted` ASK-0008, dark mode |
| Nov 6, 12:30 AM | 2:00 PM | Pull request #14 (Excel export) opens; preview ready at 12:38 AM |
| 9:30 AM | 11:00 PM, Nov 5 | `desk.handover` Scout to Priya; `brief.posted` |
| 9:42 AM | 11:12 PM, Nov 5 | `cr.confirmed` CR-004 at 200 h by Ravi; `cr.priced` A $10,350 (M2 to Dec 24), B $10,350, C $2,650 (M2 to Dec 15), D $0 swapping I9 |
| 9:50 AM | 11:20 PM, Nov 5 | `cr.approved` CR-004 A to D by Priya; `co.sent` |
| 7:00 PM | 8:30 AM | `desk.handover` Priya to Scout |
| 7:10 PM | 8:40 AM | `client.decided` CR-004 D; `plan.updated`: I9 out, I11 "View-only Android app" 56 h in; `ledger.updated` with one swap |

**Final KPIs:** revenue protected $2,030; change orders sent 3, approved 2, pending 0, swaps 1; goodwill 2 of 8 hours.

### Director mode (for recording the video)
A floating panel opened with the `D` key or `?director` in the URL, available only in mock or demo mode.
- Play and pause; speeds 1×, 10×, 60× and 600×; step to the next event.
- Jump to the ten beats: The Flip, Sam's message, Sorted in a minute, Excel approved, Android estimate, Previews up, Dark mode accepted, Morning handover, Options approved, Sam picks D. Jumping backwards resets and fast-forwards silently.
- Buttons for Flip now, Morning now and Reset.
- Keys: space to play or pause, `.` for the next event, `]` and `[` for the next and previous beat, `R` to reset.
- In live mode, the same controls call `/api/demo/*` instead.

---

## 11. Quality bar
- **Accessibility:** WCAG 2.2 AA. Full keyboard use with visible focus, labelled controls, text summaries and table fallbacks for every chart, an `aria-live` region for the feed, colour never the only signal, and reduced motion respected.
- **Responsive:** check 390, 768, 1024 and 1440 px. The page never scrolls sideways; wide tables scroll inside their own container.
- **States:** skeletons while loading; helpful empty states, such as *"No asks yet. When a client asks for something in chat, it appears here within a minute."*; clear errors with a retry; the Disconnected banner.
- **Performance:** route-level code splitting, React Flow and CodeMirror loaded lazily, long lists virtualised, and a Lighthouse score of at least 95 for performance, accessibility and best practices on Mission Control in a production build.
- **Formatting:** money through `Intl.NumberFormat` in USD, with currency as a setting; hours with a decimal only when needed; both time zones everywhere.
- **Unit tests:** formatters, the options cards, the estimate chart's scale, the Desk switch states and the story engine's ordering. Share the MSW handlers between the app and the tests.
- **End-to-end test:** Playwright runs the story at 600× in mock mode and asserts the final state: revenue protected $2,030, CR-004's choice D, I9 removed and I11 added, and the desk back with Scout. It also saves screenshots of every page in light and dark at 1440 and 390 px for review.

---

## 12. Build order and definition of done
Build in this order, checking each phase in the browser before the next:
1. Scaffold, tokens, fonts, the shell, themes, types, seed data and MSW.
2. The story engine and Mission Control: the Desk, KPIs, pipeline, activity feed and Needs a yes.
3. The change-request detail: estimate chart, options, what-if timeline and actions.
4. The Asks table and drawer.
5. The Plan timeline, and the Scope map with its YAML editor.
6. The Rooms map with live pulses and the matrix toggle.
7. The Ledger, Settings and the public change-order page.
8. Director mode, the Switch lens and the command palette.
9. Polish: accessibility, responsiveness, motion, empty and error states, tests and Lighthouse.

**The demo moments that must look perfect:**
- At 7:00 PM IST the Desk switch slides to Scout and the UI turns to night, smoothly.
- Four ask cards appear and get their category and clause within the story's first minute.
- The revenue ticker moves from $1,890 to $2,030 when CR-005 is approved.
- CR-004 shows the estimate range with history ticks and four option cards, and hovering A moves Dec 12 to Dec 24 on the timeline.
- At 9:30 AM IST the switch returns to Priya, the UI turns to day, and Needs a yes lists CR-004.
- When Sam picks D, card D wins, the swap animates in the plan, and the ledger shows one swap.
- The Rooms map pulses on every message, and the membership boundary is obvious.
- The Switch lens explains rooms, roles, links, references and agents in one click.
- Every page works in light and dark themes, at 390 and 1440 px, and by keyboard.
- Live mode works by setting `VITE_API_MODE=live` and `VITE_API_BASE_URL`, with no code changes.

**Finish with a README:** screenshots, how to run it (`npm install`, `npm run dev`), mock versus live mode, keyboard shortcuts, and the backend contract additions from section 9.
