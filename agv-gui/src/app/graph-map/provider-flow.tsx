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
import { useCallback, useEffect, useRef, useState } from "react"
import {
  createGraphEdge,
  createGraphNode,
  deleteGraphEdge,
  deleteGraphNode,
  fetchGraph,
  updateGraphNode,
  type GraphEdge,
  type GraphNode,
} from "@/lib/api"
import Sidebar from "./sidebar"

const MAP_ID = "map_1"

// Protected nodes that cannot be deleted
const PROTECTED_NODE_IDS = ["Node 1", "Node 2"]

// Helper function to convert backend GraphNode to ReactFlow Node
function graphNodeToReactFlowNode(graphNode: GraphNode): Node {
  return {
    id: graphNode.node_id,
    data: { label: graphNode.node_id, dbId: graphNode.id },
    position: { x: graphNode.x, y: graphNode.y },
    ...nodeDefaults,
  }
}

// Helper function to convert backend GraphEdge to ReactFlow Edge
function graphEdgeToReactFlowEdge(graphEdge: GraphEdge): Edge {
  return {
    id: `e${graphEdge.start_node.node_id}-${graphEdge.end_node.node_id}`,
    source: graphEdge.start_node.node_id,
    target: graphEdge.end_node.node_id,
    data: { dbId: graphEdge.id },
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
  }
}

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
    id: "Node 1",
    data: { label: `Node 1` },
    position: { x: 0, y: 0 },
    ...nodeDefaults,
  },
  {
    id: "Node 2",
    data: { label: `Node 2` },
    position: { x: 100, y: 0 },
    ...nodeDefaults,
  },
]

const initialEdges: Edge[] = [
  {
    id: "eNode 1-Node 2",
    source: "Node 1",
    target: "Node 2",
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
  },
]
const nodeOrigin = [0.5, 0]

// Helper function to renumber nodes to maintain consecutive IDs
function renumberNodes(
  currentNodes: Node[],
  currentEdges: Edge[]
): { nodes: Node[]; edges: Edge[] } {
  // Sort nodes by their current numeric ID to maintain order
  const sortedNodes = [...currentNodes].sort((a, b) => {
    const numA = parseInt(a.id.replace("Node ", ""))
    const numB = parseInt(b.id.replace("Node ", ""))
    return numA - numB
  })

  // Create mapping from old ID to new ID
  const idMapping: Record<string, string> = {}
  sortedNodes.forEach((node, index) => {
    const newId = `Node ${index + 1}`
    idMapping[node.id] = newId
  })

  // Renumber nodes
  const renumberedNodes = sortedNodes.map((node, index) => ({
    ...node,
    id: `Node ${index + 1}`,
    data: { ...node.data, label: `Node ${index + 1}` },
  }))

  // Update edges to use new node IDs
  const renumberedEdges = currentEdges.map((edge) => ({
    ...edge,
    id: `e${idMapping[edge.source]}-${idMapping[edge.target]}`,
    source: idMapping[edge.source],
    target: idMapping[edge.target],
  }))

  return { nodes: renumberedNodes, edges: renumberedEdges }
}

