"use client"

import { useState, useEffect } from "react"
import { Loader2, RefreshCw, Car, Wifi, WifiOff } from "lucide-react"

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
import { useMqttTelemetry } from "@/contexts/MqttContext"

export default function FleetDashboardPage() {
  const [agvs, setAgvs] = useState<Agv[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [selectedAgv, setSelectedAgv] = useState<Agv | null>(null)
  const [detailsModalOpen, setDetailsModalOpen] = useState(false)

  // Use MQTT Telemetry instead of HTTP polling
  const {
    agvStates,
    agvConnections,
    isConnected,
    setInitialStates,
    setInitialConnections,
  } = useMqttTelemetry()

  // Only load statically once
  useEffect(() => {
    let mounted = true

    const loadData = async () => {
      if (!mounted) return
      setLoading(true)
      setError(null)

      try {
        // 1. Fetch all AGVs
        const agvsData = await fetchAgvs()
        if (!mounted) return
        setAgvs(agvsData)
        setInitialConnections(agvsData)

        // 2. Fetch latest state for each AGV just once on initial load
        // so we don't have blank cards while waiting for the first MQTT message
        const statesMap: Record<string, import("@/lib/api").AGVState | null> =
          {}

        await Promise.all(
          agvsData.map(async (agv) => {
            try {
              const states = await fetchAgvStates(agv.serial_number)
              statesMap[agv.serial_number] =
                states.length > 0 ? states[0] : null
            } catch (e) {
              console.warn(
                `Failed to fetch initial state for AGV ${agv.serial_number}`,
                e
              )
              statesMap[agv.serial_number] = null
            }
          })
        )

        if (mounted) {
          setInitialStates(statesMap)
        }
      } catch (err) {
        console.error("Failed to load initial fleet data:", err)
        if (mounted) {
          setError(
            err instanceof Error ? err.message : "Failed to load fleet data"
          )
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }

    loadData()

    return () => {
      mounted = false
    }
  }, [setInitialStates, setInitialConnections])

  function handleAgvClick(agv: Agv) {
    setSelectedAgv(agv)
    setDetailsModalOpen(true)
  }

  function handleManualRefresh() {
    // Only refresh the static definitions
    setLoading(true)
    fetchAgvs()
      .then((data) => {
        setAgvs(data)
        setInitialConnections(data)
        setError(null)
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Failed to refresh fleet data"
        )
      })
      .finally(() => {
        setLoading(false)
      })
  }

  // Calculate some overview stats using real-time data
  const onlineAgvsCount = agvs.filter(
    (a) => agvConnections[a.serial_number] ?? a.is_online
  ).length
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
        <div className="flex items-center space-x-4">
          {isConnected ? (
            <Badge
              variant="outline"
              className="border-green-200 bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
            >
              <Wifi className="mr-1 h-3 w-3" /> Live
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="border-red-200 bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
            >
              <WifiOff className="mr-1 h-3 w-3" /> Disconnected
            </Badge>
          )}
          <Button
            onClick={handleManualRefresh}
            variant="outline"
            size="sm"
            disabled={loading}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error Loading Fleet Data</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {loading && !error && agvs.length === 0 && (
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
      {(!loading || agvs.length > 0) && !error && agvs.length > 0 && (
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
      {(!loading || agvs.length > 0) && !error && agvs.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {agvs.map((agv) => {
            const state = agvStates[agv.serial_number]
            const isOnline = agvConnections[agv.serial_number] ?? agv.is_online
            const charge = state?.battery_state?.batteryCharge ?? 0

            // Time since last seen from MQTT is immediate if online, otherwise use DB last_seen
            let lastSeenText = "Never"
            if (isOnline) {
              lastSeenText = "Live"
            } else if (agv.last_seen) {
              const timeSinceLastSeen = Math.floor(
                (new Date().getTime() - new Date(agv.last_seen).getTime()) /
                  1000
              )
              lastSeenText =
                timeSinceLastSeen < 60
                  ? `${timeSinceLastSeen}s ago`
                  : `${Math.floor(timeSinceLastSeen / 60)}m ago`
            }

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
                      variant={isOnline ? "default" : "destructive"}
                      className={
                        isOnline ? "bg-green-600 hover:bg-green-700" : ""
                      }
                    >
                      {isOnline ? "ONLINE" : "OFFLINE"}
                    </Badge>
                  </div>
                  <CardDescription className="flex items-center justify-between">
                    <span>{agv.manufacturer}</span>
                    <span className="text-xs text-muted-foreground">
                      {isOnline ? (
                        <span className="flex items-center text-green-600 dark:text-green-500">
                          <span className="relative mr-1 flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"></span>
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500"></span>
                          </span>
                          Live
                        </span>
                      ) : (
                        `Seen: ${lastSeenText}`
                      )}
                    </span>
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
