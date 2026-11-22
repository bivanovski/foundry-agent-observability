"""B5: recompute every number claimed in paper v3 from the run and grading files (not from summary tables).

    .venv/bin/python results/paper/v3_checks/b5_recompute.py   (run from the repo root)
    -> results/paper/v3_checks/b5_numbers.csv, b5_numbers.md

Bootstrap CIs use the paper's method (resample items, ratio of sums) with 20,000 resamples and a fixed seed;
they are compared with the paper allowing Monte Carlo noise of +-0.15 in the last reported digit.
Claim 34 (kappa on the audit sample) is computed as an aggregate only: per-answer verdicts are never printed,
and audit_key.csv is not opened (the 40 items are identified from results/main.judge2.jsonl).
"""
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

R = Path("results")
OUT = R / "paper" / "v3_checks"
B = 20000


def load(stem):
    g = pd.read_json(R / f"{stem}.graded.jsonl", lines=True)
    tq = pd.read_json("data/testset.jsonl", lines=True).set_index("id")
    g["subtype"] = g.qid.map(tq["subtype"])
    g["tokens"] = g.input_tokens + g.output_tokens
    j3 = pd.read_json(R / f"{stem}.judge3.jsonl", lines=True)[["qid", "condition", "rep", "answer_correct_v3"]]
    g = g.merge(j3, on=["qid", "condition", "rep"], how="left")
    return g


A = {"5m": load("main"), "41m": load("main_gpt41mini")}
FE = {"5m": pd.read_json(R / "main.foundry_eval.jsonl", lines=True),
      "41m": pd.read_json(R / "main_gpt41mini.foundry_eval.jsonl", lines=True)}


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def boot(d, col, seed=7):
    """after - before, items resampled; d must hold one scenario."""
    rng = np.random.default_rng(seed)
    d = d[d[col].notna()].copy()
    d[col] = d[col].astype(float)
    items = sorted(d.qid.unique())
    S = {}
    for c in ("before", "after"):
        g = d[d.condition == c].groupby("qid")[col]
        S[c] = (g.sum().reindex(items, fill_value=0).to_numpy(), g.count().reindex(items, fill_value=0).to_numpy())
    pt = S["after"][0].sum() / S["after"][1].sum() - S["before"][0].sum() / S["before"][1].sum()
    idx = rng.integers(0, len(items), size=(B, len(items)))
    bs = S["after"][0][idx].sum(1) / S["after"][1][idx].sum(1) - S["before"][0][idx].sum(1) / S["before"][1][idx].sum(1)
    return pt, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def kappa(a, b):
    a, b = list(a), list(b)
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(k) / n) * (b.count(k) / n) for k in set(a) | set(b))
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def sc(arm, scen, cond=None):
    d = A[arm]
    d = d[(d.scenario == scen) & d.error.isna()]
    return d if cond is None else d[d.condition == cond]


def k_of_n(s):
    s = s.dropna().astype(bool)
    return f"{int(s.sum())}/{len(s)}"


rows = []


def add(n, claim, paper, computed, status, note=""):
    rows.append(dict(n=n, claim=claim, paper=paper, recomputed=computed, status=status, note=note))


# 1
c = {a: (len(d), int(d.error.notna().sum())) for a, d in A.items()}
add(1, "Conversations per model", "400 completed, 0 excluded",
    f"5m {c['5m'][0]} rows, {c['5m'][1]} errors; 41m {c['41m'][0]} rows, {c['41m'][1]} errors",
    "MATCH" if all(v == (400, 0) for v in c.values()) else "MISMATCH")
