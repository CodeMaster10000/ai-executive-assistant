import { get, post, put, del, upload } from "./client"
import type { Profile, ProfileCreate, ProfileUpdate } from "./types"

export function listProfiles() {
  return get<Profile[]>("/profiles")
}

export function getProfile(id: string) {
  return get<Profile>(`/profiles/${id}`)
}

export function createProfile(data: ProfileCreate) {
  return post<Profile>("/profiles", data)
}

export function updateProfile(id: string, data: ProfileUpdate) {
  return put<Profile>(`/profiles/${id}`, data)
}

export function deleteProfile(id: string) {
  return del(`/profiles/${id}`)
}

export function uploadCv(profileId: string, file: File) {
  return upload<{ detail: string; cv_path: string }>(`/profiles/${profileId}/cv`, file)
}
