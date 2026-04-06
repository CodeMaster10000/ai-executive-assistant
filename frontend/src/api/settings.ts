import { get, put, del } from "./client"
import type { ApiKeyStatus, ApiKeyUpdate } from "./types"

export function getApiKeyStatus() {
  return get<ApiKeyStatus>("/settings/api-key-status")
}

export function updateApiKey(data: ApiKeyUpdate) {
  return put<ApiKeyStatus>("/settings/api-key", data)
}

export function deleteApiKey() {
  return del<{ detail: string }>("/settings/api-key")
}