# 2
v = {(a, cd): k_of_n(sc(a, "mistake1", cd).n_file_search_calls > 0) for a in A for cd in ("before", "after")}
add(2, "F1 searched, B and A, both models", "60/60", str(v), "MATCH" if set(v.values()) == {"60/60"} else "MISMATCH")
# 3
v = {(a, cd): k_of_n(sc(a, "mistake2", cd).invented_id.astype(bool) | sc(a, "mistake2", cd).wrong_id.astype(bool)) for a in A for cd in ("before", "after")}
add(3, "F2 invented or wrong ID, B and A, both models", "0/60", str(v), "MATCH" if set(v.values()) == {"0/60"} else "MISMATCH")
# 4
v = {a: k_of_n(sc(a, "mistake2", "before").pipe(lambda x: x[x.subtype.isin(["id_first", "id_buried"])]).id_in_handoff) for a in A}
add(4, "Order ID in handoff, B runs with an ID, both models", "40/40", str(v), "MATCH" if set(v.values()) == {"40/40"} else "MISMATCH")
# 5
v = {(a, cd): k_of_n(sc(a, "mistake2", cd).pipe(lambda x: x[x.subtype == "no_id"]).n_tool_calls == 0) for a in A for cd in ("before", "after")}
add(5, "no_id items: no tool call", "20/20", str(v), "MATCH" if set(v.values()) == {"20/20"} else "MISMATCH")
# 6
b, a_ = sc("5m", "mistake3", "before"), sc("5m", "mistake3", "after")
pt, lo, hi = boot(sc("5m", "mistake3"), "n_identical_calls")
txt = f"mean {b.n_identical_calls.mean():.2f} (max {b.n_identical_calls.max()}) -> {a_.n_identical_calls.mean():.2f} ({a_.n_identical_calls.max()}); diff {pt:+.2f} [{lo:+.2f}, {hi:+.2f}]"
ok = (round(b.n_identical_calls.mean(), 2) == 2.42 and b.n_identical_calls.max() == 7 and a_.n_identical_calls.mean() == 1.0
      and abs(lo - (-1.9)) <= 0.15 and abs(hi - (-1.0)) <= 0.15)
add(6, "F3 5m identical calls per run", "2.42 (7) -> 1.00 (1); -1.4 [-1.9, -1.0]", txt, "MATCH" if ok else "CHECK",
    "CI bounds vary by about +-0.1 between bootstrap runs; the package tables show [-2.0, -1.1] (prereg) and [-1.9, -1.0] (model comparison)")
# 7
add(7, "F3 5m looped", "9/40 -> 0/40", f"{k_of_n(b.looped)} -> {k_of_n(a_.looped)}",
    "MATCH" if (k_of_n(b.looped), k_of_n(a_.looped)) == ("9/40", "0/40") else "MISMATCH")
# 8
pt, lo, hi = boot(sc("5m", "mistake3"), "task_success")
txt = f"{100*b.task_success.mean():.1f}% -> {100*a_.task_success.mean():.1f}%; {100*pt:+.1f} pp [{100*lo:+.1f}, {100*hi:+.1f}]"
ok = abs(100 * b.task_success.mean() - 62.5) < 0.05 and abs(100 * a_.task_success.mean() - 95.0) < 0.05 and abs(100 * lo - 15.0) <= 2.6 and abs(100 * hi - 55.0) <= 2.6
add(8, "F3 5m task success (v2)", "62.5% -> 95.0%; +32.5 pp [+15.0, +55.0]", txt, "MATCH" if ok else "CHECK",
    "with 8 items, CI bounds move in steps of 2.5 pp between bootstrap runs")
# 9
pt, lo, hi = boot(sc("5m", "mistake3"), "tokens")
add(9, "F3 5m tokens per conversation", "-638 [-1,166, -168]", f"{pt:+.1f} [{lo:+.0f}, {hi:+.0f}]",
    "MATCH" if round(pt) == -638 else "MISMATCH", "point estimate exact; CI bounds vary between bootstrap runs (package: [-1,235, -171] prereg, [-1,166, -168] comparison)")
# 10
pt, lo, hi = boot(sc("5m", "mistake3"), "latency_s")
add(10, "F3 5m latency per conversation", "-3.1 s [-4.5, -1.6]", f"{pt:+.2f} s [{lo:+.2f}, {hi:+.2f}]",
    "MATCH" if round(pt, 1) == -3.1 else "MISMATCH", "point estimate exact; CI bounds vary by about +-0.1")
# 11
loops = b.groupby("qid").looped.apply(lambda s: f"{int(s.sum())}/{len(s)}").to_dict()
add(11, "F3 5m loops by item", "X08 5/5, X07 0/5", str(loops),
    "MATCH" if loops.get("X08") == "5/5" and loops.get("X07") == "0/5" else "MISMATCH")
# 12
b41, a41 = sc("41m", "mistake3", "before"), sc("41m", "mistake3", "after")
add(12, "F3 41m identical calls", "mean 1.05, max 2", f"mean {b41.n_identical_calls.mean():.3f}, max {b41.n_identical_calls.max()}",
    "MATCH" if round(b41.n_identical_calls.mean(), 2) == 1.05 and b41.n_identical_calls.max() == 2 else "MISMATCH")
