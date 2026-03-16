import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { Play, Ban } from "lucide-react"
import { listRuns, createRun, cancelRun } from "@/api/runs"
import type { Run, RunCreate } from "@/api/types"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingSpinner } from "@/components/shared/LoadingSpinner"
import { EmptyState } from "@/components/shared/EmptyState"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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

export default function RunsListPage() {
  const { profileId } = useParams()
  const navigate = useNavigate()
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [mode, setMode] = useState<RunCreate["mode"]>("daily")
  const [cancelTarget, setCancelTarget] = useState<Run | null>(null)

  function load() {
    if (!profileId) return
    listRuns(profileId)
      .then(setRuns)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [profileId])

  async function handleStart() {
    if (!profileId) return
    const run = await createRun(profileId, { mode })
    toast.success(`Run started (${mode})`)
    navigate(`/profiles/${profileId}/runs/${run.id}`)
  }

  async function handleCancel(run: Run) {
    if (!profileId) return
    await cancelRun(profileId, run.id)
    toast.success("Cancellation requested")
    setCancelTarget(null)
    load()
  }

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader title="Runs" description="Pipeline execution history" />

      {/* Start run controls */}
      <Card className="p-4 mb-6">
        <div className="flex items-center gap-3">
          <Select value={mode} onValueChange={(v) => setMode(v as RunCreate["mode"])}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="daily">Daily</SelectItem>
              <SelectItem value="weekly">Weekly</SelectItem>
              <SelectItem value="cover_letter">Cover Letter</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={handleStart}>
            <Play className="h-4 w-4 mr-2" /> Start Run
          </Button>
        </div>
      </Card>

      {runs.length === 0 ? (
        <EmptyState
          icon={<Play className="h-10 w-10" />}
          title="No runs yet"
          description="Start your first pipeline run above."
        />
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run ID</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Verifier</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Finished</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((r) => (
                <TableRow
                  key={r.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/profiles/${profileId}/runs/${r.id}`)}
                >
                  <TableCell className="font-mono text-xs">{r.id.slice(0, 8)}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{r.mode}</Badge>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={r.status} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={r.verifier_status} />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {r.started_at ? new Date(r.started_at).toLocaleString() : "-"}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {r.finished_at ? new Date(r.finished_at).toLocaleString() : "-"}
                  </TableCell>
                  <TableCell>
                    {(r.status === "running" || r.status === "pending") && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation()
                          setCancelTarget(r)
                        }}
                      >
                        <Ban className="h-4 w-4" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      <AlertDialog open={!!cancelTarget} onOpenChange={() => setCancelTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel run?</AlertDialogTitle>
            <AlertDialogDescription>
              This will request cancellation of run {cancelTarget?.id.slice(0, 8)}.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>No</AlertDialogCancel>
            <AlertDialogAction onClick={() => cancelTarget && handleCancel(cancelTarget)}>
              Yes, cancel
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
