import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
} from "react"
import mqtt from "mqtt"
import type { AGVState } from "@/lib/api"
import type { Agv } from "@/types/agv"

interface MqttContextValue {
  client: mqtt.MqttClient | null
  isConnected: boolean
  agvStates: Record<string, AGVState | null>
  agvConnections: Record<string, boolean>
  setInitialStates: (states: Record<string, AGVState | null>) => void
  setInitialConnections: (agvs: Agv[]) => void
}

const MqttContext = createContext<MqttContextValue | undefined>(undefined)

// URL fallback for dev environment where env var might not be set
const MQTT_URL = import.meta.env.VITE_MQTT_WS_URL || "ws://localhost:9001"

export function MqttProvider({ children }: { children: React.ReactNode }) {
  const [client, setClient] = useState<mqtt.MqttClient | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [agvStates, setAgvStates] = useState<Record<string, AGVState | null>>(
    {}
  )
  const [agvConnections, setAgvConnections] = useState<Record<string, boolean>>(
    {}
  )

  // We use a ref to track current states to avoid stale closures in the message handler
  const statesRef = useRef<Record<string, AGVState | null>>({})
  const connectionsRef = useRef<Record<string, boolean>>({})

  // Allow initializing states from HTTP fetch to avoid blank cards before the first MQTT message
  const setInitialStates = React.useCallback(
    (states: Record<string, AGVState | null>) => {
      setAgvStates((prev) => {
        const merged = { ...states, ...prev }
        statesRef.current = merged
        return merged
      })
    },
    []
  )

  const setInitialConnections = React.useCallback((agvs: Agv[]) => {
    setAgvConnections((prev) => {
      const initialMap: Record<string, boolean> = {}
      agvs.forEach((agv) => {
        initialMap[agv.serial_number] = agv.is_online ?? false
      })
      const merged = { ...initialMap, ...prev }
      connectionsRef.current = merged
      return merged
    })
  }, [])

  useEffect(() => {
    console.log(`Connecting to MQTT Broker at ${MQTT_URL}...`)
    const mqttClient = mqtt.connect(MQTT_URL)

    mqttClient.on("connect", () => {
      console.log("Connected to MQTT Broker via WebSockets")
      setIsConnected(true)

      // Subscribe to all AGV state and connection topics
      const topics = ["uagv/v2/+/+/state", "uagv/v2/+/+/connection"]
      mqttClient.subscribe(topics, (err) => {
        if (err) {
          console.error("MQTT subscription error:", err)
        } else {
          console.log("Subscribed to AGV state and connection topics")
        }
      })
    })

    mqttClient.on("message", (topic, message) => {
      try {
        const payload = JSON.parse(message.toString())

        // Topic: uagv/v2/{manufacturer}/{serial_number}/{msg_type}
        const parts = topic.split("/")
        if (parts.length < 5) return

        const serialNumber = parts[3]
        const msgType = parts[4]

        if (msgType === "state") {
          // Adapt VDA5050 raw payload (camelCase) to our AGVState interface (snake_case)
          const mappedState: Partial<AGVState> = {
            header_id: payload.headerId || 0,
            timestamp: payload.timestamp,
            order_id: payload.orderId || "",
            last_node_id: payload.lastNodeId || "",
            last_node_sequence_id: payload.lastNodeSequenceId || 0,
            driving: payload.driving || false,
            paused: payload.paused || false,
            operating_mode: payload.operatingMode || "",
            battery_state: payload.batteryState || {
              batteryCharge: 0,
              batteryVoltage: 0,
              batteryHealth: 0,
            },
            agv_position: payload.agvPosition || {
              x: 0,
              y: 0,
              theta: 0,
              mapId: "",
              positionInitialized: false,
            },
            velocity: payload.velocity || { vx: 0, vy: 0, omega: 0 },
            safety_state: payload.safetyState || {
              eStop: "NONE",
              fieldViolation: false,
            },
            errors: payload.errors || [],
            loads: payload.loads || [],
          }

          setAgvStates((prev) => {
            const currentState = prev[serialNumber] || ({} as AGVState)
            const newState = { ...currentState, ...mappedState } as AGVState

            statesRef.current = {
              ...statesRef.current,
              [serialNumber]: newState,
            }

            return statesRef.current
          })
        } else if (msgType === "connection") {
          const isOnline = payload.connectionState === "ONLINE"

          setAgvConnections(() => {
            connectionsRef.current = {
              ...connectionsRef.current,
              [serialNumber]: isOnline,
            }
            return connectionsRef.current
          })
        }
      } catch (err) {
        console.error("Error parsing MQTT message on topic", topic, err)
      }
    })

    mqttClient.on("error", (err) => {
      console.error("MQTT Connection Error:", err)
      setIsConnected(false)
    })

    mqttClient.on("close", () => {
      setIsConnected(false)
    })

    setClient(mqttClient)

    return () => {
      mqttClient.end()
    }
  }, [])

  return (
    <MqttContext.Provider
      value={{
        client,
        isConnected,
        agvStates,
        agvConnections,
        setInitialStates,
        setInitialConnections,
      }}
    >
      {children}
    </MqttContext.Provider>
  )
}

export function useMqttTelemetry() {
  const context = useContext(MqttContext)
  if (context === undefined) {
    throw new Error("useMqttTelemetry must be used within an MqttProvider")
  }
  return context
}
