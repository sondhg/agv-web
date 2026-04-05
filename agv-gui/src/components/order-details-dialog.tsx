"use client"

import { ArrowRight, Package, Calendar, Hash, CheckCircle2 } from "lucide-react"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import type { Order } from "@/lib/api"

interface OrderDetailsDialogProps {
  order: Order | null
  open: boolean
  onOpenChange: (open: boolean) => void
  agvSerialNumber: string
}

export function OrderDetailsDialog({
  order,
  open,
  onOpenChange,
  agvSerialNumber,
}: OrderDetailsDialogProps) {
  if (!order) return null

  function getStatusColor(status: string): string {
    switch (status) {
      case "CREATED":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
      case "SENT":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200"
      case "ACTIVE":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
      case "QUEUED":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
      case "COMPLETED":
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200"
      case "REJECTED":
      case "FAILED":
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
      case "CANCELLED":
        return "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200"
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200"
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3/4">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Order Details: {order.order_id}
          </DialogTitle>
          <DialogDescription>
            Complete information about this transport order
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Basic Info */}
          <div className="rounded-lg border bg-muted/50 p-4">
            <h3 className="mb-3 font-semibold">Basic Information</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Order ID:</span>
                <p className="font-mono font-medium">{order.order_id}</p>
              </div>
              <div>
                <span className="text-muted-foreground">AGV:</span>
                <p className="font-medium">{agvSerialNumber}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Status:</span>
                <p>
                  <span
                    className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${getStatusColor(order.status)}`}
                  >
                    {order.status}
                  </span>
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Header ID:</span>
                <p className="font-mono">{order.header_id}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Order Update ID:</span>
                <p className="font-mono">{order.order_update_id}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Zone Set ID:</span>
                <p className="font-mono">{order.zone_set_id}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Created:</span>
                <p className="text-xs">
                  {new Date(order.created_at).toLocaleString()}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Last Updated:</span>
                <p className="text-xs">
                  {new Date(order.updated_at).toLocaleString()}
                </p>
              </div>
            </div>

            {order.rejection_reason && (
              <div className="mt-3 rounded border-l-4 border-red-500 bg-red-50 p-3 dark:bg-red-950">
                <span className="text-xs font-semibold text-red-800 dark:text-red-200">
                  Rejection Reason:
                </span>
                <p className="text-sm text-red-700 dark:text-red-300">
                  {order.rejection_reason}
                </p>
              </div>
            )}
          </div>

          {/* Path Visualization */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="mb-3 font-semibold">Execution Path</h3>
            <div className="flex flex-wrap items-center gap-2">
              {order.nodes.map((node, index) => (
                <div key={index} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <div className="flex items-center gap-1">
                      {index === order.nodes.length - 1 && (
                        <CheckCircle2 className="h-3 w-3 text-green-600" />
                      )}
                      <span className="rounded bg-blue-100 px-3 py-1.5 font-mono text-sm font-medium text-blue-900 dark:bg-blue-950 dark:text-blue-100">
                        {node.nodeId}
                      </span>
                    </div>
                    <span className="mt-1 text-xs text-muted-foreground">
                      seq: {node.sequenceId}
                    </span>
                  </div>
                  {index < order.nodes.length - 1 && (
                    <ArrowRight className="mx-2 h-4 w-4 text-muted-foreground" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* VDA5050 Nodes */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="mb-3 flex items-center gap-2 font-semibold">
              <Hash className="h-4 w-4" />
              VDA5050 Nodes ({order.nodes.length})
            </h3>
            <div className="space-y-2">
              {order.nodes.map((node, index) => (
                <div
                  key={index}
                  className="rounded border bg-muted/30 p-3 text-xs"
                >
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="font-semibold">Node ID:</span>{" "}
                      <span className="font-mono">{node.nodeId}</span>
                    </div>
                    <div>
                      <span className="font-semibold">Sequence ID:</span>{" "}
                      {node.sequenceId}
                    </div>
                    <div>
                      <span className="font-semibold">Position:</span> (
                      {node.nodePosition.x}, {node.nodePosition.y})
                    </div>
                    <div>
                      <span className="font-semibold">Map ID:</span>{" "}
                      {node.nodePosition.mapId}
                    </div>
                    <div>
                      <span className="font-semibold">Released:</span>{" "}
                      {node.released ? "✓ Yes" : "✗ No"}
                    </div>
                    <div>
                      <span className="font-semibold">Actions:</span>{" "}
                      {node.actions.length} action(s)
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* VDA5050 Edges */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="mb-3 flex items-center gap-2 font-semibold">
              <ArrowRight className="h-4 w-4" />
              VDA5050 Edges ({order.edges.length})
            </h3>
            <div className="space-y-2">
              {order.edges.map((edge, index) => (
                <div
                  key={index}
                  className="rounded border bg-muted/30 p-3 text-xs"
                >
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="font-semibold">Edge ID:</span>{" "}
                      <span className="font-mono">{edge.edgeId}</span>
                    </div>
                    <div>
                      <span className="font-semibold">Sequence ID:</span>{" "}
                      {edge.sequenceId}
                    </div>
                    <div>
                      <span className="font-semibold">Path:</span>{" "}
                      <span className="font-mono">
                        {edge.startNodeId} → {edge.endNodeId}
                      </span>
                    </div>
                    <div>
                      <span className="font-semibold">Max Speed:</span>{" "}
                      {edge.maxSpeed} m/s
                    </div>
                    <div>
                      <span className="font-semibold">Released:</span>{" "}
                      {edge.released ? "✓ Yes" : "✗ No"}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Timestamps */}
          <div className="rounded-lg border bg-muted/50 p-4">
            <h3 className="mb-3 flex items-center gap-2 font-semibold">
              <Calendar className="h-4 w-4" />
              Timestamps
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Order Timestamp:</span>
                <span className="font-mono text-xs">
                  {new Date(order.timestamp).toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created At:</span>
                <span className="font-mono text-xs">
                  {new Date(order.created_at).toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Updated At:</span>
                <span className="font-mono text-xs">
                  {new Date(order.updated_at).toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
