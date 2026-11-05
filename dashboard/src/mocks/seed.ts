/**
 * Seed data for mock mode (FRONTEND_PROMPT §10). Everything here is the state of the
 * Acme Web Portal project at Nov 5, 2026, 6:59 PM IST, just before the story starts.
 */
import type {
  Ask,
  ChangeRequest,
  ChatLink,
  Clause,
  DeskState,
  LedgerEntry,
  Member,
  Plan,
  Question,
  RoomMap,
  StreamEvent,
  WorkItem,
} from '@/lib/api/types'

/** `ist('11-05', '19:00')` → `2026-11-05T19:00:00+05:30`. */
export function ist(monthDay: string, time: string): string {
  const t = time.length === 5 ? `${time}:00` : time
  return `2026-${monthDay}T${t}+05:30`
}

export const PROJECT = {
  name: 'Acme Web Portal',
  client: 'Acme',
  agency: 'Pixel & Co',
  month: '2026-11',
  currency: 'USD',
  rateCents: 4500,
  contingency: { high: 0.05, medium: 0.15, low: 0.25 },
  roundingCents: 1000,
  envelope: { maxPriceCents: 50000, confidence: 'high' as const, milestoneImpact: false },
  goodwillBucketHours: 8,
  warrantyDays: 30,
} as const

export const STORY_START = ist('11-05', '18:59')

// ---------------------------------------------------------------- people and agents

export const MEMBERS: Record<string, Member> = {
  sam: { id: 'sam', name: 'Sam', kind: 'person', side: 'client' },
  priya: { id: 'priya', name: 'Priya', kind: 'person', side: 'agency' },
  ravi: { id: 'ravi', name: 'Ravi', kind: 'person', side: 'agency' },
  aisha: { id: 'aisha', name: 'Aisha', kind: 'person', side: 'agency' },
  scout: { id: 'scout', name: 'Scout', kind: 'agent', side: 'agency', vendor: 'OpenCode' },
  clerk: { id: 'clerk', name: 'Clerk', kind: 'agent', side: 'agency', vendor: 'Custom' },
  estimator: { id: 'estimator', name: 'Estimator', kind: 'agent', side: 'agency', vendor: 'Claude Code' },
  builder: { id: 'builder', name: 'Builder', kind: 'agent', side: 'agency', vendor: 'Codex' },
}

export const MEMBER_TITLES: Record<string, string> = {
  sam: 'Product owner, Acme',
  priya: 'Account manager',
  ravi: 'Delivery lead',
  aisha: 'Developer',
  scout: 'Client-desk agent',
  clerk: 'Contract-keeper agent',
  estimator: 'Estimates from the code',
  builder: 'Builds approved work',
}

// ---------------------------------------------------------------- chat links

export function discord(room: string, msg?: string): ChatLink {
  return {
    app: 'discord',
    room,
    url: `https://discord.com/channels/acme-hq/${room}${msg ? `/${msg}` : ''}`,
  }
}

export function slack(room: string, ts?: string): ChatLink {
  return {
    app: 'slack',
    room,
    url: `https://pixelco.slack.com/archives/${room}${ts ? `/p${ts}` : ''}`,
  }
}

// ---------------------------------------------------------------- scope

export const CLAUSES: Clause[] = [
  {
    id: '1.1',
    deliverable: 'D1',
    title: 'Responsive web app',
    kind: 'in',
    includes: ['Current browsers including Safari', 'Login'],
    excerpt: 'Pixel & Co will deliver a responsive web app that works in current browsers, including Safari, with login.',
  },
  {
    id: '2.4',
    deliverable: 'D2',
    title: 'Theming',
    kind: 'in',
    includes: ['Light theme', 'Dark theme', 'Brand colours', 'Brand typeface'],
    excerpt: 'The app supports light and dark themes using Acme brand colours and typeface.',
  },
  {
    id: '3.2',
    deliverable: 'D3',
    title: 'Reports page',
    kind: 'in',
    includes: ['Filters', 'CSV export'],
    excerpt: 'A reports page with filters and export to CSV.',
  },
  {
    id: '4.1',
    deliverable: 'D4',
    title: 'Admin analytics dashboard',
    kind: 'in',
    includes: ['Usage charts for admins'],
    excerpt: 'An admin analytics dashboard showing usage for Acme administrators.',
  },
  {
    id: '1.3',
    title: 'Native mobile apps',
    kind: 'out',
    includes: [],
    excerpt: 'Native iOS and Android apps are out of scope for this statement of work.',
  },
  {
    id: '3.5',
    title: 'Third-party BI integrations',
    kind: 'out',
    includes: [],
    excerpt: 'Integrations with third-party BI tools are out of scope.',
  },
]

// ---------------------------------------------------------------- plan

