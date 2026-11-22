"""Offline tests: no Azure needed. A fake Foundry backend replays each mistake,
then the grader and the analysis must catch it.

    pytest -q
"""
import json
import subprocess
import sys
from types import SimpleNamespace as NS

import pytest

from src import foundry, grade, pipeline
from src.run_experiment import load_testset

TQ = {q["id"]: q for q in load_testset()}


def resp(text="", items=(), rid="r1", tin=100, tout=20):
    return NS(id=rid, output_text=text, output=list(items), usage=NS(input_tokens=tin, output_tokens=tout))


def fake_backend(condition):
    """Behaves like the article: before = all three bugs, after = all three fixes."""
    def call_agent(agent, input, previous_response_id=None):
        if agent == "triage-agent":
            msg = input
            route = "policy" if any(w in msg.lower() for w in ("return them", "warranty", "express", "kosovo", "send stuff"))\
                and not any(ch.isdigit() for ch in msg[:20]) else "order"
            if msg.lower().startswith(("thanks", "hello", "can you help me write")):
                return resp(json.dumps({"route": "none", "summary": "", "reply": "Happy to help!"})), 0.1
            return resp(json.dumps({"route": route, "summary": "Customer is asking about a delayed order"})), 0.2
        if agent.startswith("policy"):
            items = [NS(type="file_search_call", queries=["return window"], results=[NS(filename="returns.md", text="30 days")])] \
                if condition == "after" else []
            return resp("Returns are accepted within 30 days.", items), 0.5
        # order agent
        if previous_response_id is None:
            import re
            ids = re.findall(r"\d{5}", input)
            oid = ids[0] if ids else ("99999" if condition == "before" else None)
            if oid is None:
                return resp("Could you share your order number?"), 0.3
            return resp("", [NS(type="function_call", name="get_order_status", arguments=json.dumps({"order_id": oid}), call_id="c1")]), 0.3
        out = input[0]["output"]
        if out == "Error":   # before: keeps knocking
            return resp("", [NS(type="function_call", name="get_order_status", arguments=json.dumps({"order_id": "48213"}), call_id="c2")],
                        rid=previous_response_id + "x"), 0.4
        return resp("Here is your update.", rid="final"), 0.3
    return call_agent


@pytest.mark.parametrize("condition", ["before", "after"])
def test_pipeline_runs_every_question(monkeypatch, condition):
    monkeypatch.setattr(foundry, "call_agent", fake_backend(condition))
    for q in TQ.values():
        r = pipeline.run_conversation(q, condition, 1)
        assert r["error"] is None, (q["id"], r["error"])
        grade.process_metrics(r, q)


def test_mistakes_are_detected(monkeypatch):
    out = {}
    for c in ("before", "after"):
        monkeypatch.setattr(foundry, "call_agent", fake_backend(c))
        out[c] = {qid: grade.process_metrics(pipeline.run_conversation(TQ[qid], c, 1), TQ[qid]) for qid in ("P01", "O01", "X01")}
    assert not out["before"]["P01"]["searched"] and out["after"]["P01"]["searched"]
    assert out["before"]["O01"]["invented_id"] and not out["after"]["O01"]["invented_id"]
    assert out["before"]["X01"]["looped"] and not out["after"]["X01"]["looped"]


def test_analysis_end_to_end(tmp_path, monkeypatch):
    rows = []
    for c in ("before", "after"):
        monkeypatch.setattr(foundry, "call_agent", fake_backend(c))
        for rep in (1, 2):
            for q in TQ.values():
                r = pipeline.run_conversation(q, c, rep)
                g = {**r, **grade.process_metrics(r, q), "answer_correct": c == "after", "judge_reason": "fake"}
                g["task_success"] = bool(g["process_ok"] and g["answer_correct"])
                rows.append(g)
    p = tmp_path / "x.graded.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    res = subprocess.run([sys.executable, "-m", "src.analyze", str(p), "--out", str(tmp_path / "paper")],
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "paper" / "table_main.md").exists()
    assert (tmp_path / "paper" / "fig_success.png").exists()
