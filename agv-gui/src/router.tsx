import {
  createRouter,
  createRoute,
  createRootRoute,
} from "@tanstack/react-router"

import GraphMapPage from "@/app/graph-map/page"
import RegisterAgvsPage from "@/app/register-agvs/page"
import Layout from "@/app/layout"
import DashboardPage from "@/app/dashboard/page"
import TaskBiddingPage from "@/app/supervise/task-bidding/page"
import SensorDataPage from "@/app/supervise/sensor-data/page"
import RoutingPage from "@/app/simulate/routing/page"

const rootRoute = createRootRoute({
  component: Layout,
  notFoundComponent: () => {
    return (
      <div className="container mx-auto space-y-6 py-10">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Page Not Found</h1>
          <p className="text-muted-foreground">
            The page you're looking for doesn't exist.
          </p>
        </div>
        <div className="rounded-lg border bg-card p-6">
          <p className="text-muted-foreground">
            Please check the URL or use the navigation menu to find what you're
            looking for.
          </p>
        </div>
      </div>
    )
  },
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: DashboardPage,
})

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/dashboard",
  component: DashboardPage,
})

// const userInputsRoute = createRoute({
//   getParentRoute: () => rootRoute,
//   path: "/user-inputs",
//   component: UserInputsPage,
// })

const taskBiddingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/supervise/task-bidding",
  component: TaskBiddingPage,
})

const sensorDataRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/supervise/sensor-data",
  component: SensorDataPage,
})

const routingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/simulate/routing",
  component: RoutingPage,
})

const graphMapRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/user-inputs/graph-map",
  component: GraphMapPage,
})

const registerAgvsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/user-inputs/register-agvs",
  component: RegisterAgvsPage,
})

const routeTree = rootRoute.addChildren([
  indexRoute,
  dashboardRoute,
  taskBiddingRoute,
  sensorDataRoute,
  routingRoute,
  graphMapRoute,
  registerAgvsRoute,
])

export const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
