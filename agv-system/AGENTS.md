# AGV Backend (agv-system) - Agent Coding Guidelines

This document provides essential instructions, commands, and coding standards for any autonomous coding agents working on the **backend** (Django/Python/MQTT) of the AGV monorepo.

**For frontend work**, see [`../agv-gui/AGENTS.md`](../agv-gui/AGENTS.md)  
**For monorepo overview**, see [`../AGENTS.md`](../AGENTS.md)

## 1. Project Context & Tech Stack
- **Backend Framework:** Django (Python 3+)
- **Communication:** MQTT (Eclipse Mosquitto) / VDA5050 standard
- **Database:** PostgreSQL (via `psycopg2-binary`)
- **Infrastructure:** Docker & Docker Compose
- **Key Domain:** Automated Guided Vehicles (AGV) load balancing, fleet management, and graph-based routing.

---

## 2. Build & Execution Commands

### Running the System
The project relies on Docker for infrastructure and local development. **All commands below must be run from the `agv-system/` directory.**

- **Start all services (detached):**
  ```bash
  docker-compose up -d
  ```
- **Stop all services:**
  ```bash
  docker-compose down
  ```
- **View logs:**
  ```bash
  docker-compose logs -f
  ```
- **Rebuild containers after dependency changes:**
  ```bash
  docker-compose up -d --build
  ```

### Database Operations
- **Make migrations:** `docker-compose exec web python manage.py makemigrations`
- **Apply migrations:** `docker-compose exec web python manage.py migrate`
- **Reset/Flush DB:** `docker-compose exec web python manage.py flush`

---

## 3. Testing Commands

The repository contains both standard Django tests and specialized load balancing tests. 

### Running Django Unit Tests
To run the standard Django test suite inside the Docker container:
- **Run all tests:**
  ```bash
  docker-compose exec web python manage.py test
  ```
- **Run a specific app's tests:**
  ```bash
  docker-compose exec web python manage.py test <app_name>
  ```
- **Run a SINGLE test file:**
  ```bash
  docker-compose exec web python manage.py test <app_name>.tests.<test_file_name>
  ```
- **Run a SINGLE test case/method:**
  ```bash
  docker-compose exec web python manage.py test <app_name>.tests.<test_file_name>.<TestClassName>.<test_method_name>
  ```

### Running AGV Load Balancing Simulation Tests
For system integration and load balancing metrics, use the test scripts provided in the `tests/` directory.
1. **Setup Test AGVs:**
   ```bash
   docker-compose exec web python manage.py setup_test_agvs --count 7
   ```
2. **Execute Load Balancing Test:**
   ```bash
   python tests/load_balancing/test_agv_load_balancing.py
   ```
*(Note: See `tests/TEST_README.md` for scenario configurations).*

---

## 4. Linting & Formatting

The project uses **Ruff** for Python linting and formatting (fast, modern, Rust-based):

- **Check for linting issues:**
  ```bash
  ruff check .
  ```
- **Auto-fix linting issues:**
  ```bash
  ruff check --fix .
  ```
- **Format code with Ruff:**
  ```bash
  ruff format .
  ```

*Note: Ruff cache is stored in `.ruff_cache/` (already gitignored).*

---

## 5. Code Style & Conventions

### Python Guidelines
- **Formatting:** Follow **PEP 8** standards. Aim for a maximum line length of 88-100 characters. Use `ruff format` for consistent formatting.
- **Type Hinting:** Use Python type hints (`typing` module) extensively for all function arguments and return types. This is critical for maintainability in complex graph and routing logic.
  ```python
  from typing import List, Dict, Optional

  def calculate_route(start_node: str, end_node: str) -> Optional[List[str]]:
      pass
  ```
- **Naming Conventions:**
  - Variables/Functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
- **Imports:** Group imports logically.
  1. Standard library imports
  2. Third-party imports (e.g., `django`, `paho.mqtt`)
  3. Local application/library specific imports
- **Error Handling:** 
  - Do not use bare `except:` clauses. Catch specific exceptions.
  - Log errors properly using Python's `logging` module rather than `print()` statements in production code.
- **Docstrings:** Use Google-style or Sphinx-style docstrings for all classes and complex functions. Briefly explain *what* the function does, its *arguments*, and its *return value*.

### Django Specifics
- **Fat Models, Skinny Views:** Keep business logic in models or dedicated service layers (e.g., routing algorithms, MQTT publishers) rather than in Django views/API views.
- **Queries:** Optimize database access using `select_related` and `prefetch_related` where appropriate to avoid N+1 query issues.

---

## 6. Agent Operational Mandates

When operating in this repository, agents **MUST**:
1. **Read Before Writing:** Always use file reading and `grep`/`glob` to understand existing architectural patterns (especially around the `vda5050` app and graph engine) before modifying code.
2. **Never Assume Libraries:** Do not import new third-party libraries without checking `backend/requirements.txt` first.
3. **Paths:** Ensure absolute paths are properly resolved relative to `/home/sondhg/Documents/agv-web/agv-system/`.
4. **Testing Edits:** If altering routing logic or load balancing, ensure that `test_agv_load_balancing.py` can still execute successfully. Do not break the test suite metrics.
5. **Simulators:** If adding a new feature that impacts AGV state, consider whether the simulators in `tests/simulators/` need updating.
6. **Docker Context:** All Docker commands must be run from the `agv-system/` directory where `docker-compose.yml` is located.
