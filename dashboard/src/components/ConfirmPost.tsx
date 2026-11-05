import { useState } from 'react'
import { Hash, MessageSquareShare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { ChatLink } from '@/lib/api/types'
import { formatChatTarget } from './ChatLink'

/**
 * Every action that posts to chat opens `ConfirmPost`, showing the exact message,
 * the room and the app (`#acme-cr-004 in Slack`) before it posts (FRONTEND_PROMPT §5).
 */
export function ConfirmPost({
  open,
  onOpenChange,
  title,
  target,
  message,
  confirmLabel = 'Post to chat',
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  target: ChatLink
  message: string
  confirmLabel?: string
  onConfirm: () => Promise<unknown> | unknown
}) {
  const [busy, setBusy] = useState(false)
  const targetLabel = formatChatTarget(target)

  const handleConfirm = async () => {
    setBusy(true)
    try {
      await onConfirm()
      onOpenChange(false)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <MessageSquareShare className="size-4 text-primary" aria-hidden="true" />
            <span>{title}</span>
          </DialogTitle>
          <DialogDescription className="text-xs">
            This will post to{' '}
            <span className="inline-flex items-center gap-0.5 rounded border border-border bg-secondary px-1.5 py-0.5 font-mono text-[11px] font-medium text-foreground">
              <Hash className="size-2.5" aria-hidden="true" />
              {target.room}
            </span>{' '}
            in <span className="font-medium text-foreground">{targetLabel.split(' in ')[1]}</span>.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5">
          <div className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
            Message to post in {targetLabel}
          </div>
          <pre className="rounded-lg border border-border bg-muted/60 p-3 font-sans text-xs leading-relaxed whitespace-pre-wrap text-foreground">
            {message}
          </pre>
        </div>

        <DialogFooter className="gap-2 sm:justify-end">
          <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancel
          </Button>
          <Button type="button" size="sm" onClick={() => void handleConfirm()} disabled={busy}>
            {busy ? 'Posting…' : `${confirmLabel} (${targetLabel})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
