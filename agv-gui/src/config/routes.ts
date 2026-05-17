export const ROUTES = {
  HOME: "/",
  DASHBOARD: "/dashboard",
  FLEET: "/fleet",
  ORDERS: "/orders",
  TASKS_CREATE: "/tasks/create",
  USER_INPUTS_REGISTER_AGVS: "/user-inputs/register-agvs",
  USER_INPUTS_GRAPH_MAP: "/user-inputs/graph-map",
  SUPERVISE_TASK_BIDDING: "/supervise/task-bidding",
  SUPERVISE_SENSOR_DATA: "/supervise/sensor-data",
  SIMULATE_ROUTING: "/simulate/routing",
} as const

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES]
