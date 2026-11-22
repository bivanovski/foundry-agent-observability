"""Judge v3: post-hoc sensitivity grader (CHANGELOG 2026-11-17, "judge v3").

Judge v2 (src/grade.py, pre-registered) sees the expected behaviour, the expected facts and the policy documents.
It does NOT see what the agent saw from its tools, so grounded details were graded as invented: the order-ID format
from the tool definition, statuses and next steps from tool results, and dates relative to the fixed date.
Judge v3 additionally receives the tool definitions, every tool call with its result, and the fixed date.

v3 never replaces v2: verdicts go to a separate file and both are reported. Same model, deployment and reasoning
effort as v2.

    python -m src.judge_v3 results/main.graded.jsonl   -> results/main.judge3.jsonl  (resumable cache)
"""
import argparse
import hashlib
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import foundry
from .config import JUDGE_MODEL, JUDGE_REASONING_EFFORT, TODAY
from .grade import load_testset, policy_documents
from .tools import TOOL_DEFINITIONS

JUDGE_PROMPT_V3 = """You are grading a customer support answer from an online electronics store's AI assistant.

Today's date in this store is {today}. Judge every date and relative time expression ("tomorrow", "two days from now") against this date.

Customer message:
<message>{message}</message>

What a correct answer does:
<expected_behavior>{behavior}</expected_behavior>

Facts a correct answer must state or be consistent with:
<facts>
{facts}
</facts>

The store's complete policy documents:
<policy_documents>
{policies}
</policy_documents>

The tools the assistant could use, with their descriptions (part of the system the assistant runs in):
<tool_definitions>
{tools}
</tool_definitions>

What the assistant's tools returned in this conversation, in order:
<tool_results>
{tool_log}
</tool_results>

The assistant's final answer:
<answer>{answer}</answer>

Grading rules:
- The answer is correct only if it does what the expected behavior says and does not contradict any listed fact, the policy documents or the tool results.
- Details taken from the policy documents, the tool definitions or the tool results are grounded, not invented. Quoting a status or next step that a tool returned is correct.
- Wording does not matter. An answer is incorrect if it invents an order status, a return reference, a policy rule, a number, a date or a promise that appears in none of the facts, policy documents, tool definitions or tool results.
- An empty answer is incorrect.

Reply with JSON only: {{"correct": true or false, "reason": "<one sentence>"}}"""

FILE_SEARCH_DESC = {"name": "file_search", "description": "Search the store's policy documents."}


def tools_text() -> str:
    defs = [FILE_SEARCH_DESC] + [{"name": d["name"], "description": d["description"],
                                  "parameters": d["parameters"]} for d in TOOL_DEFINITIONS]
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in defs)


def tool_log(r: dict) -> str:
    lines = []
    for fs in r.get("file_search") or []:
        lines.append(f"file_search(queries={json.dumps(fs.get('queries', []), ensure_ascii=False)}) -> "
                     f"returned passages from: {', '.join(sorted(set(f for f in fs.get('files', []) if f)))}")
    for tc in r.get("tool_calls") or []:
        lines.append(f"{tc['name']}({json.dumps(tc['args'], ensure_ascii=False)}) -> {str(tc['output'])[:1200]}")
    return "\n".join(lines) or "(the assistant called no tools)"


def judge3(r: dict, q: dict) -> dict:
    if r.get("error") or not (r.get("answer") or "").strip():
        return {"answer_correct_v3": False, "judge_v3_reason": "error or empty answer"}
    prompt = JUDGE_PROMPT_V3.format(today=TODAY, message=q["message"], behavior=q["expected_behavior"],
                                    facts="\n".join(f"- {f}" for f in q["expected_facts"]) or "- (none)",
                                    policies=policy_documents(), tools=tools_text(), tool_log=tool_log(r),
                                    answer=r["answer"])
    text = foundry.call_model(JUDGE_MODEL, prompt, JUDGE_REASONING_EFFORT)
    m = re.search(r"\{.*\}", text or "", flags=re.S)
    try:
        d = json.loads(m.group(0))
        return {"answer_correct_v3": bool(d["correct"]), "judge_v3_reason": d.get("reason", "")}
    except Exception:  # noqa: BLE001
        return {"answer_correct_v3": None, "judge_v3_reason": f"unparseable judge output: {(text or '')[:200]}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("graded")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", nargs="*", help="qid:condition:rep keys, for spot checks")
    a = ap.parse_args()
    src = Path(a.graded)
    stem = src.name.replace(".graded.jsonl", "").replace(".jsonl", "")
    rows = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if not r.get("error")]
    if a.only:
        want = {tuple(k.split(":")) for k in a.only}
        rows = [r for r in rows if (r["qid"], r["condition"], str(r["rep"])) in want]
    tq = load_testset()
    cache_path = src.parent / f"{stem}.judge3_cache.jsonl"
    cache = {}
    if cache_path.exists():
        for l in cache_path.read_text().splitlines():
            if l.strip():
                c = json.loads(l)
                cache[c["key"]] = c
    lock = threading.Lock()

    def one(r):
        k = f'{r["qid"]}|{r["condition"]}|{r["rep"]}|{hashlib.sha1((r.get("answer") or "").encode()).hexdigest()[:12]}'
        base = {"qid": r["qid"], "condition": r["condition"], "rep": r["rep"]}
        if k in cache:
            return {**base, "answer_correct_v3": cache[k]["answer_correct_v3"], "judge_v3_reason": cache[k]["judge_v3_reason"]}
        try:
            v = judge3(r, tq[r["qid"]])
        except Exception as e:  # noqa: BLE001
            v = {"answer_correct_v3": None, "judge_v3_reason": f"judge error: {type(e).__name__}: {str(e)[:150]}"}
        if v["answer_correct_v3"] is not None:
            with lock, cache_path.open("a") as fh:
                fh.write(json.dumps({"key": k, **v}, ensure_ascii=False) + "\n")
        return {**base, **v}

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        res = list(ex.map(one, rows))
    missing = sum(1 for x in res if x["answer_correct_v3"] is None)
    if a.only:
        for x in res:
            print(x)
        return
    out = src.parent / f"{stem}.judge3.jsonl"
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in res) + "\n")
    print(f"Judge v3 on {len(res)} answers -> {out}" + (f"  ({missing} without a verdict: re-run the same command)" if missing else ""))


if __name__ == "__main__":
    main()
