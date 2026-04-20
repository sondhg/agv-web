"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { Loader2, RefreshCw, Car } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { AgvDetailsModal } from "@/components/agv-details-modal"

import { fetchAgvs, fetchAgvStates } from "@/lib/api"
import type { Agv } from "@/types/agv"
import type { AGVState } from "@/lib/api"

export default function FleetDashboardPage() {
  const [agvs, setAgvs] = useState<Agv[]>([])
  const [agvStates, setAgvStates] = useState<Record<string, AGVState | null>>(
    {}
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())

  const [selectedAgv, setSelectedAgv] = useState<Agv | null>(null)
  const [detailsModalOpen, setDetailsModalOpen] = useState(false)

  const isPollingRef = React.useRef(false)

  // Auto-refresh every 3 seconds, wait for previous request to finish
  useEffect(() => {
    let timeoutId: NodeJS.Timeout
    let mounted = true

    const pollData = async () => {
      if (!mounted) return
      if (isPollingRef.current) {
        timeoutId = setTimeout(pollData, 3000)
        return
      }

      isPollingRef.current = true
      try {
        await loadData(false)
      } finally {
        isPollingRef.current = false
        if (mounted) {
          timeoutId = setTimeout(pollData, 3000)
        }
      }
    }

    // Initial load
    loadData(true).then(() => {
      if (mounted) {
        timeoutId = setTimeout(pollData, 3000)
      }
    })

    return () => {
      mounted = false
      clearTimeout(timeoutId)
    }
  }, [])

  async function loadData(showLoading = true) {
    if (showLoading) setLoading(true)
    setError(null)

    try {
      // 1. Fetch all AGVs
      const agvsData = await fetchAgvs()
      setAgvs(agvsData)

      // 2. Fetch latest state for each AGV
      const statesMap: Record<string, AGVState | null> = {}

      await Promise.all(
        agvsData.map(async (agv) => {
          try {
            const states = await fetchAgvStates(agv.serial_number)
            statesMap[agv.serial_number] = states.length > 0 ? states[0] : null
          } catch (e) {
            console.warn(
              `Failed to fetch state for AGV ${agv.serial_number}`,
              e
            )
            statesMap[agv.serial_number] = null
          }
        })
      )

      setAgvStates(statesMap)
      setLastRefresh(new Date())
    } catch (err) {
      console.error("Failed to load fleet data:", err)
      setError(err instanceof Error ? err.message : "Failed to load fleet data")
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  function handleAgvClick(agv: Agv) {
    setSelectedAgv(agv)
    setDetailsModalOpen(true)
  }

  // Calculate some overview stats
  const onlineAgvsCount = agvs.filter((a) => a.is_online).length
  const drivingAgvsCount = Object.values(agvStates).filter(
    (s) => s?.driving
  ).length
  const pausedAgvsCount = Object.values(agvStates).filter(
    (s) => s?.paused
  ).length

  return (
    <div className="container mx-auto space-y-6 py-10">
      {/* AGV Details Modal */}
      <AgvDetailsModal
        agv={selectedAgv}
        state={
          selectedAgv ? agvStates[selectedAgv.serial_number] || null : null
        }
        open={detailsModalOpen}
        onOpenChange={setDetailsModalOpen}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Fleet Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor AGV fleet status in real-time
          </p>
        </div>
        <Button onClick={() => loadData(true)} variant="outline" size="sm">
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
          <AlertTitle>Error Loading Fleet Data</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {loading && !error && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {!loading && !error && agvs.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-lg border bg-card py-12 text-center">
          <Car className="mb-4 h-12 w-12 text-muted-foreground" />
          <h3 className="text-lg font-semibold">No AGVs Registered</h3>
          <p className="text-sm text-muted-foreground">
            Register AGVs to monitor them here.
          </p>
        </div>
      )}

      {/* Overview Stats */}
      {!loading && !error && agvs.length > 0 && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-lg border bg-card p-4">
            <div className="text-2xl font-bold">{agvs.length}</div>
            <div className="text-xs text-muted-foreground">Total AGVs</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="text-2xl font-bold text-green-600 dark:text-green-500">
              {onlineAgvsCount}
            </div>
            <div className="text-xs text-muted-foreground">Online</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-500">
              {drivingAgvsCount}
            </div>
            <div className="text-xs text-muted-foreground">Driving</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-500">
              {pausedAgvsCount}
            </div>
            <div className="text-xs text-muted-foreground">Paused</div>
          </div>
        </div>
      )}

      {/* Fleet Grid */}
      {!loading && !error && agvs.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {agvs.map((agv) => {
            const state = agvStates[agv.serial_number]
            const charge = state?.battery_state?.batteryCharge ?? 0

            // Time since last seen
            const timeSinceLastSeen = agv.last_seen
              ? Math.floor(
                  (new Date().getTime() - new Date(agv.last_seen).getTime()) /
                    1000
                )
              : null
            const lastSeenText =
              timeSinceLastSeen !== null
                ? timeSinceLastSeen < 60
                  ? `${timeSinceLastSeen}s ago`
                  : `${Math.floor(timeSinceLastSeen / 60)}m ago`
                : "Never"

            return (
              <Card
                key={agv.serial_number}
                className="cursor-pointer transition-all hover:bg-muted/50 hover:shadow-md"
                onClick={() => handleAgvClick(agv)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">
                      {agv.serial_number}
                    </CardTitle>
                    <Badge
                      variant={agv.is_online ? "default" : "destructive"}
                      className={
                        agv.is_online ? "bg-green-600 hover:bg-green-700" : ""
                      }
                    >
                      {agv.is_online ? "ONLINE" : "OFFLINE"}
                    </Badge>
                  </div>
                  <CardDescription className="flex items-center justify-between">
                    <span>{agv.manufacturer}</span>
                    <span className="text-xs">Seen: {lastSeenText}</span>
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {/* Battery indicator */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span>Battery</span>
                        <span
                          className={
                            charge < 20
                              ? "font-medium text-red-500"
                              : charge < 50
                                ? "font-medium text-yellow-500"
                                : "font-medium text-green-500"
                          }
                        >
                          {state ? `${charge.toFixed(1)}%` : "--%"}
                        </span>
                      </div>
                      <Progress value={state ? charge : 0} className="h-2" />
                    </div>

                    {/* Status info */}
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="block text-muted-foreground">
                          Position
                        </span>
                        <span className="block truncate font-medium">
                          {state?.last_node_id || "Unknown"}
                        </span>
                      </div>
                      <div>
                        <span className="block text-muted-foreground">
                          State
                        </span>
                        <span className="font-medium">
                          {state
                            ? state.driving
                              ? "🚚 Driving"
                              : state.paused
                                ? "⏸️ Paused"
                                : "🟢 Idle"
                            : "Unknown"}
                        </span>
                      </div>
                      <div className="col-span-2">
                        <span className="block text-muted-foreground">
                          Order
                        </span>
                        <span className="block truncate font-mono text-xs">
                          {state?.order_id || "No active task"}
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