export const PLAN: Plan = {
  capacityHoursPerWeek: 120,
  milestones: [
    {
      id: 'M1',
      name: 'Launch',
      due: '2026-10-25',
      items: [
        { id: 'I1', title: 'Responsive layout and login', deliverable: 'D1', hours: 46, status: 'done', doneOn: '2026-10-20' },
        { id: 'I2', title: 'Reports page with filters v1', deliverable: 'D3', hours: 40, status: 'done', doneOn: '2026-10-25' },
      ],
    },
    {
      id: 'M2',
      name: 'Reporting release',
      due: '2026-12-12',
      items: [
        { id: 'I8', title: 'CSV export', deliverable: 'D3', hours: 12, status: 'done', doneOn: '2026-10-28' },
        { id: 'I9', title: 'Admin analytics dashboard', deliverable: 'D4', hours: 58, status: 'unstarted', priority: 2 },
        { id: 'I10', title: 'Report filters v2', deliverable: 'D3', hours: 24, status: 'unstarted', priority: 1 },
      ],
    },
  ],
}

// ---------------------------------------------------------------- history

export const ASKS: Ask[] = [
  {
    id: 'ASK-0001',
    quote: 'Can we upload our logo on the Settings page?',
    requester: 'sam',
    createdAt: ist('10-12', '20:14'),
    status: 'accepted',
    category: 'IN_SCOPE',
    clauseIds: ['2.4'],
    confidence: 0.93,
    reason: 'Brand assets are part of theming (clause 2.4).',
    workItemIds: [],
    source: discord('acme-client', '1001'),
  },
  {
    id: 'ASK-0002',
    quote: 'Could the app text users when their reports are ready?',
    requester: 'sam',
    createdAt: ist('10-15', '21:02'),
    status: 'declined',
    category: 'OUT_OF_SCOPE',
    clauseIds: ['3.2'],
    decisionId: 'DEC-002',
    confidence: 0.88,
    reason: 'Decision DEC-002: notifications are email-only; no SMS.',
    workItemIds: [],
    source: discord('acme-client', '1002'),
  },
  {
    id: 'ASK-0003',
    quote: 'Can you connect the portal to our Slack?',
    requester: 'sam',
    createdAt: ist('10-22', '19:40'),
    status: 'declined',
    category: 'OUT_OF_SCOPE',
    clauseIds: ['3.5'],
    confidence: 0.9,
    reason: 'Third-party integrations are excluded (clause 3.5).',
    crId: 'CR-001',
    workItemIds: [],
    source: discord('acme-client', '1003'),
  },
  {
    id: 'ASK-0004',
    quote: 'We need a monthly summary email for managers.',
    requester: 'sam',
    createdAt: ist('10-29', '20:05'),
    status: 'invoiced',
    category: 'OUT_OF_SCOPE',
    clauseIds: ['3.2'],
    confidence: 0.86,
    reason: 'Reports cover the page and CSV export, not scheduled emails (clause 3.2).',
    crId: 'CR-002',
    workItemIds: [],
    source: discord('acme-client', '1004'),
  },
  {
    id: 'ASK-0005',
    quote: 'Can reports go out automatically every Monday?',
    requester: 'sam',
    createdAt: ist('11-02', '19:48'),
    status: 'building',
    category: 'OUT_OF_SCOPE',
    clauseIds: ['3.2'],
    confidence: 0.91,
    reason: 'Scheduled delivery is beyond the reports page and CSV export (clause 3.2).',
    crId: 'CR-003',
    workItemIds: [],
    source: discord('acme-client', '1005'),
  },
  {
    id: 'ASK-0006',
    quote: 'Could reports show a "last updated" time?',
    requester: 'sam',
    createdAt: ist('11-03', '20:22'),
    status: 'accepted',
    category: 'OUT_OF_SCOPE',
    clauseIds: ['3.2'],
    confidence: 0.82,
    reason: 'Small and out of scope; Priya covered it with 2 h of goodwill.',
    workItemIds: [],
    source: discord('acme-client', '1006'),
  },
]

/** Internal change-request record; `sentAt` drives the month's change-order counts. */
export interface DbChangeRequest extends ChangeRequest {
  sentAt?: string
}

export const CHANGE_REQUESTS: DbChangeRequest[] = [
  {
    id: 'CR-001',
    askId: 'ASK-0003',
    title: 'Slack integration',
    room: slack('acme-cr-001'),
    createdAt: ist('10-22', '19:42'),
    status: 'closed',
    options: [],
    clientChoice: 'DECLINE',
    decidedAt: ist('10-23', '20:10'),
    sentAt: ist('10-22', '21:30'),
  },
  {
    id: 'CR-002',
    askId: 'ASK-0004',
    title: 'Monthly summary email',
    room: slack('acme-cr-002'),
    createdAt: ist('10-29', '20:07'),
    status: 'decided',
    confirmedHours: 20,
    confirmedBy: 'ravi',
    options: [
      { key: 'A', label: 'Add it now', description: 'Build the monthly email in this phase.', hours: 20, priceCents: 95000, shiftDays: 0 },
    ],
    approvedBy: 'priya',
    approvedAt: ist('10-30', '10:05'),
    approvedOptions: ['A'],
    clientChoice: 'A',
    decidedAt: ist('10-30', '20:40'),
    sentAt: ist('10-30', '10:06'),
  },
  {
    id: 'CR-003',
    askId: 'ASK-0005',
    title: 'Monday report delivery',
    room: slack('acme-cr-003'),
    createdAt: ist('11-02', '19:50'),
    status: 'decided',
    confirmedHours: 40,
    confirmedBy: 'ravi',
    options: [
      { key: 'A', label: 'Add it now', description: 'Schedule reports every Monday, in this phase.', hours: 40, priceCents: 189000, shiftDays: 0 },
    ],
    approvedBy: 'priya',
    approvedAt: ist('11-02', '20:20'),
    approvedOptions: ['A'],
    clientChoice: 'A',
    decidedAt: ist('11-02', '20:40'),
    sentAt: ist('11-02', '20:21'),
  },
]

