"use client"

import { useState, useEffect } from "react"
import { Loader2, CheckCircle2, XCircle, ArrowRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { createTask, fetchGraphNodes } from "@/lib/api"
import type { TaskResponse, GraphNode } from "@/lib/api"

export default function CreateTaskPage() {
  // Form state
  const [pickupNodeId, setPickupNodeId] = useState<string>("")
  const [deliveryNodeId, setDeliveryNodeId] = useState<string>("")

  // Available nodes
  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [nodesLoading, setNodesLoading] = useState(true)
  const [nodesError, setNodesError] = useState<string | null>(null)

  // Task creation state
  const [isCreating, setIsCreating] = useState(false)
  const [result, setResult] = useState<TaskResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Load nodes on mount
  useEffect(() => {
    loadNodes()
  }, [])

  async function loadNodes() {
    setNodesLoading(true)
    setNodesError(null)
    try {
      const data = await fetchGraphNodes()
      console.log("Loaded nodes:", data)
      setNodes(data)
    } catch (err) {
      console.error("Failed to load nodes:", err)
      setNodesError(
        err instanceof Error ? err.message : "Failed to load graph nodes"
      )
    } finally {
      setNodesLoading(false)
    }
  }

  async function handleCreateTask() {
    // Validation
    if (!pickupNodeId) {
      setError("Please select a pickup node")
      return
    }
    if (!deliveryNodeId) {
      setError("Please select a delivery node")
      return
    }
    if (pickupNodeId === deliveryNodeId) {
      setError("Pickup and delivery nodes must be different")
      return
    }

    // Clear previous results
    setError(null)
    setResult(null)
    setIsCreating(true)

    try {
      const taskResult = await createTask({
        pickup_node_id: pickupNodeId,
        delivery_node_id: deliveryNodeId,
      })

      console.log("Task result:", taskResult)
      setResult(taskResult)
    } catch (err) {
      console.error("Task creation failed:", err)
      setError(err instanceof Error ? err.message : "Failed to create task")
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <div className="container mx-auto space-y-6 py-10">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Create Transport Task
        </h1>
        <p className="text-muted-foreground">
          Assign a pickup and delivery task to the AGV fleet. The system will
          automatically select the best AGV using the auction-based bidding
          algorithm.
        </p>
      </div>

      {/* Debug Info */}
      {nodes.length > 0 && (
        <div className="rounded border bg-muted p-4 text-sm">
          <p>
            <strong>Nodes loaded:</strong> {nodes.length} nodes
          </p>
          <p className="text-xs text-muted-foreground">
            {nodes.map((n) => n.node_id).join(", ")}
          </p>
        </div>
      )}

      {/* Nodes Loading Error */}
      {nodesError && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Error Loading Nodes</AlertTitle>
          <AlertDescription>{nodesError}</AlertDescription>
        </Alert>
      )}

      {/* Task Creation Form */}
      <div className="rounded-lg border bg-card p-6">
        <div className="space-y-6">
          {/* Pickup Node Selector - Using native HTML select temporarily */}
          <div className="space-y-2">
            <Label htmlFor="pickup-node">Pickup Node</Label>
            <select
              id="pickup-node"
              value={pickupNodeId}
              onChange={(e) => setPickupNodeId(e.target.value)}
              disabled={nodesLoading || !!nodesError}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="">Select pickup location</option>
              {nodes.map((node) => (
                <option key={node.id} value={node.node_id}>
                  {node.node_id}
                  {node.description && ` - ${node.description}`}
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">
              The location where the AGV will pick up the load
            </p>
          </div>

          {/* Delivery Node Selector - Using native HTML select temporarily */}
          <div className="space-y-2">
            <Label htmlFor="delivery-node">Delivery Node</Label>
            <select
              id="delivery-node"
              value={deliveryNodeId}
              onChange={(e) => setDeliveryNodeId(e.target.value)}
              disabled={nodesLoading || !!nodesError}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="">Select delivery location</option>
              {nodes.map((node) => (
                <option key={node.id} value={node.node_id}>
                  {node.node_id}
                  {node.description && ` - ${node.description}`}
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">
              The destination where the AGV will deliver the load
            </p>
          </div>

          {/* Create Task Button */}
          <Button
            onClick={handleCreateTask}
            disabled={
              isCreating ||
              nodesLoading ||
              !!nodesError ||
              !pickupNodeId ||
              !deliveryNodeId
            }
            className="w-full"
            size="lg"
          >
            {isCreating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running Auction...
              </>
            ) : (
              "Create Transport Task"
            )}
          </Button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Task Creation Failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Success Result */}
      {result && result.success && (
        <Alert className="border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950">
          <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
          <AlertTitle className="text-green-900 dark:text-green-100">
            Task Assigned Successfully
          </AlertTitle>
          <AlertDescription className="space-y-3 text-green-800 dark:text-green-200">
            <p className="font-medium">{result.message}</p>

            <div className="space-y-2 rounded-md border border-green-300 bg-white p-4 dark:border-green-800 dark:bg-green-950">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="font-semibold">Winner AGV:</span>
                </div>
                <div className="font-mono">{result.winner_agv}</div>

                <div>
                  <span className="font-semibold">Order ID:</span>
                </div>
                <div className="font-mono">{result.order_id}</div>

                <div>
                  <span className="font-semibold">Status:</span>
                </div>
                <div>
                  <span className="rounded bg-blue-100 px-2 py-1 text-xs font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                    {result.status}
                  </span>
                </div>

                <div>
                  <span className="font-semibold">Pickup:</span>
                </div>
                <div className="font-mono">{result.pickup_node}</div>

                <div>
                  <span className="font-semibold">Delivery:</span>
                </div>
                <div className="font-mono">{result.delivery_node}</div>
              </div>

              {/* Path Display */}
              {result.path && result.path.length > 0 && (
                <div className="mt-4 space-y-2 border-t border-green-200 pt-4 dark:border-green-800">
                  <div className="font-semibold">Calculated Path:</div>
                  <div className="flex flex-wrap items-center gap-2">
                    {result.path.map((nodeId, index) => (
                      <div key={index} className="flex items-center">
                        <span className="rounded bg-blue-50 px-2 py-1 font-mono text-sm text-blue-900 dark:bg-blue-950 dark:text-blue-100">
                          {nodeId}
                        </span>
                        {index < result.path.length - 1 && (
                          <ArrowRight className="mx-1 h-4 w-4 text-green-600" />
                        )}
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Total waypoints: {result.path.length}
                  </p>
                </div>
              )}
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Auction Failed */}
      {result && !result.success && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Auction Failed</AlertTitle>
          <AlertDescription>
            {result.error || "No suitable AGV found for this task"}
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
