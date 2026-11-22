"""Runs one customer conversation through the support desk and records
everything the paper needs: route, tool calls with arguments, file search
usage, tokens, latency per step, and the trace id."""
import json
import re
import time
from datetime import datetime, timezone

from . import foundry, telemetry
from .config import MAX_TOOL_ROUNDS, agent_name, handoff_message
from .tools import run_tool


def _items(resp):
    return list(getattr(resp, "output", None) or [])


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _usage(resp):
    u = getattr(resp, "usage", None)
    return (_get(u, "input_tokens", 0) or 0, _get(u, "output_tokens", 0) or 0) if u else (0, 0)


def _parse_triage(text: str) -> dict:
    t = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", t, flags=re.S)
    try:
        d = json.loads(m.group(0) if m else t)
    except Exception:  # noqa: BLE001
        return {"route": "none", "summary": "", "reply": text, "parse_error": True}
    if d.get("route") not in ("order", "policy", "none"):
        d["route"] = "none"
    return d


def run_conversation(q: dict, condition: str, rep: int) -> dict:
    rec = dict(qid=q["id"], condition=condition, rep=rep, scenario=q["scenario"], category=q["category"],
               message=q["message"], started_at=datetime.now(timezone.utc).isoformat(),
               steps=[], tool_calls=[], file_search=[], n_model_calls=0, input_tokens=0, output_tokens=0,
               hit_cap=False, error=None)
    system_down = q["order_system"] == "down"
    t_start = time.perf_counter()

    def account(step, agent, resp, secs):
        i, o = _usage(resp)
        rec["n_model_calls"] += 1
        rec["input_tokens"] += i
        rec["output_tokens"] += o
        u = getattr(resp, "usage", None)
        reasoning_tokens = _get(_get(u, "output_tokens_details"), "reasoning_tokens") if u else None
        effort = _get(getattr(resp, "reasoning", None), "effort")
        rec["steps"].append(dict(step=step, agent=agent, seconds=round(secs, 3), input_tokens=i, output_tokens=o,
                                 reasoning_tokens=reasoning_tokens, reasoning_effort=effort,
                                 model=getattr(resp, "model", None), response_id=getattr(resp, "id", None)))
        for it in _items(resp):
            if _get(it, "type") == "file_search_call":
                results = _get(it, "results") or []
                rec["file_search"].append(dict(
                    agent=agent,
                    queries=list(_get(it, "queries") or []),
                    files=[_get(r, "filename") for r in results],
                    top_text=[(_get(r, "text") or "")[:300] for r in results[:3]],
                ))

    with telemetry.span("invoke_workflow support-desk", **{
            "experiment.qid": q["id"], "experiment.condition": condition, "experiment.rep": rep,
            "experiment.scenario": q["scenario"], "experiment.order_system": q["order_system"]}) as root:
        rec["trace_id"] = telemetry.current_trace_id()
        try:
            # 1) Triage
            triage = agent_name("triage")
            with telemetry.span(f"invoke_agent {triage}", **{"gen_ai.operation.name": "invoke_agent",
                                                              "gen_ai.agent.name": triage}) as s:
                resp, secs = foundry.call_agent(triage, q["message"])
                i, o = _usage(resp)
                s.set_attribute("gen_ai.usage.input_tokens", i)
                s.set_attribute("gen_ai.usage.output_tokens", o)
            account("triage", triage, resp, secs)
            t = _parse_triage(resp.output_text)
            rec["route"] = t["route"]
            rec["triage_summary"] = t.get("summary", "")
            rec["triage_parse_error"] = bool(t.get("parse_error"))

            if t["route"] == "none":
                rec["answer"] = t.get("reply") or ""
            else:
                # 2) Handoff to the specialist
                spec = agent_name(t["route"], condition)
                handoff = handoff_message(condition, t.get("summary", ""), q["message"])
                rec["handoff"] = handoff
                rec["specialist"] = spec
                with telemetry.span(f"invoke_agent {spec}", **{"gen_ai.operation.name": "invoke_agent",
                                                               "gen_ai.agent.name": spec,
                                                               "experiment.handoff": handoff}) as spec_span:
                    tok0 = (rec["input_tokens"], rec["output_tokens"])
                    resp, secs = foundry.call_agent(spec, handoff)
                    account("specialist", spec, resp, secs)
                    # 3) Client-side function tool loop (order agent)
                    for rnd in range(MAX_TOOL_ROUNDS + 1):
                        calls = [it for it in _items(resp) if _get(it, "type") == "function_call"]
                        if not calls:
                            break
                        if rnd == MAX_TOOL_ROUNDS:
                            rec["hit_cap"] = True
                            break
                        outputs = []
                        for c in calls:
                            name = _get(c, "name")
                            raw = _get(c, "arguments") or "{}"
                            try:
                                args = json.loads(raw)
                            except Exception:  # noqa: BLE001
                                args = {"_raw": raw}
                            with telemetry.span(f"execute_tool {name}", **{
                                    "gen_ai.operation.name": "execute_tool", "gen_ai.agent.name": spec,
                                    "gen_ai.tool.type": "function",
                                    "gen_ai.tool.name": name, "gen_ai.tool.call.arguments": json.dumps(args),
                                    "gen_ai.tool.call.id": _get(c, "call_id")}) as ts:
                                out = run_tool(name, args, condition, system_down)
                                ts.set_attribute("gen_ai.tool.call.result", out)
                            rec["tool_calls"].append(dict(round=rnd, name=name, args=args, output=out))
                            outputs.append({"type": "function_call_output", "call_id": _get(c, "call_id"), "output": out})
                        resp, secs = foundry.call_agent(spec, outputs, previous_response_id=resp.id)
                        account(f"specialist_round_{rnd + 1}", spec, resp, secs)
                    spec_span.set_attribute("gen_ai.usage.input_tokens", rec["input_tokens"] - tok0[0])
                    spec_span.set_attribute("gen_ai.usage.output_tokens", rec["output_tokens"] - tok0[1])
                rec["answer"] = resp.output_text or ""
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"{type(e).__name__}: {e}"
            root.set_attribute("error.type", type(e).__name__)

    rec["latency_s"] = round(time.perf_counter() - t_start, 3)
    rec["n_tool_calls"] = len(rec["tool_calls"])
    rec["n_file_search_calls"] = len(rec["file_search"])
    return rec
