"""Runs the paper's trace assertions (Fig. 3) as real KQL queries in Application Insights and compares what they
find with the client-side metrics. Unlike src/export_spans.py (which evaluates assertions in Python on exported
spans), this checks that the queries a reader would type into the portal actually work.

    python -m src.kql_assertions gpt-5-mini=results/main.graded.jsonl gpt-4.1-mini=results/main_gpt41mini.graded.jsonl
        -> results/trace_queries.kql            the queries as first written (Nov 17)
           results/paper/kql_assertions.md      what (a) and (b) found vs the client-side metric

    python -m src.kql_assertions ... --paper-v3 --out results/paper/v3_checks
        runs the three queries exactly as printed in Fig. 3 of paper v3, including (c) the error contract, over an
        explicit time range (16-17 Nov 2026, the days of the runs), and writes kql_assertions_v3.md/.csv,
        kql_error_contract.csv and the query texts.

Times: --start/--end default to the run days. A relative window (the old --offset 30d) would drop those days after
mid-December, so the v3 mode always uses explicit timestamps.
"""
import argparse
import json
import subprocess
from pathlib import Path

import pandas as pd

from .export_spans import env, kql

# ---- queries as first written (Nov 17); kept for reproducibility of results/paper/kql_assertions.md ----
OMISSION = """// Fig. 3a  Omission: policy agent answered without searching the policy documents
let conversations = dependencies
    | where name startswith "invoke_workflow"
    | project operation_Id,
              qid = tostring(customDimensions["experiment.qid"]),
              condition = tostring(customDimensions["experiment.condition"]);
let policy_invoked = dependencies
    | where name startswith "invoke_agent policy-agent" and name !contains ":"
    | distinct operation_Id;
let searched = dependencies
    | where name startswith "execute_tool file_search"
    | distinct operation_Id;
conversations
| join kind=inner policy_invoked on operation_Id
| join kind=leftanti searched on operation_Id
| project operation_Id, qid, condition"""

REPETITION = """// Fig. 3b  Repetition: the same tool call (name + arguments) executed 3+ times in one conversation
dependencies
| where name startswith "execute_tool"
    and tostring(customDimensions["gen_ai.tool.type"]) == "function"
| summarize identical_calls = count()
    by operation_Id,
       tool = tostring(customDimensions["gen_ai.tool.name"]),
       arguments = tostring(customDimensions["gen_ai.tool.call.arguments"])
| where identical_calls >= 3
| summarize max_identical_calls = max(identical_calls) by operation_Id"""

# ---- the three queries exactly as printed in Fig. 3 of paper v3 (whitespace as in the figure) ----
PAPER_A = """// (a) Omission: policy agent ran, no file search
let searched = dependencies
  | where name startswith "execute_tool file_search"
  | distinct operation_Id;
dependencies
| where name startswith "invoke_agent policy-agent"
    and name !contains ":"
| distinct operation_Id
| join kind=leftanti searched on operation_Id"""

PAPER_B = """// (b) Repetition: same function call 3+ times
dependencies
| where name startswith "execute_tool"
| extend d = customDimensions
| where tostring(d["gen_ai.tool.type"]) == "function"
| summarize n = count() by operation_Id,
    tool = tostring(d["gen_ai.tool.name"]),
    args = tostring(d["gen_ai.tool.call.arguments"])
| where n >= 3"""

PAPER_C = """// (c) Error contract: a tool returned a bare "Error"
dependencies | where name startswith "execute_tool"
| where tostring(customDimensions
    ["gen_ai.tool.call.result"]) == "Error\""""


def kql_range(query: str, start: str, end: str) -> list[dict]:
    rg, app = env()
    out = subprocess.run(["az", "monitor", "app-insights", "query", "-g", rg, "--app", app, "--start-time", start,
                          "--end-time", end, "--analytics-query", query, "-o", "json"], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"KQL query failed: {out.stderr[-800:]}")
    t = json.loads(out.stdout)["tables"][0]
    cols = [c["name"] for c in t["columns"]]
    return [dict(zip(cols, r)) for r in t["rows"]]


