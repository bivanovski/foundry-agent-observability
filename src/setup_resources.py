"""Uploads the policy documents to a vector store and creates the agents.

    python -m src.setup_resources

Creates 5 agents in the Foundry project:
  triage-agent                (shared by both conditions)
  policy-agent-before / -after
  order-agent-before  / -after
and writes their names and versions to .state.json.
"""
import json
import sys

from . import foundry
from .config import (AGENT_MODEL, CONDITIONS, DATA, ORDER_INSTRUCTIONS, POLICY_INSTRUCTIONS, STATE_FILE,
                     TRIAGE_INSTRUCTIONS, agent_name)
from .tools import TOOL_DEFINITIONS


def main():
    oa = foundry.openai_client()

    print("Uploading policy documents...")
    vs = oa.vector_stores.create(name="voltcart-policies")
    files = sorted((DATA / "policies").glob("*.md"))
    for f in files:
        with f.open("rb") as fh:
            oa.vector_stores.files.upload_and_poll(vector_store_id=vs.id, file=fh)
        print(f"  {f.name}")

    state = {"vector_store_id": vs.id, "agent_model": AGENT_MODEL, "agents": {}}

    def make(name, instructions, tools=None):
        a = foundry.create_prompt_agent(name, AGENT_MODEL, instructions, tools)
        state["agents"][name] = {"name": a.name, "version": getattr(a, "version", None), "instructions": instructions}
        print(f"  {name} v{getattr(a, 'version', '?')}")

    print("Creating agents...")
    make(agent_name("triage"), TRIAGE_INSTRUCTIONS)
    for c in CONDITIONS:
        make(agent_name("policy", c), POLICY_INSTRUCTIONS[c], [foundry.file_search_tool(vs.id)])
        make(agent_name("order", c), ORDER_INSTRUCTIONS[c], foundry.function_tools(TOOL_DEFINITIONS))

    STATE_FILE.write_text(json.dumps(state, indent=2))
    print(f"Wrote {STATE_FILE}")


if __name__ == "__main__":
    sys.exit(main())