# 13
add(13, "Asked to re-confirm a valid ID", "41m 40/40 -> 0/40; 5m 18/40 -> 0/40",
    f"41m {k_of_n(b41.asked_to_confirm_id)} -> {k_of_n(a41.asked_to_confirm_id)}; 5m {k_of_n(b.asked_to_confirm_id)} -> {k_of_n(a_.asked_to_confirm_id)}",
    "MATCH" if (k_of_n(b41.asked_to_confirm_id), k_of_n(a41.asked_to_confirm_id), k_of_n(b.asked_to_confirm_id), k_of_n(a_.asked_to_confirm_id)) == ("40/40", "0/40", "18/40", "0/40") else "MISMATCH")
# 14
add(14, "F3 41m task success (v2)", "2.5% -> 97.5%", f"{100*b41.task_success.mean():.1f}% -> {100*a41.task_success.mean():.1f}%",
    "MATCH" if (round(100 * b41.task_success.mean(), 1), round(100 * a41.task_success.mean(), 1)) == (2.5, 97.5) else "MISMATCH")
# 15
v = {(a, cd): k_of_n(sc(a, "control", cd).route_ok) for a in A for cd in ("before", "after")}
add(15, "Controls routed correctly", "100%", str(v), "MATCH" if set(v.values()) == {"40/40"} else "MISMATCH")
# 16
v = {(a, cd): f"{100*sc(a, 'control', cd).answer_correct.astype(float).mean():.1f}%" for a in A for cd in ("before", "after")}
ok = [v[("5m", "before")], v[("5m", "after")], v[("41m", "before")], v[("41m", "after")]] == ["70.0%", "80.0%", "75.0%", "87.5%"]
add(16, "Controls answer correct (v2)", "5m 70.0% -> 80.0%; 41m 75.0% -> 87.5%", str(v), "MATCH" if ok else "MISMATCH")
# 17
sp5 = pd.read_csv(R / "main.spans.csv")
t = sp5[(sp5.operation_Id == "2e0fea3c358956c0af5913063bea5867") & sp5.name.str.startswith("invoke_agent order") & ~sp5.name.str.contains(":")]
add(17, "Order-agent span, trace 2e0fea3c...", "about 18 s (18,458 ms)", f"{t.duration.iloc[0]:.0f} ms", "MATCH" if round(t.duration.iloc[0]) == 18458 else "MISMATCH")
# 18, 19 from the KQL run (A1 output, written by src/kql_assertions.py)
kq = OUT / "kql_assertions_v3.csv"
if kq.exists():
    k = pd.read_csv(kq)
    rep_hits = int(k.repetition_hits.sum())
    client_loops = int(k.client_looped.sum())
    om_hits = int(k.omission_hits.sum())
    add(18, "Repetition KQL", "9 hits = 9 client loops; 0 elsewhere", f"{rep_hits} hits, {client_loops} client loops; per row: {k[['model','condition','repetition_hits']].values.tolist()}",
        "MATCH" if rep_hits == client_loops == 9 else "MISMATCH")
else:
    add(18, "Repetition KQL", "9 hits = 9 client loops", "run A1 first", "PENDING")
pol = {a: int((d.specialist.fillna("").str.startswith("policy") & d.error.isna()).sum()) for a, d in A.items()}
if kq.exists():
    add(19, "Omission KQL", "0 hits; policy agent reached in 300 (150 per model)", f"{om_hits} hits; policy agent reached: {pol}",
        "MATCH" if om_hits == 0 and pol == {"5m": 150, "41m": 150} else "MISMATCH")
# 20
calls = []
for a, d in A.items():
    for _, r in d[d.error.isna()].iterrows():
        for tc in r.tool_calls or []:
            oid = str(tc["args"].get("order_id", "")).lstrip("#")
            calls.append(dict(arm=a, in_msg=bool(oid) and oid in r.message))
cdf = pd.DataFrame(calls)
by = cdf.groupby("arm").in_msg.agg(["size", "sum"]).to_dict("index")
add(20, "Provenance: function-tool calls, IDs found in the customer message", "411 (246 + 165), all found",
    f"5m {by['5m']['size']} calls ({by['5m']['sum']} found); 41m {by['41m']['size']} calls ({by['41m']['sum']} found)",
    "MATCH" if (by["5m"]["size"], by["41m"]["size"]) == (246, 165) and cdf.in_msg.all() else "MISMATCH")
