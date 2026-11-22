"""A2 summary: what each detector found on the post-hoc positive controls.

Run from the repo root after:  python -m src.grade results/paper/v3_checks/positive_controls.jsonl
                               python -m src.judge_v3 results/paper/v3_checks/positive_controls.graded.jsonl
                               python -m src.evaluate_foundry results/paper/v3_checks/positive_controls.graded.jsonl
    .venv/bin/python results/paper/v3_checks/a2_summary.py  -> a2_positive_controls.md / .csv
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
from src.kql_assertions import PAPER_A, PAPER_B, kql_range  # noqa: E402

D = Path("results/paper/v3_checks")
g = pd.read_json(D / "positive_controls.graded.jsonl", lines=True)
raw = pd.read_json(D / "positive_controls.jsonl", lines=True)[["qid", "rep", "variant"]]
g = g.drop(columns=[c for c in ("variant",) if c in g]).merge(raw, on=["qid", "rep"])
j3 = pd.read_json(D / "positive_controls.judge3.jsonl", lines=True)[["qid", "condition", "rep", "answer_correct_v3"]]
g = g.merge(j3, on=["qid", "condition", "rep"], how="left")
fe = pd.read_json(D / "positive_controls.foundry_eval.jsonl", lines=True)
g = g.merge(fe.drop(columns=["scenario", "trace_id"], errors="ignore"), on=["qid", "condition", "rep"], how="left")

start, end = sys.argv[1] if len(sys.argv) > 1 else "2026-11-21T00:00:00Z", sys.argv[2] if len(sys.argv) > 2 else "2026-11-23T00:00:00Z"
om = {r["operation_Id"] for r in kql_range(PAPER_A, start, end)}
rp = {r["operation_Id"] for r in kql_range(PAPER_B, start, end)}
g["omission_query_hit"] = g.trace_id.isin(om)
g["repetition_query_hit"] = g.trace_id.isin(rp)
g["provenance_violation"] = g.apply(lambda r: any(str(tc["args"].get("order_id", "")).lstrip("#") not in r.message
                                                  for tc in (r.tool_calls or [])), axis=1)


def counts(s):
    s = s.fillna("missing").astype(str)
    return ", ".join(f"{k} {v}" for k, v in s.value_counts().items())


lines = [f"# A2. Positive controls (post hoc detector validation), run 2026-11-21\n",
         "Not part of the pre-specified experiment. gpt-5-mini agents, `before` instructions. "
         "F1-forced: the policy agent is a copy of `policy-agent-before` without File Search (`tool_choice=\"none\"` "
         "was accepted by the API but File Search still ran, so the agent-copy variant was used). F2-forced: the order agent "
         "receives only the triage summary with every 4+-digit run replaced by `[number]`.\n"]
rows = []
for v, x in g.groupby("variant"):
    rec = dict(variant=v, conversations=len(x), errors=int(x.error.notna().sum()),
               routed_as_expected=int(x.route_ok.astype(bool).sum()),
               searched=int(x.searched.astype(bool).sum()),
               omission_query_hits=int(x.omission_query_hit.sum()),
               repetition_query_hits=int(x.repetition_query_hit.sum()),
               tool_calls=int(x.n_tool_calls.sum()), runs_with_tool_call=int((x.n_tool_calls > 0).sum()),
               provenance_violations=int(x.provenance_violation.sum()),
               invented_id=int(x.invented_id.astype(bool).sum()), wrong_id=int(x.wrong_id.astype(bool).sum()),
               asked_for_id=int(x.asked_for_id.astype(bool).sum()),
               judge_v2_correct=int(x.answer_correct.astype(bool).sum()),
               judge_v3_correct=int(x.answer_correct_v3.fillna(False).astype(bool).sum()))
    for ev in ("tool_selection", "task_adherence", "tool_input_accuracy", "tool_call_accuracy", "intent_resolution"):
        col = f"{ev}_result"
        if col in x and x[col].notna().any():
            rec[ev] = counts(x[col])
    rows.append(rec)
t = pd.DataFrame(rows).set_index("variant").T
t.to_csv(D / "a2_positive_controls.csv")
lines += ["| Measure | " + " | ".join(t.columns) + " |", "|---|" + "---|" * len(t.columns)]
lines += [f"| {i} | " + " | ".join(str(v) for v in t.loc[i]) + " |" for i in t.index]

lines += ["", "## Evaluator reasons (most frequent, shortened)\n"]
for v, x in g.groupby("variant"):
    for ev in ("tool_selection", "task_adherence", "tool_input_accuracy", "tool_call_accuracy"):
        rc = f"{ev}_reason"
        if rc in x and x[rc].notna().any():
            for res in ("not_applicable", "pass", "fail"):
                y = x[x[f"{ev}_result"] == res][rc].dropna()
                if len(y):
                    lines.append(f"- {v}, {ev}, {res} ({len(y)}): \"{str(y.iloc[0])[:220]}\"")

lines += ["", "## Example runs (trace ids)\n"]
for v, x in g.groupby("variant"):
    for _, r in x.sort_values(["qid", "rep"]).head(2).iterrows():
        tc = "; ".join(f"{c['name']}({json.dumps(c['args'])})" for c in (r.tool_calls or [])) or "no tool call"
        lines.append(f"- {v} {r.qid} rep {r.rep}: trace `{r.trace_id}`; searched {bool(r.searched)}; {tc}; handoff: "
                     f"\"{(r.handoff or '')[:160]}\"; answer: \"{(r.answer or '')[:160]}\"")
(D / "a2_positive_controls.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
