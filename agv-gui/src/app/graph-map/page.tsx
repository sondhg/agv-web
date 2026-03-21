import { GuideAlerts } from "./guide-alerts"
import { ProviderFlow } from "./provider-flow"

export default function GraphMapPage() {
  return (
    <div className="container mx-auto space-y-6 py-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Graph map</h1>
        <p className="text-muted-foreground">
          Create graph map to mimic real warehouse environment.
        </p>
      </div>
      <GuideAlerts />
      {/* Needs height and width specified for ReactFlow */}
      <div className="h-screen w-full border-2 border-black">
        <ProviderFlow />
      </div>
    </div>
  )
}
