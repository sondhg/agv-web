import { Background, Controls, ReactFlow } from "@xyflow/react"
import "@xyflow/react/dist/style.css"

export default function GraphMapPage() {
  const initialNodes = [
    {
      id: "n1",
      position: { x: 0, y: 0 },
      data: { label: "Node 1" },
      type: "input",
    },
    {
      id: "n2",
      position: { x: 100, y: 100 },
      data: { label: "Node 2" },
    },
  ]
  return (
    <div className="container mx-auto space-y-6 py-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Graph map</h1>
        <p className="text-muted-foreground">
          Create graph map to mimic real warehouse environment.
        </p>
      </div>

      <div className="rounded-lg border bg-card p-6">
        <p className="text-muted-foreground">
          Click to create nodes, then click on a node and drag to another node
          to create edges.
        </p>
      </div>

      <div style={{ height: "100vh", width: "100%" }}>
        <ReactFlow nodes={initialNodes}>
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  )
}
