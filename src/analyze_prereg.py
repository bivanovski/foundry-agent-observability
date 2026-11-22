"""Pre-registered analysis (results/CHANGELOG.md, 2026-11-16 "decisions and pre-registered metrics").

    python -m src.analyze_prereg results/main.graded.jsonl \
        [--trace-check results/main.trace_check.csv] [--foundry results/main.foundry_eval.jsonl]

Writes to results/paper/prereg/:
  table_primary.md / .csv      every pre-registered metric: before, after (Wilson 95% CI), difference with a
                               95% bootstrap CI that resamples ITEMS (5000 resamples), Fisher exact p
  table_subtypes.md / .csv     the same metrics split by item subtype
  table_latency_tokens.md      p50/p95 latency, tokens, share of correct runs over 10 s
  table_triage.md              triage reasoning overhead
  table_trace_assertions.md    Fig. 3 trace assertions (spans) vs client-side metrics
  table_evaluators.md          built-in evaluators: pass / fail / not applicable, and agreement with deterministic metrics
  per_item.csv                 every metric per item and condition
  summary.md                   the headline numbers in one place
"""
import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

B = 5000
RNG = np.random.default_rng(2027)
SC = {"mistake1": "M1 missing lookup", "mistake2": "M2 lost context", "mistake3": "M3 runaway loop", "control": "Control"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def pct(x):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.1f}%"


def rate_str(k, n):
    if n == 0:
        return "n/a (0 runs)"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}] ({k}/{n})"


def boot_diff(d: pd.DataFrame, col: str, kind: str):
    """After minus before, bootstrapping items. kind = 'rate' (binary) or 'mean' (numeric)."""
    items = sorted(d.qid.unique())
    if not items:
        return (math.nan, math.nan, math.nan)
    agg = {}
    for c in ("before", "after"):
        g = d[d.condition == c].groupby("qid")[col]
        s = g.sum() if kind == "rate" else g.sum()
        n = g.count()
        agg[c] = (s.reindex(items, fill_value=0).to_numpy(float), n.reindex(items, fill_value=0).to_numpy(float))
    point_b = agg["before"][0].sum() / agg["before"][1].sum() if agg["before"][1].sum() else math.nan
    point_a = agg["after"][0].sum() / agg["after"][1].sum() if agg["after"][1].sum() else math.nan
    idx = RNG.integers(0, len(items), size=(B, len(items)))
    with np.errstate(invalid="ignore", divide="ignore"):
        rb = agg["before"][0][idx].sum(1) / agg["before"][1][idx].sum(1)
        ra = agg["after"][0][idx].sum(1) / agg["after"][1][idx].sum(1)
    diffs = (ra - rb)[~np.isnan(ra - rb)]
    if len(diffs) == 0:
        return (point_a - point_b, math.nan, math.nan)
    return (point_a - point_b, float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)))


def metric_row(d: pd.DataFrame, col: str, label: str, kind: str = "rate", lower_is_better=False):
    d = d[d[col].notna()].copy()
    if kind == "rate":
        d[col] = d[col].astype(bool).astype(int)
    rec = {"metric": label, "column": col, "kind": kind, "items": d.qid.nunique()}
    ks = {}
    for c in ("before", "after"):
        x = d[d.condition == c][col]
        if kind == "rate":
            ks[c] = (int(x.sum()), int(len(x)))
            rec[c] = rate_str(*ks[c])
            rec[f"{c}_rate"] = x.mean() if len(x) else math.nan
        else:
            rec[c] = f"mean {x.mean():.2f}, max {int(x.max()) if len(x) else 0} (n={len(x)})" if len(x) else "n/a"
            rec[f"{c}_rate"] = x.mean() if len(x) else math.nan
    diff, lo, hi = boot_diff(d, col, kind)
    unit = 100 if kind == "rate" else 1
    rec["diff_after_minus_before"] = (f"{unit * diff:+.1f}{' pp' if kind == 'rate' else ''} "
                                      f"[{unit * lo:+.1f}, {unit * hi:+.1f}]") if not math.isnan(diff) else "n/a"
    rec["diff"], rec["diff_lo"], rec["diff_hi"] = diff, lo, hi
    if kind == "rate" and ks["before"][1] and ks["after"][1]:
        (kb, nb), (ka, na) = ks["before"], ks["after"]
        p = fisher_exact([[kb, nb - kb], [ka, na - ka]])[1]
        rec["fisher_p"] = "<0.001" if p < 0.001 else f"{p:.3f}"
    else:
        rec["fisher_p"] = "n/a"
    return rec


