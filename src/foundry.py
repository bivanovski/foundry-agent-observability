"""Every call into the Foundry SDK goes through this file.

The Foundry SDKs moved fast in 2025-2026. If a call here fails because a
name or parameter changed, fix it HERE and nowhere else. Written against
azure-ai-projects 2.x (new Foundry agents: create_version + Responses API).
"""
import json
import time
from functools import lru_cache

from azure.identity import DefaultAzureCredential

from .config import PROJECT_ENDPOINT, STATE_FILE


@lru_cache
def credential():
    return DefaultAzureCredential()


@lru_cache
def project_client():
    from azure.ai.projects import AIProjectClient
    if not PROJECT_ENDPOINT:
        raise SystemExit("PROJECT_ENDPOINT is empty. Run infra/deploy.sh first (it writes .env).")
    return AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential())


@lru_cache
def openai_client():
    """OpenAI-compatible client scoped to the Foundry project (Responses API, vector stores)."""
    return project_client().get_openai_client()


def load_state() -> dict:
    if not STATE_FILE.exists():
        raise SystemExit(".state.json missing. Run: python -m src.setup_resources")
    return json.loads(STATE_FILE.read_text())


def create_prompt_agent(name: str, model: str, instructions: str, tools: list | None = None):
    """Creates (or adds a new version of) a prompt agent. Returns the agent version object."""
    from azure.ai.projects.models import PromptAgentDefinition
    definition = PromptAgentDefinition(model=model, instructions=instructions, tools=tools or [])
    return project_client().agents.create_version(agent_name=name, definition=definition)


def file_search_tool(vector_store_id: str):
    from azure.ai.projects.models import FileSearchTool
    return FileSearchTool(vector_store_ids=[vector_store_id])


def function_tools(defs: list[dict]):
    from azure.ai.projects.models import FunctionTool
    return [FunctionTool(name=d["name"], description=d["description"], parameters=d["parameters"], strict=True)
            for d in defs]


def call_agent(agent: str, input, previous_response_id: str | None = None, retries: int = 6):
    """One Responses API call against a named agent. Retries on throttling.

    `input` is either a string or a list of input items (function_call_output).
    Returns (response, seconds).
    """
    kwargs = dict(
        input=input,
        extra_body={"agent_reference": {"name": agent, "type": "agent_reference"}},
        include=["file_search_call.results"],
    )
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id
    delay = 4
    for attempt in range(retries):
        t0 = time.perf_counter()
        try:
            resp = openai_client().responses.create(**kwargs)
            return resp, time.perf_counter() - t0
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if attempt < retries - 1 and any(s in msg for s in ("429", "rate", "Rate", "timeout", "503", "502")):
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise


def call_model(model: str, prompt: str, reasoning_effort: str | None = None, retries: int = 12,
               temperature: float | None = None) -> str:
    """Plain model call (no agent) for the LLM judge. gpt-5-mini is a reasoning model and rejects
    `temperature`, so consistency comes from a fixed reasoning effort and a strict JSON rubric."""
    delay = 4
    kwargs = dict(model=model, input=prompt)
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    if temperature is not None:  # only for non-reasoning models (the second judge, gpt-4.1-mini)
        kwargs["temperature"] = temperature
    for attempt in range(retries):
        try:
            resp = openai_client().responses.create(**kwargs)
            return resp.output_text
        except Exception as e:  # noqa: BLE001
            if attempt < retries - 1 and any(s in str(e) for s in ("429", "rate", "Rate", "timeout", "503", "502")):
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise


def app_insights_connection_string() -> str | None:
    try:
        return project_client().telemetry.get_application_insights_connection_string()
    except Exception as e:  # noqa: BLE001
        print(f"[telemetry] Could not get App Insights connection string: {e}")
        return None
