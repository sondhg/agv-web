# AGV Frontend (agv-gui) - Agent Coding Guidelines

This document provides essential instructions, commands, and coding standards for any autonomous coding agents working on the **frontend** (React/TypeScript/Vite) of the AGV monorepo.

**For backend work**, see [`../agv-system/AGENTS.md`](../agv-system/AGENTS.md)  
**For monorepo overview**, see [`../AGENTS.md`](../AGENTS.md)

---

## 1. Project Context & Tech Stack

- **Framework**: React 19 + TypeScript 5.9
- **Build Tool**: Vite 7 (lightning-fast dev server & HMR)
- **UI Library**: shadcn/ui with Radix UI primitives
- **Styling**: Tailwind CSS 4 (with JIT compilation)
- **Code Quality**: ESLint 9 + Prettier 3
- **Package Manager**: pnpm (fast, disk-efficient)
- **Key Domain**: AGV fleet monitoring dashboard, real-time visualization, control interface

---

## 2. Build & Development Commands

**All commands below must be run from the `agv-gui/` directory.**

### Development Workflow
```bash
# Install dependencies (first time or after package.json changes)
pnpm install

# Start dev server (http://localhost:5173)
pnpm dev

# Build for production
pnpm build

# Preview production build
pnpm preview
```

### Code Quality Commands
```bash
# Lint TypeScript/React files
pnpm lint

# Format all TypeScript files with Prettier
pnpm format

# Type-check without emitting files (catches type errors)
pnpm typecheck
```

### Example Workflow
```bash
# Before committing changes:
pnpm lint          # Fix linting issues
pnpm format        # Format code
pnpm typecheck     # Verify types
pnpm build         # Ensure build succeeds
```

---

## 3. Testing Commands

**Note**: This project currently has no test framework configured.

If implementing tests:
- Consider Vitest (recommended for Vite projects)
- Add test scripts to `package.json`
- Document test commands in this section

---

## 4. Code Style & Conventions

### TypeScript Guidelines

#### Type Safety
- **Strict mode enabled**: All TypeScript strict checks are active
- **No implicit any**: Always specify types explicitly
- **No unused variables**: Remove or prefix with `_` if intentionally unused
- **Type imports**: Use `type` keyword for type-only imports
  ```typescript
  import type { ComponentProps } from "react"
  import { useState } from "react"
  ```

#### Naming Conventions
- **Components**: `PascalCase` (e.g., `Button`, `UserProfile`)
- **Files**: Match component names (e.g., `Button.tsx`, `UserProfile.tsx`)
- **Hooks**: `camelCase` with `use` prefix (e.g., `useTheme`, `useAgvData`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `API_BASE_URL`)
- **Variables/Functions**: `camelCase` (e.g., `userData`, `fetchAgvStatus`)

#### Imports Organization
Group imports in the following order (separated by blank lines):
1. React/React ecosystem
2. Third-party libraries
3. Local components (using `@/` alias)
4. Types (using `type` keyword)
5. Styles/assets

```typescript
import { useState, useEffect } from "react"
import { createRoot } from "react-dom/client"

import { cva } from "class-variance-authority"
import { Slot } from "radix-ui"

import { Button } from "@/components/ui/button"
import { ThemeProvider } from "@/components/theme-provider"
import { cn } from "@/lib/utils"

import type { AgvStatus, FleetData } from "@/types/agv"

import "./index.css"
```

### React Guidelines

#### Component Structure
- **Functional components only**: Use hooks, not class components
- **Named exports**: Prefer named exports over default exports (except for main App)
- **Component organization**:
  ```typescript
  // 1. Imports
  // 2. Type definitions
  // 3. Component definition
  // 4. Helper functions (if needed)
  ```

#### Hooks Rules
- Call hooks at the top level (not in loops/conditions)
- Follow React Hooks rules (ESLint will catch violations)
- Custom hooks must start with `use` prefix

#### Props & Types
- Define explicit prop types for all components
- Use `interface` for props (not `type`)
- Prefer destructuring props in function signature
  ```typescript
  interface ButtonProps {
    variant?: "default" | "outline"
    size?: "sm" | "md" | "lg"
    disabled?: boolean
    onClick?: () => void
  }

  export function Button({ variant = "default", size = "md", ...props }: ButtonProps) {
    // Component implementation
  }
  ```

### Styling with Tailwind CSS

#### Class Organization
- Use the `cn()` utility from `@/lib/utils` to merge class names
- Order: layout → spacing → sizing → colors → typography → effects
- Use Tailwind's responsive prefixes: `sm:`, `md:`, `lg:`, `xl:`
- Use dark mode classes: `dark:bg-gray-800`