export const QUESTIONS: Question[] = []
export const WORK_ITEMS: WorkItem[] = []

export const LEDGER: LedgerEntry[] = [
  {
    date: ist('10-30', '20:40'),
    ref: 'CR-002',
    title: 'Monthly summary email',
    hours: 20,
    amountCents: 95000,
    approvedBy: 'priya',
    link: slack('acme-cr-002'),
    kind: 'change_order',
  },
  {
    date: ist('11-02', '20:40'),
    ref: 'CR-003',
    title: 'Monday report delivery',
    hours: 40,
    amountCents: 189000,
    approvedBy: 'priya',
    link: slack('acme-cr-003'),
    kind: 'change_order',
  },
  {
    date: ist('11-03', '20:40'),
    ref: 'ASK-0006',
    title: '"Last updated" time on reports',
    hours: 2,
    amountCents: 0,
    approvedBy: 'priya',
    link: slack('acme-intake'),
    kind: 'goodwill',
  },
]

export const DESK: DeskState = {
  holder: 'priya',
  mode: 'copilot',
  since: ist('11-05', '09:30'),
  nextHandoverAt: ist('11-05', '19:00'),
  nextHolder: 'scout',
}

/**
 * Minutes from ask to decision for this month's decided asks (median 52 at the start).
 */
export const DECISION_MINUTES: number[] = [38, 44, 52, 66, 71]

/** A few recent events so the activity feed has history at 6:59 PM. */
export const HISTORY_EVENTS: StreamEvent[] = [
  {
    id: 'h-1',
    ts: ist('11-03', '20:40'),
    type: 'ledger.updated',
    actor: 'priya',
    text: 'Priya covered ASK-0006 ("last updated" time) with 2 h of goodwill.',
    askId: 'ASK-0006',
    link: slack('acme-intake'),
  },
  {
    id: 'h-2',
    ts: ist('11-05', '09:30'),
    type: 'desk.handover',
    actor: 'priya',
    text: 'Priya took the client desk from Scout. Copilot mode.',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
  },
  {
    id: 'h-3',
    ts: ist('11-05', '09:31'),
    type: 'brief.posted',
    actor: 'scout',
    text: 'Scout posted the morning brief: nothing waiting on a yes.',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
  },
  {
    id: 'h-4',
    ts: ist('11-05', '16:12'),
    type: 'work.pr_opened',
    actor: 'aisha',
    text: 'Aisha opened pull request #11 for Monday report delivery (CR-003).',
    crId: 'CR-003',
    askId: 'ASK-0005',
    link: slack('acme-delivery'),
  },
]

export const ROOMS: RoomMap = {
  rooms: [
    {
      id: 'acme-client',
      name: 'acme-client',
      app: 'discord',
      kind: 'client',
      members: [MEMBERS.sam!, MEMBERS.priya!, MEMBERS.scout!],
      roles: [{ name: '@client-desk', holder: 'priya' }],
      references: ['SOW v1.2', 'Plan'],
    },
    {
      id: 'acme-intake',
      name: 'acme-intake',
      app: 'slack',
      kind: 'intake',
      members: [MEMBERS.priya!, MEMBERS.scout!, MEMBERS.clerk!, MEMBERS.ravi!],
      roles: [
        { name: '@account-manager', holder: 'priya' },
        { name: '@client-desk', holder: 'priya' },
      ],
      references: ['SOW v1.2', 'Decisions'],
    },
    {
      id: 'acme-delivery',
      name: 'acme-delivery',
      app: 'slack',
      kind: 'delivery',
      members: [MEMBERS.ravi!, MEMBERS.aisha!, MEMBERS.builder!, MEMBERS.estimator!],
      roles: [{ name: '@delivery-lead', holder: 'ravi' }],
      references: ['Repo', 'Plan'],
    },
  ],
  links: [
    { from: 'acme-client', to: 'acme-intake', description: 'asks in, client-ready answers out' },
    { from: 'acme-intake', to: 'acme-delivery', description: 'approved work in, previews out' },
  ],
}