const AddNodeOnEdgeDrop = () => {
  const reactFlowWrapper = useRef(null)

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [originalNodes, setOriginalNodes] = useState<Node[]>([])
  const [originalEdges, setOriginalEdges] = useState<Edge[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { screenToFlowPosition } = useReactFlow()

  // Renumber nodes whenever they change (add/delete)
  useEffect(() => {
    if (!isLoading && nodes.length > 0) {
      const { nodes: renumberedNodes, edges: renumberedEdges } = renumberNodes(
        nodes,
        edges
      )
      // Only update if IDs actually changed
      const idsChanged = nodes.some(
        (node, idx) => node.id !== renumberedNodes[idx]?.id
      )
      if (idsChanged) {
        setNodes(renumberedNodes)
        setEdges(renumberedEdges)
      }
    }
  }, [nodes.length, isLoading])

  // Track changes whenever nodes or edges change
  useEffect(() => {
    if (!isLoading) {
      const nodesChanged =
        JSON.stringify(nodes) !== JSON.stringify(originalNodes)
      const edgesChanged =
        JSON.stringify(edges) !== JSON.stringify(originalEdges)
      setHasChanges(nodesChanged || edgesChanged)
    }
  }, [nodes, edges, originalNodes, originalEdges, isLoading])

  // Load graph data from backend on mount
  useEffect(() => {
    loadGraphFromBackend()
  }, [])

  const loadGraphFromBackend = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const graphData = await fetchGraph(MAP_ID)

      if (graphData.nodes.length > 0) {
        // Backend has data - load it
        const reactFlowNodes = graphData.nodes.map(graphNodeToReactFlowNode)
        const reactFlowEdges = graphData.edges.map(graphEdgeToReactFlowEdge)

        setNodes(reactFlowNodes)
        setEdges(reactFlowEdges)
        setOriginalNodes(reactFlowNodes)
        setOriginalEdges(reactFlowEdges)
      } else {
        // Backend is empty - show initial nodes but don't set as "original"
        // This way, they will be detected as new nodes that need to be saved
        setNodes(initialNodes)
        setEdges(initialEdges)
        setOriginalNodes([]) // Keep empty so initial nodes are detected as new
        setOriginalEdges([]) // Keep empty so initial edge is detected as new
      }
    } catch (err) {
      console.error("Failed to load graph:", err)
      setError("Failed to load graph from backend. Using default nodes.")
      // Use default nodes if loading fails, but mark them as needing to be saved
      setNodes(initialNodes)
      setEdges(initialEdges)
      setOriginalNodes([])
      setOriginalEdges([])
    } finally {
      setIsLoading(false)
    }
  }

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
        // Use a temporary ID - it will be renumbered automatically
        const tempId = `Node ${Date.now()}`
        const { clientX, clientY } =
          "changedTouches" in event ? event.changedTouches[0] : event
        const newNode = {
          id: tempId,
          position: screenToFlowPosition({
            x: clientX,
            y: clientY,
          }),
          data: { label: tempId },
          origin: [0.5, 0.0],
          ...nodeDefaults,
        }

        setNodes((nds) => nds.concat(newNode))
        setEdges((eds) =>
          eds.concat({
            id: `e${connectionState.fromNode.id}-${tempId}`,
            source: connectionState.fromNode.id,
            target: tempId,
            markerEnd: {
              type: MarkerType.ArrowClosed,
            },
          })
        )
      }
    },
    [screenToFlowPosition, setNodes, setEdges]
  )

  // Override node deletion to protect Node 1 and Node 2
  const customOnNodesChange = useCallback(
    (changes: any[]) => {
      const filteredChanges = changes.filter((change) => {
        if (change.type === "remove") {
          if (PROTECTED_NODE_IDS.includes(change.id)) {
            alert(`${change.id} cannot be deleted.`)
            return false
          }
        }
        return true
      })
      onNodesChange(filteredChanges)
    },
    [onNodesChange]
  )

  // Override edge deletion to protect the edge between Node 1 and Node 2
  const customOnEdgesChange = useCallback(
    (changes: any[]) => {
      const filteredChanges = changes.filter((change) => {
        if (change.type === "remove") {
          const edge = edges.find((e) => e.id === change.id)
          if (
            edge &&
            PROTECTED_NODE_IDS.includes(edge.source) &&
            PROTECTED_NODE_IDS.includes(edge.target)
          ) {
            alert("The edge between Node 1 and Node 2 cannot be deleted.")
            return false
          }
        }
        return true
      })
      onEdgesChange(filteredChanges)
    },
    [onEdgesChange, edges]
  )

  const handleSave = async () => {
    setIsSaving(true)
    setError(null)

    try {
      // Find nodes to create, update, and delete
      const originalNodeIds = new Set(originalNodes.map((n) => n.id))
      const currentNodeIds = new Set(nodes.map((n) => n.id))

      const nodesToCreate = nodes.filter((n) => !originalNodeIds.has(n.id))
      const nodesToUpdate = nodes.filter((n) => {
        if (!originalNodeIds.has(n.id)) return false
        const original = originalNodes.find((on) => on.id === n.id)
        return JSON.stringify(n) !== JSON.stringify(original)
      })
      const nodesToDelete = originalNodes.filter(
        (n) => !currentNodeIds.has(n.id)
      )

      // Find edges to create and delete
      const originalEdgeIds = new Set(originalEdges.map((e) => e.id))
      const currentEdgeIds = new Set(edges.map((e) => e.id))

      const edgesToCreate = edges.filter((e) => !originalEdgeIds.has(e.id))
      const edgesToDelete = originalEdges.filter(
        (e) => !currentEdgeIds.has(e.id)
      )

      // Execute operations
      // 1. Create new nodes
      for (const node of nodesToCreate) {
        await createGraphNode({
          node_id: node.id,
          map_id: MAP_ID,
          x: node.position.x,
          y: node.position.y,
          theta: 0.0,
          description: "",
        })
      }

      // 2. Update existing nodes
      for (const node of nodesToUpdate) {
        const dbId = node.data?.dbId
        if (dbId) {
          await updateGraphNode(dbId, {
            x: node.position.x,
            y: node.position.y,
          })
        }
      }

      // 3. Delete edges first (before deleting nodes)
      for (const edge of edgesToDelete) {
        const dbId = edge.data?.dbId
        if (dbId) {
          await deleteGraphEdge(dbId)
        }
      }

      // 4. Delete nodes
      for (const node of nodesToDelete) {
        const dbId = node.data?.dbId
        if (dbId) {
          await deleteGraphNode(dbId)
        }
      }

      // 5. Create new edges
      for (const edge of edgesToCreate) {
        await createGraphEdge({
          start_node_id: edge.source,
          end_node_id: edge.target,
          map_id: MAP_ID,
          max_velocity: 1.0,
          is_directed: true,
        })
      }

      // Reload graph from backend to get the latest state
      await loadGraphFromBackend()

      alert("Graph saved successfully!")
    } catch (err) {
      console.error("Failed to save graph:", err)
      setError(
        err instanceof Error ? err.message : "Failed to save graph changes"
      )
      alert("Failed to save graph. Check console for details.")
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    if (
      hasChanges &&
      !confirm("Are you sure you want to discard all changes?")
    ) {
      return
    }
    setNodes(originalNodes)
    setEdges(originalEdges)
    setHasChanges(false)
  }

  const [backgroundVariant, setBackgroundVariant] = useState(
    BackgroundVariant.Dots
  )

  return (
    <div className="flex h-full flex-col md:flex-row" ref={reactFlowWrapper}>
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={customOnNodesChange}
          onEdgesChange={customOnEdgesChange}
          onConnect={onConnect}
          onConnectEnd={onConnectEnd}
          fitView
          fitViewOptions={{ padding: 2 }}
          nodeOrigin={nodeOrigin}
        >
          <MiniMap nodeStrokeWidth={3} zoomable pannable />
          <Panel position="top-left">
            <div className="space-y-2 rounded-lg border bg-white p-4 shadow-md">
              <div className="flex gap-2">
                <Button
                  onClick={handleSave}
                  disabled={!hasChanges || isSaving || isLoading}
                  variant={hasChanges ? "default" : "outline"}
                  size="sm"
                >
                  {isSaving ? "Saving..." : "Save"}
                </Button>
                <Button
                  onClick={handleCancel}
                  disabled={!hasChanges || isSaving || isLoading}
                  variant="outline"
                  size="sm"
                >
                  Cancel
                </Button>
              </div>
              {isLoading && (
                <div className="text-xs text-gray-600">Loading graph...</div>
              )}
              {error && (
                <div className="text-xs text-red-600">Error: {error}</div>
              )}
              {hasChanges && !isLoading && (
                <div className="text-xs text-orange-600">Unsaved changes</div>
              )}
            </div>
          </Panel>
          <Panel position="top-right">
            <div className="rounded-lg border bg-white p-4 shadow-md">
              <div>Change background grid:</div>
              <div className="flex gap-2">
                {Object.values(BackgroundVariant).map((v) => (
                  <Button key={v} onClick={() => setBackgroundVariant(v)}>
                    {v}
                  </Button>
                ))}
              </div>
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
