import { Moon, Sun } from 'lucide-react'
import { useNow } from '@/lib/clock'
import { formatClock, hourOfDay, ZONES, type ZoneKey } from '@/lib/format'

interface WorkingHours {
  start: number
  end: number
}

const HOURS: Record<ZoneKey, WorkingHours> = {
  agency: { start: 9.5, end: 19 }, // 9:30 AM - 7:00 PM IST
  client: { start: 9, end: 17 }, // 9:00 AM - 5:00 PM ET
}

function ZoneClock({ zoneKey }: { zoneKey: ZoneKey }) {
  const now = useNow()
  const zone = ZONES[zoneKey]
  const clockText = formatClock(now, zoneKey)
  const currentHour = hourOfDay(now, zoneKey)
  const hours = HOURS[zoneKey]

  const isWorking = currentHour >= hours.start && currentHour < hours.end
  const isSun = currentHour >= 6 && currentHour < 18.5

  const startPct = (hours.start / 24) * 100
  const widthPct = ((hours.end - hours.start) / 24) * 100
  const currentPct = Math.min(100, Math.max(0, (currentHour / 24) * 100))

  return (
    <div className="flex flex-col gap-1 text-xs">
      <div className="flex items-center gap-1.5 font-medium text-foreground">
        {isSun ? (
          <Sun className="size-3 text-amber-500 shrink-0" aria-hidden="true" />
        ) : (
          <Moon className="size-3 text-indigo-400 shrink-0" aria-hidden="true" />
        )}
        <span className="font-semibold">{zone.city}</span>
        <span className="tabular font-mono text-[11px] text-muted-foreground">{clockText}</span>
        <span className="font-mono text-[10px] text-muted-foreground/80">{zone.label}</span>
      </div>

      {/* 24-hour strip showing working hours window and current time marker */}
      <div
        className="relative h-1.5 w-24 sm:w-28 rounded-full bg-secondary overflow-hidden"
        title={`${zone.city} ${isWorking ? 'working hours' : 'outside working hours'}`}
      >
        {/* Working hours window */}
        <div
          className="absolute h-full bg-primary/25 rounded-full"
          style={{ left: `${startPct}%`, width: `${widthPct}%` }}
        />
        {/* Current hour tick */}
        <div
          className="absolute top-0 h-full w-1 -ml-0.5 bg-primary rounded-full shadow-xs"
          style={{ left: `${currentPct}%` }}
        />
      </div>
    </div>
  )
}

export function LiveClocks() {
  return (
    <div className="flex items-center gap-4 py-1">
      <ZoneClock zoneKey="agency" />
      <ZoneClock zoneKey="client" />
    </div>
  )
}