```typescript
<button
  className={cn(
    "flex items-center justify-center",     // layout
    "px-4 py-2",                            // spacing
    "h-10 w-full",                          // sizing
    "bg-primary text-white",                // colors
    "text-sm font-medium",                  // typography
    "rounded-lg shadow-md",                 // effects
    "hover:bg-primary/90",                  // interactive
    "dark:bg-primary/80",                   // dark mode
    className                               // user overrides
  )}
>
  Click me
</button>
```

#### shadcn/ui Components
- Use shadcn/ui components as base primitives
- Components live in `src/components/ui/`
- Customize via `cva` (class-variance-authority)
- Add new components: `npx shadcn@latest add <component-name>`

### Prettier Configuration
Follow the `.prettierrc` settings:
- **No semicolons** (enforced)
- **Double quotes** for strings
- **Line length**: 80 characters
- **Trailing commas**: ES5 style
- **2 spaces** for indentation
- **LF** line endings

### Path Aliases
Use the `@/` alias for cleaner imports:
```typescript
// ✅ Good
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// ❌ Avoid
import { Button } from "../../components/ui/button"
import { cn } from "../../../lib/utils"
```

---

## 5. Error Handling & Best Practices

### Error Handling
- Use try-catch for async operations
- Display user-friendly error messages
- Log errors to console in development
- Consider error boundaries for React component errors

### Performance
- Use React.memo() for expensive components
- Lazy load routes/components: `const Component = lazy(() => import("./Component"))`
- Optimize images (use WebP, lazy loading)
- Monitor bundle size: check `pnpm build` output

### Accessibility
- Use semantic HTML elements
- Include ARIA labels where needed
- Ensure keyboard navigation works
- Test with screen readers

---

## 6. Agent Operational Mandates

When operating in this repository, agents **MUST**:

1. **Read Before Writing**: Always use `glob`/`grep` to understand existing component patterns and folder structure before creating new components.

2. **Never Assume Libraries**: Do not install new npm packages without checking `package.json` first. If adding a package, justify why it's needed.

3. **Paths**: Ensure absolute paths resolve correctly:
   - Project root: `/home/sondhg/Documents/agv-web/agv-gui/`
   - Use `@/` alias for imports from `src/`

4. **Type Safety**: Never use `any` type without explicit justification. Use `unknown` if the type is genuinely unknown, then narrow it.

5. **Component Consistency**: Follow existing component patterns (check `src/components/ui/` for examples). Use shadcn/ui components as base when possible.

6. **Build Verification**: Always run `pnpm build` and `pnpm typecheck` after changes to ensure no errors were introduced.

7. **Format Before Commit**: Run `pnpm format` to ensure consistent code style.

8. **No Console Logs**: Remove `console.log()` statements before committing (unless for error handling).

9. **Responsive Design**: Ensure all UI components work on mobile, tablet, and desktop (use Tailwind responsive prefixes).

10. **Dark Mode Support**: All new components must support dark mode using Tailwind's `dark:` prefix.

---

## 7. Project Structure Reference

```
agv-gui/
├── src/
│   ├── app/              # Application pages/routes
│   ├── components/       # Reusable components
│   │   ├── ui/          # shadcn/ui components
│   │   └── ...          # Custom components
│   ├── hooks/           # Custom React hooks
│   ├── lib/             # Utility functions
│   ├── assets/          # Static assets (images, icons)
│   ├── App.tsx          # Root application component
│   ├── main.tsx         # Application entry point
│   └── index.css        # Global styles & Tailwind imports
├── public/              # Static files (favicon, etc.)
├── index.html           # HTML template
├── package.json         # Dependencies & scripts
├── tsconfig.json        # TypeScript configuration
├── vite.config.ts       # Vite configuration
├── eslint.config.js     # ESLint configuration
└── .prettierrc          # Prettier configuration
```

---

## 8. Common Patterns & Examples

### Creating a New Component
```typescript
// src/components/AgvCard.tsx
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface AgvCardProps {
  id: string
  status: "idle" | "busy" | "charging"
  battery: number
  className?: string
}

export function AgvCard({ id, status, battery, className }: AgvCardProps) {
  return (
    <Card className={cn("p-4", className)}>
      <h3 className="text-lg font-semibold">AGV {id}</h3>
      <p className="text-sm text-muted-foreground">Status: {status}</p>
      <p className="text-sm">Battery: {battery}%</p>
    </Card>
  )
}
```

### Creating a Custom Hook
```typescript
// src/hooks/useAgvStatus.ts
import { useState, useEffect } from "react"
import type { AgvStatus } from "@/types/agv"

export function useAgvStatus(agvId: string) {
  const [status, setStatus] = useState<AgvStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    // Fetch AGV status logic
    fetchAgvStatus(agvId)
      .then(setStatus)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [agvId])

  return { status, loading, error }
}
```

---

**Remember**: This is the frontend layer only. For backend API changes, coordinate with the backend team and update `agv-system/` accordingly.
