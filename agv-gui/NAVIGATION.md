# AGV Web GUI - Navigation Guide

## Available Routes

The application now has full routing implemented with TanStack Router. Here are all available pages:

### Main Routes

1. **Dashboard** - `/` or `/dashboard`
   - Landing page with fleet overview
   - Quick stats and system health

2. **User Inputs** - `/user-inputs`
   - **CSV Import**: Upload AGV fleet data from CSV files
   - **Data Table**: View and manage imported AGV fleet
   - Create or update AGVs based on ID

3. **Supervise Section**
   - **Task Bidding** - `/supervise/task-bidding`
     - Monitor auction-based task assignment
     - View bidding processes
   - **Sensor Data** - `/supervise/sensor-data`
     - Real-time sensor readings
     - Position, speed, battery monitoring

4. **Simulate Section**
   - **Routing** - `/simulate/routing`
     - Path simulation and visualization
     - Test routing algorithms

## Features

- ✅ **Client-side routing** with TanStack Router
- ✅ **Active link highlighting** in sidebar
- ✅ **Dynamic breadcrumbs** showing current location
- ✅ **Type-safe navigation** with TypeScript
- ✅ **Smooth transitions** between pages
- ✅ **URL-based navigation** (bookmark-able routes)

## Usage

### Starting the Dev Server

```bash
cd agv-gui
pnpm dev
```

Then navigate to:

- Home: `http://localhost:5173/`
- User Inputs (CSV Import): `http://localhost:5173/user-inputs`
- Any other route as listed above

### Sidebar Navigation

Click on any menu item in the sidebar to navigate to that page. The active page will be highlighted.

## Adding New Routes

To add a new route:

1. Create a page component in `src/app/[route-name]/page.tsx`
2. Add the route to `src/router.tsx`
3. Add navigation link to `src/components/app-sidebar.tsx`
4. Update breadcrumbs in `src/app/layout.tsx`

## Sample CSV for Testing

A sample CSV file is included at `sample-agv-fleet.csv` for testing the User Inputs page.
