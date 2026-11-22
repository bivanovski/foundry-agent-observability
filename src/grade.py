"""Grades every run in a results file.

Two kinds of grading, kept separate on purpose:
  process metrics   deterministic, read straight from the recorded run (did it search? which order id did it send?)
  answer_correct    LLM judge (JUDGE_MODEL at a fixed reasoning effort) against the ground truth in the test set

    python -m src.grade results/main.jsonl            -> results/main.graded.jsonl
    python -m src.grade results/main.jsonl --no-judge (process metrics only, free)
"""
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .config import DATA, JUDGE_MODEL, JUDGE_REASONING_EFFORT

JUDGE_PROMPT = """You are grading a customer support answer from an online electronics store's AI assistant.

Customer message:
<message>{message}</message>

What a correct answer does:
<expected_behavior>{behavior}</expected_behavior>

Facts a correct answer must state or be consistent with:
<facts>
{facts}
</facts>

The store's complete policy documents (the only source of truth for store policy):
<policy_documents>
{policies}
</policy_documents>

The assistant's final answer:
<answer>{answer}</answer>

Grading rules:
- The answer is correct only if it does what the expected behavior says and does not contradict any listed fact or the policy documents.
- Wording does not matter. Extra helpful detail is fine if it is in the policy documents. Made-up rules, numbers, order statuses or promises are not.
- An answer that invents an order status, a return reference, or a policy rule that is in neither the facts nor the policy documents is incorrect.
- An empty answer is incorrect.

Reply with JSON only: {{"correct": true or false, "reason": "<one sentence>"}}"""


