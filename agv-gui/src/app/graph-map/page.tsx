import { Button } from "@/components/ui/button"
import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  type Edge,
  type Node,
  type OnConnect,
  type OnEdgesChange,
  type OnNodeDrag,
  type OnNodesChange,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { useCallback, useState } from "react"

export default function GraphMapPage() {
  const onNodeDrag: OnNodeDrag = (_, node) => {
    console.log("drag event", node.data)
  }

  const [variant, setVariant] = useState(BackgroundVariant.Dots)

  const initialNodes: Node[] = [
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

  const initialEdges: Edge[] = [
    {
      id: "n1-n2",
      source: "n1",
      target: "n2",
    },
  ]

  const [nodes, setNodes] = useState(initialNodes)
  const [edges, setEdges] = useState(initialEdges)

  const onNodesChange: OnNodesChange = useCallback(
    (changes) =>
      setNodes((nodesSnapshot) => applyNodeChanges(changes, nodesSnapshot)),
    []
  )

  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) =>
      setEdges((edgesSnapshot) => applyEdgeChanges(changes, edgesSnapshot)),
    []
  )

  const onConnect: OnConnect = useCallback(
    (params) => setEdges((edgesSnapshot) => addEdge(params, edgesSnapshot)),
    []
  )

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

      <div
        style={{ height: "100vh", width: "100%" }}
        className="border-2 border-black"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeDrag={onNodeDrag}
          fitView
        >
          <MiniMap nodeStrokeWidth={3} zoomable pannable />
          <Background variant={variant} />
          <Panel>
            <div>variant:</div>
            <Button onClick={() => setVariant(BackgroundVariant.Dots)}>
              dots
            </Button>
            <Button onClick={() => setVariant(BackgroundVariant.Lines)}>
              lines
            </Button>
            <Button onClick={() => setVariant(BackgroundVariant.Cross)}>
              cross
            </Button>
          </Panel>
          <Controls />
        </ReactFlow>
      </div>
    </div>
  )
}
