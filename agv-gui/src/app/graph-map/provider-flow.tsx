import { Button } from "@/components/ui/button"
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
import Sidebar from "./sidebar"
import { toast } from "sonner"

const MAP_ID = "map_1"

import { NodeTable } from "./node-table"
import { getNodeColor } from "./utils"

// Helper function to convert backend GraphNode to ReactFlow Node
function graphNodeToReactFlowNode(graphNode: GraphNode): Node {
  return {
    id: graphNode.node_id,
    data: {
      label: graphNode.node_id,
      dbId: graphNode.id,
      node_type: graphNode.node_type,
    },
    position: { x: graphNode.x, y: graphNode.y },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    style: {
      backgroundColor: getNodeColor(graphNode.node_type),
      width: 50,
      height: 50,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      border: "1px solid #222",
      borderRadius: "8px",
    },
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
    // borderRadius: "100%",
    backgroundColor: getNodeColor("DEFAULT"),
    width: 50,
    height: 50,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    border: "1px solid #222",
    borderRadius: "8px",
  },
}

const nodeOrigin: [number, number] = [0.5, 0]

// Helper function to generate a safe, unique ID for NEW nodes
function generateNewNodeId(currentNodes: Node[]): string {
  let maxNumber = 0

  // Look through all existing nodes to find the highest "Node X" number
  currentNodes.forEach((node) => {
    const match = node.id.match(/^Node (\d+)$/)
    if (match) {
      const num = parseInt(match[1], 10)
      if (num > maxNumber) {
        maxNumber = num
      }
    }
  })

  return `Node ${maxNumber + 1}`
}

import { createPortal } from "react-dom"

