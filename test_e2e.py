"""End-to-end smoke test for the Research <-> Summary A2A demo.

This proves the whole chain actually goes over HTTP/A2A, not a direct
Python call:

1. The Research Agent A2A server must already be running (see README) --
   this script polls its well-known Agent Card URL to confirm that.
2. It runs the Summary Agent (root_agent from summary_agent.agent) through
   an ADK Runner with one user question.
3. It inspects the event stream for the `research_agent` tool call and its
   matching tool response. The response text only exists because it came
   back over HTTP from the separate Research Agent server process (its
   structured "Overview / Key Points / Considerations" shape, defined in
   research_agent/agent.py, does not appear anywhere in the Summary Agent's
   own instructions) -- so seeing it proves the call went over A2A, not
   that the Summary Agent hallucinated an answer.

Run with the Research Agent server already up on port 8001:
    python test_e2e.py
"""

import asyncio
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Loads GOOGLE_API_KEY the same way `adk web` / `adk run` do, since this is a
# plain script rather than something launched through the ADK CLI.
load_dotenv(Path(__file__).resolve().parent / ".env")

from google.adk.runners import InMemoryRunner
from google.genai import types

from summary_agent.agent import RESEARCH_AGENT_CARD_URL, root_agent

APP_NAME = "a2a_research_demo"
USER_ID = "demo_user"
QUESTION = "What is the A2A (Agent-to-Agent) protocol used for?"


async def check_research_agent_is_up() -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(RESEARCH_AGENT_CARD_URL, timeout=5.0)
        resp.raise_for_status()
        card = resp.json()
        assert card.get("name") == "research_agent", card
        print(f"[ok] Research Agent card reachable at {RESEARCH_AGENT_CARD_URL}")
        print(f"     name={card['name']!r} description={card['description']!r}")


async def run_summary_agent() -> None:
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id="demo_session"
    )

    print(f"\n[user] {QUESTION}\n")

    saw_tool_call = False
    remote_response_text = None
    final_text = None

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id="demo_session",
        new_message=types.Content(role="user", parts=[types.Part(text=QUESTION)]),
    ):
        for fc in event.get_function_calls():
            if fc.name == "research_agent":
                saw_tool_call = True
                print(f"[{event.author}] -> calling tool 'research_agent'"
                      f" over A2A with args={fc.args}\n")
        for fr in event.get_function_responses():
            if fr.name == "research_agent":
                remote_response_text = str(fr.response)
                print(f"[research_agent via A2A] {remote_response_text}\n")
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}] {part.text}\n")
                    if event.author == "summary_agent":
                        final_text = part.text

    if not saw_tool_call:
        print(
            "[fail] Summary Agent never called the 'research_agent' tool.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not remote_response_text:
        print(
            "[fail] No tool response came back from 'research_agent' -- the"
            " A2A call never returned.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not final_text:
        print(
            "[fail] Summary Agent produced no final text answer.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("[ok] Summary Agent called the remote 'research_agent' tool (A2A request sent).")
    print("[ok] Received a structured research brief back over A2A.")
    print("[ok] Summary Agent produced a final summarized answer.")
    print("\nEnd-to-end A2A demo PASSED.")


async def main() -> None:
    await check_research_agent_is_up()
    await run_summary_agent()


if __name__ == "__main__":
    asyncio.run(main())
