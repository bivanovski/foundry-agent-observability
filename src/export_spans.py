"""Exports every span of the conversations in a results file from Application Insights,
checks that each trace is complete, and runs the paper's two trace assertions.

    python -m src.export_spans results/main.graded.jsonl            -> results/main.spans.jsonl / .csv
                                                                       results/main.trace_check.csv

Needs the Azure CLI (az login) and RESOURCE_GROUP / APPINSIGHTS_NAME in .env.

Trace assertions (Fig. 3 of the paper), evaluated on spans only, never on client logs:
  omission    a policy-agent invocation with no file_search execute_tool span in the trace
  repetition  the same execute_tool (tool name + arguments) appears 3 or more times in the trace
"""
import argparse
import csv
import json
import os
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from .config import ROOT

DIMS = ["gen_ai.operation.name", "gen_ai.agent.name", "gen_ai.agent.id", "gen_ai.tool.name", "gen_ai.tool.type",
        "gen_ai.tool.call.arguments", "gen_ai.tool.call.result", "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens", "gen_ai.request.model", "gen_ai.response.model", "error.type",
        "experiment.qid", "experiment.condition", "experiment.rep", "experiment.scenario"]


def env():
    vals = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()
    return vals["RESOURCE_GROUP"], vals["APPINSIGHTS_NAME"]


def kql(query: str, offset: str) -> list[dict]:
    rg, app = env()
    out = subprocess.run(["az", "monitor", "app-insights", "query", "-g", rg, "--app", app, "--offset", offset,
                          "--analytics-query", query, "-o", "json"], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"KQL query failed: {out.stderr[-800:]}")
    t = json.loads(out.stdout)["tables"][0]
    cols = [c["name"] for c in t["columns"]]
    return [dict(zip(cols, r)) for r in t["rows"]]


def fetch(trace_ids: list[str], offset: str) -> list[dict]:
    dims = ", ".join(f'["{d}"]=tostring(customDimensions["{d}"])' for d in DIMS)
    spans = []
    for i in range(0, len(trace_ids), 50):
        chunk = ", ".join(f'"{t}"' for t in trace_ids[i:i + 50])
        spans += kql(f"""union dependencies, requests
| where operation_Id in ({chunk})
| project operation_Id, id, operation_ParentId, name, timestamp, duration, success, itemCount, {dims}
| order by operation_Id asc, timestamp asc""", offset)
    return spans


def check(rows: list[dict], spans: list[dict]) -> list[dict]:
    by_trace = defaultdict(list)
    for s in spans:
        by_trace[s["operation_Id"]].append(s)
    out = []
    for r in rows:
        ss = by_trace.get(r.get("trace_id"), [])
        names = [s["name"] for s in ss]
        tool_spans = [s for s in ss if s["name"].startswith("execute_tool ") and s.get("gen_ai.tool.type") == "function"]
        fs_spans = [s for s in ss if s["name"].startswith("execute_tool file_search")]
        policy_invoked = any(n.startswith("invoke_agent policy-agent") for n in names)
        rep = Counter((s.get("gen_ai.tool.name"), s.get("gen_ai.tool.call.arguments")) for s in tool_spans)
        out.append(dict(
            qid=r["qid"], condition=r["condition"], rep=r["rep"], trace_id=r.get("trace_id"),
            n_spans=len(ss),
            has_root=any(n.startswith("invoke_workflow") for n in names),
            client_agent_spans=sum(1 for s in ss if s["name"].startswith("invoke_agent") and ":" not in s["name"]),
            tool_spans=len(tool_spans), tool_calls_logged=len(r.get("tool_calls") or []),
            file_search_spans=len(fs_spans), file_search_logged=r.get("n_file_search_calls", 0),
            sampled=any((s.get("itemCount") or 1) > 1 for s in ss),
            complete=(any(n.startswith("invoke_workflow") for n in names)
                      and len(tool_spans) == len(r.get("tool_calls") or [])
                      and not any((s.get("itemCount") or 1) > 1 for s in ss)),
            # Fig. 3 trace assertions, from spans only
            trace_omission=policy_invoked and not fs_spans,
            trace_repetition=max(rep.values() or [0]) >= 3,
            trace_max_identical_calls=max(rep.values() or [0]),
        ))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--offset", default="30d", help="how far back App Insights is searched")
    a = ap.parse_args()
    src = Path(a.results)
    rows = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if r.get("trace_id") and not r.get("error")]
    stem = src.name.replace(".graded.jsonl", "").replace(".jsonl", "")
    spans = fetch(sorted({r["trace_id"] for r in rows}), a.offset)

    (src.parent / f"{stem}.spans.jsonl").write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in spans) + "\n")
    with (src.parent / f"{stem}.spans.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(spans[0].keys()) if spans else ["operation_Id"])
        w.writeheader()
        w.writerows(spans)
    res = check(rows, spans)
    with (src.parent / f"{stem}.trace_check.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0].keys()))
        w.writeheader()
        w.writerows(res)
    n = len(res)
    print(f"{len(spans)} spans for {n} conversations -> {stem}.spans.jsonl/.csv, {stem}.trace_check.csv")
    print(f"  complete traces: {sum(x['complete'] for x in res)}/{n}, with root: {sum(x['has_root'] for x in res)}/{n}, "
          f"sampled: {sum(x['sampled'] for x in res)}/{n}")
    print(f"  tool spans {sum(x['tool_spans'] for x in res)} vs logged tool calls {sum(x['tool_calls_logged'] for x in res)}; "
          f"file_search spans {sum(x['file_search_spans'] for x in res)} vs logged {sum(x['file_search_logged'] for x in res)}")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONWARNINGS", "ignore")
    main()
