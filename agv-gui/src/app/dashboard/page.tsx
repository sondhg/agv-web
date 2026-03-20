export default function DashboardPage() {
  return (
    <div className="container mx-auto space-y-6 py-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to the AGV Fleet Management Dashboard
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-lg border bg-card p-6">
          <h3 className="mb-2 text-lg font-semibold">Fleet Overview</h3>
          <p className="text-sm text-muted-foreground">
            Monitor your AGV fleet status in real-time
          </p>
        </div>

        <div className="rounded-lg border bg-card p-6">
          <h3 className="mb-2 text-lg font-semibold">Active Tasks</h3>
          <p className="text-sm text-muted-foreground">
            Track ongoing operations and assignments
          </p>
        </div>

        <div className="rounded-lg border bg-card p-6">
          <h3 className="mb-2 text-lg font-semibold">System Health</h3>
          <p className="text-sm text-muted-foreground">
            Monitor system performance and alerts
          </p>
        </div>
      </div>
    </div>
  )
}
