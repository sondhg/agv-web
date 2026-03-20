export default function TaskBiddingPage() {
  return (
    <div className="container mx-auto space-y-6 py-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Task Bidding</h1>
        <p className="text-muted-foreground">
          Monitor the auction-based task assignment system
        </p>
      </div>

      <div className="rounded-lg border bg-card p-6">
        <p className="text-muted-foreground">
          This page will display active bidding processes, task assignments, and
          AGV selection based on the auction system.
        </p>
      </div>
    </div>
  )
}
