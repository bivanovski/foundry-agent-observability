"""Turns graded results into the numbers, tables and figures for the paper.

    python -m src.analyze results/main.graded.jsonl [--foundry results/main.foundry_eval.jsonl]

Writes to results/paper/:
  table_main.md / .tex / .csv   before vs after per scenario, Wilson 95% CIs, Fisher exact p
  table_efficiency.md / .csv    latency and tokens per scenario
  table_foundry_evaluators.md   built-in evaluator pass rates (if --foundry given)
  per_question.csv              success rate per question and condition (appendix / sanity check)
  example_traces.md             trace ids to open in the portal for the paper's screenshots
  fig_success.png, fig_mistake3_latency.png
"""
import argparse
import json
import math
import random
from pathlib import Path

import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

SCENARIOS = [("mistake1", "M1: missing lookup"), ("mistake2", "M2: lost context"),
             ("mistake3", "M3: runaway loop"), ("control", "Control")]

# (column, label, scenarios it applies to, higher_is_better)
METRICS = [
    ("task_success", "Task success", None, True),
    ("answer_correct", "Answer correct (judge)", None, True),
    ("process_ok", "Correct process", None, True),
    ("searched", "Searched policy documents", ["mistake1"], True),
    ("id_in_handoff", "Order ID reached order agent", ["mistake2"], True),
    ("invented_id", "Tool called with invented order ID", ["mistake2"], False),
    ("looped", "Same tool call repeated 3+ times", ["mistake3"], False),
]


def wilson(k, n, z=1.96):
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def fmt_rate(k, n):
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{100*k/n:.1f}% [{100*lo:.1f}, {100*hi:.1f}] ({k}/{n})"


