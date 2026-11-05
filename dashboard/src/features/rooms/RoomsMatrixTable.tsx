import { Check, X } from 'lucide-react'
import { Avatar } from '@/components/Avatar'
import type { Member, Room } from '@/lib/api/types'

export function RoomsMatrixTable({
  rooms,
  allMembers,
}: {
  rooms: Room[]
  allMembers: Member[]
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-xs">
      <table className="w-full text-left text-xs border-collapse">
        <caption className="sr-only">Members by Switch Rooms Access Matrix</caption>
        <thead>
          <tr className="border-b border-border bg-secondary/50 font-semibold text-muted-foreground">
            <th scope="col" className="px-4 py-3">Member</th>
            <th scope="col" className="px-4 py-3">Type</th>
            <th scope="col" className="px-4 py-3">Side</th>
            {rooms.map((r) => (
              <th key={r.id} scope="col" className="px-4 py-3 text-center font-mono">
                #{r.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">
          {allMembers.map((m) => {
            return (
              <tr key={m.id} className="hover:bg-secondary/30 transition-colors">
                <td className="px-4 py-2.5 font-medium text-foreground whitespace-nowrap">
                  <Avatar id={m.id} size="xs" showName showVendor />
                </td>
                <td className="px-4 py-2.5 capitalize text-muted-foreground whitespace-nowrap">
                  {m.kind}
                </td>
                <td className="px-4 py-2.5 capitalize text-muted-foreground whitespace-nowrap">
                  {m.side}
                </td>
                {rooms.map((r) => {
                  const hasAccess = r.members.some((mem) => mem.id === m.id)
                  return (
                    <td key={r.id} className="px-4 py-2.5 text-center">
                      {hasAccess ? (
                        <span className="inline-flex size-5 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                          <Check className="size-3.5" aria-hidden="true" />
                          <span className="sr-only">Has access</span>
                        </span>
                      ) : (
                        <span className="inline-flex size-5 items-center justify-center rounded-full text-muted-foreground/30">
                          <X className="size-3" aria-hidden="true" />
                          <span className="sr-only">No access</span>
                        </span>
                      )}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
