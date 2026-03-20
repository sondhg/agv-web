export default function SensorDataPage() {
  return (
    <div className="container mx-auto space-y-6 py-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Sensor Data</h1>
        <p className="text-muted-foreground">
          Real-time sensor data from AGV fleet
        </p>
      </div>

      <div className="rounded-lg border bg-card p-6">
        <p className="text-muted-foreground">
          This page will display real-time sensor readings including position,
          speed, battery levels, and environmental data.
        </p>
      </div>
    </div>
  )
}
