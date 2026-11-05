import { ExternalLink, Hash } from 'lucide-react'
import type { ChatLink as ChatLinkType } from '@/lib/api/types'
import { cn } from '@/lib/utils'

const APP_LABEL: Record<ChatLinkType['app'], string> = {
  discord: 'Discord',
  slack: 'Slack',
  mattermost: 'Mattermost',
  teams: 'Teams',
}

export function formatChatTarget(link: ChatLinkType): string {
  return `#${link.room} in ${APP_LABEL[link.app]}`
}

export function ChatLink({
  link,
  variant = 'open',
  className,
}: {
  link: ChatLinkType
  variant?: 'open' | 'room'
  className?: string
}) {
  const appName = APP_LABEL[link.app]
  return (
    <a
      href={link.url}
      target="_blank"
      rel="noreferrer"
      onClick={(e) => e.stopPropagation()}
      className={cn(
        'inline-flex items-center gap-1 rounded text-xs font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:text-foreground',
        className,
      )}
    >
      {variant === 'room' ? (
        <>
          <Hash className="size-3 shrink-0" aria-hidden="true" />
          <span className="font-mono">{link.room}</span>
          <span className="text-muted-foreground/80">in {appName}</span>
        </>
      ) : (
        <>
          <span>Open in {appName}</span>
          <ExternalLink className="size-3 shrink-0" aria-hidden="true" />
        </>
      )}
    </a>
  )
}