def metrics_for(scen: str, d: pd.DataFrame):
    """The pre-registered metric list per scenario: (column, label, kind)."""
    if scen == "mistake1":
        return [(d, "searched", "Searched the policy documents [primary]", "rate"),
                (d, "answer_correct", "Answer correct (judge v2)", "rate"),
                (d, "task_success", "Task success (process ok and answer correct)", "rate"),
                (d, "route_ok", "Routed to the policy agent", "rate")]
    if scen == "mistake2":
        has_id = d[d.subtype.isin(["id_first", "id_buried"])]
        miss = has_id[has_id.id_missing_from_handoff == True]  # noqa: E712
        noid = d[d.subtype == "no_id"]
        return [(d, "invented_id", "Tool called with an ID not in the message [primary]", "rate"),
                (d, "wrong_id", "Tool called with any ID other than the expected one [primary]", "rate"),
                (has_id, "id_in_handoff", "Order ID present in the handoff (items with an ID)", "rate"),
                (miss, "invented_id", "Invented ID | ID missing from handoff [primary]", "rate"),
                (miss, "wrong_id", "Wrong ID | ID missing from handoff [primary]", "rate"),
                (noid, "asked_for_id", "Asked for the order number (no_id items)", "rate"),
                (noid, "no_tool_call", "No tool call (no_id items)", "rate"),
                (d, "answer_correct", "Answer correct (judge v2)", "rate"),
                (d, "task_success", "Task success", "rate")]
    if scen == "mistake3":
        return [(d, "n_identical_calls", "Identical tool calls per run [primary]", "mean"),
                (d, "n_tool_calls", "Tool calls per run", "mean"),
                (d, "looped", "Looped (3+ identical calls or round cap)", "rate"),
                (d, "offered_email", "Offered an email follow-up", "rate"),
                (d, "asked_to_confirm_id", "Asked the customer to confirm a correct order ID [exploratory]", "rate"),
                (d, "answer_correct", "Answer correct (judge v2)", "rate"),
                (d, "task_success", "Task success", "rate"),
                (d, "total_tokens", "Tokens per conversation", "mean"),
                (d, "latency_s", "Latency per conversation (s)", "mean")]
    return [(d, "route_ok", "Routed correctly [primary]", "rate"),
            (d, "answer_correct", "Answer correct (judge v2) [primary]", "rate"),
            (d, "no_tool_call", "No function tool call", "rate"),
            (d, "task_success", "Task success", "rate")]


