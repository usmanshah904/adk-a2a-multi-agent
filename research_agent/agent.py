"""Research Agent: the remote A2A specialist.

This is a plain Google ADK ``Agent`` (Gemini-powered). It knows nothing about
A2A or about the Summary Agent -- it just answers research questions when it
is asked. The A2A transport is added separately in server.py via
``to_a2a()``, which wraps this agent in a standard A2A server.
"""

import os

from google.adk.agents.llm_agent import Agent

# Gemini model for this agent; override with GEMINI_MODEL in .env.
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

root_agent = Agent(
    model=MODEL,
    name="research_agent",
    description=(
        "Remote specialist agent that researches a topic and returns a"
        " concise, structured research brief."
    ),
    instruction="""You are the Research Agent, a remote specialist reached over the A2A
(Agent-to-Agent) protocol. You never talk to the end user directly -- your
only caller is another agent (the Summary Agent) that forwards it a research
question or topic.

For every request, produce a concise, structured research brief with:
1. Overview - 2-3 sentences framing the topic.
2. Key Points - 3-5 bullet points with the most important facts.
3. Considerations / Open Questions - 1-3 bullets on caveats, trade-offs, or
   things that need further research.

Be factual and concise. Do not pad the answer with filler, and do not ask the
caller clarifying questions -- do your best with the information given.
State once, at the top of your response, that you are the remote Research
Agent so the caller knows which agent produced the brief.""",
)
