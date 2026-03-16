import { get } from "./client"
import type { Opportunity } from "./types"

export function listOpportunities(profileId: string) {
  return get<Opportunity[]>(`/profiles/${profileId}/opportunities`)
}

export function getOpportunity(profileId: string, opportunityId: string) {
  return get<Opportunity>(`/profiles/${profileId}/opportunities/${opportunityId}`)
}
