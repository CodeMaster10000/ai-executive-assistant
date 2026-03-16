import { useEffect, useState } from "react"
import { Shield } from "lucide-react"
import { listPolicies } from "@/api/policies"
import type { Policy } from "@/api/types"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingSpinner } from "@/components/shared/LoadingSpinner"
import { EmptyState } from "@/components/shared/EmptyState"
import { Badge } from "@/components/ui/badge"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import yaml from "@/lib/yaml"

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listPolicies()
      .then(setPolicies)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Policies"
        description="Read-only policy files governing agent behavior"
        actions={
          <Badge variant="secondary" className="text-xs">
            Read-only
          </Badge>
        }
      />

      {policies.length === 0 ? (
        <EmptyState
          icon={<Shield className="h-10 w-10" />}
          title="No policies found"
          description="Policy YAML files should be placed in the /policy directory."
        />
      ) : (
        <Accordion type="multiple" className="w-full">
          {policies.map((p) => (
            <AccordionItem key={p.name} value={p.name}>
              <AccordionTrigger className="text-sm font-medium">
                {p.name}.yaml
              </AccordionTrigger>
              <AccordionContent>
                <pre className="bg-muted rounded-md p-4 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
                  {yaml.dump(p.content)}
                </pre>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      )}
    </div>
  )
}
