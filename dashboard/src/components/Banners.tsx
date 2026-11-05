import { useState } from 'react'
import { AlertCircle, Key, Radio, RefreshCw, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { API_BASE_URL, clearApiToken, getApiToken, IS_MOCK, setApiToken } from '@/lib/config'
import { useConnectionStore } from '@/stores/ui'

export function Banners() {
  const status = useConnectionStore((s) => s.status)
  const reconnect = useConnectionStore((s) => s.reconnect)

  const [tokenDialogOpen, setTokenDialogOpen] = useState(false)
  const [tokenInput, setTokenInput] = useState(getApiToken() ?? '')

  const isDisconnected = status === 'error' || status === 'closed'

  const handleSaveToken = () => {
    if (tokenInput.trim()) {
      setApiToken(tokenInput.trim())
    } else {
      clearApiToken()
    }
    setTokenDialogOpen(false)
    reconnect()
  }

  return (
    <>
      {/* Disconnected alert banner */}
      {isDisconnected && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 bg-destructive px-4 py-2 text-xs font-medium text-white shadow-sm"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="size-4 shrink-0" />
            <span>
              Connection to {IS_MOCK ? 'mock story stream' : `${API_BASE_URL}/api/stream`} dropped. Retrying automatically or click to reconnect.
            </span>
          </div>
          <Button
            type="button"
            size="xs"
            variant="outline"
            onClick={reconnect}
            className="border-white/40 bg-white/10 text-white hover:bg-white/20 gap-1 text-xs"
          >
            <RefreshCw className="size-3" />
            <span>Reconnect now</span>
          </Button>
        </div>
      )}

      {/* Mode Ribbon */}
      {IS_MOCK ? (
        <div className="flex items-center justify-between border-b border-border/60 bg-secondary/30 px-4 py-1 text-[11px] text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Sparkles className="size-3 text-primary" />
            <span>
              <strong className="font-semibold text-foreground">Mock data · story mode</strong>. Press{' '}
              <kbd className="rounded border border-border bg-background px-1 py-0.2 font-mono text-[10px] text-foreground">
                D
              </kbd>{' '}
              for Director Mode.
            </span>
          </div>
          <span className="font-mono text-[10px] text-muted-foreground">
            Backend URL: http://localhost:8000 (Switch to live via VITE_API_MODE=live)
          </span>
        </div>
      ) : (
        <div className="flex items-center justify-between border-b border-border/60 bg-primary/10 px-4 py-1 text-[11px] text-primary">
          <div className="flex items-center gap-1.5">
            <Radio className="size-3 text-emerald-500 animate-pulse" />
            <span>
              <strong className="font-semibold">Live backend mode</strong> connected to{' '}
              <span className="font-mono">{API_BASE_URL}</span>
            </span>
          </div>
          <button
            type="button"
            onClick={() => setTokenDialogOpen(true)}
            className="flex items-center gap-1 font-mono text-[10px] underline hover:text-foreground"
          >
            <Key className="size-3" />
            <span>{getApiToken() ? 'Change API Token' : 'Set API Token'}</span>
          </button>
        </div>
      )}

      {/* Token Dialog */}
      {tokenDialogOpen && (
        <Dialog open={tokenDialogOpen} onOpenChange={setTokenDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base flex items-center gap-2">
                <Key className="size-4 text-primary" />
                <span>Backend API Token</span>
              </DialogTitle>
              <DialogDescription className="text-xs">
                Bearer authentication token sent in the Authorization header to {API_BASE_URL}.
              </DialogDescription>
            </DialogHeader>

            <div className="py-2">
              <input
                type="password"
                placeholder="sk_live_..."
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                className="w-full rounded-lg border border-border bg-background p-2.5 font-mono text-xs text-foreground focus:outline-hidden"
              />
            </div>

            <DialogFooter className="gap-2 sm:justify-end">
              <Button size="sm" variant="outline" onClick={() => setTokenDialogOpen(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleSaveToken}>
                Save Token
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </>
  )
}
