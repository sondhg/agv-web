import { Button } from "@/components/ui/button"
import {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  MiniMap,
  Panel,
  Position,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type Node,
  type OnConnect,
  type OnConnectEnd,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { useCallback, useRef, useState } from "react"
import Sidebar from "./sidebar"

const nodeDefaults = {
  sourcePosition: Position.Right,
  targetPosition: Position.Left,
  style: {
    borderRadius: "100%",
    backgroundColor: "#fff",
    width: 50,
    height: 50,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
}

const initialNodes: Node[] = [
  {
    id: "0",
    type: "input",
    data: { label: "Node" },
    position: { x: 0, y: 50 },
    ...nodeDefaults,
  },
]

const initialEdges: Edge[] = []
let id = 1
const getId = () => `${id++}`
const nodeOrigin = [0.5, 0]

const AddNodeOnEdgeDrop = () => {
  const reactFlowWrapper = useRef(null)

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const { screenToFlowPosition } = useReactFlow()
  const onConnect: OnConnect = useCallback(
    (params) =>
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            markerEnd: {
              type: MarkerType.ArrowClosed,
            },
          },
          eds
        )
      ),
    []
  )

  const onConnectEnd: OnConnectEnd = useCallback(
    (event, connectionState) => {
      // when a connection is dropped on the pane it's not valid
      if (!connectionState.isValid) {
        // we need to remove the wrapper bounds, in order to get the correct position
        const id = getId()
        const { clientX, clientY } =
          "changedTouches" in event ? event.changedTouches[0] : event
        const newNode = {
          id,
          position: screenToFlowPosition({
            x: clientX,
            y: clientY,
          }),
          data: { label: `Node ${id}` },
          origin: [0.5, 0.0],
          ...nodeDefaults,
        }

        setNodes((nds) => nds.concat(newNode))
        setEdges((eds) =>
          eds.concat({
            id,
            source: connectionState.fromNode.id,
            target: id,
            markerEnd: {
              type: MarkerType.ArrowClosed,
            },
          })
        )
      }
    },
    [screenToFlowPosition]
  )

  const [backgroundVariant, setBackgroundVariant] = useState(
    BackgroundVariant.Dots
  )

  return (
    <div className="flex h-full flex-col md:flex-row" ref={reactFlowWrapper}>
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onConnectEnd={onConnectEnd}
          fitView
          fitViewOptions={{ padding: 2 }}
          nodeOrigin={nodeOrigin}
        >
          <MiniMap nodeStrokeWidth={3} zoomable pannable />
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
          <Background variant={backgroundVariant} />
        </ReactFlow>
      </div>
      <Sidebar nodes={nodes} setNodes={setNodes} />
    </div>
  )
}

export default () => (
  <ReactFlowProvider>
    <AddNodeOnEdgeDrop />
  </ReactFlowProvider>
)
