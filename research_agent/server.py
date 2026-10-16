"""Runs the Research Agent as a standalone A2A server.

``to_a2a()`` (google.adk.a2a.utils.agent_to_a2a) wraps the plain ADK agent
defined in agent.py into a Starlette app that speaks the A2A protocol: it
adds the JSON-RPC message endpoint and publishes the agent's "Agent Card" at
the standard well-known path (/.well-known/agent-card.json). Nothing here
runs any Summary Agent code -- this process only knows how to answer
research questions over HTTP.

Start it with:
    uvicorn research_agent.server:a2a_app --host localhost --port 8001

or simply:
    python -m research_agent.server
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Loads GOOGLE_API_KEY (and friends) from the .env file at the project root
# (a2a_research_agents/.env), the same way `adk web` / `adk run` do.
# Required here because this script is started directly with uvicorn,
# bypassing the ADK CLI, which would otherwise load it automatically.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .agent import root_agent

# Where the A2A server listens; override with RESEARCH_AGENT_HOST / RESEARCH_AGENT_PORT.
HOST = os.getenv("RESEARCH_AGENT_HOST", "localhost")
PORT = int(os.getenv("RESEARCH_AGENT_PORT", "8001"))

# A Starlette ASGI app: A2A routes + agent card are mounted at app startup.
a2a_app = to_a2a(root_agent, host=HOST, port=PORT)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(a2a_app, host=HOST, port=PORT)
