import { get, post } from "./client"
import type { AuditTrail, ReplayRequest, ReplayResponse, DiffResponse } from "./types"

export function getAudit(profileId: string, runId: string) {
  return get<AuditTrail>(`/profiles/${profileId}/runs/${runId}/audit`)
}

export function getVerifierReport(profileId: string, runId: string) {
  return get<Record<string, unknown>>(`/profiles/${profileId}/runs/${runId}/verifier-report`)
}

export function replay(profileId: string, runId: string, data: ReplayRequest) {
  return post<ReplayResponse>(`/profiles/${profileId}/runs/${runId}/replay`, data)
}

export function diff(profileId: string, runId: string, otherRunId: string) {
  return get<DiffResponse>(`/profiles/${profileId}/runs/${runId}/diff/${otherRunId}`)
}
