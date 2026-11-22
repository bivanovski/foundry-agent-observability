"""Experiment configuration. Everything that defines a condition lives here,
so the paper's Method section can be written from this one file."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT", "")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
AGENT_MODEL = os.environ.get("AGENT_MODEL_DEPLOYMENT", "gpt-5-mini-agent")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL_DEPLOYMENT", "gpt-5-mini-judge")
# gpt-5-mini is a reasoning model: no temperature. The judge runs at a fixed reasoning effort instead,
# and the agents keep the model default (record it in the paper).
JUDGE_REASONING_EFFORT = os.environ.get("JUDGE_REASONING_EFFORT", "medium")

DATA = ROOT / "data"
RESULTS = ROOT / "results"
# Model comparison arms (CHANGELOG 2026-11-16): AGENT_TAG names a separate agent set for another agent model.
# Unset = the main gpt-5-mini arm, unchanged.
AGENT_TAG = os.environ.get("AGENT_TAG", "").strip()
STATE_FILE = ROOT / (f".state.{AGENT_TAG}.json" if AGENT_TAG else ".state.json")   # written by setup_resources.py

STORE = "VoltCart"
TODAY = "19 November 2026"          # fixed so order statuses read the same in every run
MAX_TOOL_ROUNDS = 8                 # safety cap on the client loop; hitting it is recorded as a runaway loop
CONDITIONS = ("before", "after")

# ---------------------------------------------------------------------------
# Agent instructions. "before" carries the three bugs from the article,
# "after" carries the three fixes. Triage is identical in both conditions.
# ---------------------------------------------------------------------------

TRIAGE_INSTRUCTIONS = f"""You are the triage agent for {STORE}, an online electronics store.
Read the customer's message and decide who should handle it.

Reply with a single JSON object and nothing else:
{{"route": "order" | "policy" | "none", "summary": "<one sentence describing what the customer needs>", "reply": "<only when route is none: a short friendly reply>"}}

Use "order" for anything about one specific order: where it is, its status, or starting a return for it.
Use "policy" for general questions about returns, refunds, warranty, shipping or prices.
Use "none" for greetings, thanks, and anything that is not customer support for {STORE}."""

POLICY_INSTRUCTIONS = {
    "before": f"""You are the policy agent for {STORE}. Today's date is {TODAY}.
Answer customer questions about returns, refunds, warranty, shipping and prices.
You can use the policy documents to help answer questions.
Be friendly and concise.""",
    "after": f"""You are the policy agent for {STORE}. Today's date is {TODAY}.
Answer customer questions about returns, refunds, warranty, shipping and prices.
Always search the policy documents before answering any question about returns, refunds, warranty, shipping or prices.
Base your answer only on what the documents say. If the documents don't cover the question, say so and offer to connect the customer with a colleague.
Be friendly and concise.""",
}

ORDER_INSTRUCTIONS = {
    "before": f"""You are the order agent for {STORE}. Today's date is {TODAY}.
Help customers with their orders. Use get_order_status to look up an order and create_return to start a return.
Be friendly and concise.""",
    "after": f"""You are the order agent for {STORE}. Today's date is {TODAY}.
Help customers with their orders. Use get_order_status to look up an order and create_return to start a return.
Only use an order ID that appears in the customer's original message. If there is no order ID, ask the customer for it and do not call any tool. Never guess or invent an order ID.
If a tool says the order system is unavailable, do not retry. Apologise and offer to email the customer when it is back.
Never call the same tool with the same arguments more than twice.
Be friendly and concise.""",
}

# Tool error returned when the order system is down.
TOOL_ERROR = {
    "before": "Error",
    "after": "The order system is temporarily unavailable. Do not retry. Apologise and offer to email the customer when it's back.",
}


def handoff_message(condition: str, summary: str, original: str) -> str:
    """Mistake 2. Before: the specialist only gets triage's summary. After: it also gets the original message."""
    if condition == "before":
        return f"Handoff from the triage agent: {summary}"
    return f"Handoff from the triage agent: {summary}\n\nCustomer's original message:\n{original}"


def agent_name(role: str, condition: str | None = None) -> str:
    base = f"{role}-agent" if condition is None else f"{role}-agent-{condition}"
    return f"{base}-{AGENT_TAG}" if AGENT_TAG else base
