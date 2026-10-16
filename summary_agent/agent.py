"""Summary Agent: the user-facing coordinator.

This agent never imports or calls the Research Agent's Python code. Instead
it talks to it purely over HTTP using the A2A protocol, via ADK's
``RemoteA2aAgent``. ``RemoteA2aAgent`` reads the Research Agent's Agent Card
(published at its well-known A2A URL) to learn how to reach it, then sends
every request as a real A2A JSON-RPC call over the network.

The remote agent is wrapped in an ``AgentTool`` so the Summary Agent's model
can call it like a tool: "ask the remote research agent, get the research
brief back, then keep going" -- matching the required flow of
User -> Summary Agent -> A2A -> Research Agent -> result -> Summary Agent ->
final answer.
"""

from google.adk.agents.llm_agent import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.agent_tool import AgentTool

# Well-known Agent Card URL for the locally running Research Agent A2A
# server (see research_agent/server.py, which serves it on port 8001).
RESEARCH_AGENT_CARD_URL = "http://localhost:8001/.well-known/agent-card.json"

research_agent = RemoteA2aAgent(
    name="research_agent",
    agent_card=RESEARCH_AGENT_CARD_URL,
    description=(
        "Remote specialist agent, reached over A2A, that researches a topic"
        " and returns a concise, structured research brief."
    ),
)

root_agent = Agent(
    model="gemini-3.5-flash",
    name="summary_agent",
    description=(
        "User-facing agent that delegates research questions to a remote"
        " Research Agent over A2A and summarizes the result."
    ),
    instruction="""You are the Summary Agent. You talk to the end user directly.

You do not have research knowledge of your own. Whenever the user asks a
research question or asks about a topic, you MUST call the `research_agent`
tool with that question -- this sends the request over A2A to the remote
Research Agent and returns its research brief to you. Never try to answer a
research question from your own knowledge.

Once you get the research brief back:
1. Read it carefully.
2. Write a short, clear summary for the user in your own words (a few
   sentences or a short bullet list) -- do not just paste the raw brief.
3. Mention that the research was produced by the remote Research Agent via
   A2A, so the user understands the two-agent flow.

If the user's message is not a research question (e.g. small talk), you may
answer directly without calling the tool.""",
    tools=[AgentTool(agent=research_agent)],
)
