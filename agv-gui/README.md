# AGV Web GUI (React + TypeScript + Vite)

This is the frontend dashboard for the AGV fleet management system.

## 🚀 Running the App with Docker

The simplest way to run the web interface is using Docker.

### Prerequisites

- Docker & Docker Compose

### Start the Application

1. Open your terminal and navigate to the frontend directory:

   ```bash
   cd agv-gui
   ```

2. Start the container in the background:

   ```bash
   docker compose up -d
   ```

3. Open your web browser and navigate to:
   **<http://localhost:5173>**

_Note: To stop the application, run `docker compose down`._

---

## Adding components

To add components to your app, run the following command:

```bash
npx shadcn@latest add button
```

This will place the ui components in the `src/components` directory.

## Using components

To use the components in your app, import them as follows:

```tsx
import { Button } from "@/components/ui/button"
```