def fmt_p(p):
    return "n/a" if p is None or (isinstance(p, float) and math.isnan(p)) else ("<0.001" if p < 0.001 else f"{p:.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("graded")
    ap.add_argument("--foundry")
    ap.add_argument("--out", default="results/paper")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_json(a.graded, lines=True)
    n_err = int(df["error"].notna().sum())
    df = df[df["error"].isna()].copy()
    print(f"{len(df)} graded runs ({n_err} errored runs excluded)")
    if df["answer_correct"].isna().any() if "answer_correct" in df else True:
        print("WARNING: some or all runs have no judge verdict; answer_correct and task_success will undercount.")

    # ---------------- main table ----------------
    rows = []
    for scen, label in SCENARIOS:
        s = df[df.scenario == scen]
        for col, mlabel, only, better in METRICS:
            if only and scen not in only:
                continue
            if col not in s:
                continue
            vals = {}
            for c in ("before", "after"):
                x = s[s.condition == c][col].dropna().astype(bool)
                vals[c] = (int(x.sum()), int(len(x)))
            (kb, nb), (ka, na) = vals["before"], vals["after"]
            p = fisher_exact([[kb, nb - kb], [ka, na - ka]])[1] if nb and na else None
            rows.append(dict(scenario=label, metric=mlabel, before=fmt_rate(kb, nb), after=fmt_rate(ka, na), p_value=fmt_p(p),
                             before_rate=kb / nb if nb else None, after_rate=ka / na if na else None, n_before=nb, n_after=na))
    t = pd.DataFrame(rows)
    t.to_csv(out / "table_main.csv", index=False)
    show = t[["scenario", "metric", "before", "after", "p_value"]]
    (out / "table_main.md").write_text(show.to_markdown(index=False), encoding="utf-8")
    (out / "table_main.tex").write_text(show.to_latex(index=False, escape=True), encoding="utf-8")
    print("\n" + show.to_markdown(index=False))

    # ---------------- efficiency ----------------
    eff = []
    for scen, label in SCENARIOS:
        s = df[df.scenario == scen]
        rec = {"scenario": label}
        for c in ("before", "after"):
            x = s[s.condition == c]
            if len(x) == 0:
                continue
            tok = x["input_tokens"] + x["output_tokens"]
            rec[f"latency_median_s_{c}"] = round(x["latency_s"].median(), 2)
            rec[f"latency_p95_s_{c}"] = round(x["latency_s"].quantile(0.95), 2)
            rec[f"tokens_mean_{c}"] = round(tok.mean(), 0)
            rec[f"model_calls_mean_{c}"] = round(x["n_model_calls"].mean(), 2)
            rec[f"tool_calls_mean_{c}"] = round(x["n_tool_calls"].mean(), 2)
        b, af = s[s.condition == "before"], s[s.condition == "after"]
        if len(b) and len(af):
            rec["latency_p"] = fmt_p(mannwhitneyu(b["latency_s"], af["latency_s"]).pvalue)
            rec["tokens_p"] = fmt_p(mannwhitneyu(b["input_tokens"] + b["output_tokens"],
                                                 af["input_tokens"] + af["output_tokens"]).pvalue)
        eff.append(rec)
    e = pd.DataFrame(eff)
    e.to_csv(out / "table_efficiency.csv", index=False)
    (out / "table_efficiency.md").write_text(e.to_markdown(index=False), encoding="utf-8")
    print("\n" + e.to_markdown(index=False))

    # ---------------- per question ----------------
    pq = df.pivot_table(index=["qid", "scenario"], columns="condition", values="task_success", aggfunc="mean").reset_index()
    pq.to_csv(out / "per_question.csv", index=False)

    # ---------------- Foundry evaluators ----------------
    if a.foundry and Path(a.foundry).exists():
        fe = pd.read_json(a.foundry, lines=True)
        pass_cols = [c for c in fe.columns if c.endswith("_pass")]
        frows = []
        for scen, label in SCENARIOS:
            for pc in pass_cols:
                rec = {"scenario": label, "evaluator": pc.removesuffix("_pass")}
                ks = {}
                for c in ("before", "after"):
                    x = fe[(fe.scenario == scen) & (fe.condition == c)][pc].dropna().astype(bool)
                    ks[c] = (int(x.sum()), len(x))
                    rec[c] = fmt_rate(*ks[c])
                (kb, nb), (ka, na) = ks["before"], ks["after"]
                rec["p_value"] = fmt_p(fisher_exact([[kb, nb - kb], [ka, na - ka]])[1]) if nb and na else "n/a"
                if nb or na:
                    frows.append(rec)
        f = pd.DataFrame(frows)
        (out / "table_foundry_evaluators.md").write_text(f.to_markdown(index=False), encoding="utf-8")
        f.to_csv(out / "table_foundry_evaluators.csv", index=False)
        print("\n" + f.to_markdown(index=False))

        # Agreement between built-in evaluators and our deterministic process metrics (validity check)
        m = fe.merge(df[["qid", "condition", "rep", "searched", "invented_id", "looped"]], on=["qid", "condition", "rep"])
        lines = ["# Evaluator vs deterministic metric agreement\n"]
        for ev, det, invert in [("tool_selection_pass", "searched", False), ("tool_input_accuracy_pass", "invented_id", True),
                                ("tool_call_success_pass", "looped", True), ("task_adherence_pass", "searched", False)]:
            if ev in m:
                x = m[[ev, det]].dropna()
                if len(x):
                    agree = ((x[ev].astype(bool)) == (~x[det].astype(bool) if invert else x[det].astype(bool))).mean()
                    lines.append(f"- {ev} vs {'not ' if invert else ''}{det}: {100*agree:.1f}% agreement (n={len(x)})")
        (out / "evaluator_agreement.md").write_text("\n".join(lines), encoding="utf-8")

    # ---------------- example traces for screenshots ----------------
    ex = ["# Trace ids for figures\n", "Open the project in the Foundry portal, then Agents > Traces (or App Insights > Transaction search) and search by trace id.\n"]
    for scen, label in SCENARIOS:
        s = df[df.scenario == scen]
        bad = s[(s.condition == "before") & (~s.task_success.astype(bool))]
        good = s[(s.condition == "after") & (s.task_success.astype(bool))]
        ex.append(f"## {label}")
        for name, part in (("before, failed", bad), ("after, succeeded", good)):
            for _, r in part.head(3).iterrows():
                ex.append(f"- {name}: {r.qid} rep{r.rep} trace `{r.get('trace_id')}` ({r.latency_s}s, {r.n_tool_calls} tool calls)")
        ex.append("")
    (out / "example_traces.md").write_text("\n".join(ex), encoding="utf-8")

    # ---------------- judge audit ----------------
    # The audit uses the stratified, blinded sample from src/audit.py (smoke review plan, step 10).
    print("\nJudge audit: python -m src.audit build <graded> (see src/audit.py)")

    # ---------------- figures ----------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ts = t[t.metric == "Task success"]
        fig, ax = plt.subplots(figsize=(3.5, 2.4), dpi=300)
        xs = range(len(ts))
        w = 0.38
        for i, (c, col) in enumerate((("before", "#9aa1ac"), ("after", "#e8500a"))):
            rates = ts[f"{c}_rate"].astype(float).values
            ns = ts[f"n_{c}"].values
            errs = [[max(0.0, r - wilson(round(r * n), n)[0]) for r, n in zip(rates, ns)],   # clamp float noise at 100%
                    [max(0.0, wilson(round(r * n), n)[1] - r) for r, n in zip(rates, ns)]]
            ax.bar([x + (i - 0.5) * w for x in xs], rates * 100, w, yerr=[[e * 100 for e in errs[0]], [e * 100 for e in errs[1]]],
                   capsize=2, color=col, label=c.capitalize(), error_kw={"lw": 0.6})
        ax.set_xticks(list(xs))
        ax.set_xticklabels([s.split(":")[0] for s in ts.scenario], fontsize=7)
        ax.set_ylabel("Task success (%)", fontsize=7)
        ax.set_ylim(0, 105)
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=6, frameon=False)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        fig.tight_layout()
        fig.savefig(out / "fig_success.png")

        m3 = df[df.scenario == "mistake3"]
        if len(m3):
            fig, ax = plt.subplots(figsize=(3.5, 2.2), dpi=300)
            ax.boxplot([m3[m3.condition == c]["latency_s"] for c in ("before", "after")], widths=0.5)
            ax.set_xticks([1, 2], ["Before", "After"])
            ax.set_ylabel("Conversation latency (s)", fontsize=7)
            ax.tick_params(labelsize=7)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
            fig.tight_layout()
            fig.savefig(out / "fig_mistake3_latency.png")
    except Exception as e:  # noqa: BLE001
        print(f"Figures skipped: {e}")

    print(f"\nAll outputs in {out}/")


if __name__ == "__main__":
    main()