def load_testset():
    return {q["id"]: q for q in (json.loads(l) for l in (DATA / "testset.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}


def process_metrics(r: dict, q: dict) -> dict:
    msg_ids = set(re.findall(r"\d{5}", q["message"]))
    calls = r.get("tool_calls", [])
    ids_used = [str(c["args"].get("order_id", "")).lstrip("#") for c in calls]
    m = dict(
        route_ok=r.get("route") == q["expected_route"],
        searched=r.get("n_file_search_calls", 0) > 0,
        n_tool_calls=len(calls),
        invented_id=any(i and i not in msg_ids for i in ids_used),
        used_expected_id=bool(q.get("expected_order_id")) and q["expected_order_id"] in ids_used,
        expected_tool_called=bool(q.get("expected_tool")) and any(c["name"] == q["expected_tool"] for c in calls),
        id_in_handoff=(q.get("expected_order_id") or "") in (r.get("handoff") or "") if q.get("expected_order_id") else None,
        same_call_repeats=max([sum(1 for d in calls if d["name"] == c["name"] and d["args"] == c["args"]) for c in calls] or [0]),
        hit_cap=r.get("hit_cap", False),
    )
    # Pre-registered additions (CHANGELOG 2026-11-16, "metrics v2"):
    ans = r.get("answer") or ""
    exp_id = q.get("expected_order_id")
    # any tool call with an id other than the expected one (catches decoys from the message, e.g. a postcode)
    m["wrong_id"] = any(i != (exp_id or "") for i in ids_used) if ids_used else False
    m["id_missing_from_handoff"] = (not m["id_in_handoff"]) if m["id_in_handoff"] is not None else None
    # no-ID items: did the agent ask for the order number (heuristic, deterministic)
    m["asked_for_id"] = bool(re.search(r"order\s*(number|no\.?|id|#|reference)", ans, re.I)) and "?" in ans
    # outage items: separate check for the email follow-up only the `after` error text suggests
    m["offered_email"] = bool(re.search(r"\be-?mail", ans, re.I))
    m["n_identical_calls"] = m["same_call_repeats"]
    # Exploratory, added post hoc (CHANGELOG 2026-11-17 "M3 manifests differently per model"): the agent asks the
    # customer to confirm / re-provide an order number although the customer already gave a valid one.
    m["asked_to_confirm_id"] = bool(exp_id) and bool(re.search(
        r"(confirm|double.?check|verify|re-?enter|provide)\b[^.?!]{0,60}\border\s*(number|id|no\.?|#)", ans, re.I))
    cat = q["category"]
    if q["expected_route"] == "policy":
        ok = m["route_ok"] and m["searched"]
    elif cat in ("order_id", "order_return", "routine") and q["expected_route"] == "order":
        ok = (m["route_ok"] and m["expected_tool_called"] and m["used_expected_id"] and not m["invented_id"]
              and not m["wrong_id"])
    elif cat == "order_noid":
        ok = m["route_ok"] and m["n_tool_calls"] == 0
    elif cat == "outage":
        ok = m["route_ok"] and m["same_call_repeats"] <= 2 and not m["hit_cap"] and not m["invented_id"]
    else:  # route none
        ok = m["route_ok"] and m["n_tool_calls"] == 0
    m["process_ok"] = bool(ok)
    m["looped"] = m["same_call_repeats"] >= 3 or m["hit_cap"]
    return m


def policy_documents() -> str:
    """The same documents the policy agent searches, so the judge can tell grounded detail from invented detail."""
    return "\n\n".join(f'<document name="{f.name}">\n{f.read_text(encoding="utf-8").strip()}\n</document>'
                       for f in sorted((DATA / "policies").glob("*.md")))


def judge(r: dict, q: dict) -> dict:
    from . import foundry
    if r.get("error") or not (r.get("answer") or "").strip():
        return {"answer_correct": False, "judge_reason": "error or empty answer"}
    prompt = JUDGE_PROMPT.format(message=q["message"], behavior=q["expected_behavior"],
                                 facts="\n".join(f"- {f}" for f in q["expected_facts"]) or "- (none)",
                                 policies=policy_documents(), answer=r["answer"])
    text = foundry.call_model(JUDGE_MODEL, prompt, JUDGE_REASONING_EFFORT)
    mm = re.search(r"\{.*\}", text or "", flags=re.S)
    try:
        d = json.loads(mm.group(0))
        return {"answer_correct": bool(d["correct"]), "judge_reason": d.get("reason", "")}
    except Exception:  # noqa: BLE001
        return {"answer_correct": None, "judge_reason": f"unparseable judge output: {text[:200]}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    tq = load_testset()
    src = Path(a.results)
    rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    # keep the last successful record per (qid, condition, rep)
    latest = {}
    for r in rows:
        k = (r["qid"], r["condition"], r["rep"])
        if k not in latest or not r.get("error"):
            latest[k] = r
    rows = list(latest.values())

    # Judge verdicts are cached as they arrive (one line per verdict), so an interrupted grading run resumes
    # without paying for the same answer twice. The cache is keyed by run and answer text.
    import hashlib
    import threading
    cache_path = src.with_suffix(".judge_cache.jsonl")
    cache = {}
    if cache_path.exists():
        for l in cache_path.read_text(encoding="utf-8").splitlines():
            if l.strip():
                c = json.loads(l)
                cache[c["key"]] = c
    lock = threading.Lock()

    def key_of(r):
        h = hashlib.sha1((r.get("answer") or "").encode()).hexdigest()[:12]
        return f'{r["qid"]}|{r["condition"]}|{r["rep"]}|{h}'

    def grade_one(r):
        q = tq[r["qid"]]
        g = {**r, **process_metrics(r, q)}
        if not a.no_judge:
            k = key_of(r)
            if k in cache:
                g.update(answer_correct=cache[k]["answer_correct"], judge_reason=cache[k]["judge_reason"])
            else:
                try:
                    v = judge(r, q)
                except Exception as e:  # noqa: BLE001  (e.g. 429 after all retries): no verdict, retried next run
                    v = {"answer_correct": None, "judge_reason": f"judge error: {type(e).__name__}: {str(e)[:150]}"}
                g.update(v)
                if v["answer_correct"] is not None:
                    with lock, cache_path.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps({"key": k, **v}, ensure_ascii=False) + "\n")
        g["task_success"] = bool(g["process_ok"] and g.get("answer_correct"))
        return g

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        graded = list(ex.map(grade_one, rows))

    out = src.with_suffix(".graded.jsonl")
    out.write_text("\n".join(json.dumps(g, ensure_ascii=False) for g in graded) + "\n", encoding="utf-8")
    missing = sum(1 for g in graded if g.get("answer_correct") is None) if not a.no_judge else 0
    print(f"Graded {len(graded)} runs -> {out}" + (f"  ({missing} without a judge verdict: re-run the same command)" if missing else ""))


if __name__ == "__main__":
    main()
