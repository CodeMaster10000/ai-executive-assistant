import { useEffect, useState } from "react"
import { Eye, EyeOff, Loader2, Trash2, Save } from "lucide-react"
import { getApiKeyStatus, updateApiKey, deleteApiKey } from "@/api/settings"
import type { ApiKeyStatus } from "@/api/types"
import { useAuth } from "@/contexts/AuthContext"
import { PageHeader } from "@/components/shared/PageHeader"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { toast } from "sonner"

export default function SettingsPage() {
  const { refreshUser } = useAuth()
  const [status, setStatus] = useState<ApiKeyStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [apiKey, setApiKey] = useState("")
  const [showKey, setShowKey] = useState(false)
  const [removeOpen, setRemoveOpen] = useState(false)

  async function loadStatus() {
    try {
      const s = await getApiKeyStatus()
      setStatus(s)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [])

  async function handleSave() {
    if (!apiKey.trim() || apiKey.length < 10) {
      toast.error("Please enter a valid API key")
      return
    }
    setSaving(true)
    try {
      const s = await updateApiKey({ api_key: apiKey })
      setStatus(s)
      setApiKey("")
      setShowKey(false)
      toast.success("API key saved and validated")
      await refreshUser()
    } catch {
      // Error toast is shown by API client
    } finally {
      setSaving(false)
    }
  }

  async function handleRemove() {
    await deleteApiKey()
    setRemoveOpen(false)
    toast.success("API key removed")
    await loadStatus()
    await refreshUser()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Settings" description="Manage your account settings" />

      <Card className="p-6 max-w-xl">
        <h3 className="text-lg font-semibold mb-1">OpenAI API Key</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Your first run is free. After that, provide your own OpenAI API key to
          continue running pipelines.
        </p>

        {status && (
          <div className="mb-4 text-sm">
            <span className="text-muted-foreground">Free runs used: </span>
            <span className="font-medium">
              {status.free_runs_used} / {status.free_run_limit}
            </span>
          </div>
        )}

        {status?.has_api_key ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Current key:</span>
              <code className="bg-muted px-2 py-1 rounded text-xs">
                {status.key_last_four}
              </code>
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setRemoveOpen(true)}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Remove key
              </Button>
            </div>

            <div className="pt-3 border-t">
              <Label htmlFor="new-key" className="text-sm font-medium">
                Update key
              </Label>
              <div className="flex gap-2 mt-1.5">
                <div className="relative flex-1">
                  <Input
                    id="new-key"
                    type={showKey ? "text" : "password"}
                    placeholder="sk-..."
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSave()}
                  />
                  <button
                    type="button"
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    onClick={() => setShowKey(!showKey)}
                  >
                    {showKey ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <Button onClick={handleSave} disabled={saving}>
                  {saving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div>
            <Label htmlFor="api-key" className="text-sm font-medium">
              API Key
            </Label>
            <div className="flex gap-2 mt-1.5">
              <div className="relative flex-1">
                <Input
                  id="api-key"
                  type={showKey ? "text" : "password"}
                  placeholder="sk-..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSave()}
                />
                <button
                  type="button"
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  onClick={() => setShowKey(!showKey)}
                >
                  {showKey ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Save className="h-4 w-4 mr-2" />
                )}
                Save
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Your key is validated with OpenAI before saving and stored encrypted.
            </p>
          </div>
        )}
      </Card>

      <AlertDialog open={removeOpen} onOpenChange={setRemoveOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove API key?</AlertDialogTitle>
            <AlertDialogDescription>
              You will not be able to run pipelines until you add a new key
              (unless you still have free runs remaining).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRemove}>
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
