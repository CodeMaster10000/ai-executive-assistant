import { get, post } from "./client"
import type { CoverLetter, CoverLetterCreate } from "./types"

export function listCoverLetters(profileId: string) {
  return get<CoverLetter[]>(`/profiles/${profileId}/cover-letters`)
}

export function getCoverLetter(profileId: string, letterId: string) {
  return get<CoverLetter>(`/profiles/${profileId}/cover-letters/${letterId}`)
}

export function createCoverLetter(profileId: string, data: CoverLetterCreate) {
  return post<CoverLetter>(`/profiles/${profileId}/cover-letters`, data)
}
