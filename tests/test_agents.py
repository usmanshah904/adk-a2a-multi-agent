"""Offline tests: no API key and no network needed.

They check how the two agents are wired together and that the Research
Agent's A2A server publishes a valid Agent Card. The live, model-backed
end-to-end run is test_e2e.py (see README).
"""

import importlib

from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.agent_tool import AgentTool
from starlette.testclient import TestClient


def test_research_agent_is_a_named_gemini_agent():
    from research_agent.agent import MODEL, root_agent

    assert root_agent.name == "research_agent"
    assert root_agent.model == MODEL
    assert "research brief" in root_agent.description


def test_summary_agent_delegates_to_research_agent_over_a2a():
    from summary_agent.agent import RESEARCH_AGENT_CARD_URL, root_agent

    assert root_agent.name == "summary_agent"
    assert len(root_agent.tools) == 1

    tool = root_agent.tools[0]
    assert isinstance(tool, AgentTool)
    # The Summary Agent only knows a URL: the remote agent is an A2A client,
    # not an import of the Research Agent's Python code.
    assert isinstance(tool.agent, RemoteA2aAgent)
    assert tool.agent.name == "research_agent"
    assert RESEARCH_AGENT_CARD_URL.endswith("/.well-known/agent-card.json")


def test_research_agent_url_can_be_configured(monkeypatch):
    monkeypatch.setenv("RESEARCH_AGENT_URL", "http://agents.internal:9000/")
    import summary_agent.agent as summary

    summary = importlib.reload(summary)
    try:
        assert summary.RESEARCH_AGENT_CARD_URL == (
            "http://agents.internal:9000/.well-known/agent-card.json"
        )
    finally:
        monkeypatch.delenv("RESEARCH_AGENT_URL")
        importlib.reload(summary)


def test_a2a_server_publishes_agent_card():
    from research_agent.server import a2a_app

    with TestClient(a2a_app) as client:
        response = client.get("/.well-known/agent-card.json")

    assert response.status_code == 200
    card = response.json()
    assert card["name"] == "research_agent"
    assert "text/plain" in card["defaultInputModes"]
    assert card["skills"], "the Agent Card should advertise at least one skill"
