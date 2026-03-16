import { useEffect, useState, useCallback } from "react"
import { useParams } from "react-router-dom"
import { RefreshCw, Ban, GitCompare } from "lucide-react"
import { getRun, cancelRun } from "@/api/runs"
import { getAudit, getVerifierReport, replay } from "@/api/audit"
import type { Run, AuditEvent, SSEEvent } from "@/api/types"
import { useSSE } from "@/hooks/useSSE"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingSpinner } from "@/components/shared/LoadingSpinner"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { toast } from "sonner"

const AGENT_NAMES = [
  "job_scout",
  "cert_scout",
  "trend_scout",
  "extractor",
  "coordinator",
  "ceo",
  "cfo",
  "cover_letter_agent",
  "verifier",
  "audit_writer",
]

type AgentStatus = "idle" | "running" | "complete"

function deriveAgentStatuses(events: SSEEvent[]): Record<string, AgentStatus> {
  const statuses: Record<string, AgentStatus> = {}
  for (const name of AGENT_NAMES) statuses[name] = "idle"
  for (const e of events) {
    if (e.agent && e.type === "agent_started") statuses[e.agent] = "running"
    if (e.agent && e.type === "agent_completed") statuses[e.agent] = "complete"
  }
  return statuses
}

export default function RunDetailPage() {
  const { profileId, runId } = useParams()
  const [run, setRun] = useState<Run | null>(null)
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [verifierReport, setVerifierReport] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const { events: sseEvents, done: sseDone } = useSSE(
    profileId,
    run?.status === "running" || run?.status === "pending" ? runId : undefined,
  )

  const load = useCallback(() => {
    if (!profileId || !runId) return
    getRun(profileId, runId)
      .then(setRun)
      .finally(() => setLoading(false))
    getAudit(profileId, runId)
      .then((a) => setAuditEvents(a.events))
      .catch(() => {})
    getVerifierReport(profileId, runId)
      .then(setVerifierReport)
      .catch(() => {})
  }, [profileId, runId])

  useEffect(() => { load() }, [load])

  // Refresh run data when SSE indicates completion
  useEffect(() => {
    if (sseDone) load()
  }, [sseDone, load])

  async function handleCancel() {
    if (!profileId || !runId) return
    await cancelRun(profileId, runId)
    toast.success("Cancellation requested")
    load()
  }

  async function handleReplay(mode: "strict" | "refresh") {
    if (!profileId || !runId) return
    const res = await replay(profileId, runId, { mode })
    toast.success(`Replay complete (${mode}): ${res.run_id.slice(0, 8)}`)
  }

  if (loading) return <LoadingSpinner />
  if (!run) return <p className="text-muted-foreground">Run not found.</p>

  const isActive = run.status === "running" || run.status === "pending"
  const agentStatuses = deriveAgentStatuses(sseEvents)

  return (
    <div>
      <PageHeader
        title={`Run ${run.id.slice(0, 8)}`}
        actions={
          <div className="flex gap-2">
            {isActive && (
              <Button variant="destructive" onClick={handleCancel}>
                <Ban className="h-4 w-4 mr-2" /> Cancel
              </Button>
            )}
            {!isActive && (
              <>
                <Button variant="outline" onClick={() => handleReplay("strict")}>
                  <RefreshCw className="h-4 w-4 mr-2" /> Replay (strict)
                </Button>
                <Button variant="outline" onClick={() => handleReplay("refresh")}>
                  <GitCompare className="h-4 w-4 mr-2" /> Replay (refresh)
                </Button>
              </>
            )}
          </div>
        }
      />

      {/* Run info card */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <p className="text-xs text-muted-foreground">Mode</p>
              <Badge variant="outline">{run.mode}</Badge>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Status</p>
              <StatusBadge status={run.status} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Verifier</p>
              <StatusBadge status={run.verifier_status} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Duration</p>
              <p className="text-sm font-medium">
                {run.started_at && run.finished_at
                  ? `${((new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000).toFixed(1)}s`
                  : run.started_at
                    ? "In progress..."
                    : "-"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Pipeline progress (SSE) */}
      {isActive && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Pipeline Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {AGENT_NAMES.map((name) => {
                const s = agentStatuses[name]
                return (
                  <div key={name} className="flex items-center gap-2 px-3 py-1.5 border rounded-md text-xs">
                    <span
                      className={
                        s === "complete"
                          ? "h-2 w-2 rounded-full bg-green-500"
                          : s === "running"
                            ? "h-2 w-2 rounded-full bg-blue-500 animate-pulse"
                            : "h-2 w-2 rounded-full bg-gray-300"
                      }
                    />
                    {name.replace(/_/g, " ")}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="audit">
        <TabsList>
          <TabsTrigger value="audit">Audit Trail</TabsTrigger>
          <TabsTrigger value="verifier">Verifier Report</TabsTrigger>
          <TabsTrigger value="outputs">Outputs</TabsTrigger>
        </TabsList>

        <TabsContent value="audit">
          <AuditTimeline events={auditEvents} />
        </TabsContent>

        <TabsContent value="verifier">
          <VerifierReportView report={verifierReport} />
        </TabsContent>

        <TabsContent value="outputs">
          <Card>
            <CardContent className="pt-6">
              <pre className="bg-muted rounded-md p-4 text-xs font-mono overflow-x-auto whitespace-pre-wrap max-h-[600px]">
                {run.audit_path ? `Artifacts stored at: ${run.audit_path}` : "No outputs available."}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function AuditTimeline({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No audit events recorded.</p>
  }

  const dotColor: Record<string, string> = {
    agent_start: "bg-blue-500",
    agent_end: "bg-green-500",
    verifier: "bg-yellow-500",
    error: "bg-red-500",
  }

  return (
    <div className="relative ml-4 border-l pl-6 space-y-4 py-4">
      {events.map((e, i) => (
        <div key={i} className="relative">
          <span
            className={`absolute -left-[1.85rem] top-1.5 h-3 w-3 rounded-full border-2 border-background ${dotColor[e.event_type] ?? "bg-gray-400"}`}
          />
          <p className="text-xs text-muted-foreground">{e.timestamp}</p>
          <p className="text-sm font-medium">
            {e.agent} — <span className="font-normal text-muted-foreground">{e.event_type}</span>
          </p>
          {Object.keys(e.data).length > 0 && (
            <pre className="mt-1 bg-muted rounded p-2 text-xs font-mono overflow-x-auto">
              {JSON.stringify(e.data, null, 2)}
            </pre>
          )}
        </div>
      ))}
    </div>
  )
}

function VerifierReportView({ report }: { report: Record<string, unknown> | null }) {
  if (!report || Object.keys(report).length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No verifier report available.</p>
  }

  const overall = (report.overall_status as string) ?? "unknown"
  const checks = (report.checks as Array<Record<string, unknown>>) ?? []

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <CardTitle className="text-base">Overall Status</CardTitle>
          <StatusBadge status={overall} />
        </div>
      </CardHeader>
      <CardContent>
        {checks.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Check</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {checks.map((c, i) => (
                <TableRow key={i}>
                  <TableCell className="text-sm">{String(c.name ?? c.check ?? `Check ${i + 1}`)}</TableCell>
                  <TableCell>
                    <StatusBadge status={String(c.status ?? "unknown")} />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {c.message ? String(c.message) : "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <pre className="bg-muted rounded-md p-4 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(report, null, 2)}
          </pre>
        )}
      </CardContent>
    </Card>
  )
}
