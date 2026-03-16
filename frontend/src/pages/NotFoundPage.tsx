import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="text-muted-foreground mt-2">Page not found</p>
      <Button asChild className="mt-6">
        <Link to="/">Go to Dashboard</Link>
      </Button>
    </div>
  )
}
