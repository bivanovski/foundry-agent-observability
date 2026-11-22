"""Model comparison (CHANGELOG 2026-11-16, "agent model as a second factor").

    python -m src.compare_models gpt-5-mini=results/main.graded.jsonl gpt-4.1-mini=results/main_gpt41mini.graded.jsonl

Writes to results/paper/models/:
  table_models.md / .csv   every pre-registered primary metric per model: before, after (Wilson CI), effect of the fix
                           (after - before, item-bootstrap 95% CI), and the difference in fix effect between models
                           (second model minus first, paired item bootstrap: the same items are resampled for both)
  table_models_efficiency.md  latency and tokens per model and condition
  fig_models.png           primary metric per scenario, model and condition
"""
import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .analyze_prereg import SC, metric_row, metrics_for, wilson

B = 5000
RNG = np.random.default_rng(2028)


def load(path):
    df = pd.read_json(path, lines=True)
    df = df[df.error.isna()].copy()
    tq = pd.read_json("data/testset.jsonl", lines=True).set_index("id")
    df["subtype"] = df.qid.map(tq["subtype"])
    df["total_tokens"] = df.input_tokens + df.output_tokens
    df["no_tool_call"] = df.n_tool_calls == 0
    return df


def per_item(d, col, kind):
    d = d[d[col].notna()].copy()
    if kind == "rate":
        d[col] = d[col].astype(bool).astype(int)
    out = {}
    for c in ("before", "after"):
        g = d[d.condition == c].groupby("qid")[col]
        out[c] = (g.sum(), g.count())
    return out


