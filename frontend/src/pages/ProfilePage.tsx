import { useEffect, useState, useCallback, useRef } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { Save, Trash2, Upload, Download, X, Plus, Play, Briefcase, FileEdit, Sparkles } from "lucide-react"
import { getProfile, updateProfile, deleteProfile, uploadCv, extractSkillsFromCv, exportProfile, importProfile } from "@/api/profiles"
import type { Profile, ProfileUpdate } from "@/api/types"
import { useProfiles } from "@/contexts/ProfileContext"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingSpinner } from "@/components/shared/LoadingSpinner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { toast } from "sonner"

const EXPERIENCE_LEVELS = ["junior", "mid", "senior", "lead", "principal", "executive"]
const WORK_ARRANGEMENTS = ["remote", "hybrid", "onsite", "flexible"]
const EVENT_ATTENDANCES = ["local", "remote", "no preference"]
const LEARNING_FORMATS = ["online", "in-person", "self-paced", "instructor-led"]

export default function ProfilePage() {
  const { profileId } = useParams()
  const navigate = useNavigate()
  const { profiles, refresh: refreshProfiles } = useProfiles()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)

  const [name, setName] = useState("")
  const [targets, setTargets] = useState<string[]>([])
  const [constraints, setConstraints] = useState<string[]>([])
  const [skills, setSkills] = useState<string[]>([])
  // Career & Job
  const [preferredTitles, setPreferredTitles] = useState<string[]>([])
  const [experienceLevel, setExperienceLevel] = useState("")
  const [industries, setIndustries] = useState<string[]>([])
  const [locations, setLocations] = useState<string[]>([])
  const [workArrangement, setWorkArrangement] = useState("")
  const [eventAttendance, setEventAttendance] = useState("")
  // Learning & Certification
  const [targetCertifications, setTargetCertifications] = useState<string[]>([])
  const [learningFormat, setLearningFormat] = useState("")
  const [importConflict, setImportConflict] = useState<{ existingId: string; data: Record<string, unknown> } | null>(null)

  const draftKey = profileId ? `profile-draft-${profileId}` : null

  const load = useCallback(() => {
    if (!profileId || !draftKey) return
    getProfile(profileId)
      .then((p) => {
        setProfile(p)
        const raw = localStorage.getItem(draftKey)
        if (raw) {
          try {
            const draft = JSON.parse(raw)
            setName(draft.name ?? p.name)
            setTargets(draft.targets ?? p.targets ?? [])
            setConstraints(draft.constraints ?? p.constraints ?? [])
            setSkills(draft.skills ?? p.skills ?? [])
            setPreferredTitles(draft.preferred_titles ?? p.preferred_titles ?? [])
            setExperienceLevel(draft.experience_level ?? p.experience_level ?? "")
            setIndustries(draft.industries ?? p.industries ?? [])
            setLocations(draft.locations ?? p.locations ?? [])
            setWorkArrangement(draft.work_arrangement ?? p.work_arrangement ?? "")
            setEventAttendance(draft.event_attendance ?? p.event_attendance ?? "")
            setTargetCertifications(draft.target_certifications ?? p.target_certifications ?? [])
            setLearningFormat(draft.learning_format ?? p.learning_format ?? "")
            return
          } catch { /* ignore corrupt draft */ }
        }
        setName(p.name)
        setTargets(p.targets ?? [])
        setConstraints(p.constraints ?? [])
        setSkills(p.skills ?? [])
        setPreferredTitles(p.preferred_titles ?? [])
        setExperienceLevel(p.experience_level ?? "")
        setIndustries(p.industries ?? [])
        setLocations(p.locations ?? [])
        setWorkArrangement(p.work_arrangement ?? "")
        setEventAttendance(p.event_attendance ?? "")
        setTargetCertifications(p.target_certifications ?? [])
        setLearningFormat(p.learning_format ?? "")
      })
      .finally(() => setLoading(false))
  }, [profileId, draftKey])

  useEffect(() => { load() }, [load])

  // Persist draft to localStorage on changes
  const dirtyRef = useRef(false)
  useEffect(() => {
    if (!draftKey || !profile) return
    const draft = {
      name, targets, constraints, skills,
      preferred_titles: preferredTitles, experience_level: experienceLevel,
      industries, locations, work_arrangement: workArrangement, event_attendance: eventAttendance,
      target_certifications: targetCertifications, learning_format: learningFormat,
    }
    const saved = {
      name: profile.name, targets: profile.targets ?? [], constraints: profile.constraints ?? [], skills: profile.skills ?? [],
      preferred_titles: profile.preferred_titles ?? [], experience_level: profile.experience_level ?? "",
      industries: profile.industries ?? [], locations: profile.locations ?? [], work_arrangement: profile.work_arrangement ?? "", event_attendance: profile.event_attendance ?? "",
      target_certifications: profile.target_certifications ?? [], learning_format: profile.learning_format ?? "",
    }
    const dirty = JSON.stringify(draft) !== JSON.stringify(saved)
    dirtyRef.current = dirty
    if (dirty) {
      localStorage.setItem(draftKey, JSON.stringify(draft))
    } else {
      localStorage.removeItem(draftKey)
    }
  }, [draftKey, name, targets, constraints, skills, preferredTitles, experienceLevel, industries, locations, workArrangement, eventAttendance, targetCertifications, learningFormat, profile])

  // Warn on navigation away with unsaved changes
  useEffect(() => {
    return () => {
      if (dirtyRef.current) {
        toast.warning("You have unsaved profile changes. Your draft has been saved.")
      }
    }
  }, [profileId])

  function canSave() {
    return name.trim().length > 0 && targets.length > 0 && skills.length > 0 && preferredTitles.length > 0 && !!profile?.cv_path
  }

  async function handleSave() {
    if (!profileId) return
    if (!canSave()) {
      const missing: string[] = []
      if (!name.trim()) missing.push("a name")
      if (targets.length === 0) missing.push("career goals")
      if (skills.length === 0) missing.push("skills")
      if (preferredTitles.length === 0) missing.push("preferred job titles")
      if (!profile?.cv_path) missing.push("a CV")
      toast.error(`Please add ${missing.join(", ")} before saving`)
      return
    }
    const data: ProfileUpdate = {
      name, targets, constraints, skills,
      preferred_titles: preferredTitles,
      experience_level: experienceLevel || null,
      industries: industries.length > 0 ? industries : null,
      locations: locations.length > 0 ? locations : null,
      work_arrangement: workArrangement || null,
      event_attendance: eventAttendance || null,
      target_certifications: targetCertifications.length > 0 ? targetCertifications : null,
      learning_format: learningFormat || null,
    }
    const updated = await updateProfile(profileId, data)
    setProfile(updated)
    if (draftKey) localStorage.removeItem(draftKey)
    await refreshProfiles()
    toast.success("Profile saved")
  }

  async function handleDelete() {
    if (!profileId) return
    await deleteProfile(profileId)
    if (draftKey) localStorage.removeItem(draftKey)
    await refreshProfiles()
    toast.success("Profile deleted")
    navigate("/")
  }

  async function handleCvUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!profileId || !e.target.files?.[0]) return
    const file = e.target.files[0]
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      toast.error("Only PDF files are accepted")
      e.target.value = ""
      return
    }
    const updated = await uploadCv(profileId, file)
    setProfile(updated)
    toast.success("CV uploaded")
  }

  const [extracting, setExtracting] = useState(false)

  async function handleExtractSkills() {
    if (!profileId) return
    setExtracting(true)
    try {
      const { skills: extracted } = await extractSkillsFromCv(profileId)
      const merged = [...new Set([...skills, ...extracted])]
      setSkills(merged)
      toast.success(`Imported ${extracted.length} skills from CV`)
    } catch {
      toast.error("Failed to extract skills from CV")
    } finally {
      setExtracting(false)
    }
  }

  async function handleExport() {
    if (!profileId) return
    const data = await exportProfile(profileId)
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${profile?.name ?? "profile"}.json`
    a.click()
    URL.revokeObjectURL(url)
    toast.success("Profile exported")
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const text = await file.text()
      const data = JSON.parse(text)
      const existing = profiles.find((p) => p.name === data.name)
      if (existing) {
        setImportConflict({ existingId: existing.id, data })
        e.target.value = ""
        return
      }
      const created = await importProfile(data)
      await refreshProfiles()
      toast.success(`Profile "${created.name}" imported`)
      navigate(`/profiles/${created.id}`)
    } catch {
      toast.error("Failed to import profile. Check the file format.")
    }
    e.target.value = ""
  }

  async function handleImportReplace() {
    if (!importConflict) return
    const { existingId, data } = importConflict
    try {
      const { name: importName, ...rest } = data
      await updateProfile(existingId, { name: importName as string, ...rest })
      await refreshProfiles()
      toast.success(`Profile "${importName}" replaced`)
      setImportConflict(null)
      navigate(`/profiles/${existingId}`)
    } catch {
      toast.error("Failed to replace profile.")
      setImportConflict(null)
    }
  }

  if (loading) return <LoadingSpinner />
  if (!profile) return <p className="text-muted-foreground">Profile not found.</p>

  return (
    <div>
      <PageHeader
        title={profile.name}
        description={`Created ${new Date(profile.created_at).toLocaleDateString()}`}
        actions={
          <div className="flex gap-2">
            <Button onClick={handleSave} disabled={!canSave()}>
              <Save className="h-4 w-4 mr-2" /> Save
            </Button>
            <Button variant="outline" onClick={handleExport}>
              <Download className="h-4 w-4 mr-2" /> Export
            </Button>
            <Label
              htmlFor="profile-import"
              className="cursor-pointer inline-flex items-center gap-2 border rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors"
            >
              <Upload className="h-4 w-4" /> Import
            </Label>
            <input id="profile-import" type="file" accept=".json" className="hidden" onChange={handleImport} />
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive">
                  <Trash2 className="h-4 w-4 mr-2" /> Delete
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete profile?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will permanently delete "{profile.name}" and all associated data.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Name */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Name <span className="text-destructive">*</span></CardTitle>
          </CardHeader>
          <CardContent>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </CardContent>
        </Card>

        {/* CV Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">CV <span className="text-destructive">*</span></CardTitle>
          </CardHeader>
          <CardContent>
            {profile.cv_path ? (
              <p className="text-sm text-muted-foreground mb-2">
                Uploaded: {profile.cv_path.split("/").pop()}
              </p>
            ) : (
              <p className="text-sm text-muted-foreground mb-2">No CV uploaded. Must be in PDF format.</p>
            )}
            <div className="flex gap-2">
              <Label
                htmlFor="cv-upload"
                className="cursor-pointer inline-flex items-center gap-2 border rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors"
              >
                <Upload className="h-4 w-4" /> Upload CV
              </Label>
              <input id="cv-upload" type="file" accept=".pdf" className="hidden" onChange={handleCvUpload} />
              {profile.cv_path && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExtractSkills}
                  disabled={extracting}
                >
                  <Sparkles className="h-4 w-4 mr-2" />
                  {extracting ? "Extracting..." : "Import Skills from CV"}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Core profile */}
        <TagCard
          label="Career Goals"
          items={targets}
          onChange={setTargets}
          placeholder="e.g. Find a software engineering job / Obtain an AI certificate / Join communities"
          examples={["Move into a leadership position", "Earn a professional certification", "Transition to a new industry", "Grow my professional network"]}
          required
        />
        <TagCard label="Skills" items={skills} onChange={setSkills} required />

        {/* Career & Job section */}
        <div className="lg:col-span-2">
          <h3 className="text-sm font-medium text-muted-foreground mb-3 uppercase tracking-wide">Career & Job Preferences</h3>
        </div>
        <TagCard
          label="Preferred Job Titles"
          items={preferredTitles}
          onChange={setPreferredTitles}
          placeholder="e.g. Staff Engineer, Engineering Manager"
          examples={["Software Engineer", "Engineering Manager", "Data Scientist", "Product Manager"]}
          required
        />
        <SelectCard label="Experience Level" value={experienceLevel} onChange={setExperienceLevel} options={EXPERIENCE_LEVELS} optional />
        <TagCard
          label="Industries"
          items={industries}
          onChange={setIndustries}
          placeholder="e.g. Fintech, AI/ML, Healthcare"
          examples={["Fintech", "AI/ML", "Healthcare", "Climate Tech"]}
          optional
        />
        <TagCard
          label="Locations"
          items={locations}
          onChange={setLocations}
          placeholder="e.g. Remote, New York, London"
          examples={["Remote", "New York", "London", "Berlin"]}
          optional
        />
        <SelectCard label="Work Arrangement" value={workArrangement} onChange={setWorkArrangement} options={WORK_ARRANGEMENTS} optional />
        <TagCard
          label="Constraints"
          items={constraints}
          onChange={setConstraints}
          placeholder="e.g. No relocation, EU timezone"
          examples={["No relocation", "Part-time or flexible hours", "Salary > 150k", "No startups"]}
          optional
        />

        {/* Events & Networking section */}
        <div className="lg:col-span-2">
          <h3 className="text-sm font-medium text-muted-foreground mb-3 uppercase tracking-wide">Events & Networking</h3>
        </div>
        <SelectCard label="Event Attendance" value={eventAttendance} onChange={setEventAttendance} options={EVENT_ATTENDANCES} optional description="How you prefer to attend events. This controls whether scouts search for in-person events near your locations, virtual events, or both." />

        {/* Learning & Certification section */}
        <div className="lg:col-span-2">
          <h3 className="text-sm font-medium text-muted-foreground mb-3 uppercase tracking-wide">Learning & Certifications</h3>
        </div>
        <TagCard
          label="Target Certifications"
          items={targetCertifications}
          onChange={setTargetCertifications}
          placeholder="e.g. AWS Solutions Architect, PMP"
          examples={["AWS Solutions Architect", "PMP", "CKA/CKAD", "Google Cloud Professional"]}
          optional
        />
        <SelectCard label="Learning Format" value={learningFormat} onChange={setLearningFormat} options={LEARNING_FORMATS} optional />

        {/* Quick actions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button variant="outline" asChild>
              <Link to={`/profiles/${profileId}/runs`}>
                <Play className="h-4 w-4 mr-2" /> Runs
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to={`/profiles/${profileId}/results`}>
                <Briefcase className="h-4 w-4 mr-2" /> Results
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to={`/profiles/${profileId}/cover-letters`}>
                <FileEdit className="h-4 w-4 mr-2" /> Cover Letters
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
      <AlertDialog open={!!importConflict} onOpenChange={(open) => !open && setImportConflict(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Profile already exists</AlertDialogTitle>
            <AlertDialogDescription>
              A profile named "{String(importConflict?.data?.name ?? "")}" already exists. Do you want to replace it with the imported data?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleImportReplace}>Replace</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function TagCard({
  label,
  items,
  onChange,
  placeholder,
  examples,
  optional,
  required,
}: {
  label: string
  items: string[]
  onChange: (v: string[]) => void
  placeholder?: string
  examples?: string[]
  optional?: boolean
  required?: boolean
}) {
  const [input, setInput] = useState("")

  function add() {
    const val = input.trim()
    if (val && !items.includes(val)) {
      onChange([...items, val])
    }
    setInput("")
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
              {label}
              {required && <span className="text-destructive">*</span>}
              {optional && <span className="text-xs font-normal text-muted-foreground">(optional)</span>}
            </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-1 mb-2">
          {items.map((item) => (
            <Badge key={item} variant="secondary" className="gap-1">
              {item}
              <button onClick={() => onChange(items.filter((i) => i !== item))}>
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={placeholder ?? `Add ${label.toLowerCase()}...`}
            onKeyDown={(e) => e.key === "Enter" && add()}
            className="flex-1"
          />
          <Button variant="outline" size="icon" onClick={() => add()}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        {examples && items.length === 0 && (
          <div className="mt-3">
            <p className="text-xs text-muted-foreground mb-1.5">Examples:</p>
            <div className="flex flex-wrap gap-1">
              {examples.map((ex) => (
                <Badge key={ex} variant="outline" className="text-muted-foreground">
                  {ex}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function SelectCard({
  label,
  value,
  onChange,
  options,
  optional,
  description,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: string[]
  optional?: boolean
  description?: string
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
              {label}
              {optional && <span className="text-xs font-normal text-muted-foreground">(optional)</span>}
            </CardTitle>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </CardHeader>
      <CardContent>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex h-9 w-full rounded-md border border-input bg-background text-foreground px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <option value="" className="bg-background text-foreground">Not set</option>
          {options.map((opt) => (
            <option key={opt} value={opt} className="bg-background text-foreground">{opt.charAt(0).toUpperCase() + opt.slice(1)}</option>
          ))}
        </select>
      </CardContent>
    </Card>
  )
}
