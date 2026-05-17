# AGV Simulators

To test the web app with fake data, you can run the `multi_agent_runner.py` script.
This script orchestrates a complete simulation: starts the mock AGV fleet, dispatches tasks, and collects metrics.

## Running the Simulator

1. **Activate Backend Environment (if needed) / Run in Docker:**
   It is recommended to run this inside the backend docker container or with access to the `API_BASE_URL` (usually `http://localhost:8000/api` if port forwarded).

2. **Basic Simulation:**
   ```bash
   python multi_agent_runner.py
   ```

3. **Specific Scenarios:**
   List all available scenarios:
   ```bash
   python multi_agent_runner.py --list
   ```
   
   Run a specific scenario (e.g., `burst`):
   ```bash
   python multi_agent_runner.py --scenario burst
   ```

4. **Custom Fleet Size (Basic scenario):**
   ```bash
   python multi_agent_runner.py --agvs 5
   ```
