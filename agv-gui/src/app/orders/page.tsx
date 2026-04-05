"use client"

import { useState, useEffect } from "react"
import { Loader2, RefreshCw, Package, CheckCircle2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { OrderDetailsDialog } from "@/components/order-details-dialog"
import { fetchOrders, fetchAgvs } from "@/lib/api"
import type { Order, Agv } from "@/lib/api"

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [agvs, setAgvs] = useState<Agv[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  // Auto-refresh every 3 seconds
  useEffect(() => {
    loadData()
    const interval = setInterval(() => {
      loadData()
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  async function loadData() {
    setError(null)
    try {
      const [ordersData, agvsData] = await Promise.all([
        fetchOrders(),
        fetchAgvs(),
      ])
      setOrders(ordersData)
      setAgvs(agvsData)
      setLastRefresh(new Date())
    } catch (err) {
      console.error("Failed to load data:", err)
      setError(err instanceof Error ? err.message : "Failed to load data")
    } finally {
      setLoading(false)
    }
  }

  function getAgvSerialNumber(agvId: number): string {
    const agv = agvs.find((a) => a.id === agvId)
    return agv?.serial_number || `AGV #${agvId}`
  }

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

  function getPath(order: Order): string {
    return order.nodes.map((n) => n.nodeId).join(" → ")
  }

  function handleOrderClick(order: Order) {
    setSelectedOrder(order)
    setDialogOpen(true)
  }

  return (
    <div className="container mx-auto space-y-6 py-10">
      {/* Order Details Dialog */}
      <OrderDetailsDialog
        order={selectedOrder}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        agvSerialNumber={
          selectedOrder ? getAgvSerialNumber(selectedOrder.agv) : ""
        }
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Order Tracking</h1>
          <p className="text-muted-foreground">
            Monitor all transport orders and their execution status
          </p>
        </div>
        <Button onClick={loadData} variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Auto-refresh indicator */}
      <div className="text-xs text-muted-foreground">
        Last updated: {lastRefresh.toLocaleTimeString()} • Auto-refreshing every
        3 seconds
      </div>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error Loading Orders</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Summary Stats */}
      {!loading && !error && orders.length > 0 && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-lg border bg-card p-4">
            <div className="text-2xl font-bold">{orders.length}</div>
            <div className="text-xs text-muted-foreground">Total Orders</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="text-2xl font-bold">
              {orders.filter((o) => o.status === "ACTIVE").length}
            </div>
            <div className="text-xs text-muted-foreground">Active</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="text-2xl font-bold">
              {orders.filter((o) => o.status === "COMPLETED").length}
            </div>
            <div className="text-xs text-muted-foreground">Completed</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="text-2xl font-bold">
              {
                orders.filter((o) =>
                  ["REJECTED", "FAILED", "CANCELLED"].includes(o.status)
                ).length
              }
            </div>
            <div className="text-xs text-muted-foreground">Failed</div>
          </div>
        </div>
      )}
      {/* Orders Table */}
      {!loading && !error && (
        <div className="rounded-lg border bg-card">
          {orders.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Package className="mb-4 h-12 w-12 text-muted-foreground" />
              <h3 className="text-lg font-semibold">No Orders Yet</h3>
              <p className="text-sm text-muted-foreground">
                Create a transport task to see orders here
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium tracking-wider uppercase">
                      Order ID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium tracking-wider uppercase">
                      AGV
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium tracking-wider uppercase">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium tracking-wider uppercase">
                      Path
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium tracking-wider uppercase">
                      Created
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium tracking-wider uppercase">
                      Updated
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {orders.map((order) => (
                    <tr
                      key={order.id}
                      onClick={() => handleOrderClick(order)}
                      className="cursor-pointer transition-colors hover:bg-muted/50"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center space-x-2">
                          {order.status === "COMPLETED" && (
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                          )}
                          <span className="font-mono text-sm">
                            {order.order_id}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-medium">
                          {getAgvSerialNumber(order.agv)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${getStatusColor(order.status)}`}
                        >
                          {order.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-mono text-sm">
                          {getPath(order)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {new Date(order.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {new Date(order.updated_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

    </div>
  )
}