def did(d1, d2, col, kind):
    """(after-before) in model 2 minus (after-before) in model 1, resampling items jointly."""
    a1, a2 = per_item(d1, col, kind), per_item(d2, col, kind)
    items = sorted(set(d1.qid) | set(d2.qid))
    if not items:
        return (math.nan,) * 3

    def arr(a, c, i):
        return a[c][i].reindex(items, fill_value=0).to_numpy(float)

    S = {(m, c): (arr(a, c, 0), arr(a, c, 1)) for m, a in ((1, a1), (2, a2)) for c in ("before", "after")}

    def eff(m, idx=None):
        r = {}
        for c in ("before", "after"):
            s, n = S[(m, c)]
            if idx is None:
                r[c] = s.sum() / n.sum() if n.sum() else np.nan
            else:
                with np.errstate(invalid="ignore", divide="ignore"):
                    r[c] = s[idx].sum(1) / n[idx].sum(1)
        return r["after"] - r["before"]

    point = eff(2) - eff(1)
    idx = RNG.integers(0, len(items), size=(B, len(items)))
    bs = eff(2, idx) - eff(1, idx)
    bs = bs[~np.isnan(bs)]
    if not len(bs):
        return (point, math.nan, math.nan)
    return (point, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+", help="label=path/to/graded.jsonl, first one is the reference")
    ap.add_argument("--out", default="results/paper/models")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    arms = [(x.split("=", 1)[0], load(x.split("=", 1)[1])) for x in a.arms]
    ref_label, ref = arms[0]

    rows = []
    for scen, slabel in SC.items():
        for i, (dd_ref, col, mlabel, kind) in enumerate(metrics_for(scen, ref[ref.scenario == scen])):
            if "primary" not in mlabel and "exploratory" not in mlabel:
                continue
            for label, df in arms:
                dd = metrics_for(scen, df[df.scenario == scen])[i][0]
                r = metric_row(dd, col, mlabel, kind)
                rec = dict(scenario=slabel, metric=mlabel.replace(" [primary]", ""), model=label, before=r["before"],
                           after=r["after"], fix_effect=r["diff_after_minus_before"], before_rate=r["before_rate"],
                           after_rate=r["after_rate"], effect=r["diff"], effect_lo=r["diff_lo"], effect_hi=r["diff_hi"])
                if label != ref_label:
                    p, lo, hi = did(dd_ref, dd, col, kind)
                    unit = 100 if kind == "rate" else 1
                    rec[f"effect_vs_{ref_label}"] = (f"{unit * p:+.1f}{' pp' if kind == 'rate' else ''} "
                                                    f"[{unit * lo:+.1f}, {unit * hi:+.1f}]") if not math.isnan(p) else "n/a"
                rows.append(rec)
    T = pd.DataFrame(rows)
    T.to_csv(out / "table_models.csv", index=False)
    cols = ["scenario", "metric", "model", "before", "after", "fix_effect"] + [c for c in T.columns if c.startswith("effect_vs_")]
    txt = ["# Model comparison: pre-registered primary metrics\n",
           f"Reference model: {ref_label}. `fix_effect` = after minus before with a 95% bootstrap CI over items. "
           f"`effect_vs_{ref_label}` = this model's fix effect minus the reference model's, paired bootstrap over items "
           "(a CI that excludes 0 means the fix works differently on the two models).\n",
           T[cols].fillna("").to_markdown(index=False)]
    (out / "table_models.md").write_text("\n".join(txt) + "\n")

    eff = []
    for label, df in arms:
        for scen, slabel in SC.items():
            for c in ("before", "after"):
                x = df[(df.scenario == scen) & (df.condition == c)]
                ok = x[x.answer_correct == True]  # noqa: E712
                eff.append(dict(model=label, scenario=slabel, condition=c, runs=len(x),
                                latency_p50_s=round(x.latency_s.median(), 2), latency_p95_s=round(x.latency_s.quantile(.95), 2),
                                correct_over_10s=f"{100 * (ok.latency_s > 10).mean():.1f}%" if len(ok) else "n/a",
                                tokens_mean=round(x.total_tokens.mean()), answer_correct=f"{100 * x.answer_correct.astype(float).mean():.1f}%"))
    E = pd.DataFrame(eff)
    E.to_csv(out / "table_models_efficiency.csv", index=False)
    (out / "table_models_efficiency.md").write_text(
        "# Latency, tokens and judged correctness per model\n\n"
        "**Do not compare latency between models.** gpt-4.1-mini agent requests were rate-limited (HTTP 429) and retried in "
        "about 46% of conversations, gpt-5-mini in none (data/rate_limit_retries.csv). Compare before vs after within a model only.\n\n"
        + E.to_markdown(index=False) + "\n")
    print("\n".join(txt))
    print("\n" + E.to_markdown(index=False))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        prim = T.drop_duplicates(["scenario", "metric", "model"])
        panels = prim.groupby("scenario", sort=False).first().reset_index()[["scenario", "metric"]]
        fig, axes = plt.subplots(1, len(panels), figsize=(7.2, 2.3), dpi=300)
        for ax, (_, p) in zip(np.atleast_1d(axes), panels.iterrows()):
            sub = prim[(prim.scenario == p.scenario) & (prim.metric == p.metric)]
            is_rate = "%" in str(sub.before.iloc[0])
            for j, (_, r) in enumerate(sub.iterrows()):
                for k, (c, colr) in enumerate((("before", "#9aa1ac"), ("after", "#e8500a"))):
                    v = r[f"{c}_rate"] * (100 if is_rate else 1)
                    ax.bar(j + (k - 0.5) * 0.38, v, 0.38, color=colr, label=c.capitalize() if j == 0 else None)
            ax.set_xticks(range(len(sub)), sub.model, fontsize=6)
            ax.set_title(f"{p.scenario.split()[0]}: {p.metric[:38]}", fontsize=6)
            ax.tick_params(labelsize=6)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
        np.atleast_1d(axes)[0].legend(fontsize=5, frameon=False)
        fig.tight_layout()
        fig.savefig(out / "fig_models.png")
    except Exception as e:  # noqa: BLE001
        print(f"Figure skipped: {e}")
    print(f"\nAll outputs in {out}/")


if __name__ == "__main__":
    main()