def legacy(a):
    Path("results/trace_queries.kql").write_text(OMISSION + "\n\n\n" + REPETITION + "\n")
    om = pd.DataFrame(kql(OMISSION, a.offset))
    rp = pd.DataFrame(kql(REPETITION, a.offset))
    om_ids = set(om.operation_Id) if len(om) else set()
    rp_ids = set(rp.operation_Id) if len(rp) else set()
    lines = ["# Fig. 3 trace assertions run as KQL in Application Insights\n",
             "| Model | Condition | Conversations | Omission query hits | Client: policy agent did not search | "
             "Repetition query hits | Client: looped (3+ identical calls) | Query = client, every conversation |",
             "|---|---|---|---|---|---|---|---|"]
    for arm in a.arms:
        label, path = arm.split("=", 1)
        df = pd.read_json(path, lines=True)
        df = df[df.error.isna()]
        for c in ("before", "after"):
            x = df[df.condition == c]
            pol = x[x.specialist.fillna("").str.startswith("policy")]
            client_om = set(pol[~pol.searched.astype(bool)].trace_id)
            client_rp = set(x[x.n_identical_calls >= 3].trace_id)
            q_om, q_rp = om_ids & set(x.trace_id), rp_ids & set(x.trace_id)
            same = (q_om == client_om) and (q_rp == client_rp)
            lines.append(f"| {label} | {c} | {len(x)} | {len(q_om)} | {len(client_om)} | {len(q_rp)} | {len(client_rp)} | "
                         f"{'yes' if same else 'NO'} |")
    Path("results/paper/kql_assertions.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def paper_v3(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "fig3_queries_as_printed.kql").write_text(PAPER_A + "\n\n\n" + PAPER_B + "\n\n\n" + PAPER_C + "\n")
    hits = {}
    for key, q in (("a", PAPER_A), ("b", PAPER_B), ("c", PAPER_C)):
        res = kql_range(q, a.start, a.end)
        hits[key] = set(r["operation_Id"] for r in res)
        print(f"query ({key}): {len(res)} result rows, {len(hits[key])} distinct traces")
    runs, rows, err_rows = [], [], []
    for arm in a.arms:
        label, path = arm.split("=", 1)
        df = pd.read_json(path, lines=True)
        df = df[df.error.isna()]
        df["model"] = label
        runs.append(df)
        stem = Path(path).name.replace(".graded.jsonl", "")
        sp = pd.read_csv(Path(path).parent / f"{stem}.spans.csv", usecols=["operation_Id", "name", "gen_ai.tool.call.result"])
        exported_err = set(sp[sp.name.str.startswith("execute_tool") & (sp["gen_ai.tool.call.result"].astype(str) == "Error")].operation_Id)
        for (scen, c), x in df.groupby(["scenario", "condition"]):
            ids = set(x.trace_id)
            pol = x[x.specialist.fillna("").str.startswith("policy")]
            rows.append(dict(model=label, scenario=scen, condition=c, conversations=len(x),
                             omission_hits=len(hits["a"] & ids), client_policy_not_searched=int((~pol.searched.astype(bool)).sum()),
                             repetition_hits=len(hits["b"] & ids), client_looped=int((x.n_identical_calls >= 3).sum()),
                             error_contract_hits=len(hits["c"] & ids), exported_spans_error=len(exported_err & ids),
                             error_contract_equals_exported=(hits["c"] & ids) == (exported_err & ids)))
        for _, r in df[df.trace_id.isin(hits["c"])].iterrows():
            err_rows.append(dict(model=label, qid=r.qid, scenario=r.scenario, condition=r.condition, rep=r.rep, operation_Id=r.trace_id))
    allruns = pd.concat(runs)
    other = {k: len(v - set(allruns.trace_id)) for k, v in hits.items()}
    t = pd.DataFrame(rows)
    t.to_csv(out / "kql_assertions_v3.csv", index=False)
    pd.DataFrame(err_rows).sort_values(["model", "qid", "rep"]).to_csv(out / "kql_error_contract.csv", index=False)
    md = [f"# Fig. 3 queries as printed in paper v3, run in Application Insights ({a.start} to {a.end})\n",
          "Hits are distinct operation_Ids (traces) matched to the 800 main-run conversations. "
          f"Hits outside the main runs (smoke and trace-check pilot traces from the same days): "
          f"(a) {other['a']}, (b) {other['b']}, (c) {other['c']}.\n",
          t.to_markdown(index=False)]
    (out / "kql_assertions_v3.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+", help="label=path/to/graded.jsonl")
    ap.add_argument("--offset", default="30d", help="legacy mode only")
    ap.add_argument("--paper-v3", action="store_true", help="run the three queries as printed in Fig. 3 of paper v3")
    ap.add_argument("--start", default="2026-11-16T00:00:00Z")
    ap.add_argument("--end", default="2026-11-18T00:00:00Z")
    ap.add_argument("--out", default="results/paper/v3_checks")
    a = ap.parse_args()
    paper_v3(a) if a.paper_v3 else legacy(a)


if __name__ == "__main__":
    main()