# 21
sp41 = pd.read_csv(R / "main_gpt41mini.spans.csv")
def errspans(sp):
    e = sp[sp.success.astype(str).str.lower() == "false"]
    return e.name.str.replace(r"(invoke_agent [^:]+):.*", r"\1:<v>", regex=True).str.replace(r"^POST .*", "POST <http>", regex=True).value_counts().to_dict()
e5, e41 = errspans(sp5), errspans(sp41)
inv41 = sum(v for k_, v in e41.items() if k_.startswith("invoke_agent"))
add(21, "Spans with error status", "none in 5m; 41m only 557 POST + 557 invoke_agent (HTTP 429)",
    f"5m {e5 or 'none'}; 41m {e41}", "MATCH" if not e5 and e41.get("POST <http>") == 557 and inv41 == 557 and len(e41) <= 2 else "CHECK")
# 22
rl = pd.read_csv(R / "rate_limit_retries.csv")
r41 = rl[rl.model == "gpt-4.1-mini"]
tc41 = pd.read_csv(R / "main_gpt41mini.trace_check.csv")
add(22, "41m HTTP 429", "557 requests in 183/400 (46%); 214 vs 150",
    f"{int(r41.rate_limited_requests.sum())} requests in {int((r41.rate_limited_requests > 0).sum())}/400 ({100*(r41.rate_limited_requests > 0).mean():.1f}%); "
    f"file-search spans {int(tc41.file_search_spans.sum())} vs logged {int(tc41.file_search_logged.sum())}",
    "MATCH" if (int(r41.rate_limited_requests.sum()), int((r41.rate_limited_requests > 0).sum()), int(tc41.file_search_spans.sum()), int(tc41.file_search_logged.sum())) == (557, 183, 214, 150) else "MISMATCH")
# 23
ok5 = A["5m"][A["5m"].answer_correct == True]  # noqa: E712
add(23, "Correct 5m runs over 10 s", "63.0% of 324; p50 11.3 s, p95 16.5 s",
    f"{100*(ok5.latency_s > 10).mean():.1f}% of {len(ok5)}; p50 {ok5.latency_s.median():.1f} s, p95 {ok5.latency_s.quantile(.95):.1f} s",
    "MATCH" if len(ok5) == 324 and round(100 * (ok5.latency_s > 10).mean(), 1) == 63.0 and round(ok5.latency_s.median(), 1) == 11.3 and round(ok5.latency_s.quantile(.95), 1) == 16.5 else "MISMATCH")
# 24
def triage(d):
    t = pd.DataFrame([s for st in d.steps for s in st if s["step"] == "triage"])
    return t.output_tokens.mean(), (t.reasoning_tokens.astype(float) / t.output_tokens).mean()
o5, r5 = triage(A["5m"]); o41, _ = triage(A["41m"])
add(24, "Triage output tokens", "mean 282, 71% reasoning (5m); 33 (41m)", f"5m mean {o5:.1f}, reasoning share {100*r5:.1f}%; 41m mean {o41:.1f}",
    "MATCH" if round(o5) == 282 and round(100 * r5) == 71 and round(o41) == 33 else "MISMATCH")
# 25
tb, ta = b41.tokens.mean(), a41.tokens.mean()
add(25, "F3 41m tokens per conversation", "+34% (652.7 -> 875.1)", f"{tb:.1f} -> {ta:.1f} ({100*(ta/tb-1):+.1f}%)",
    "MATCH" if (round(tb, 1), round(ta, 1), round(100 * (ta / tb - 1))) == (652.7, 875.1, 34) else "MISMATCH")
# 26
tcb, tca = b.n_tool_calls.mean(), a_.n_tool_calls.mean()
tkp = 100 * (a_.tokens.mean() / b.tokens.mean() - 1)
add(26, "Table III F3 5m", "tool calls 2.67 -> 1.02; tokens -27%; median latency 11.8 -> 9.2 s",
    f"tool calls {tcb:.3f} -> {tca:.3f}; tokens {b.tokens.mean():.1f} -> {a_.tokens.mean():.1f} ({tkp:+.1f}%); median latency {b.latency_s.median():.2f} -> {a_.latency_s.median():.2f} s",
    "MATCH" if (round(tcb, 2), round(tca, 2), round(tkp), round(b.latency_s.median(), 1), round(a_.latency_s.median(), 1)) == (2.67, 1.02, -27, 11.8, 9.2) else "CHECK")
