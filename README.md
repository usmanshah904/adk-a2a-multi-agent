# Research -> Summary Agents (Google ADK + A2A)

A small, two-agent demo built with **Google's Agent Development Kit (ADK)**
where the two agents are **separate processes** that talk to each other over
the **A2A (Agent-to-Agent) protocol** -- real HTTP/JSON-RPC, not a Python
function call.

```
User
  -> Summary Agent (ADK, Gemini)      [process A, your terminal / adk web]
  -> A2A (HTTP JSON-RPC)
  -> Research Agent (ADK, Gemini)     [process B, uvicorn server, port 8001]
  -> research result
  -> Summary Agent
  -> final answer
```

## What ADK is doing

Both agents are ordinary **`google.adk.agents.llm_agent.Agent`** instances
backed by Gemini (`gemini-3.5-flash`). ADK handles the LLM call, the
tool-calling loop, and session/event bookkeeping for each agent. Nothing
about being "the remote one" or "the caller" is special-cased in the model
-- it's just a `name`, `description` and `instruction`.

## What A2A is doing

A2A is the transport that lets one agent call another **across a process
boundary**, the same way two microservices would talk over REST:

- `google.adk.a2a.utils.agent_to_a2a.to_a2a(...)` wraps the Research Agent
  in a Starlette app that exposes:
  - a JSON-RPC endpoint that accepts A2A `message/send` requests and runs
    the wrapped ADK agent,
  - the standard **Agent Card** at `/.well-known/agent-card.json` --
    metadata describing the agent's name, description, and how to reach it.
- `google.adk.agents.remote_a2a_agent.RemoteA2aAgent` is a client-side ADK
  agent that, given the Research Agent's Agent Card URL, fetches the card
  and sends real HTTP requests to it whenever it's invoked.

The Summary Agent never imports `research_agent`'s Python module. It only
knows an HTTP URL.

## The Research Agent (`research_agent/`)

- `agent.py` defines `root_agent`, a Gemini-backed `Agent` named
  `research_agent`. Its instruction tells it that it is **the remote
  specialist**: given a topic/question, it returns a structured brief
  (Overview / Key Points / Considerations) and explicitly states that it is
  the remote Research Agent.
- `server.py` loads `.env`, wraps `root_agent` with `to_a2a(...)`, and
  exposes the resulting Starlette app as `a2a_app` on `localhost:8001`.
  This is the process you start first -- it's a standalone A2A service with
  no knowledge of the Summary Agent.

## The Summary Agent (`summary_agent/`)

- `agent.py` defines `root_agent`, a Gemini-backed `Agent` named
  `summary_agent`. It builds a `RemoteA2aAgent` pointed at
  `http://localhost:8001/.well-known/agent-card.json` (the Research Agent's
  card) and wraps it with `AgentTool` so the model can call it like a tool
  named `research_agent`.
- Its instruction explicitly tells it: **whenever the user asks a research
  question, call the `research_agent` tool** (which sends the request over
  A2A to the remote agent), then **summarize the returned brief** in its own
  words for the user, and mention that the research came from the remote
  agent via A2A.

## Why A2A instead of a direct Python function call

- **Process isolation** -- the Research Agent can be developed, deployed,
  scaled, restarted, or owned by a different team entirely, independent of
  the Summary Agent. A function call can't do that; A2A can.
- **Language/framework agnostic** -- any A2A-compliant client could call the
  Research Agent, not just this specific ADK agent. Conversely the Summary
  Agent could call any A2A agent, ADK-based or not, by pointing at its card.
- **Standardized discovery** -- the Agent Card is a well-known, standard
  format, so the Summary Agent doesn't need hardcoded knowledge of the
  Research Agent's internals, only its URL.
- **This is the point of the exercise** -- Task 6 is specifically about
  demonstrating real ADK + A2A wiring (`to_a2a` / `RemoteA2aAgent`), which a
  same-process function call would only fake.

## Setup

From the `a2a_research_agents/` directory, with the project's virtual
environment active (adjust the path/activation for your shell):

```
pip install google-adk python-dotenv
```

`.env` (already present, **never commit or print it**) must contain:

```
GOOGLE_API_KEY=<your key>
```

`.gitignore` already excludes `.env`.

## Running the demo

**1) Start the Research Agent A2A server** (leave this running in its own
terminal):

```
cd a2a_research_agents
uvicorn research_agent.server:a2a_app --host localhost --port 8001
```

Verify its Agent Card is up (in another terminal):

```
curl http://localhost:8001/.well-known/agent-card.json
```

**2) Run the Summary Agent**, in a second terminal, from the same
`a2a_research_agents/` directory:

```
adk run summary_agent
```

(or `adk web` to use the ADK dev UI, then pick `summary_agent`.)

**Sample prompt** to type into the Summary Agent:

```
What is the A2A (Agent-to-Agent) protocol used for?
```

The Summary Agent will call the remote Research Agent over A2A, then reply
with its own summary of the research brief it got back.

## End-to-end automated test

`test_e2e.py` proves the whole chain works over real A2A, not a hallucinated
answer: it checks the Research Agent's Agent Card is reachable, runs the
Summary Agent through an ADK `InMemoryRunner`, and asserts that a
`research_agent` tool call and a matching tool response actually occurred
before the final summary is produced.

With the Research Agent server already running on port 8001:

```
cd a2a_research_agents
python test_e2e.py
```

## Architecture diagram

```
+-------------+        A2A (HTTP/JSON-RPC)        +-------------------+
|             |  ------------------------------->  |                   |
|   Summary   |   message/send: "research topic"   |     Research      |
|    Agent    |                                    |       Agent       |
| (port: n/a, |  <-------------------------------  | (Starlette/uvicorn|
|  CLI/adk    |   structured research brief text    |   on :8001, via   |
|    web)     |                                    |    to_a2a(...))   |
+-------------+                                    +-------------------+
      ^                                                       |
      | user question                     Agent Card served at
      |                                    /.well-known/agent-card.json
      |
   +------+
   | User |
   +------+
```
