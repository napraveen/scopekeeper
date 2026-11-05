import { useState } from 'react'
import {
  CheckCircle2,
  Clock,
  Cpu,
  DollarSign,
  GitBranch,
  Radio,
  Save,
  ShieldCheck,
  Sliders,
} from 'lucide-react'
import { SwitchTag } from '@/components/SwitchTag'
import { Button } from '@/components/ui/button'
import { PROJECT } from '@/mocks/seed'
import { toast } from 'sonner'

export function SettingsPage() {
  const [rate, setRate] = useState(PROJECT.rateCents / 100)
  const [goodwillBucket, setGoodwillBucket] = useState<number>(PROJECT.goodwillBucketHours)
  const [demoMode, setDemoMode] = useState(true)

  // Interactive envelope simulator inputs
  const [simHours, setSimHours] = useState(3)
  const [simConfidence, setSimConfidence] = useState<'high' | 'medium' | 'low'>('high')

  // Live calculation of preview
  const contingencyFactor = PROJECT.contingency[simConfidence]
  const rawCost = simHours * rate * (1 + contingencyFactor)
  const roundedPrice = Math.round(rawCost / 10) * 10
  const isAutoEnvelope =
    roundedPrice <= 500 && simConfidence === 'high'

  const handleSave = () => {
    toast.success('Settings and rate rules updated successfully.')
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Settings &amp; Rate Governance
            </h1>
            <SwitchTag kind="Reference" label="Governance Config" />
          </div>
          <p className="text-xs text-muted-foreground">
            Rate card formulas, automated client envelopes, shift schedule, and protocol integration.
          </p>
        </div>

        <Button size="sm" onClick={handleSave} className="gap-1.5 text-xs font-semibold">
          <Save className="size-3.5" />
          <span>Save Changes</span>
        </Button>
      </div>

      {/* 1. Rate Card & Contingency */}
      <div className="rounded-xl border border-border bg-card p-5 space-y-4 shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-border/70">
          <div className="flex items-center gap-2">
            <DollarSign className="size-4 text-primary" />
            <h2 className="text-sm font-bold text-foreground">Blended Rate &amp; Contingency</h2>
          </div>
          <span className="font-mono text-xs text-muted-foreground">USD / Hour</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <label className="text-xs space-y-1 block">
            <span className="font-medium text-foreground">Blended Hourly Rate ($):</span>
            <input
              type="number"
              value={rate}
              onChange={(e) => setRate(Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-background p-2 text-sm font-mono font-bold text-foreground focus:outline-hidden"
            />
          </label>

          <label className="text-xs space-y-1 block">
            <span className="font-medium text-foreground">Price Rounding:</span>
            <input
              type="text"
              readOnly
              value="Nearest $10"
              className="w-full rounded-lg border border-border bg-muted/50 p-2 text-sm font-mono text-muted-foreground cursor-not-allowed"
            />
          </label>

          <label className="text-xs space-y-1 block">
            <span className="font-medium text-foreground">Monthly Goodwill Bucket:</span>
            <input
              type="number"
              value={goodwillBucket}
              onChange={(e) => setGoodwillBucket(Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-background p-2 text-sm font-mono font-bold text-foreground focus:outline-hidden"
            />
          </label>
        </div>

        <div className="rounded-lg bg-secondary/40 p-3 text-xs text-muted-foreground">
          <div className="font-semibold text-foreground mb-1">Confidence Contingency Buffers:</div>
          <div className="flex flex-wrap gap-4 font-mono text-[11px]">
            <span>High Confidence: <strong>+5%</strong></span>
            <span>Medium Confidence: <strong>+15%</strong></span>
            <span>Low Confidence: <strong>+25%</strong></span>
          </div>
        </div>
      </div>

      {/* 2. Auto-Approval Envelope with Live Simulator (§8) */}
      <div className="rounded-xl border border-border bg-card p-5 space-y-4 shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-border/70">
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-sm font-bold text-foreground">Auto-Approval Envelope Rules</h2>
          </div>
          <span className="rounded bg-emerald-500/10 px-2 py-0.5 font-mono text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
            Autonomous Overnight Delivery
          </span>
        </div>

        <p className="text-xs text-muted-foreground leading-relaxed">
          Out-of-scope asks meeting all three conditions are priced, approved, and dispatched to Builder automatically overnight without waiting for morning review.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-lg border border-border p-3 text-xs bg-background">
            <span className="text-muted-foreground block text-[10px] uppercase font-bold">Rule 1</span>
            <span className="font-semibold text-foreground">Price &le; $500 USD</span>
          </div>
          <div className="rounded-lg border border-border p-3 text-xs bg-background">
            <span className="text-muted-foreground block text-[10px] uppercase font-bold">Rule 2</span>
            <span className="font-semibold text-foreground">High Confidence only</span>
          </div>
          <div className="rounded-lg border border-border p-3 text-xs bg-background">
            <span className="text-muted-foreground block text-[10px] uppercase font-bold">Rule 3</span>
            <span className="font-semibold text-foreground">0 milestone impact</span>
          </div>
        </div>

        {/* Live Interactive Envelope Preview */}
        <div className="rounded-xl border border-primary/30 bg-accent/20 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Sliders className="size-3.5 text-primary" /> Live Envelope Simulator
            </span>
            <span className="font-mono text-[11px] font-bold text-primary">
              Formula: Hours &times; Rate &times; (1 + Contingency)
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs">
            <label className="flex items-center gap-1.5 font-medium">
              <span>Effort:</span>
              <input
                type="number"
                min="1"
                max="20"
                value={simHours}
                onChange={(e) => setSimHours(Number(e.target.value))}
                className="w-16 rounded border border-border bg-background p-1 text-center font-mono font-bold"
              />
              <span>hours</span>
            </label>

            <label className="flex items-center gap-1.5 font-medium">
              <span>Confidence:</span>
              <select
                value={simConfidence}
                onChange={(e) => setSimConfidence(e.target.value as 'high' | 'medium' | 'low')}
                className="rounded border border-border bg-background px-2 py-1 font-medium"
              >
                <option value="high">High (+5%)</option>
                <option value="medium">Medium (+15%)</option>
                <option value="low">Low (+25%)</option>
              </select>
            </label>
          </div>

          <div className="rounded-lg bg-background/80 p-3 text-xs flex items-center justify-between border border-border/70">
            <div className="space-y-0.5">
              <span className="text-muted-foreground">Calculated Price:</span>
              <div className="font-mono text-base font-bold text-foreground">
                ${roundedPrice} USD
              </div>
            </div>

            <div className="text-right">
              {isAutoEnvelope ? (
                <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold text-xs">
                  <CheckCircle2 className="size-4" />
                  Auto-approved &amp; sent immediately
                </span>
              ) : (
                <span className="text-amber-600 dark:text-amber-400 font-medium text-xs">
                  Requires delivery lead confirmation
                </span>
              )}
            </div>
          </div>

          <p className="text-[11px] text-muted-foreground italic">
            “A {simHours} h, {simConfidence}-confidence change priced at ${roundedPrice} would {isAutoEnvelope ? 'be sent automatically' : 'wait for human approval'}.”
          </p>
        </div>
      </div>

      {/* 3. Shift Schedule (The Flip) */}
      <div className="rounded-xl border border-border bg-card p-5 space-y-4 shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-border/70">
          <div className="flex items-center gap-2">
            <Clock className="size-4 text-primary" />
            <h2 className="text-sm font-bold text-foreground">Shift Schedule (The Flip)</h2>
          </div>
          <span className="font-mono text-xs text-muted-foreground">Mumbai &amp; New York</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="rounded-xl border border-border bg-background p-3.5 space-y-2">
            <div className="font-semibold text-foreground flex items-center gap-1.5">
              <span>☀️ Morning Handover to Priya (Copilot)</span>
            </div>
            <div className="font-mono text-xs text-muted-foreground">
              09:30 AM IST · 11:00 PM ET
            </div>
            <p className="text-muted-foreground text-[11px]">
              Scout releases role @client-desk and posts morning brief.
            </p>
          </div>

          <div className="rounded-xl border border-border bg-background p-3.5 space-y-2">
            <div className="font-semibold text-foreground flex items-center gap-1.5">
              <span>🌙 Evening Handover to Scout (Autopilot)</span>
            </div>
            <div className="font-mono text-xs text-muted-foreground">
              07:00 PM IST · 08:30 AM ET
            </div>
            <p className="text-muted-foreground text-[11px]">
              Scout assumes @client-desk and covers overnight client day.
            </p>
          </div>
        </div>
      </div>

      {/* 4. Integrations Status (Read-Only Rows) */}
      <div className="rounded-xl border border-border bg-card p-5 space-y-3 shadow-xs">
        <h2 className="text-sm font-bold text-foreground">Integration Health</h2>

        <div className="divide-y divide-border/60 text-xs">
          <div className="py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Radio className="size-4 text-emerald-500" />
              <span className="font-medium text-foreground">Switch Protocol Bridge</span>
            </div>
            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-medium">
              Connected (Discord &amp; Slack)
            </span>
          </div>

          <div className="py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="size-4 text-emerald-500" />
              <span className="font-medium text-foreground">LLM Providers</span>
            </div>
            <span className="font-mono text-muted-foreground">
              Claude Code (Estimator) · OpenCode (Scout) · Codex (Builder)
            </span>
          </div>

          <div className="py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <GitBranch className="size-4 text-emerald-500" />
              <span className="font-medium text-foreground">Git Repository Host</span>
            </div>
            <span className="font-mono text-muted-foreground">
              github.com/pixelco/acme-portal (main)
            </span>
          </div>
        </div>
      </div>

      {/* 5. Demo Mode Toggle */}
      <div className="rounded-xl border border-border bg-card p-5 flex items-center justify-between shadow-xs">
        <div>
          <div className="font-semibold text-sm text-foreground">Demo &amp; Story Replay Mode</div>
          <p className="text-xs text-muted-foreground">
            Enables floating Director HUD (hotkey <kbd className="px-1 border rounded bg-secondary">D</kbd>) and simulated fast-forward playback.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setDemoMode(!demoMode)}
          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
            demoMode ? 'bg-primary' : 'bg-secondary'
          }`}
        >
          <span
            className={`pointer-events-none inline-block size-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
              demoMode ? 'translate-x-5' : 'translate-x-0'
            }`}
          />
        </button>
      </div>
    </div>
  )
}
