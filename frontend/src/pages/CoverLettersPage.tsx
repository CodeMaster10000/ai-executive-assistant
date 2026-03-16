import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { FileEdit, Plus } from "lucide-react"
import { listCoverLetters, createCoverLetter } from "@/api/coverLetters"
import { listOpportunities } from "@/api/opportunities"
import type { CoverLetter, Opportunity } from "@/api/types"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingSpinner } from "@/components/shared/LoadingSpinner"
import { EmptyState } from "@/components/shared/EmptyState"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"

export default function CoverLettersPage() {
  const { profileId } = useParams()
  const [letters, setLetters] = useState<CoverLetter[]>([])
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedOpp, setSelectedOpp] = useState<string>("")
  const [jdText, setJdText] = useState("")
  const [expanded, setExpanded] = useState<string | null>(null)

  function load() {
    if (!profileId) return
    Promise.all([listCoverLetters(profileId), listOpportunities(profileId)])
      .then(([cl, opps]) => {
        setLetters(cl)
        setOpportunities(opps)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [profileId])

  async function handleGenerate() {
    if (!profileId) return
    await createCoverLetter(profileId, {
      opportunity_id: selectedOpp || undefined,
      jd_text: jdText || undefined,
    })
    toast.success("Cover letter generation started")
    setDialogOpen(false)
    setSelectedOpp("")
    setJdText("")
    load()
  }

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Cover Letters"
        description="Generated cover letters"
        actions={
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" /> Generate
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Generate Cover Letter</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                <div>
                  <Label>Select Opportunity (optional)</Label>
                  <Select value={selectedOpp} onValueChange={setSelectedOpp}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose an opportunity..." />
                    </SelectTrigger>
                    <SelectContent>
                      {opportunities.map((o) => (
                        <SelectItem key={o.id} value={o.id}>
                          {o.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Or paste job description</Label>
                  <Textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder="Paste the job description here..."
                    rows={6}
                  />
                </div>
                <Button onClick={handleGenerate} className="w-full">
                  Generate
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        }
      />

      {letters.length === 0 ? (
        <EmptyState
          icon={<FileEdit className="h-10 w-10" />}
          title="No cover letters yet"
          description="Generate a cover letter from an opportunity or a raw job description."
          actionLabel="Generate"
          onAction={() => setDialogOpen(true)}
        />
      ) : (
        <div className="space-y-4">
          {letters.map((cl) => (
            <Card
              key={cl.id}
              className="cursor-pointer"
              onClick={() => setExpanded(expanded === cl.id ? null : cl.id)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">
                    Cover Letter — {new Date(cl.created_at).toLocaleDateString()}
                  </CardTitle>
                  <div className="flex gap-1">
                    {cl.opportunity_id && (
                      <Badge variant="secondary" className="text-xs">
                        Opportunity linked
                      </Badge>
                    )}
                    {cl.evidence_ids.length > 0 && (
                      <Badge variant="outline" className="text-xs">
                        {cl.evidence_ids.length} evidence
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              {expanded === cl.id ? (
                <CardContent>
                  <div className="bg-muted rounded-md p-4 text-sm whitespace-pre-wrap">
                    {cl.content}
                  </div>
                </CardContent>
              ) : (
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-2">{cl.content}</p>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
