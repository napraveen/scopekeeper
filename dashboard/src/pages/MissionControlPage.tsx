import { DeskHero } from '@/features/desk/DeskHero'
import { KpiStrip } from '@/features/kpis/KpiStrip'
import { LivePipeline } from '@/features/pipeline/LivePipeline'
import { NeedsAYes } from '@/features/pipeline/NeedsAYes'
import { ActivityFeed } from '@/features/activity/ActivityFeed'

export function MissionControlPage() {
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* The Desk Hero */}
      <DeskHero />

      {/* KPI Strip */}
      <KpiStrip />

      {/* Main dashboard columns:
          Desktop: 2/3 width for Pipeline & Needs a yes, 1/3 for Activity Feed
          Mobile: Desk, KPIs, Needs a yes, Pipeline (vertical list), then Feed */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="flex flex-col gap-6 xl:col-span-2">
          <div className="order-2 xl:order-1">
            <LivePipeline />
          </div>
          <div className="order-1 xl:order-2">
            <NeedsAYes />
          </div>
        </div>

        <div className="xl:col-span-1">
          <ActivityFeed />
        </div>
      </div>
    </div>
  )
}
