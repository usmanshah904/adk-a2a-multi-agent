#!/usr/bin/env bash
# Starts the Research Agent A2A server, waits for its Agent Card, then runs the
# Summary Agent. Stops the server again when you exit.
#
#   ./start.sh          # ADK web UI at http://localhost:8000 (default)
#   ./start.sh run      # chat in the terminal
#   ./start.sh e2e      # run the end-to-end A2A test
#
# Run from this folder with the virtual environment activated.
set -euo pipefail

MODE="${1:-web}"
PORT="${RESEARCH_AGENT_PORT:-8001}"
CARD_URL="http://localhost:${PORT}/.well-known/agent-card.json"

echo "Starting Research Agent A2A server on port ${PORT}..."
python -m uvicorn research_agent.server:a2a_app --host localhost --port "${PORT}" &
SERVER_PID=$!
trap 'echo "Stopping Research Agent server..."; kill "${SERVER_PID}" 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
  if curl -fs "${CARD_URL}" > /dev/null; then break; fi
  sleep 1
done
curl -fs "${CARD_URL}" > /dev/null || { echo "Research Agent did not start: no Agent Card at ${CARD_URL}"; exit 1; }
echo "Research Agent is up. Agent Card: ${CARD_URL}"

case "${MODE}" in
  web) adk web ;;
  run) adk run summary_agent ;;
  e2e) python test_e2e.py ;;
  *) echo "Usage: ./start.sh [web|run|e2e]"; exit 2 ;;
esac
