"""Re-judges answers with a second model from another generation (self-preference check).

The judge prompt is identical to src/grade.py (judge v2, with policy documents). gpt-4.1-mini is not a
reasoning model, so it runs at temperature 0 instead of a fixed reasoning effort.

    python -m src.second_judge results/main.graded.jsonl --keys results/audit/audit_key.csv
        -> results/main.judge2.jsonl  (only the audited rows, unless --all)
"""
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from . import foundry
from .grade import JUDGE_PROMPT, load_testset, policy_documents

JUDGE2_MODEL = "gpt-4.1-mini-judge2"   # deployment name; model gpt-4.1-mini 2025-04-14


def judge2(r: dict, q: dict) -> dict:
    if r.get("error") or not (r.get("answer") or "").strip():
        return {"answer_correct_judge2": False, "judge2_reason": "error or empty answer"}
    prompt = JUDGE_PROMPT.format(message=q["message"], behavior=q["expected_behavior"],
                                 facts="\n".join(f"- {f}" for f in q["expected_facts"]) or "- (none)",
                                 policies=policy_documents(), answer=r["answer"])
    text = foundry.call_model(JUDGE2_MODEL, prompt, temperature=0)
    m = re.search(r"\{.*\}", text or "", flags=re.S)
    try:
        d = json.loads(m.group(0))
        return {"answer_correct_judge2": bool(d["correct"]), "judge2_reason": d.get("reason", "")}
    except Exception:  # noqa: BLE001
        return {"answer_correct_judge2": None, "judge2_reason": f"unparseable: {(text or '')[:200]}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("graded")
    ap.add_argument("--keys", help="audit_key.csv: only re-judge these (qid, condition, rep)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    src = Path(a.graded)
    rows = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if not r.get("error")]
    if a.keys and not a.all:
        k = pd.read_csv(a.keys)
        want = set(zip(k.qid, k.condition, k.rep))
        rows = [r for r in rows if (r["qid"], r["condition"], r["rep"]) in want]
    tq = load_testset()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        res = list(ex.map(lambda r: {"qid": r["qid"], "condition": r["condition"], "rep": r["rep"],
                                     **judge2(r, tq[r["qid"]])}, rows))
    out = src.parent / (src.name.replace(".graded.jsonl", "") + ".judge2.jsonl")
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in res) + "\n")
    print(f"Second judge ({JUDGE2_MODEL}) on {len(res)} answers -> {out}")


if __name__ == "__main__":
    main()
