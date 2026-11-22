"""Post-hoc Task Adherence rerun on F1 with full File Search results (CHANGELOG 2026-11-21, approved by Bojan).

The original evaluator input (src/evaluate_foundry.to_agent_messages) used the File Search excerpts our pipeline
recorded: the first 300 characters of the top 3 results (src/pipeline.py:67). Here the input is rebuilt with the full
File Search result text taken from the exported server-side spans (results/<arm>.spans.csv,
`execute_tool file_search.msearch`, attribute gen_ai.tool.call.result). Each logged search is matched to the span whose
arguments carry the same queries (the gpt-4.1-mini arm has extra file-search spans from HTTP 429 retries).
Everything else in the input (query, tool definitions, final answer) and the evaluator (same class, judge deployment,
reasoning-model settings) is unchanged.

    python -m src.v3_ta_rerun     -> results/paper/v3_checks/b1_ta_rerun.jsonl (+ cache, resumable), b1_ta_rerun.md
"""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from .evaluate_foundry import FILE_SEARCH_DEF, load_evaluators, summarize

OUT = Path("results/paper/v3_checks")
ARMS = (("main", "gpt-5-mini"), ("main_gpt41mini", "gpt-4.1-mini"))


def full_results(spans: pd.DataFrame, trace_id: str, logged: list) -> tuple[list, int]:
    s = spans[(spans.operation_Id == trace_id) & spans.name.str.startswith("execute_tool file_search")].sort_values("timestamp")
    cand = []
    for _, x in s.iterrows():
        try:
            q = json.loads(x["gen_ai.tool.call.arguments"]).get("queries")
        except Exception:  # noqa: BLE001
            q = None
        cand.append((q, str(x["gen_ai.tool.call.result"])))
    out, unmatched = [], 0
    for fs in logged:
        hits = [res for q, res in cand if q == fs.get("queries")]
        if hits:
            out.append(hits[-1])           # the last attempt with these queries is the one whose response was used
        else:
            unmatched += 1
            out.append(" ".join(fs.get("top_text") or []))
    return out, unmatched


def messages(r: dict, results: list):
    query = [{"role": "user", "content": [{"type": "text", "text": r["message"]}]}]
    response = []
    for n, (fs, full) in enumerate(zip(r.get("file_search", []), results), 1):
        cid = f"fs_{n}"
        response.append({"role": "assistant", "content": [{"type": "tool_call", "tool_call_id": cid, "name": "file_search",
                                                            "arguments": {"queries": fs.get("queries", [])}}]})
        response.append({"role": "tool", "tool_call_id": cid, "content": [{"type": "tool_result", "tool_result": full}]})
    response.append({"role": "assistant", "content": [{"type": "text", "text": r.get("answer") or ""}]})
    return query, response, [FILE_SEARCH_DEF]


def main():
    ta = load_evaluators()["task_adherence"][0]
    cache_p = OUT / "b1_ta_rerun.cache.jsonl"
    cache = {}
    if cache_p.exists():
        for l in cache_p.read_text().splitlines():
            c = json.loads(l)
            cache[(c["model"], c["qid"], c["condition"], c["rep"])] = c
    lock = threading.Lock()
    rows = []
    for stem, label in ARMS:
        g = pd.read_json(f"results/{stem}.graded.jsonl", lines=True)
        g = g[(g.scenario == "mistake1") & g.error.isna()]
        fe = pd.read_json(f"results/{stem}.foundry_eval.jsonl", lines=True)
        spans = pd.read_csv(f"results/{stem}.spans.csv", usecols=["operation_Id", "name", "timestamp",
                                                                   "gen_ai.tool.call.arguments", "gen_ai.tool.call.result"])

        def one(r):
            key = (label, r["qid"], r["condition"], r["rep"])
            if key in cache:
                return cache[key]
            res, unmatched = full_results(spans, r["trace_id"], r.get("file_search") or [])
            q, resp, defs = messages(r, res)
            old = fe[(fe.qid == r["qid"]) & (fe.condition == r["condition"]) & (fe.rep == r["rep"])].iloc[0]
            try:
                new = summarize("task_adherence", ta(query=q, response=resp, tool_definitions=defs))
                err = None
            except Exception as e:  # noqa: BLE001
                new, err = {}, f"{type(e).__name__}: {str(e)[:200]}"
            row = dict(model=label, qid=r["qid"], condition=r["condition"], rep=r["rep"], trace_id=r["trace_id"],
                       n_searches=len(res), unmatched_searches=unmatched, tool_result_chars=sum(len(x) for x in res),
                       judge_v2=bool(r["answer_correct"]), old_result=old.get("task_adherence_result"),
                       new_result=new.get("task_adherence_result"), new_reason=new.get("task_adherence_reason"), error=err)
            if err is None:
                with lock, cache_p.open("a") as fh:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            return row

        with ThreadPoolExecutor(max_workers=6) as ex:
            rows += list(ex.map(one, [r for _, r in g.iterrows()]))
        print(f"{label}: {len(g)} F1 runs re-evaluated", flush=True)
    df = pd.DataFrame(rows)
    df.drop(columns=["new_reason"]).to_csv(OUT / "b1_ta_rerun.csv", index=False)
    (OUT / "b1_ta_rerun.jsonl").write_text("\n".join(df.to_json(orient="records", lines=True).splitlines()) + "\n")
    hol = pd.read_csv(OUT / "b1_holiday_runs.csv")[["model", "qid", "condition", "rep"]].assign(holiday=True)
    df = df.merge(hol, on=["model", "qid", "condition", "rep"], how="left").fillna({"holiday": False})
    lines = ["# B1 rerun: Task Adherence on F1 with full File Search results\n",
             f"Runs: {len(df)}; errors: {int(df.error.notna().sum())}; logged searches not matched to a span: {int(df.unmatched_searches.sum())}.\n",
             "| Model | Condition | Runs | Old pass | New pass | Old fail | New fail | Judge v2 correct |", "|---|---|---|---|---|---|---|---|"]
    for (m, c), x in df.groupby(["model", "condition"], sort=False):
        lines.append(f"| {m} | {c} | {len(x)} | {int((x.old_result == 'pass').sum())} | {int((x.new_result == 'pass').sum())} | "
                     f"{int((x.old_result == 'fail').sum())} | {int((x.new_result == 'fail').sum())} | {int(x.judge_v2.sum())} |")
    h = df[df.holiday]
    lines += ["", f"The 53 runs whose answer mentions the holiday extension: old fail {int((h.old_result == 'fail').sum())}, "
              f"new fail {int((h.new_result == 'fail').sum())}.",
              f"Verdict changes overall: fail -> pass {int(((df.old_result == 'fail') & (df.new_result == 'pass')).sum())}, "
              f"pass -> fail {int(((df.old_result == 'pass') & (df.new_result == 'fail')).sum())}."]
    (OUT / "b1_ta_rerun.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
