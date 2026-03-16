import { get } from "./client"
import type { Policy } from "./types"

export function listPolicies() {
  return get<Policy[]>("/policies")
}

export function getPolicy(name: string) {
  return get<Policy>(`/policies/${name}`)
}
