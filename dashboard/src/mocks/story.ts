/**
 * The demo story (FRONTEND_PROMPT §10), as an ordered schedule of stream events.
 * Each step may mutate the mock database; the story engine applies steps in order and
 * emits them through the same stream interface the live mode uses.
 */
import type { Ask, OptionQuote, StreamEvent } from '@/lib/api/types'
import { findAsk, findCr, findWork, upsert, type MockDb } from './db'
import { discord, ist, slack } from './seed'

export type BeatId =
  | 'flip'
  | 'sam-message'
  | 'sorted'
  | 'excel-approved'
  | 'android-estimate'
  | 'previews-up'
  | 'dark-mode-accepted'
  | 'morning-handover'
  | 'options-approved'
  | 'sam-picks-d'

export const BEATS: { id: BeatId; label: string }[] = [
  { id: 'flip', label: 'The Flip' },
  { id: 'sam-message', label: "Sam's message" },
  { id: 'sorted', label: 'Sorted in a minute' },
  { id: 'excel-approved', label: 'Excel approved' },
  { id: 'android-estimate', label: 'Android estimate' },
  { id: 'previews-up', label: 'Previews up' },
  { id: 'dark-mode-accepted', label: 'Dark mode accepted' },
  { id: 'morning-handover', label: 'Morning handover' },
  { id: 'options-approved', label: 'Options approved' },
  { id: 'sam-picks-d', label: 'Sam picks D' },
]

export interface StoryStep extends Omit<StreamEvent, 'id'> {
  /** The step that starts a beat carries its id. */
  beat?: BeatId
  apply?: (db: MockDb) => void
  /** Skip the step (silently) when someone already did it from the dashboard. */
  skipIf?: (db: MockDb) => boolean
}

const SAM_MESSAGE =
  'Morning team. A few things: login is broken on Safari again, can we get dark mode, can the reports export to Excel, and we would love an Android app for the board meeting.'

function newAsk(id: string, quote: string, msg: string): Ask {
  return {
    id,
    quote,
    requester: 'sam',
    createdAt: ist('11-05', '20:30:20'),
    status: 'received',
    clauseIds: [],
    workItemIds: [],
    source: discord('acme-client', msg),
  }
}

const CR004_OPTIONS: OptionQuote[] = [
  {
    key: 'A',
    label: 'Add it now',
    description: 'Build the full Android app in this phase; M2 moves to Dec 24.',
    hours: 200,
    priceCents: 1_035_000,
    milestoneId: 'M2',
    shiftDays: 12,
    newDue: '2026-12-24',
  },
  {
    key: 'B',
    label: 'Next phase',
    description: 'Build the full Android app after M2, with no date change now.',
    hours: 200,
    priceCents: 1_035_000,
    shiftDays: 0,
  },
  {
    key: 'C',
    label: 'View-only now',
    description: 'A view-only app for the board meeting; M2 moves 3 days.',
    hours: 56,
    priceCents: 265_000,
    milestoneId: 'M2',
    shiftDays: 3,
    newDue: '2026-12-15',
  },
  {
    key: 'D',
    label: 'Swap',
    description: 'The view-only app in place of unstarted I9, at no cost and no date change.',
    hours: 56,
    priceCents: 0,
    milestoneId: 'M2',
    shiftDays: 0,
    swapOut: ['I9'],
    swapIn: 'View-only Android app',
  },
]

function setDesk(db: MockDb, holder: 'priya' | 'scout', since: string, next: string): void {
  db.desk = {
    holder,
    mode: holder === 'priya' ? 'copilot' : 'autopilot',
    since,
    nextHandoverAt: next,
    nextHolder: holder === 'priya' ? 'scout' : 'priya',
  }
  for (const room of db.rooms.rooms) {
    for (const role of room.roles) if (role.name === '@client-desk') role.holder = holder
  }
}

