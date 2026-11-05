/**
 * The ScopeKeeper data contract (FRONTEND_PROMPT §9).
 * All times are ISO 8601 strings with offsets; money is integer cents.
 * If the backend returns a different shape, adapt it in `adapters.ts`, never here.
 */

export type Category = 'DEFECT' | 'IN_SCOPE' | 'UNCLEAR' | 'OUT_OF_SCOPE' | 'DUPLICATE' | 'ALREADY_DECIDED'
export type AskStatus =
  | 'received'
  | 'classified'
  | 'question_pending'
  | 'ticketed'
  | 'change_open'
  | 'linked'
  | 'reminded'
  | 'change_sent'
  | 'approved'
  | 'swapped'
  | 'declined'
  | 'building'
  | 'preview'
  | 'accepted'
  | 'invoiced'
export type Confidence = 'high' | 'medium' | 'low'
export type OptionKey = 'A' | 'B' | 'C' | 'D'
export type ChatApp = 'discord' | 'slack' | 'mattermost' | 'teams'
export interface ChatLink {
  app: ChatApp
  room: string
  url: string
}
export interface Ask {
  id: string
  quote: string
  requester: string
  createdAt: string
  status: AskStatus
  category?: Category
  clauseIds: string[]
  relatedItem?: string
  decisionId?: string
  confidence?: number
  reason?: string
  crId?: string
  questionId?: string
  workItemIds: string[]
  source: ChatLink
}
export interface Question {
  id: string
  askId: string
  text: string
  choices: string[]
  answer?: string
  askedAt: string
  answeredAt?: string
}
export interface EstimateVersion {
  title?: string
  p50Hours: number
  p90Hours: number
  confidence: Confidence
}
export interface Estimate {
  full: EstimateVersion
  smaller?: EstimateVersion
  touches: string[]
  similar: { ref: string; hours: number }[]
  risks: string[]
  assumptions: string[]
  postedAt: string
}
export interface OptionQuote {
  key: OptionKey
  label: string
  description: string
  hours: number
  priceCents: number
  milestoneId?: string
  shiftDays: number
  newDue?: string
  swapOut?: string[]
  swapIn?: string
  draft?: boolean
}
export interface EnvelopeResult {
  passed: boolean
  failedRules: string[]
}
export type ChangeRequestStatus =
  | 'estimating'
  | 'awaiting_confirmation'
  | 'awaiting_approval'
  | 'sent'
  | 'decided'
  | 'closed'
export interface ChangeRequest {
  id: string
  askId: string
  title: string
  room: ChatLink
  createdAt: string
  status: ChangeRequestStatus
  estimate?: Estimate
  confirmedHours?: number
  confirmedBy?: string
  options: OptionQuote[]
  envelope?: EnvelopeResult
  approvedBy?: string
  approvedAt?: string
  approvedOptions?: OptionKey[]
  clientChoice?: OptionKey | 'DECLINE'
  decidedAt?: string
}
export interface WorkItem {
  id: string
  askId: string
  crId?: string
  title: string
  branch: string
  prUrl?: string
  previewUrl?: string
  status: 'queued' | 'building' | 'pr_open' | 'preview' | 'merged' | 'accepted'
}
export type DeskHolder = 'priya' | 'scout'
export interface DeskState {
  holder: DeskHolder
  mode: 'copilot' | 'autopilot'
  since: string
  nextHandoverAt: string
  nextHolder: DeskHolder
}
export interface Overview {
  month: string
  revenueProtectedCents: number
  changeOrders: { sent: number; approved: number; pending: number; swaps: number }
  goodwill: { usedHours: number; bucketHours: number }
  medianAskToDecisionMinutes: number
  asksByCategory: Record<Category, number>
}
export interface LedgerEntry {
  date: string
  ref: string
  title: string
  hours: number
  amountCents: number
  approvedBy?: string
  link?: ChatLink
  kind: 'change_order' | 'swap' | 'goodwill' | 'defect' | 'in_scope'
}
export interface PlanItem {
  id: string
  title: string
  deliverable: string
  hours: number
  status: 'done' | 'in_progress' | 'unstarted'
  doneOn?: string
  priority?: number
}
export interface Milestone {
  id: string
  name: string
  due: string
  items: PlanItem[]
}
export interface Plan {
  capacityHoursPerWeek: number
  milestones: Milestone[]
}
export interface Member {
  id: string
  name: string
  kind: 'person' | 'agent'
  side: 'client' | 'agency'
  vendor?: 'OpenCode' | 'Claude Code' | 'Codex' | 'Custom'
}
export interface Room {
  id: string
  name: string
  app: ChatApp
  kind: 'client' | 'intake' | 'delivery' | 'change'
  members: Member[]
  roles: { name: string; holder?: string }[]
  references: string[]
}
export interface RoomMap {
  rooms: Room[]
  links: { from: string; to: string; description: string }[]
}
export interface StreamEvent {
  id: string
  ts: string
  type: string
  actor: string
  text: string
  askId?: string
  crId?: string
  roomId?: string
  link?: ChatLink
  data?: unknown
}

/** Known stream event types (§9). `type` stays a string so unknown types never break the UI. */
export type StreamEventType =
  | 'desk.handover'
  | 'room.message'
  | 'ask.created'
  | 'ask.classified'
  | 'question.asked'
  | 'question.answered'
  | 'cr.created'
  | 'cr.estimated'
  | 'cr.confirmed'
  | 'cr.priced'
  | 'cr.approved'
  | 'co.sent'
  | 'client.decided'
  | 'work.created'
  | 'work.pr_opened'
  | 'work.preview_ready'
  | 'ask.accepted'
  | 'brief.posted'
  | 'plan.updated'
  | 'ledger.updated'

/** `GET /api/health` — contract addition: exact shape. */
export interface Health {
  ok: boolean
  switch: 'connected' | 'disconnected'
  serverTime: string
}

/** `GET /api/asks` page. */
export interface AskPage {
  items: Ask[]
  nextCursor?: string
}

/** `GET /api/config/scope-map` — contract addition: exact shape. */
export interface Clause {
  id: string
  deliverable?: string
  title: string
  kind: 'in' | 'out'
  includes: string[]
  excerpt: string
}
export interface ScopeMap {
  clauses: Clause[]
  warrantyDays: number
}
