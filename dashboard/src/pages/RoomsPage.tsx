import { useMemo, useState } from 'react'
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  Network,
  Shield,
  TableProperties,
} from 'lucide-react'
import { SwitchTag } from '@/components/SwitchTag'
import { useEvents } from '@/lib/api/queries'
import type { Member, Room } from '@/lib/api/types'
import { MEMBERS } from '@/mocks/seed'
import { RoomNode } from '@/features/rooms/RoomNode'
import { RoomsMatrixTable } from '@/features/rooms/RoomsMatrixTable'

const nodeTypes = {
  room: RoomNode,
}

export function RoomsPage() {
  const [viewMode, setViewMode] = useState<'graph' | 'matrix'>('graph')
  const { data: events } = useEvents()

  // Room data
  const initialRooms: Room[] = useMemo(
    () => [
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
      {
        id: 'acme-cr-004',
        name: 'acme-cr-004',
        app: 'slack',
        kind: 'change',
        members: [MEMBERS.priya!, MEMBERS.ravi!, MEMBERS.clerk!, MEMBERS.estimator!],
        roles: [{ name: '@delivery-lead', holder: 'ravi' }],
        references: ['CR-004', 'ASK-0010'],
      },
    ],
    [],
  )

  // Most recent room pulse
  const recentRoomId = events?.[0]?.roomId

  // Graph nodes
  const nodes: Node[] = useMemo(
    () => [
      {
        id: 'acme-client',
        type: 'room',
        position: { x: 50, y: 140 },
        data: {
          ...initialRooms[0]!,
          pulsed: recentRoomId === 'acme-client',
        },
      },
      {
        id: 'acme-intake',
        type: 'room',
        position: { x: 440, y: 60 },
        data: {
          ...initialRooms[1]!,
          pulsed: recentRoomId === 'acme-intake',
        },
      },
      {
        id: 'acme-cr-004',
        type: 'room',
        position: { x: 440, y: 290 },
        data: {
          ...initialRooms[3]!,
          pulsed: recentRoomId === 'acme-cr-004',
        },
      },
      {
        id: 'acme-delivery',
        type: 'room',
        position: { x: 820, y: 140 },
        data: {
          ...initialRooms[2]!,
          pulsed: recentRoomId === 'acme-delivery',
        },
      },
    ],
    [initialRooms, recentRoomId],
  )

  // Graph edges
  const edges: Edge[] = useMemo(
    () => [
      {
        id: 'e-client-intake',
        source: 'acme-client',
        target: 'acme-intake',
        label: 'asks in, client-ready answers out',
        animated: true,
        style: { stroke: 'var(--primary)', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--primary)' },
      },
      {
        id: 'e-client-cr',
        source: 'acme-client',
        target: 'acme-cr-004',
        label: 'out-of-scope CRs',
        style: { stroke: 'var(--cat-out)', strokeWidth: 1.5, strokeDasharray: '4 4' },
      },
      {
        id: 'e-intake-delivery',
        source: 'acme-intake',
        target: 'acme-delivery',
        label: 'approved work in, previews out',
        animated: true,
        style: { stroke: 'var(--primary)', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--primary)' },
      },
      {
        id: 'e-cr-delivery',
        source: 'acme-cr-004',
        target: 'acme-delivery',
        label: 'sized options & estimates',
        style: { stroke: 'var(--muted-foreground)', strokeWidth: 1.5 },
      },
    ],
    [],
  )

  const allMembersList: Member[] = Object.values(MEMBERS)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Rooms (Switch Map)
            </h1>
            <SwitchTag kind="Membership boundary" />
            <SwitchTag kind="Room link" />
          </div>
          <p className="text-xs text-muted-foreground">
            Multi-room topology connecting Discord (client) and Slack (agency) with role-based governance.
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-1.5 rounded-lg border border-border bg-secondary/40 p-1">
          <button
            type="button"
            onClick={() => setViewMode('graph')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              viewMode === 'graph'
                ? 'bg-background font-semibold text-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Network className="size-3.5" />
            <span>Interactive Graph</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode('matrix')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              viewMode === 'matrix'
                ? 'bg-background font-semibold text-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <TableProperties className="size-3.5" />
            <span>Matrix Table</span>
          </button>
        </div>
      </div>

      {viewMode === 'graph' ? (
        <div className="relative h-[620px] rounded-2xl border border-border bg-card shadow-xs overflow-hidden">
          {/* Boundary Announcement Ribbon (§8) */}
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2 rounded-lg border border-dashed border-violet-500/60 bg-card/90 px-3 py-1.5 backdrop-blur text-xs text-foreground shadow-sm">
            <Shield className="size-3.5 text-violet-500 shrink-0" />
            <span>
              <strong>Membership Boundary:</strong> Internal pricing &amp; rate discussions remain in Slack; client-facing Scout never enters internal rooms.
            </span>
          </div>

          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.5}
            maxZoom={1.5}
            className="bg-muted/10"
          >
            <Background gap={16} size={1} />
            <Controls className="bg-card border-border shadow-xs rounded-lg" />
            <MiniMap
              nodeColor={(n) => (n.id === 'acme-client' ? '#f59e0b' : '#6366f1')}
              className="border border-border bg-card rounded-lg"
            />
          </ReactFlow>
        </div>
      ) : (
        <RoomsMatrixTable rooms={initialRooms} allMembers={allMembersList} />
      )}
    </div>
  )
}
