# AGV Monorepo - Agent Coding Guidelines

This document provides navigation and essential instructions for autonomous coding agents operating within the AGV Monorepo.

## 🗂️ Repository Structure

This is a **monorepo** containing two main projects:

```
/home/sondhg/Documents/agv-web/
├── agv-system/          # Django backend (Fleet Management + MQTT)
│   ├── backend/         # Django application
│   ├── tests/           # Integration & load balancing tests
│   ├── docker-compose.yml
│   └── AGENTS.md        # ⭐ Backend-specific guidelines
└── agv-gui/             # React frontend (Web UI)
    ├── src/             # TypeScript + React source
    ├── package.json
    └── AGENTS.md        # ⭐ Frontend-specific guidelines
```

## 📋 Project-Specific Guidelines

**When working on the backend** (Django/Python/MQTT):
- **Read**: [`agv-system/AGENTS.md`](agv-system/AGENTS.md)
- Contains: Docker commands, Django testing, Python style, MQTT patterns

**When working on the frontend** (React/TypeScript):
- **Read**: [`agv-gui/AGENTS.md`](agv-gui/AGENTS.md)
- Contains: npm/pnpm commands, TypeScript style, React patterns, component guidelines

---

## 🚀 Quick Reference

### Starting the Full Stack

**Backend (from `agv-system/`):**
```bash
cd agv-system
docker-compose up -d
```

**Frontend (from `agv-gui/`):**
```bash
cd agv-gui
pnpm install
pnpm dev
```

### Common Commands

| Task | Backend (agv-system/) | Frontend (agv-gui/) |
|------|----------------------|---------------------|
| **Install** | `docker-compose up -d` | `pnpm install` |
| **Dev Server** | Runs in Docker | `pnpm dev` |
| **Build** | N/A (Django) | `pnpm build` |
| **Lint** | N/A | `pnpm lint` |
| **Format** | N/A | `pnpm format` |
| **Type Check** | Python type hints | `pnpm typecheck` |
| **Run All Tests** | `docker-compose exec web python manage.py test` | N/A (no tests yet) |
| **Run Single Test** | `docker-compose exec web python manage.py test app.tests.file.Class.method` | N/A |

---

## 🎯 Cross-Project Guidelines

### 1. Path Resolution
- **Backend absolute path**: `/home/sondhg/Documents/agv-web/agv-system/`
- **Frontend absolute path**: `/home/sondhg/Documents/agv-web/agv-gui/`
- Always use correct project-relative paths when referencing files

### 2. Code Reading Protocol
Before making changes:
1. Use `glob` or `grep` to understand existing patterns
2. Read related files to maintain consistency
3. Check both `AGENTS.md` files if changes affect multiple projects

### 3. Dependencies
- **Backend**: Check `agv-system/backend/requirements.txt` before adding Python packages
- **Frontend**: Check `agv-gui/package.json` before adding npm packages
- Never assume a library is available without verification

### 4. Testing Requirements
- **Backend**: Run Django tests after changes to core logic
- **Frontend**: Currently no test framework (add tests if implementing new features)
- Always verify builds succeed before committing

### 5. File Operations
- Use specialized tools: `Read` (not cat), `Edit` (not sed), `Write` (not echo)
- For complex searches across projects, use the `Task` tool with explore agent
- Avoid `find`/`grep` bash commands; use `Glob`/`Grep` tools instead

### 6. Communication Standards
- Backend-Frontend API contracts must be documented
- MQTT message formats follow VDA5050 standard
- API endpoints should follow REST conventions

---

## 🏗️ Technology Stack Summary

### Backend (agv-system)
- **Framework**: Django 4.2+ with Django REST Framework
- **Database**: PostgreSQL
- **Messaging**: MQTT (Eclipse Mosquitto) / VDA5050 standard
- **Routing**: NetworkX for graph-based pathfinding
- **Infrastructure**: Docker + Docker Compose
- **Language**: Python 3.10+
- **Domain**: AGV fleet management, load balancing, auction-based task assignment

### Frontend (agv-gui)
- **Framework**: React 19 + TypeScript 5.9
- **Build Tool**: Vite 7
- **UI Library**: shadcn/ui with Radix UI primitives
- **Styling**: Tailwind CSS 4
- **Code Quality**: ESLint 9 + Prettier 3
- **Package Manager**: pnpm
- **Domain**: AGV monitoring dashboard, fleet visualization, control interface

---

## 📖 Navigation Tips

1. **Backend work?** → Open `agv-system/AGENTS.md` for detailed Django/Python guidelines
2. **Frontend work?** → Open `agv-gui/AGENTS.md` for detailed React/TypeScript guidelines
3. **Full-stack feature?** → Read both project-specific AGENTS.md files
4. **Architecture questions?** → Check `agv-system/README.md` and `agv-system/docs/`

---

## ⚠️ Critical Rules for Agents

1. **Always read project-specific AGENTS.md** before making changes to backend or frontend
2. **Never mix concerns**: Keep backend logic in Django, UI logic in React
3. **Maintain API contracts**: Document any changes to REST endpoints or MQTT topics
4. **Test before committing**: Run appropriate tests for the project you're modifying
5. **Follow existing patterns**: Use `grep`/`glob` to find similar code before implementing new features

---

**For detailed coding standards, build commands, and project-specific requirements, refer to the AGENTS.md file in each project directory.**