# 27
t41b, t41a = b41.n_tool_calls.mean(), a41.n_tool_calls.mean()
add(27, "Table III F3 41m tool calls", "1.07 -> 1.00", f"{t41b:.4f} -> {t41a:.4f} (= {int(b41.n_tool_calls.sum())}/40 -> {int(a41.n_tool_calls.sum())}/40)",
    "MATCH" if f"{t41b:.2f}" == "1.07" and f"{t41a:.2f}" == "1.00" else "ROUNDING",
    "43/40 = 1.075 exactly: '1.07' (round half to even / float) or '1.08' (round half up); consider writing 1.075 or 1.08")
# 28
ts = {a: k_of_n(f[(f.scenario == "mistake1")].tool_selection_pass) for a, f in FE.items()}
tsn = {a: int((f[(f.scenario == "mistake1")].get("tool_selection_result", pd.Series(dtype=str)) == "not_applicable").sum()) for a, f in FE.items()}
add(28, "Tool Selection (F1)", "240/240 pass", f"{ts}; not_applicable {tsn}",
    "MATCH" if ts == {"5m": "120/120", "41m": "120/120"} else "MISMATCH")
# 29
taf = {(a, cd): int((f[(f.scenario == "mistake1") & (f.condition == cd)].task_adherence_result == "fail").sum()) for a, f in FE.items() for cd in ("before", "after")}
jv2 = {(a, cd): f"{100*sc(a, 'mistake1', cd).answer_correct.astype(float).mean():.1f}%" for a in A for cd in ("before", "after")}
ok = taf == {("5m", "before"): 14, ("5m", "after"): 22, ("41m", "before"): 28, ("41m", "after"): 29}
add(29, "Task Adherence fails on F1 (B/A)", "5m 14/60, 22/60; 41m 28/60, 29/60 (23-48%); judge v2 F1 correct 98-100%",
    f"fails {taf} (= {100*min(taf.values())/60:.1f}%-{100*max(taf.values())/60:.1f}%); judge v2 correct {jv2}", "MATCH" if ok else "MISMATCH",
    "see B1: these fails are partly caused by our truncation of search results")
# 30
def tool_runs(a):
    f = FE[a][FE[a].scenario == "mistake2"]
    g = A[a][A[a].scenario == "mistake2"][["qid", "condition", "rep", "n_tool_calls"]]
    m = f.merge(g, on=["qid", "condition", "rep"])
    m = m[m.n_tool_calls > 0]
    return len(m), int((m.tool_input_accuracy_pass == True).sum()), int((m.tool_call_accuracy_pass == True).sum())  # noqa: E712
t5, t41 = tool_runs("5m"), tool_runs("41m")
add(30, "Tool Input Accuracy and Tool Call Accuracy, runs with a tool call", "passed 160/160",
    f"5m {t5[0]} runs: TIA {t5[1]}, TCA {t5[2]}; 41m {t41[0]} runs: TIA {t41[1]}, TCA {t41[2]}; total {t5[0]+t41[0]}",
    "MATCH" if t5[0] + t41[0] == 160 and t5[1] == t5[2] == t5[0] and t41[1] == t41[2] == t41[0] else "MISMATCH")
# 31
v = {(a, cd): (k_of_n(f[(f.scenario == "mistake3") & (f.condition == cd)].task_completion_pass), k_of_n(f[(f.scenario == "mistake3") & (f.condition == cd)].tool_call_success_pass)) for a, f in FE.items() for cd in ("before", "after")}
add(31, "Task Completion and Tool Call Success on F3", "0/40 pass, both conditions, both models", str(v),
    "MATCH" if all(x == ("0/40", "0/40") for x in v.values()) else "MISMATCH")
# 32
ir = FE["41m"][(FE["41m"].scenario == "mistake3") & (FE["41m"].condition == "before")]
blk = {a: f[f.get("intent_resolution_result", pd.Series(dtype=str)) == "blocked_content_filter"][["qid", "condition", "rep"]].values.tolist() for a, f in FE.items()}
add(32, "Intent Resolution 41m F3 B; content filter", "37/40 pass; 3 blocked (5m O04 B)", f"41m F3 B: {k_of_n(ir.intent_resolution_pass)}; blocked: {blk}",
    "MATCH" if k_of_n(ir.intent_resolution_pass) == "37/40" and len(blk["5m"]) == 3 and all(x[0] == "O04" and x[1] == "before" for x in blk["5m"]) and not blk["41m"] else "MISMATCH")
