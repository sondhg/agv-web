import { useCallback, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

const initialNodes = [
  {
    id: "1",
    data: { label: "Node 1" },
    position: { x: 250, y: 5 },
  },
  { id: "2", data: { label: "Node 2" }, position: { x: 100, y: 100 } },
  { id: "3", data: { label: "Node 3" }, position: { x: 400, y: 100 } },
  { id: "4", data: { label: "Node 4" }, position: { x: 400, y: 200 } },
]

const initialEdges = [
  {
    id: "e1-2",
    source: "1",
    target: "2",
  },
  { id: "e1-3", source: "1", target: "3" },
]

const ProviderFlow = () => {
  const [backgroundVariant, setBackgroundVariant] = useState(
    BackgroundVariant.Dots
  )

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const onConnect = useCallback(
    (params) => setEdges((els) => addEdge(params, els)),
    []
  )

  return (
    <ReactFlowProvider>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        // fitView
      >
        <MiniMap nodeStrokeWidth={3} zoomable pannable />
        <Background variant={backgroundVariant} />
        <Panel>
          <div>Change background grid:</div>
          <div className="flex gap-2">
            {Object.values(BackgroundVariant).map((v) => (
              <Button key={v} onClick={() => setBackgroundVariant(v)}>
                {v}
              </Button>
            ))}
          </div>
        </Panel>
        <Controls />
      </ReactFlow>
    </ReactFlowProvider>
  )
}

export default ProviderFlow
