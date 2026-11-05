import { useState } from 'react'
import {
  Check,
  CheckCircle2,
  Clock,
  ExternalLink,
  Pencil,
  Share2,
} from 'lucide-react'
import { Link } from 'react-router'
import { Avatar } from '@/components/Avatar'
import { ChatLink } from '@/components/ChatLink'
import { ConfirmPost } from '@/components/ConfirmPost'
import { SwitchTag } from '@/components/SwitchTag'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { api, qk } from '@/lib/api/client'
import type { ChangeRequest, OptionKey } from '@/lib/api/types'
import { person } from '@/lib/people'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { EstimateChart } from './EstimateChart'
import { OptionsCards } from './OptionsCards'
import { WhatIfTimeline } from './WhatIfTimeline'

export function ChangeRequestDetail({ cr }: { cr: ChangeRequest }) {
  const queryClient = useQueryClient()
  const [hoveredOption, setHoveredOption] = useState<OptionKey | null>(null)
  const [selectedKeys, setSelectedKeys] = useState<OptionKey[]>(
    cr.options.map((o) => o.key),
  )

  // Dialog states
  const [confirmPostData, setConfirmPostData] = useState<{
    open: boolean
    title: string
    message: string
    onConfirm: () => Promise<void>
  }>({
    open: false,
    title: '',
    message: '',
    onConfirm: async () => {},
  })

  const [editPriceData, setEditPriceData] = useState<{
    open: boolean
    key: OptionKey
    currentCents: number
    newCents: number
  }>({
    open: false,
    key: 'A',
    currentCents: 0,
    newCents: 0,
  })

  const toggleSelectOption = (key: OptionKey) => {
    setSelectedKeys((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    )
  }

  // Action: Approve all
  const handleApproveAll = () => {
    const allKeys = cr.options.map((o) => o.key)
    setConfirmPostData({
      open: true,
      title: `Approve All Options for ${cr.id}`,
      message: `Priya: Approved all options (${allKeys.join(', ')}) for ${cr.id} (${cr.title}). Posting official change order to Sam in #acme-client.`,
      onConfirm: async () => {
        await api.approve(cr.id, allKeys)
        toast.success(`Approved all options for ${cr.id}`)
        void queryClient.invalidateQueries({ queryKey: qk.changeRequest(cr.id) })
        void queryClient.invalidateQueries({ queryKey: qk.changeRequests })
      },
    })
  }

  // Action: Approve selected
  const handleApproveSelected = () => {
    if (selectedKeys.length === 0) {
      toast.error('Select at least one option to approve')
      return
    }
    setConfirmPostData({
      open: true,
      title: `Approve Selected Options (${selectedKeys.join(', ')}) for ${cr.id}`,
      message: `Priya: Approved options ${selectedKeys.join(', ')} for ${cr.id} (${cr.title}).`,
      onConfirm: async () => {
        await api.approve(cr.id, selectedKeys)
        toast.success(`Approved options ${selectedKeys.join(', ')} for ${cr.id}`)
        void queryClient.invalidateQueries({ queryKey: qk.changeRequest(cr.id) })
        void queryClient.invalidateQueries({ queryKey: qk.changeRequests })
      },
    })
  }

  // Action: Decline
  const handleDecline = () => {
    setConfirmPostData({
      open: true,
      title: `Decline Change Request ${cr.id}`,
      message: `Priya: Declining ${cr.id} (${cr.title}) for the current phase based on team bandwidth.`,
      onConfirm: async () => {
        await api.decline(cr.id, 'Declined for current phase based on team bandwidth.')
        toast.success(`Declined ${cr.id}`)
        void queryClient.invalidateQueries({ queryKey: qk.changeRequest(cr.id) })
        void queryClient.invalidateQueries({ queryKey: qk.changeRequests })
      },
    })
  }

  // Action: Share public change order link
  const handleShare = () => {
    const url = `${window.location.origin}/co/${cr.id}`
    navigator.clipboard?.writeText(url)
    toast.success(`Copied public change order link to clipboard: /co/${cr.id}`)
  }

  // Action: Edit price
  const handleSavePrice = async () => {
    try {
      const res = await fetch(`/api/change-requests/${cr.id}/options/${editPriceData.key}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priceCents: editPriceData.newCents }),
      })
      if (!res.ok) throw new Error('Failed to update price')
      toast.success(`Updated Option ${editPriceData.key} price`)
      setEditPriceData((p) => ({ ...p, open: false }))
      void queryClient.invalidateQueries({ queryKey: qk.changeRequest(cr.id) })
    } catch {
      toast.error('Failed to update price')
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="rounded-xl border border-border bg-card p-5 space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="font-mono text-xl font-bold text-foreground">{cr.id}</span>
            <span className="text-xl font-semibold text-foreground">·</span>
            <h2 className="text-xl font-bold text-foreground">{cr.title}</h2>
            <span className="rounded-md bg-secondary px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider text-foreground">
              {cr.status.replace('_', ' ')}
            </span>
            <SwitchTag kind="Room" label={`Room · #${cr.room.room}`} />
          </div>

          <div className="flex items-center gap-2">
            <ChatLink link={cr.room} variant="room" className="text-xs" />
            <Link
              to={`/co/${cr.id}`}
              className="inline-flex items-center gap-1 rounded-md border border-border bg-secondary/60 px-2.5 py-1 text-xs font-medium text-foreground hover:bg-secondary transition-colors"
            >
              <ExternalLink className="size-3" />
              <span>Public Change Order</span>
            </Link>
          </div>
        </div>

        {/* Client's Original Quote */}
        <div className="rounded-lg bg-secondary/30 p-3 text-xs text-foreground">
          <span className="font-semibold text-muted-foreground mr-1">Client ask quote:</span>
          <span className="italic font-medium">
            “We would love an Android app for the board meeting.”
          </span>
        </div>

        {/* Confirmation status pill */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 pt-3 text-xs">
          <div className="flex items-center gap-2">
            <Avatar id={cr.confirmedBy ?? 'ravi'} size="xs" />
            {cr.confirmedHours ? (
              <span className="text-foreground">
                <strong>{person(cr.confirmedBy).name}</strong> confirmed{' '}
                <strong className="font-mono text-primary">{cr.confirmedHours} h</strong> at 9:42 AM IST
              </span>
            ) : (
              <span className="text-muted-foreground flex items-center gap-1">
                <Clock className="size-3 text-amber-500" />
                Awaiting delivery lead (<strong>@delivery-lead</strong>) confirmation
              </span>
            )}
          </div>

          {cr.approvedBy && (
            <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
              <CheckCircle2 className="size-3.5" />
              Approved by {person(cr.approvedBy).name} at 9:50 AM IST
            </span>
          )}
        </div>
      </div>

      {/* Codebase Grounded Estimate Chart */}
      {cr.estimate && <EstimateChart estimate={cr.estimate} />}

      {/* Options Cards */}
      {cr.options.length > 0 && (
        <OptionsCards
          options={cr.options}
          clientChoice={cr.clientChoice}
          selectedKeys={selectedKeys}
          onToggleSelect={toggleSelectOption}
          onHoverOption={setHoveredOption}
        />
      )}

      {/* What-If Milestone Timeline */}
      <WhatIfTimeline
        hoveredOption={hoveredOption}
        clientChoice={cr.clientChoice}
      />

      {/* Account Manager Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-card p-4 shadow-xs">
        <div className="flex items-center gap-2">
          <Avatar id="priya" size="sm" />
          <span className="text-xs font-semibold text-foreground">Account Manager Actions:</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="default"
            onClick={handleApproveAll}
            className="gap-1.5 font-semibold text-xs"
          >
            <Check className="size-3.5" />
            <span>Approve all ({cr.options.length})</span>
          </Button>

          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleApproveSelected}
            className="text-xs"
          >
            Approve selected ({selectedKeys.length})
          </Button>

          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => {
              const opt = cr.options[0]
              if (opt) {
                setEditPriceData({
                  open: true,
                  key: opt.key,
                  currentCents: opt.priceCents,
                  newCents: opt.priceCents,
                })
              }
            }}
            className="gap-1 text-xs"
          >
            <Pencil className="size-3" />
            <span>Edit price</span>
          </Button>

          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleShare}
            className="gap-1 text-xs"
          >
            <Share2 className="size-3" />
            <span>Share change order</span>
          </Button>

          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={handleDecline}
            className="text-xs text-destructive hover:bg-destructive/10"
          >
            Decline
          </Button>
        </div>
      </div>

      {/* ConfirmPost Dialog */}
      {confirmPostData.open && (
        <ConfirmPost
          open={confirmPostData.open}
          onOpenChange={(open) => setConfirmPostData((p) => ({ ...p, open }))}
          title={confirmPostData.title}
          target={cr.room}
          message={confirmPostData.message}
          confirmLabel="Post to chat"
          onConfirm={confirmPostData.onConfirm}
        />
      )}

      {/* Edit Price Dialog */}
      {editPriceData.open && (
        <Dialog
          open={editPriceData.open}
          onOpenChange={(open) => setEditPriceData((p) => ({ ...p, open }))}
        >
          <DialogContent className="sm:max-w-xs">
            <DialogHeader>
              <DialogTitle className="text-sm">Edit Option {editPriceData.key} Price</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 py-2">
              <label className="text-xs text-muted-foreground block">
                Price in Dollars:
                <input
                  type="number"
                  step="10"
                  defaultValue={editPriceData.currentCents / 100}
                  onChange={(e) =>
                    setEditPriceData((p) => ({
                      ...p,
                      newCents: Math.round(Number(e.target.value) * 100),
                    }))
                  }
                  className="mt-1 w-full rounded-md border border-border bg-background p-2 text-sm font-mono font-bold text-foreground"
                />
              </label>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditPriceData((p) => ({ ...p, open: false }))}
              >
                Cancel
              </Button>
              <Button size="sm" onClick={handleSavePrice}>
                Save Price
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}