export const STORY: StoryStep[] = [
  // ------------------------------------------------------------ Beat 1: the flip
  {
    beat: 'flip',
    ts: ist('11-05', '19:00'),
    type: 'desk.handover',
    actor: 'scout',
    text: 'Priya handed the client desk to Scout. Autopilot until 9:30 AM IST.',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
    data: { from: 'priya', to: 'scout' },
    apply: (db) => setDesk(db, 'scout', ist('11-05', '19:00'), ist('11-06', '09:30')),
  },
  // ------------------------------------------------------------ Beat 2: Sam's message
  {
    beat: 'sam-message',
    ts: ist('11-05', '20:30'),
    type: 'room.message',
    actor: 'sam',
    text: `Sam in #acme-client: "${SAM_MESSAGE}"`,
    roomId: 'acme-client',
    link: discord('acme-client', '1107'),
  },
  ...(
    [
      ['ASK-0007', 'Login is broken on Safari again.'],
      ['ASK-0008', 'Can we get dark mode?'],
      ['ASK-0009', 'Can the reports export to Excel?'],
      ['ASK-0010', 'We would love an Android app for the board meeting.'],
    ] as const
  ).map(
    ([id, quote]): StoryStep => ({
      ts: ist('11-05', '20:30:20'),
      type: 'ask.created',
      actor: 'scout',
      text: `Scout logged ${id}: "${quote}"`,
      askId: id,
      roomId: 'acme-intake',
      link: discord('acme-client', '1107'),
      data: { group: 'sam-1107' },
      apply: (db) => upsert(db.asks, newAsk(id, quote, '1107')),
    }),
  ),
  // ------------------------------------------------------------ Beat 3: sorted in a minute
  {
    beat: 'sorted',
    ts: ist('11-05', '20:30:40'),
    type: 'ask.classified',
    actor: 'clerk',
    text: 'Clerk sorted ASK-0007 as a defect under clause 1.1. Defects are always free.',
    askId: 'ASK-0007',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
    data: { group: 'sort-1107' },
    apply: (db) =>
      Object.assign(findAsk(db, 'ASK-0007'), {
        status: 'ticketed',
        category: 'DEFECT',
        clauseIds: ['1.1'],
        confidence: 0.96,
        reason: 'Clause 1.1 promises login in current browsers, including Safari.',
      } satisfies Partial<Ask>),
  },
  {
    ts: ist('11-05', '20:30:40'),
    type: 'ask.classified',
    actor: 'clerk',
    text: 'Clerk sorted ASK-0008, dark mode, as in scope under clause 2.4.',
    askId: 'ASK-0008',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
    data: { group: 'sort-1107' },
    apply: (db) =>
      Object.assign(findAsk(db, 'ASK-0008'), {
        status: 'ticketed',
        category: 'IN_SCOPE',
        clauseIds: ['2.4'],
        confidence: 0.94,
        reason: 'Clause 2.4 includes a dark theme.',
      } satisfies Partial<Ask>),
  },
  {
    ts: ist('11-05', '20:30:40'),
    type: 'ask.classified',
    actor: 'clerk',
    text: 'Clerk marked ASK-0009, Excel export, as unclear under clause 3.2.',
    askId: 'ASK-0009',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
    data: { group: 'sort-1107' },
    apply: (db) =>
      Object.assign(findAsk(db, 'ASK-0009'), {
        status: 'classified',
        category: 'UNCLEAR',
        clauseIds: ['3.2'],
        confidence: 0.58,
        reason: 'Clause 3.2 covers CSV export; a native Excel file would be extra.',
      } satisfies Partial<Ask>),
  },
  {
    ts: ist('11-05', '20:30:40'),
    type: 'ask.classified',
    actor: 'clerk',
    text: 'Clerk sorted ASK-0010, an Android app, as out of scope under clause 1.3.',
    askId: 'ASK-0010',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
    data: { group: 'sort-1107' },
    apply: (db) =>
      Object.assign(findAsk(db, 'ASK-0010'), {
        status: 'classified',
        category: 'OUT_OF_SCOPE',
        clauseIds: ['1.3'],
        confidence: 0.97,
        reason: 'Clause 1.3 excludes native mobile apps.',
      } satisfies Partial<Ask>),
  },
  {
    ts: ist('11-05', '20:30:50'),
    type: 'question.asked',
    actor: 'scout',
    text: 'Scout asked Sam one question about Excel export (clause 3.2).',
    askId: 'ASK-0009',
    roomId: 'acme-client',
    link: discord('acme-client', '1108'),
    apply: (db) => {
      upsert(db.questions, {
        id: 'Q-0001',
        askId: 'ASK-0009',
        text: 'CSV that opens in Excel, or a native .xlsx file with formatting?',
        choices: ['CSV that opens in Excel', 'A native .xlsx file with formatting'],
        askedAt: ist('11-05', '20:30:50'),
      })
      Object.assign(findAsk(db, 'ASK-0009'), { status: 'question_pending', questionId: 'Q-0001' })
    },
  },
  {
    ts: ist('11-05', '20:30:50'),
    type: 'room.message',
    actor: 'scout',
    text: 'Scout in #acme-client: "Quick check on Excel: a CSV that opens in Excel, or a native .xlsx file with formatting?"',
    roomId: 'acme-client',
    link: discord('acme-client', '1108'),
  },
  {
    ts: ist('11-05', '20:31'),
    type: 'cr.created',
    actor: 'clerk',
    text: 'Clerk opened change request CR-004, Android app, in #acme-cr-004.',
    askId: 'ASK-0010',
    crId: 'CR-004',
    roomId: 'acme-cr-004',
    link: slack('acme-cr-004'),
    apply: (db) => {
      upsert(db.changeRequests, {
        id: 'CR-004',
        askId: 'ASK-0010',
        title: 'Android app',
        room: slack('acme-cr-004'),
        createdAt: ist('11-05', '20:31'),
        status: 'estimating',
        options: [],
      })
      Object.assign(findAsk(db, 'ASK-0010'), { status: 'change_open', crId: 'CR-004' })
    },
  },
  {
    ts: ist('11-05', '20:31'),
    type: 'work.created',
    actor: 'builder',
    text: 'Builder started W-0001, the Safari login fix, and W-0002, dark mode.',
    askId: 'ASK-0007',
    roomId: 'acme-delivery',
    link: slack('acme-delivery'),
    apply: (db) => {
      upsert(db.workItems, {
        id: 'W-0001',
        askId: 'ASK-0007',
        title: 'Safari login fix',
        branch: 'fix/safari-login',
        status: 'building',
      })
      upsert(db.workItems, {
        id: 'W-0002',
        askId: 'ASK-0008',
        title: 'Dark mode',
        branch: 'feat/dark-mode',
        status: 'building',
      })
      Object.assign(findAsk(db, 'ASK-0007'), { status: 'building', workItemIds: ['W-0001'] })
      Object.assign(findAsk(db, 'ASK-0008'), { status: 'building', workItemIds: ['W-0002'] })
    },
  },
  {
    ts: ist('11-05', '20:32:30'),
    type: 'room.message',
    actor: 'sam',
    text: 'Sam in #acme-client: "A native .xlsx file, please. Finance lives in Excel."',
    roomId: 'acme-client',
    link: discord('acme-client', '1109'),
  },
  {
    ts: ist('11-05', '20:32:30'),
    type: 'question.answered',
    actor: 'sam',
    text: 'Sam answered: a native .xlsx file. Clerk moved ASK-0009 to out of scope (clause 3.2).',
    askId: 'ASK-0009',
    roomId: 'acme-client',
    link: discord('acme-client', '1109'),
    apply: (db) => {
      const q = db.questions.find((x) => x.id === 'Q-0001')
      if (q) Object.assign(q, { answer: 'A native .xlsx file with formatting', answeredAt: ist('11-05', '20:32:30') })
      Object.assign(findAsk(db, 'ASK-0009'), {
        status: 'classified',
        category: 'OUT_OF_SCOPE',
        confidence: 0.92,
        reason: 'Clause 3.2 covers CSV export only; a formatted .xlsx file is extra.',
      } satisfies Partial<Ask>)
    },
  },
  {
    ts: ist('11-05', '20:32:30'),
    type: 'cr.created',
    actor: 'clerk',
    text: 'Clerk opened change request CR-005, native Excel export, in #acme-cr-005.',
    askId: 'ASK-0009',
    crId: 'CR-005',
    roomId: 'acme-cr-005',
    link: slack('acme-cr-005'),
    apply: (db) => {
      upsert(db.changeRequests, {
        id: 'CR-005',
        askId: 'ASK-0009',
        title: 'Native Excel export',
        room: slack('acme-cr-005'),
        createdAt: ist('11-05', '20:32:30'),
        status: 'estimating',
        options: [],
      })
      Object.assign(findAsk(db, 'ASK-0009'), { status: 'change_open', crId: 'CR-005' })
    },
  },
  {
    ts: ist('11-05', '20:36'),
    type: 'cr.estimated',
    actor: 'estimator',
    text: 'Estimator sized CR-005 at 3 h, high confidence, from the reports export code.',
    crId: 'CR-005',
    askId: 'ASK-0009',
    roomId: 'acme-cr-005',
    link: slack('acme-cr-005'),
    apply: (db) =>
      Object.assign(findCr(db, 'CR-005'), {
        estimate: {
          full: { p50Hours: 3, p90Hours: 3, confidence: 'high' },
          touches: ['src/reports/export.ts', 'src/reports/ReportsPage.tsx'],
          similar: [{ ref: 'CSV export (I8)', hours: 4 }],
          risks: [],
          assumptions: ['One sheet per report, with header formatting'],
          postedAt: ist('11-05', '20:36'),
        },
      }),
  },
  {
    ts: ist('11-05', '20:37'),
    type: 'cr.priced',
    actor: 'clerk',
    text: 'Clerk priced CR-005 at $140. Inside the auto-approval envelope.',
    crId: 'CR-005',
    askId: 'ASK-0009',
    roomId: 'acme-cr-005',
    link: slack('acme-cr-005'),
    apply: (db) =>
      Object.assign(findCr(db, 'CR-005'), {
        status: 'sent',
        options: [
          { key: 'A', label: 'Add it now', description: 'Native .xlsx export on the reports page.', hours: 3, priceCents: 14_000, shiftDays: 0 },
        ],
        envelope: { passed: true, failedRules: [] },
        approvedBy: 'envelope',
        approvedAt: ist('11-05', '20:37'),
        approvedOptions: ['A'],
      }),
  },
  {
    ts: ist('11-05', '20:37'),
    type: 'co.sent',
    actor: 'scout',
    text: 'Scout sent Sam change order CR-005: native Excel export for $140.',
    crId: 'CR-005',
    askId: 'ASK-0009',
    roomId: 'acme-client',
    link: discord('acme-client', '1110'),
    apply: (db) => {
      findCr(db, 'CR-005').sentAt = ist('11-05', '20:37')
      findAsk(db, 'ASK-0009').status = 'change_sent'
    },
  },
  // ------------------------------------------------------------ Beat 4: Excel approved
  {
    beat: 'excel-approved',
    ts: ist('11-05', '20:41'),
    type: 'room.message',
    actor: 'sam',
    text: 'Sam in #acme-client: "Approved, go ahead with the Excel export."',
    roomId: 'acme-client',
    link: discord('acme-client', '1111'),
  },
  {
    ts: ist('11-05', '20:41'),
    type: 'client.decided',
    actor: 'sam',
    text: 'Sam approved CR-005 option A, native Excel export, for $140.',
    crId: 'CR-005',
    askId: 'ASK-0009',
    roomId: 'acme-client',
    link: discord('acme-client', '1111'),
    apply: (db) => {
      Object.assign(findCr(db, 'CR-005'), { status: 'decided', clientChoice: 'A', decidedAt: ist('11-05', '20:41') })
      findAsk(db, 'ASK-0009').status = 'approved'
      db.decisionMinutes.push(11)
    },
  },
  {
    ts: ist('11-05', '20:41'),
    type: 'ledger.updated',
    actor: 'clerk',
    text: 'Revenue protected this month is now $2,030.',
    crId: 'CR-005',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
    apply: (db) =>
      db.ledger.push({
        date: ist('11-05', '20:41'),
        ref: 'CR-005',
        title: 'Native Excel export',
        hours: 3,
        amountCents: 14_000,
        approvedBy: 'sam',
        link: slack('acme-cr-005'),
        kind: 'change_order',
      }),
  },
  {
    ts: ist('11-05', '20:41'),
    type: 'work.created',
    actor: 'builder',
    text: 'Builder started W-0003, the Excel export.',
    askId: 'ASK-0009',
    crId: 'CR-005',
    roomId: 'acme-delivery',
    link: slack('acme-delivery'),
    apply: (db) => {
      upsert(db.workItems, {
        id: 'W-0003',
        askId: 'ASK-0009',
        crId: 'CR-005',
        title: 'Excel export',
        branch: 'feat/xlsx-export',
        status: 'building',
      })
      Object.assign(findAsk(db, 'ASK-0009'), { status: 'building', workItemIds: ['W-0003'] })
    },
  },
  // ------------------------------------------------------------ Beat 5: Android estimate
  {
    beat: 'android-estimate',
    ts: ist('11-05', '20:44'),
    type: 'cr.estimated',
    actor: 'estimator',
    text: 'Estimator sized the Android app: P50 190 h, P90 240 h (medium). A view-only version is 56 h (high).',
    crId: 'CR-004',
    askId: 'ASK-0010',
    roomId: 'acme-cr-004',
    link: slack('acme-cr-004'),
    apply: (db) =>
      Object.assign(findCr(db, 'CR-004'), {
        estimate: {
          full: { title: 'Full Android app', p50Hours: 190, p90Hours: 240, confidence: 'medium' },
          smaller: { title: 'View-only board-meeting app', p50Hours: 56, p90Hours: 64, confidence: 'high' },
          touches: ['src/api/*', 'src/reports/*', 'auth/session.ts', 'New Android project'],
          similar: [
            { ref: 'Reports v2', hours: 61 },
            { ref: 'Admin users page', hours: 52 },
            { ref: 'Auth refresh', hours: 18 },
          ],
          risks: ['Play Store review time', 'Offline sync is not specified'],
          assumptions: ['Reuses the existing REST API', 'Phones only, no tablets'],
          postedAt: ist('11-05', '20:44'),
        },
      }),
  },
  {
    ts: ist('11-05', '20:45'),
    type: 'cr.priced',
    actor: 'clerk',
    text: 'Clerk drafted CR-004 at 190 h ($9,830). Outside the envelope on price, confidence and milestone impact, so it waits for @delivery-lead.',
    crId: 'CR-004',
    askId: 'ASK-0010',
    roomId: 'acme-cr-004',
    link: slack('acme-cr-004'),
    apply: (db) =>
      Object.assign(findCr(db, 'CR-004'), {
        status: 'awaiting_confirmation',
        options: [
          {
            key: 'A',
            label: 'Add it now',
            description: 'Draft at the P50 estimate, waiting for the delivery lead.',
            hours: 190,
            priceCents: 983_000,
            milestoneId: 'M2',
            shiftDays: 11,
            draft: true,
          },
        ],
        envelope: {
          passed: false,
          failedRules: ['Price over $500', 'Confidence below high', 'Moves milestone M2'],
        },
      }),
  },
  // ------------------------------------------------------------ Beat 6: previews up
  {
    beat: 'previews-up',
    ts: ist('11-05', '21:20'),
    type: 'work.pr_opened',
    actor: 'builder',
    text: 'Builder opened pull request #12, the Safari login fix.',
    askId: 'ASK-0007',
    roomId: 'acme-delivery',
    link: slack('acme-delivery'),
    apply: (db) =>
      Object.assign(findWork(db, 'W-0001'), {
        status: 'pr_open',
        prUrl: 'https://github.com/pixelco/acme-portal/pull/12',
      }),
  },
  {
    ts: ist('11-05', '21:34'),
    type: 'work.preview_ready',
    actor: 'builder',
    text: 'The preview for the Safari login fix is ready.',
    askId: 'ASK-0007',
    roomId: 'acme-client',
    link: discord('acme-client', '1112'),
    apply: (db) => {
      Object.assign(findWork(db, 'W-0001'), { status: 'preview', previewUrl: 'https://pr-12.acme-portal.preview.pixelco.dev' })
      findAsk(db, 'ASK-0007').status = 'preview'
    },
  },
  {
    ts: ist('11-05', '21:58'),
    type: 'work.pr_opened',
    actor: 'builder',
    text: 'Builder opened pull request #13, dark mode.',
    askId: 'ASK-0008',
    roomId: 'acme-delivery',
    link: slack('acme-delivery'),
    apply: (db) =>
      Object.assign(findWork(db, 'W-0002'), {
        status: 'pr_open',
        prUrl: 'https://github.com/pixelco/acme-portal/pull/13',
      }),
  },
  {
    ts: ist('11-05', '22:12'),
    type: 'work.preview_ready',
    actor: 'builder',
    text: 'The dark mode preview is ready. Scout shared it with Sam.',
    askId: 'ASK-0008',
    roomId: 'acme-client',
    link: discord('acme-client', '1113'),
    apply: (db) => {
      Object.assign(findWork(db, 'W-0002'), { status: 'preview', previewUrl: 'https://pr-13.acme-portal.preview.pixelco.dev' })
      findAsk(db, 'ASK-0008').status = 'preview'
    },
  },
  // ------------------------------------------------------------ Beat 7: dark mode accepted
  {
    beat: 'dark-mode-accepted',
    ts: ist('11-05', '23:40'),
    type: 'room.message',
    actor: 'sam',
    text: 'Sam in #acme-client: "Dark mode looks great. Accepted."',
    roomId: 'acme-client',
    link: discord('acme-client', '1114'),
  },
  {
    ts: ist('11-05', '23:40'),
    type: 'ask.accepted',
    actor: 'sam',
    text: 'Sam accepted ASK-0008, dark mode.',
    askId: 'ASK-0008',
    roomId: 'acme-client',
    link: discord('acme-client', '1114'),
    apply: (db) => {
      findWork(db, 'W-0002').status = 'accepted'
      findAsk(db, 'ASK-0008').status = 'accepted'
    },
  },
  {
    ts: ist('11-06', '00:30'),
    type: 'work.pr_opened',
    actor: 'builder',
    text: 'Builder opened pull request #14, the Excel export.',
    askId: 'ASK-0009',
    crId: 'CR-005',
    roomId: 'acme-delivery',
    link: slack('acme-delivery'),
    apply: (db) =>
      Object.assign(findWork(db, 'W-0003'), {
        status: 'pr_open',
        prUrl: 'https://github.com/pixelco/acme-portal/pull/14',
      }),
  },
  {
    ts: ist('11-06', '00:38'),
    type: 'work.preview_ready',
    actor: 'builder',
    text: 'The Excel export preview is ready.',
    askId: 'ASK-0009',
    crId: 'CR-005',
    roomId: 'acme-client',
    link: discord('acme-client', '1115'),
    apply: (db) => {
      Object.assign(findWork(db, 'W-0003'), { status: 'preview', previewUrl: 'https://pr-14.acme-portal.preview.pixelco.dev' })
      findAsk(db, 'ASK-0009').status = 'preview'
    },
  },
  // ------------------------------------------------------------ Beat 8: morning handover
  {
    beat: 'morning-handover',
    ts: ist('11-06', '09:30'),
    type: 'desk.handover',
    actor: 'priya',
    text: 'Scout handed the client desk back to Priya. Copilot mode.',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
    data: { from: 'scout', to: 'priya' },
    apply: (db) => setDesk(db, 'priya', ist('11-06', '09:30'), ist('11-06', '19:00')),
  },
  {
    ts: ist('11-06', '09:30'),
    type: 'brief.posted',
    actor: 'scout',
    text: 'Scout posted the morning brief: 4 asks overnight, $140 approved, CR-004 needs a yes.',
    crId: 'CR-004',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
  },
  {
    ts: ist('11-06', '09:42'),
    type: 'cr.confirmed',
    actor: 'ravi',
    text: 'Ravi confirmed CR-004 at 200 h.',
    crId: 'CR-004',
    askId: 'ASK-0010',
    roomId: 'acme-cr-004',
    link: slack('acme-cr-004'),
    apply: (db) => Object.assign(findCr(db, 'CR-004'), { confirmedHours: 200, confirmedBy: 'ravi' }),
  },
  {
    ts: ist('11-06', '09:42'),
    type: 'cr.priced',
    actor: 'clerk',
    text: 'Clerk priced four options for CR-004: A $10,350, B $10,350, C $2,650, D $0 (swap I9).',
    crId: 'CR-004',
    askId: 'ASK-0010',
    roomId: 'acme-cr-004',
    link: slack('acme-cr-004'),
    apply: (db) =>
      Object.assign(findCr(db, 'CR-004'), {
        status: 'awaiting_approval',
        options: structuredClone(CR004_OPTIONS),
      }),
  },
  // ------------------------------------------------------------ Beat 9: options approved
  {
    beat: 'options-approved',
    ts: ist('11-06', '09:50'),
    type: 'cr.approved',
    actor: 'priya',
    text: 'Priya approved all four options for CR-004.',
    crId: 'CR-004',
    askId: 'ASK-0010',
    roomId: 'acme-cr-004',
    link: slack('acme-cr-004'),
    skipIf: (db) => findCr(db, 'CR-004').approvedAt !== undefined,
    apply: (db) => approveCr004(db, 'priya', ist('11-06', '09:50')),
  },
  {
    ts: ist('11-06', '09:50'),
    type: 'co.sent',
    actor: 'priya',
    text: 'Priya sent Sam change order CR-004 with options A to D.',
    crId: 'CR-004',
    askId: 'ASK-0010',
    roomId: 'acme-client',
    link: discord('acme-client', '1116'),
    skipIf: (db) => findCr(db, 'CR-004').sentAt !== undefined,
    apply: (db) => {
      const cr = findCr(db, 'CR-004')
      cr.status = 'sent'
      cr.sentAt ??= ist('11-06', '09:50')
      findAsk(db, 'ASK-0010').status = 'change_sent'
    },
  },
  {
    ts: ist('11-06', '19:00'),
    type: 'desk.handover',
    actor: 'scout',
    text: 'Priya handed the client desk to Scout. Autopilot until 9:30 AM IST.',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
    data: { from: 'priya', to: 'scout' },
    apply: (db) => setDesk(db, 'scout', ist('11-06', '19:00'), ist('11-07', '09:30')),
  },
  // ------------------------------------------------------------ Beat 10: Sam picks D
  {
    beat: 'sam-picks-d',
    ts: ist('11-06', '19:10'),
    type: 'room.message',
    actor: 'sam',
    text: 'Sam in #acme-client: "Let\'s go with D. The view-only app is all the board needs."',
    roomId: 'acme-client',
    link: discord('acme-client', '1117'),
  },
  {
    ts: ist('11-06', '19:10'),
    type: 'client.decided',
    actor: 'sam',
    text: 'Sam picked option D for CR-004: the view-only Android app in place of I9.',
    crId: 'CR-004',
    askId: 'ASK-0010',
    roomId: 'acme-client',
    link: discord('acme-client', '1117'),
    apply: (db) => {
      Object.assign(findCr(db, 'CR-004'), { status: 'decided', clientChoice: 'D', decidedAt: ist('11-06', '19:10') })
      findAsk(db, 'ASK-0010').status = 'swapped'
      db.decisionMinutes.push(1360)
    },
  },
  {
    ts: ist('11-06', '19:10'),
    type: 'plan.updated',
    actor: 'clerk',
    text: 'Clerk swapped I9, Admin analytics dashboard (58 h), for I11, View-only Android app (56 h). No date change.',
    crId: 'CR-004',
    roomId: 'acme-delivery',
    link: slack('acme-delivery'),
    apply: (db) => {
      const m2 = db.plan.milestones.find((m) => m.id === 'M2')
      if (!m2) return
      m2.items = m2.items.filter((i) => i.id !== 'I9')
      if (!m2.items.some((i) => i.id === 'I11')) {
        m2.items.push({ id: 'I11', title: 'View-only Android app', deliverable: 'CR-004', hours: 56, status: 'unstarted', priority: 2 })
      }
    },
  },
  {
    ts: ist('11-06', '19:10'),
    type: 'ledger.updated',
    actor: 'clerk',
    text: 'The ledger shows $2,030 approved this month and one swap.',
    crId: 'CR-004',
    roomId: 'acme-intake',
    link: slack('acme-intake'),
    apply: (db) =>
      db.ledger.push({
        date: ist('11-06', '19:10'),
        ref: 'CR-004',
        title: 'Swap: View-only Android app for I9',
        hours: 56,
        amountCents: 0,
        approvedBy: 'priya',
        link: slack('acme-cr-004'),
        kind: 'swap',
      }),
  },
]

/** Shared by the story and the `POST /approve` handler. */
export function approveCr004(db: MockDb, by: string, at: string): void {
  approveChangeRequest(db, 'CR-004', ['A', 'B', 'C', 'D'], by, at)
}

export function approveChangeRequest(
  db: MockDb,
  id: string,
  keys: OptionQuote['key'][],
  by: string,
  at: string,
): void {
  const cr = findCr(db, id)
  Object.assign(cr, { approvedBy: by, approvedAt: at, approvedOptions: keys })
}
