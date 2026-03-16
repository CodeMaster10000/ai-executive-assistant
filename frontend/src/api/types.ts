// Mirrors Pydantic schemas in app/schemas/

export interface ProfileCreate {
  name: string
  targets?: string[] | null
  constraints?: string[] | null
  skills?: string[] | null
}

export interface ProfileUpdate {
  name?: string | null
  targets?: string[] | null
  constraints?: string[] | null
  skills?: string[] | null
}

export interface Profile {
  id: string
  name: string
  targets: string[] | null
  constraints: string[] | null
  skills: string[] | null
  cv_path: string | null
  created_at: string
  updated_at: string
}

export interface RunCreate {
  mode: "daily" | "weekly" | "cover_letter"
  options?: Record<string, unknown> | null
}

export interface Run {
  id: string
  profile_id: string
  mode: string
  status: string
  started_at: string | null
  finished_at: string | null
  verifier_status: string | null
  audit_path: string | null
}

export interface Opportunity {
  id: string
  profile_id: string
  run_id: string
  opportunity_type: string
  title: string
  source: string
  url: string | null
  description: string | null
  evidence_ids: string[]
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface CoverLetterCreate {
  opportunity_id?: string | null
  jd_text?: string | null
}

export interface CoverLetter {
  id: string
  profile_id: string
  opportunity_id: string | null
  run_id: string | null
  content: string
  evidence_ids: string[]
  created_at: string
}

export interface Policy {
  name: string
  content: Record<string, unknown>
}

export interface SSEEvent {
  type: string
  run_id?: string
  agent?: string
  status?: string
  verifier_status?: string
  error?: string
  timestamp?: string
  mode?: string
}

export interface AuditEvent {
  timestamp: string
  event_type: string
  agent: string
  data: Record<string, unknown>
}

export interface AuditTrail {
  run_id: string
  events: AuditEvent[]
}

export interface ReplayRequest {
  mode: "strict" | "refresh"
}

export interface ReplayResponse {
  run_id: string
  replay_mode: string
  original_run_id: string
  result: Record<string, unknown>
  verifier_report: Record<string, unknown>
  drift: unknown[]
}

export interface DiffResponse {
  run_a: string
  run_b: string
  additions: unknown[]
  removals: unknown[]
  changes: unknown[]
  summary: Record<string, unknown>
}
