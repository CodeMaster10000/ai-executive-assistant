import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const variants: Record<string, string> = {
  pass: "bg-green-100 text-green-800 border-green-200",
  completed: "bg-green-100 text-green-800 border-green-200",
  fail: "bg-red-100 text-red-800 border-red-200",
  failed: "bg-red-100 text-red-800 border-red-200",
  partial: "bg-yellow-100 text-yellow-800 border-yellow-200",
  running: "bg-blue-100 text-blue-800 border-blue-200",
  pending: "bg-gray-100 text-gray-800 border-gray-200",
  cancelled: "bg-gray-100 text-gray-600 border-gray-200",
  unknown: "bg-gray-100 text-gray-500 border-gray-200",
}

export function StatusBadge({ status, className }: { status: string | null; className?: string }) {
  const s = (status ?? "unknown").toLowerCase()
  return (
    <Badge variant="outline" className={cn(variants[s] ?? variants.unknown, className)}>
      {s}
    </Badge>
  )
}