def md(df: pd.DataFrame, cols):
    return df[cols].to_markdown(index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("graded")
    ap.add_argument("--trace-check")
    ap.add_argument("--foundry")
    ap.add_argument("--judge3", help="post-hoc judge v3 verdicts (src/judge_v3.py)")
    ap.add_argument("--out", default="results/paper/prereg")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    raw = pd.read_json(a.graded, lines=True)
    n_err = int(raw.error.notna().sum())
    df = raw[raw.error.isna()].copy()
    tq = pd.read_json("data/testset.jsonl", lines=True).set_index("id")
    df["subtype"] = df.qid.map(tq["subtype"])
    df["total_tokens"] = df.input_tokens + df.output_tokens
    df["no_tool_call"] = df.n_tool_calls == 0
    if a.judge3 and Path(a.judge3).exists():
        j3 = pd.read_json(a.judge3, lines=True)[["qid", "condition", "rep", "answer_correct_v3"]]
        df = df.merge(j3, on=["qid", "condition", "rep"], how="left")
        df["task_success_v3"] = (df.process_ok.astype(bool) & (df.answer_correct_v3 == True)).where(df.answer_correct_v3.notna())  # noqa: E712

    def v3rows(d):
        if "answer_correct_v3" not in d:
            return []
        return [(d, "answer_correct_v3", "Answer correct (judge v3, post hoc)", "rate"),
                (d, "task_success_v3", "Task success (judge v3, post hoc)", "rate")]

    summary = [f"# Main run: pre-registered results\n",
               f"Runs: {len(raw)} recorded, {n_err} errored (excluded), {len(df)} analysed. "
               f"Items: {df.qid.nunique()}. Reps per item and condition: "
               f"{df.groupby(['qid', 'condition']).size().min()}-{df.groupby(['qid', 'condition']).size().max()}.\n",
               "Differences are after minus before, with 95% bootstrap CIs over items (5000 resamples).\n"]

    # ---------- primary table + subtypes ----------
    prim, subs = [], []
    for scen, label in SC.items():
        d = df[df.scenario == scen]
        for dd, col, mlabel, kind in metrics_for(scen, d) + v3rows(d):
            prim.append({"scenario": label, **metric_row(dd, col, mlabel, kind)})
        for st in sorted(d.subtype.dropna().unique()):
            ds = d[d.subtype == st]
            for dd, col, mlabel, kind in metrics_for(scen, ds) + v3rows(ds):
                if dd is ds or len(dd):
                    subs.append({"scenario": label, "subtype": st, **metric_row(dd, col, mlabel, kind)})
    P = pd.DataFrame(prim)
    S = pd.DataFrame(subs)
    P.to_csv(out / "table_primary.csv", index=False)
    S.to_csv(out / "table_subtypes.csv", index=False)
    cols = ["scenario", "metric", "before", "after", "diff_after_minus_before", "fisher_p"]
    (out / "table_primary.md").write_text("# Pre-registered metrics\n\n" + md(P, cols) + "\n")
    (out / "table_subtypes.md").write_text("# Metrics by item subtype\n\n" + md(S, ["scenario", "subtype"] + cols[1:]) + "\n")
    summary += ["## Primary metrics\n", md(P[P.metric.str.contains("primary")], cols), ""]

    # ---------- judge v2 vs v3 (post hoc) ----------
    if "answer_correct_v3" in df:
        jr = []
        for scen, label in SC.items():
            for c in ("before", "after"):
                x = df[(df.scenario == scen) & (df.condition == c) & df.answer_correct.notna() & df.answer_correct_v3.notna()]
                if not len(x):
                    continue
                v2, v3 = x.answer_correct.astype(bool), x.answer_correct_v3.astype(bool)
                jr.append(dict(scenario=label, condition=c, n=len(x), judge_v2_correct=f"{100 * v2.mean():.1f}%",
                               judge_v3_correct=f"{100 * v3.mean():.1f}%", agreement=f"{100 * (v2 == v3).mean():.1f}%",
                               v2_incorrect_to_v3_correct=int((~v2 & v3).sum()), v2_correct_to_v3_incorrect=int((v2 & ~v3).sum())))
        J = pd.DataFrame(jr)
        J.to_csv(out / "table_judges.csv", index=False)
        (out / "table_judges.md").write_text(
            "# Judge v2 (pre-registered) vs judge v3 (post hoc: also sees tool definitions, tool results and the fixed date)\n\n"
            + J.to_markdown(index=False) + "\n")
        summary += ["## Judge v2 vs v3 (post hoc)\n", J.to_markdown(index=False), ""]

    # ---------- latency and tokens ----------
    lt = []
    for scen, label in SC.items():
        for c in ("before", "after"):
            x = df[(df.scenario == scen) & (df.condition == c)]
            if not len(x):
                continue
            ok = x[x.answer_correct == True]  # noqa: E712
            spec = [s["seconds"] for steps in x.steps for s in steps if s["step"] != "triage"]
            lt.append(dict(scenario=label, condition=c, runs=len(x),
                           latency_p50_s=round(x.latency_s.median(), 2), latency_p95_s=round(x.latency_s.quantile(.95), 2),
                           correct_runs=len(ok), correct_runs_over_10s=pct((ok.latency_s > 10).mean() if len(ok) else math.nan),
                           specialist_calls_p50_s=round(float(np.median(spec)), 2) if spec else None,
                           tokens_mean=round(x.total_tokens.mean()), tokens_p95=round(x.total_tokens.quantile(.95)),
                           model_calls_mean=round(x.n_model_calls.mean(), 2)))
    L = pd.DataFrame(lt)
    L.to_csv(out / "table_latency_tokens.csv", index=False)
    (out / "table_latency_tokens.md").write_text("# Latency and tokens\n\n" + L.to_markdown(index=False) + "\n")
    allok = df[df.answer_correct == True]  # noqa: E712
    summary += ["## Latency\n", f"Correct runs over 10 s: {pct((allok.latency_s > 10).mean())} of {len(allok)} "
                f"(p50 {allok.latency_s.median():.1f} s, p95 {allok.latency_s.quantile(.95):.1f} s).\n"]

    # ---------- triage overhead ----------
    tri = pd.DataFrame([s for steps in df.steps for s in steps if s["step"] == "triage"])
    if len(tri):
        tri["reasoning_tokens"] = pd.to_numeric(tri.get("reasoning_tokens"), errors="coerce")
        share = (tri.reasoning_tokens / tri.output_tokens).replace([np.inf], np.nan)
        T = pd.DataFrame([dict(triage_calls=len(tri), latency_p50_s=round(tri.seconds.median(), 2),
                               latency_p95_s=round(tri.seconds.quantile(.95), 2),
                               output_tokens_mean=round(tri.output_tokens.mean(), 1),
                               reasoning_tokens_mean=round(tri.reasoning_tokens.mean(), 1),
                               reasoning_share_of_output=pct(share.mean()),
                               reasoning_effort=", ".join(sorted({str(e) for e in tri.get("reasoning_effort", [])})))])
        (out / "table_triage.md").write_text("# Triage overhead (one-line JSON routing decision)\n\n" + T.to_markdown(index=False) + "\n")
        summary += ["## Triage overhead\n", T.to_markdown(index=False), ""]

    # ---------- trace assertions vs client metrics ----------
    if a.trace_check and Path(a.trace_check).exists():
        tc = pd.read_csv(a.trace_check)
        m = tc.merge(df[["qid", "condition", "rep", "scenario", "searched", "looped", "specialist", "n_identical_calls"]],
                     on=["qid", "condition", "rep"])
        pol = m[m.specialist.fillna("").str.startswith("policy")]
        lines = ["# Trace assertions (spans only) vs client-side metrics\n",
                 f"Traces: {len(tc)}; complete: {int(tc.complete.sum())}; with root span: {int(tc.has_root.sum())}; "
                 f"sampled: {int(tc.sampled.sum())}. Tool spans {int(tc.tool_spans.sum())} vs logged tool calls "
                 f"{int(tc.tool_calls_logged.sum())}; file-search spans {int(tc.file_search_spans.sum())} vs logged "
                 f"{int(tc.file_search_logged.sum())}.\n",
                 ("Note: file-search spans exceed the logged searches because Foundry ran the search in agent requests "
                  "that then returned HTTP 429 (rate limit) and were retried automatically by the client library. The "
                  "client log only records the successful attempt; the trace shows the retried work too "
                  "(data/rate_limit_retries.csv).\n") if tc.file_search_spans.sum() > tc.file_search_logged.sum() else "",
                 "## Omission (policy agent invoked, no file_search span) vs client `searched == False`\n",
                 pd.crosstab(pol.trace_omission, ~pol.searched.astype(bool), rownames=["trace_omission"],
                             colnames=["client_not_searched"]).to_markdown(), "",
                 "By condition: " + ", ".join(f"{c}: {int(g.trace_omission.sum())}/{len(g)} omissions"
                                             for c, g in pol.groupby("condition")) + "\n",
                 "## Repetition (3+ identical execute_tool spans) vs client `looped`\n",
                 pd.crosstab(m.trace_repetition, m.looped.astype(bool), rownames=["trace_repetition"],
                             colnames=["client_looped"]).to_markdown(), "",
                 f"Max identical calls, trace vs client, equal in {int((m.trace_max_identical_calls == m.n_identical_calls).sum())}"
                 f"/{len(m)} runs.\n"]
        (out / "table_trace_assertions.md").write_text("\n".join(lines))
        summary += [l for l in lines[1:2]]

    # ---------- built-in evaluators ----------
    if a.foundry and Path(a.foundry).exists():
        fe = pd.read_json(a.foundry, lines=True)
        m = fe.merge(df[["qid", "condition", "rep", "searched", "wrong_id", "invented_id", "answer_correct",
                         "n_identical_calls", "task_success"]], on=["qid", "condition", "rep"])
        rows = []
        for col in [c for c in fe.columns if c.endswith("_pass")]:
            ev = col.removesuffix("_pass")
            for scen in SC:
                for c in ("before", "after"):
                    x = m[(m.scenario == scen) & (m.condition == c)]
                    if col not in x or x[col].isna().all() and f"{ev}_result" not in x:
                        continue
                    res = x.get(f"{ev}_result", pd.Series(dtype=str)).fillna("missing")
                    if (res == "missing").all() and x[col].isna().all():
                        continue
                    k = int((x[col] == True).sum())  # noqa: E712
                    f = int((x[col] == False).sum())  # noqa: E712
                    na = int((res == "not_applicable").sum())
                    blocked = int((res == "blocked_content_filter").sum())
                    rows.append(dict(evaluator=ev, scenario=SC[scen], condition=c, pass_=k, fail=f, not_applicable=na,
                                     blocked_by_content_filter=blocked, pass_rate=rate_str(k, k + f)))
        E = pd.DataFrame(rows).rename(columns={"pass_": "pass"})
        agree = ["", "## Agreement with deterministic metrics (runs where the evaluator gave a verdict)\n",
                 "| Evaluator | Reference | Agreement | n | Not applicable |", "|---|---|---|---|---|"]
        for ev, ref, inv in [("tool_selection", "searched", False), ("task_adherence", "answer_correct", False),
                             ("tool_input_accuracy", "wrong_id", True), ("tool_call_accuracy", "wrong_id", True),
                             ("tool_call_success", "task_success", False), ("task_completion", "answer_correct", False),
                             ("intent_resolution", "answer_correct", False)]:
            col = f"{ev}_pass"
            if col not in m:
                continue
            x = m[m[col].notna() & m[ref].notna()]
            if not len(x):
                continue
            refv = ~x[ref].astype(bool) if inv else x[ref].astype(bool)
            n_na = int((m.get(f"{ev}_result", pd.Series(dtype=str)) == "not_applicable").sum())
            agree.append(f"| {ev} | {'not ' if inv else ''}{ref} | {pct((x[col].astype(bool) == refv).mean())} | {len(x)} | "
                         f"{n_na} |")
        (out / "table_evaluators.md").write_text("# Built-in evaluators\n\n" + E.to_markdown(index=False) + "\n" + "\n".join(agree) + "\n")
        summary += ["## Built-in evaluators vs deterministic metrics\n"] + agree[2:] + [""]

    # ---------- per item ----------
    keep = ["searched", "invented_id", "wrong_id", "id_in_handoff", "asked_for_id", "n_identical_calls", "looped", "asked_to_confirm_id",
            "offered_email", "route_ok", "answer_correct", "task_success", "latency_s", "total_tokens"]
    pi = df.assign(**{k: pd.to_numeric(df[k].map(lambda v: float(v) if v is not None and v == v else np.nan), errors="coerce")
                      for k in keep}).groupby(["qid", "scenario", "subtype", "condition"])[keep].mean().round(3).reset_index()
    pi.to_csv(out / "per_item.csv", index=False)

    (out / "summary.md").write_text("\n".join(summary) + "\n")
    print("\n".join(summary))
    print(f"\nAll outputs in {out}/")


if __name__ == "__main__":
    main()
