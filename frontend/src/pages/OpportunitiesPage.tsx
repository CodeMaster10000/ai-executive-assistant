import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { Briefcase, Search } from "lucide-react"
import { listOpportunities } from "@/api/opportunities"
import type { Opportunity } from "@/api/types"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingSpinner } from "@/components/shared/LoadingSpinner"
import { EmptyState } from "@/components/shared/EmptyState"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"

export default function OpportunitiesPage() {
  const { profileId } = useParams()
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState("")

  useEffect(() => {
    if (!profileId) return
    listOpportunities(profileId)
      .then(setOpportunities)
      .finally(() => setLoading(false))
  }, [profileId])

  if (loading) return <LoadingSpinner />

  const filtered = opportunities.filter((o) => {
    const q = filter.toLowerCase()
    return (
      !q ||
      o.title.toLowerCase().includes(q) ||
      o.opportunity_type.toLowerCase().includes(q) ||
      (o.description ?? "").toLowerCase().includes(q)
    )
  })

  return (
    <div>
      <PageHeader title="Opportunities" description="Discovered career opportunities" />

      {opportunities.length > 0 && (
        <div className="relative mb-6 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter by title or type..."
            className="pl-9"
          />
        </div>
      )}

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Briefcase className="h-10 w-10" />}
          title={opportunities.length === 0 ? "No opportunities yet" : "No matches"}
          description={
            opportunities.length === 0
              ? "Run a daily or weekly pipeline to discover opportunities."
              : "Try a different search term."
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((o) => (
            <Card key={o.id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base leading-snug">{o.title}</CardTitle>
                  <Badge variant="outline" className="shrink-0">
                    {o.opportunity_type}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground mb-2">{o.source}</p>
                {o.description && (
                  <p className="text-sm line-clamp-3">{o.description}</p>
                )}
                {o.url && (
                  <a
                    href={o.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline mt-2 inline-block"
                  >
                    View source
                  </a>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