# 33
m2 = sc("5m", "mistake2")
v2, v3 = m2.answer_correct.astype(bool), m2.answer_correct_v3.astype(bool)
add(33, "Judge v3 on F2 5m", "changed 32/120 (28 to correct, 4 to incorrect)",
    f"changed {int((v2 != v3).sum())}/{len(m2)} ({int((~v2 & v3).sum())} to correct, {int((v2 & ~v3).sum())} to incorrect)",
    "MATCH" if (int((v2 != v3).sum()), int((~v2 & v3).sum()), int((v2 & ~v3).sum())) == (32, 28, 4) else "MISMATCH")
# 34 (aggregate only; audit_key.csv not opened)
j2 = pd.read_json(R / "main.judge2.jsonl", lines=True)
m = j2.merge(A["5m"][["qid", "condition", "rep", "answer_correct", "answer_correct_v3"]], on=["qid", "condition", "rep"])
k2, k3 = kappa(m.answer_correct.astype(bool), m.answer_correct_judge2.astype(bool)), kappa(m.answer_correct_v3.astype(bool), m.answer_correct_judge2.astype(bool))
add(34, "Second judge vs v2 / vs v3", "kappa 0.41 / 0.74 (n = 40)", f"kappa {k2:.2f} / {k3:.2f} (n = {len(m)})",
    "MATCH" if (round(k2, 2), round(k3, 2), len(m)) == (0.41, 0.74, 40) else "MISMATCH", "aggregate only; no per-answer verdict shown")
# 35
r35 = {}
for a in A:
    d = sc(a, "mistake2")
    for col in ("answer_correct", "answer_correct_v3"):
        pt, lo, hi = boot(d, col)
        r35[(a, col)] = f"{100*pt:+.1f} pp [{100*lo:+.1f}, {100*hi:+.1f}] ({100*d[d.condition=='before'][col].astype(float).mean():.1f}% -> {100*d[d.condition=='after'][col].astype(float).mean():.1f}%)"
ok = (r35[("5m", "answer_correct")].startswith("+11.7") and r35[("5m", "answer_correct_v3")].startswith("+8.3")
      and r35[("41m", "answer_correct")].startswith("+16.7") and r35[("41m", "answer_correct_v3")].startswith("+0.0"))
add(35, "F2 judged gain", "5m v2 +11.7 [+1.7, +21.7], v3 +8.3 [-1.7, +21.7]; 41m v2 +16.7, v3 0 (83.3% both)", str(r35),
    "MATCH" if ok else "MISMATCH", "point estimates exact; CI bounds move in steps of about 1.7 pp between bootstrap runs")
# 36
soc = A["5m"][(A["5m"].scenario == "control") & (A["5m"].subtype == "social")]
acc = {cd: f"{int(soc[soc.condition == cd].answer_correct.astype(bool).sum())}/{len(soc[soc.condition == cd])}" for cd in ("before", "after")}
rej = sorted(soc[~soc.answer_correct.astype(bool)].qid.unique())
add(36, "5m social controls accepted", "15/25 -> 17/25; all rejections R03 or R04", f"{acc['before']} -> {acc['after']}; rejected items {rej}",
    "MATCH" if acc == {"before": "15/25", "after": "17/25"} and set(rej) <= {"R03", "R04"} else "MISMATCH")
# 37
lo, hi = wilson(0, 60)
lo2, hi2 = wilson(0, 120)
add(37, "F1 omission rate upper bound", "below 6% at 95% (Wilson, 0/60)", f"Wilson upper bound for 0/60 = {100*hi:.2f}%; for 0/120 (both models pooled) = {100*hi2:.2f}%",
    "MISMATCH", "6.02% is not below 6%; write 'at most 6.0%' per model, or 'below 3.2%' pooled over both models (0/120)")

df = pd.DataFrame(rows)
df.to_csv(OUT / "b5_numbers.csv", index=False)
md = ["| # | Claim | Paper | Recomputed | Status | Note |", "|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r['n']} | {r['claim']} | {r['paper']} | {r['recomputed']} | **{r['status']}** | {r['note']} |")
(OUT / "b5_numbers.md").write_text("\n".join(md) + "\n")
print(df[["n", "status", "recomputed"]].to_string(index=False, max_colwidth=150))