const AddNodeOnEdgeDrop = () => {
  const reactFlowWrapper = useRef(null)

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [originalNodes, setOriginalNodes] = useState<Node[]>([])
  const [originalEdges, setOriginalEdges] = useState<Edge[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { screenToFlowPosition } = useReactFlow()

  // Track changes whenever nodes or edges change
  useEffect(() => {
    if (!isLoading) {
      const nodesChanged =
        JSON.stringify(nodes) !== JSON.stringify(originalNodes)
      const edgesChanged =
        JSON.stringify(edges) !== JSON.stringify(originalEdges)
      setHasChanges(nodesChanged || edgesChanged)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, originalNodes, originalEdges, isLoading])

  // Load graph data from backend on mount
  useEffect(() => {
    loadGraphFromBackend()
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        // Backend is empty
        setNodes([])
        setEdges([])
        setOriginalNodes([])
        setOriginalEdges([])
      }
    } catch (err) {
      console.error("Failed to load graph:", err)
      setError("Failed to load graph from backend.")
      setNodes([])
      setEdges([])
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
    [setEdges]
  )

  const onConnectEnd: OnConnectEnd = useCallback(
    (event, connectionState) => {
      // when a connection is dropped on the pane it's not valid
      if (!connectionState.isValid && connectionState.fromNode) {
        // we need to remove the wrapper bounds, in order to get the correct position
        const tempId = generateNewNodeId(nodes)
        const fromNodeId = connectionState.fromNode.id
        const { clientX, clientY } =
          "changedTouches" in event ? event.changedTouches[0] : event
        const newNode: Node = {
          id: tempId,
          position: screenToFlowPosition({
            x: clientX,
            y: clientY,
          }),
          data: { label: tempId, node_type: "DEFAULT" },
          origin: [0.5, 0.0] as [number, number],
          ...nodeDefaults,
        }

        setNodes((nds) => nds.concat(newNode))
        setEdges((eds) =>
          eds.concat({
            id: `e${fromNodeId}-${tempId}`,
            source: fromNodeId,
            target: tempId,
            markerEnd: {
              type: MarkerType.ArrowClosed,
            },
          })
        )
      }
    },
    [screenToFlowPosition, setNodes, setEdges, nodes]
  )

  const handleAddNode = useCallback(() => {
    const tempId = generateNewNodeId(nodes)
    const position = screenToFlowPosition({
      x: window.innerWidth / 2,
      y: window.innerHeight / 2,
    })
    const newNode: Node = {
      id: tempId,
      position,
      data: { label: tempId, node_type: "DEFAULT" },
      origin: [0.5, 0.0] as [number, number],
      ...nodeDefaults,
    }
    setNodes((nds) => nds.concat(newNode))
  }, [screenToFlowPosition, setNodes, nodes])

  const onPaneDoubleClick = useCallback(
    (event: React.MouseEvent) => {
      const tempId = generateNewNodeId(nodes)
      const newNode: Node = {
        id: tempId,
        position: screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        }),
        data: { label: tempId, node_type: "DEFAULT" },
        origin: [0.5, 0.0] as [number, number],
        ...nodeDefaults,
      }
      setNodes((nds) => nds.concat(newNode))
    },
    [screenToFlowPosition, setNodes, nodes]
  )

  const handleSave = async () => {
    setIsSaving(true)
    setError(null)

    try {
      // Create a map of dbId to nodes for efficient lookup
      const originalNodesByDbId = new Map<number, Node>(
        originalNodes
          .filter(
            (n): n is Node & { data: { dbId: number } } =>
              n.data !== undefined &&
              "dbId" in n.data &&
              typeof n.data.dbId === "number"
          )
          .map((n) => [n.data.dbId, n])
      )
      const currentNodesByDbId = new Map<number, Node>(
        nodes
          .filter(
            (n): n is Node & { data: { dbId: number } } =>
              n.data !== undefined &&
              "dbId" in n.data &&
              typeof n.data.dbId === "number"
          )
          .map((n) => [n.data.dbId, n])
      )

      // Find nodes to create (no dbId means new node)
      const nodesToCreate: Node[] = nodes.filter(
        (n) => !n.data || !("dbId" in n.data)
      )

      // Find nodes to update (has dbId and exists in both original and current)
      const nodesToUpdate = nodes.filter(
        (n): n is Node & { data: { dbId: number; node_type?: string } } => {
          if (!n.data || !("dbId" in n.data) || typeof n.data.dbId !== "number")
            return false
          const original = originalNodesByDbId.get(n.data.dbId)
          if (!original) return false
          // Check if position or type changed
          return (
            n.position.x !== original.position.x ||
            n.position.y !== original.position.y ||
            n.data.node_type !== original.data?.node_type
          )
        }
      )

      // Find nodes to delete (has dbId in original but not in current)
      const nodesToDelete = originalNodes.filter(
        (n): n is Node & { data: { dbId: number } } =>
          n.data !== undefined &&
          "dbId" in n.data &&
          typeof n.data.dbId === "number" &&
          !currentNodesByDbId.has(n.data.dbId)
      )

      // For edges, we need to track by dbId too
      const currentEdgesByDbId = new Map<number, Edge>(
        edges
          .filter(
            (e): e is Edge & { data: { dbId: number } } =>
              e.data !== undefined &&
              "dbId" in e.data &&
              typeof e.data.dbId === "number"
          )
          .map((e) => [e.data.dbId, e])
      )

      // Find edges to create (no dbId means new edge)
      const edgesToCreate: Edge[] = edges.filter(
        (e) => !e.data || !("dbId" in e.data)
      )

      // Find edges to delete (has dbId in original but not in current)
      const edgesToDelete = originalEdges.filter(
        (e): e is Edge & { data: { dbId: number } } =>
          e.data !== undefined &&
          "dbId" in e.data &&
          typeof e.data.dbId === "number" &&
          !currentEdgesByDbId.has(e.data.dbId)
      )

      // Execute operations in the correct order to avoid conflicts
      // 1. Delete edges first (before deleting nodes they reference)
      for (const edge of edgesToDelete) {
        const dbId = edge.data.dbId
        await deleteGraphEdge(dbId)
      }

      // 2. Delete nodes (frees up node_id names for renumbering)
      for (const node of nodesToDelete) {
        const dbId = node.data.dbId
        await deleteGraphNode(dbId)
      }

      // 3. Update existing nodes (position changes)
      for (const node of nodesToUpdate) {
        const dbId = node.data.dbId
        await updateGraphNode(dbId, {
          x: node.position.x,
          y: node.position.y,
          node_type: (node.data.node_type as string) || "DEFAULT",
        })
      }

      // 4. Update node_id for nodes that were renumbered
      // This must happen AFTER deletions to avoid uniqueness conflicts
      for (const node of nodes) {
        if (
          !node.data ||
          !("dbId" in node.data) ||
          typeof node.data.dbId !== "number"
        )
          continue // Skip new nodes
        const original = originalNodesByDbId.get(node.data.dbId)
        if (!original) continue
        // If ID changed (due to renumbering)
        if (node.id !== original.id) {
          await updateGraphNode(node.data.dbId, {
            node_id: node.id,
          })
        }
      }

      // 5. Create new nodes
      for (const node of nodesToCreate) {
        await createGraphNode({
          node_id: node.id,
          map_id: MAP_ID,
          x: node.position.x,
          y: node.position.y,
          theta: 0.0,
          description: "",
          node_type: (node.data?.node_type as string) || "DEFAULT",
        })
      }

      // 6. Create new edges
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

      toast.success("Graph saved successfully!", { position: "top-right" })
    } catch (err) {
      console.error("Failed to save graph:", err)
      setError(
        err instanceof Error ? err.message : "Failed to save graph changes"
      )
      toast.error("Failed to save graph. Check console for details.", {
        position: "top-right",
      })
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

  const updateNodeType = useCallback(
    (
      nodeId: string,
      nodeType: "DEFAULT" | "PICKUP" | "DELIVERY" | "CHARGING"
    ) => {
      setNodes((nds) => {
        const target = nds.find((n) => n.id === nodeId)
        const dbId = target?.data?.dbId

        // if these lines are uncommented, the node type will be updated as soon as user choose an option in the dropdown. no need to click 'Save' button in the map
        // -------
        if (dbId && typeof dbId === "number") {
          updateGraphNode(dbId, { node_type: nodeType }).catch((err) => {
            console.error("Failed to save node type:", err)
            toast.error("Failed to save node type")
          })
        }
        // -------

        return nds.map((n) => {
          if (n.id === nodeId) {
            return {
              ...n,
              data: { ...n.data, node_type: nodeType },
              style: {
                ...n.style,
                backgroundColor: getNodeColor(nodeType),
              },
            }
          }
          return n
        })
      })
    },
    [setNodes]
  )

  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  return (
    <>
      <div className="flex h-full flex-col md:flex-row" ref={reactFlowWrapper}>
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onConnectEnd={onConnectEnd}
            onPaneDoubleClick={onPaneDoubleClick}
            fitView
            fitViewOptions={{ padding: 2 }}
            nodeOrigin={nodeOrigin}
          >
            <MiniMap nodeStrokeWidth={3} zoomable pannable />
            <Panel position="top-left">
              <div className="space-y-2 rounded-lg border p-4 shadow-md">
                <div className="flex gap-2">
                  <Button
                    onClick={handleAddNode}
                    disabled={isLoading}
                    variant="secondary"
                    size="sm"
                  >
                    Add Node
                  </Button>
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
                    variant="destructive"
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
              <div className="rounded-lg border p-4 shadow-md">
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
        {mounted && document.getElementById("node-table-portal-target")
          ? createPortal(
              <div>
                <h2 className="mb-4 text-2xl font-semibold">Node Management</h2>
                <NodeTable nodes={nodes} updateNodeType={updateNodeType} />
              </div>,
              document.getElementById("node-table-portal-target")!
            )
          : null}
      </div>
    </>
  )
}

export function ProviderFlow() {
  return (
    <ReactFlowProvider>
      <AddNodeOnEdgeDrop />
    </ReactFlowProvider>
  )
}
