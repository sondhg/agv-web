"use client"

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import type { Agv } from "@/types/agv"
import type { AGVState as ApiAGVState } from "@/lib/api"

interface AgvDetailsModalProps {
  agv: Agv | null
  state: ApiAGVState | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AgvDetailsModal({
  agv,
  state,
  open,
  onOpenChange,
}: AgvDetailsModalProps) {
  if (!agv) return null

  // Calculate time since last seen
  const timeSinceLastSeen = agv.last_seen
    ? Math.floor(
        (new Date().getTime() - new Date(agv.last_seen).getTime()) / 1000
      )
    : null

  const lastSeenText =
    timeSinceLastSeen !== null
      ? timeSinceLastSeen < 60
        ? `${timeSinceLastSeen}s ago`
        : `${Math.floor(timeSinceLastSeen / 60)}m ago`
      : "Never"

  const charge = state?.battery_state?.batteryCharge ?? 0
  const isLowBattery = charge < 20
  const isMedBattery = charge >= 20 && charge < 50

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="mt-2 flex items-center justify-between">
            <DialogTitle>AGV Details: {agv.serial_number}</DialogTitle>
            <Badge variant={agv.is_online ? "default" : "destructive"}>
              {agv.is_online ? "ONLINE" : "OFFLINE"}
            </Badge>
          </div>
        </DialogHeader>

        <div className="grid gap-4 py-4 text-sm">
          <div className="flex justify-between text-muted-foreground">
            <span>Last seen: {lastSeenText}</span>
            {state?.operating_mode && <span>Mode: {state.operating_mode}</span>}
          </div>

          <Separator />

          {/* Battery */}
          <div className="space-y-2">
            <h4 className="font-semibold text-foreground">Battery</h4>
            {state?.battery_state ? (
              <div className="space-y-1 text-muted-foreground">
                <div className="mb-1 flex items-center justify-between">
                  <span>Charge: {charge.toFixed(1)}%</span>
                  <span
                    className={
                      isLowBattery
                        ? "font-medium text-red-500"
                        : isMedBattery
                          ? "font-medium text-yellow-500"
                          : "font-medium text-green-500"
                    }
                  >
                    {charge.toFixed(1)}%
                  </span>
                </div>
                <Progress value={charge} className="h-2" />
                <div className="flex items-center justify-between pt-1">
                  <span>
                    Voltage:{" "}
                    {state.battery_state.batteryVoltage?.toFixed(2) || "N/A"} V
                  </span>
                  <span>
                    Health:{" "}
                    {state.battery_state.batteryHealth?.toFixed(1) || "N/A"}%
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground italic">No battery data</p>
            )}
          </div>

          <Separator />

          {/* Position */}
          <div className="space-y-2">
            <h4 className="font-semibold text-foreground">Position</h4>
            {state?.agv_position ? (
              <div className="grid grid-cols-2 gap-2 text-muted-foreground">
                <div>Map: {state.agv_position.mapId || "Unknown"}</div>
                <div>
                  Last Node: {state.last_node_id || "Unknown"} (seq:{" "}
                  {state.last_node_sequence_id || 0})
                </div>
                <div>X: {state.agv_position.x?.toFixed(2) || "0.00"}</div>
                <div>Y: {state.agv_position.y?.toFixed(2) || "0.00"}</div>
                <div>
                  &theta; (Theta):{" "}
                  {state.agv_position.theta?.toFixed(3) || "0.000"}
                </div>
                <div>
                  Init: {state.agv_position.positionInitialized ? "Yes" : "No"}
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground italic">No position data</p>
            )}
          </div>

          <Separator />

          {/* Velocity */}
          <div className="space-y-2">
            <h4 className="font-semibold text-foreground">Velocity</h4>
            {state?.velocity ? (
              <div className="grid grid-cols-2 gap-2 text-muted-foreground">
                <div>vx: {state.velocity.vx?.toFixed(2) || "0.00"} m/s</div>
                <div>vy: {state.velocity.vy?.toFixed(2) || "0.00"} m/s</div>
                <div className="col-span-2">
                  &omega; (Omega): {state.velocity.omega?.toFixed(2) || "0.00"}{" "}
                  rad/s
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground italic">No velocity data</p>
            )}
          </div>

          <Separator />

          {/* Safety & Errors */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <h4 className="font-semibold text-foreground">Safety</h4>
              {state?.safety_state ? (
                <div className="space-y-1 text-muted-foreground">
                  <div className="flex items-center justify-between">
                    <span>E-Stop:</span>
                    <span
                      className={
                        state.safety_state.eStop !== "NONE"
                          ? "font-medium text-red-500"
                          : "font-medium text-green-500"
                      }
                    >
                      {state.safety_state.eStop || "UNKNOWN"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Field Violation:</span>
                    <span
                      className={
                        state.safety_state.fieldViolation
                          ? "font-medium text-red-500"
                          : "font-medium text-green-500"
                      }
                    >
                      {state.safety_state.fieldViolation ? "Yes" : "No"}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-muted-foreground italic">No safety data</p>
              )}
            </div>

            <div className="space-y-2">
              <h4 className="font-semibold text-foreground">Errors</h4>
              {state?.errors && state.errors.length > 0 ? (
                <div className="font-medium text-red-500">
                  {state.errors.length} active error(s)
                </div>
              ) : (
                <div className="font-medium text-green-500">None</div>
              )}
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <h4 className="font-semibold text-foreground">Loads</h4>
            {state?.loads && state.loads.length > 0 ? (
              <div className="text-muted-foreground">
                {state.loads.length} load(s) active
              </div>
            ) : (
              <div className="text-muted-foreground italic">None</div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
