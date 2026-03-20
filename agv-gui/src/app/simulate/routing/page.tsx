export default function RoutingPage() {
  return (
    <div className="container mx-auto space-y-6 py-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Routing Simulation
        </h1>
        <p className="text-muted-foreground">
          Simulate and visualize AGV routing paths
        </p>
      </div>

      <div className="rounded-lg border bg-card p-6">
        <p className="text-muted-foreground">
          This page will provide tools to simulate AGV routing, test pathfinding
          algorithms, and visualize trajectories.
        </p>
      </div>
    </div>
  )
}
