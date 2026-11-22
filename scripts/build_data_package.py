"""Builds the data package for writing the paper (smoke review plan, section D).

It is meant to be read by people AND fed to an LLM agent, so it is self-describing:
  START_HERE.md        entry point: what the experiment is, which file answers which question, rules for using the numbers
  manifest.json        machine-readable list of every file with its purpose, row count and key columns
  DATA_DICTIONARY.md   every column of runs.csv and the graded JSONL, with its exact definition
  results/             pre-registered tables, latency, triage, trace assertions, evaluators, figures
  data/                runs.csv, graded JSONL, evaluator results, span export, trace check
  method/              conditions.md, testset.jsonl, CHANGELOG.md, policy documents
  audit/               human audit status (and results once the two authors have labelled)
  traces.md            2-3 trace ids per scenario and condition for Fig. 2 and the examples

    python scripts/build_data_package.py   -> results/package/ and results/package_<date>.zip
"""
import csv
import json
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import config  # noqa: E402

R = ROOT / "results"
PKG = R / "package"
STEM = "main"
# (results file stem, model label); the first arm is the primary analysis
ARMS = [("main", "gpt-5-mini"), ("main_gpt41mini", "gpt-4.1-mini")]

DICT = [
    # (column, definition)
    ("qid", "Test item id. P = policy (M1), O = order (M2), X = order system down (M3), R = control."),
    ("scenario", "mistake1 (missing lookup), mistake2 (lost context), mistake3 (runaway loop), control."),
    ("subtype", "Item design: prior_conflict / easy (M1); id_first / id_buried / no_id (M2); plain / insist (M3); social / uncovered (control)."),
    ("condition", "before = the three bugs; after = the three fixes. Exact texts in method/conditions.md."),
    ("rep", "Repetition 1-5. Repetitions of one item are NOT independent samples."),
    ("route", "Triage decision: policy, order or none."),
    ("route_ok", "Triage route equals the expected route."),
    ("searched", "The policy agent ran at least one file_search (deterministic, from the recorded run). M1 primary metric."),
    ("n_file_search_calls", "Number of file_search calls by the policy agent."),
    ("n_tool_calls", "Number of client-executed function tool calls (get_order_status, create_return)."),
    ("invented_id", "A function tool was called with an order ID that does not appear in the customer's message. M2 primary metric."),
    ("wrong_id", "A function tool was called with any ID other than the expected order ID (includes decoys from the message, e.g. a postcode). M2 primary metric."),
    ("id_in_handoff", "The expected order ID appears in the text handed to the specialist. Empty for items without an ID."),
    ("id_missing_from_handoff", "Negation of id_in_handoff (items with an ID only). M2 metrics are also reported conditional on this."),
    ("asked_for_id", "Heuristic: the answer mentions an order number and asks a question. Meaningful for no_id items."),
    ("n_identical_calls", "Highest number of identical tool calls (same tool, same arguments) in the run. M3 primary metric."),
    ("looped", "n_identical_calls >= 3 or the 8-round cap was hit. M3 secondary metric."),
    ("asked_to_confirm_id", "EXPLORATORY, added post hoc: the answer asks the customer to confirm or re-provide an order number although a valid one was given (heuristic on the answer text). Shows how a bare tool error is misdiagnosed."),
    ("offered_email", "The answer mentions email. Deterministic side check for M3; only the 'after' error text suggests email."),
    ("process_ok", "Deterministic process criterion per category (route, search, correct ID, no repeated calls)."),
    ("answer_correct", "LLM judge v2 verdict (gpt-5-mini-judge, reasoning effort medium, sees expected behaviour, expected facts and the policy documents)."),
    ("judge_reason", "One-sentence reason from judge v2."),
    ("answer_correct_v3", "Judge v3 verdict (post hoc, not pre-registered): same model and effort as v2, additionally sees the tool definitions, every tool call with its result, and the fixed date (19 November 2026)."),
    ("task_success_v3", "process_ok AND answer_correct_v3 (post hoc)."),
    ("judge_v3_reason", "One-sentence reason from judge v3."),
    ("task_success", "process_ok AND answer_correct."),
    ("latency_s", "Wall-clock seconds for the whole conversation (triage + specialist + tool rounds)."),
    ("input_tokens / output_tokens", "Tokens summed over all model calls in the conversation (output includes reasoning tokens)."),
    ("n_model_calls", "Number of Responses API calls in the conversation."),
    ("trace_id", "OpenTelemetry trace id = operation_Id in Application Insights. Every number links back to a real trace."),
    ("model", "Agent model of the arm (runs.csv only): gpt-5-mini or gpt-4.1-mini. The judge is the same for both."),
]

RULES = """## Rules for using these numbers (for people and for agents)

1. **Use only numbers that appear in these files.** Do not estimate, extrapolate or round a CI into a point claim. If a number you need is not here, say it is missing.
2. **Primary metrics are pre-registered** (method/CHANGELOG.md, "decisions and pre-registered metrics", written before the main run). Lead with them. Everything else is secondary or exploratory and must be labelled so.
3. **Report the observed rates whatever they are.** If a fault rarely appeared in `before` (for example M1 on gpt-5-mini), that is a finding, not a failure of the experiment. Do not describe the intended fault as if it was observed. The draft's F1-F3 paragraphs must be rewritten from results/table_primary.md and traces.md.
4. **The unit of inference is the item, not the run.** 5 repetitions per item measure run-to-run variance. Use the bootstrap CIs over items (column `diff_after_minus_before`); Fisher p-values treat runs as independent and are secondary.
5. **The `after` condition is a fix package per scenario**, not single fixes: M2 = original message in the handoff + "only use an ID from the original message"; M3 = actionable error text + "do not retry" + "never more than twice". Effects cannot be attributed to one instruction.
6. **Models:** primary agents and the judge are gpt-5-mini (2025-08-07) on separate deployments, reasoning effort medium, no temperature (reasoning model). Robustness arm: gpt-4.1-mini (2025-04-14) agents at default settings, graded by the same judge. Second judge for the audit: gpt-4.1-mini, temperature 0. o4-mini was planned as a third arm but Azure refused new deployments (model being retired). Not GPT-6: no GPT-6 quota (method/CHANGELOG.md). The gpt-5-mini arm is primary; compare models only with results/models/table_models.md.
7. **Human audit:** the two labels must come from two authors working independently and blind. They must not be produced by an LLM or an agent; otherwise the paper cannot call it human agreement. Until audit/audit_results.md exists, report judge agreement as pending.
8. **Every example in the text should cite a trace id** from traces.md or data/<model>/runs.csv.
9. **Three judge versions, report them honestly.** v1 (expected facts only) was replaced by v2 before the main run (it penalised details from the policy documents). **v2 is the pre-registered judge**: `answer_correct`, `task_success`. v3 was added AFTER seeing the gpt-5-mini results, because v2 also penalised details the agent took from its tool definitions and tool results and relative dates: `answer_correct_v3`, `task_success_v3`. Report v2 as the main judged result and v3 as a post-hoc sensitivity analysis, always side by side (results/table_judges.md), never v3 alone. A spot check of 14 runs chosen by Claude agreed 14/14 with v3's intended behaviour; that is not a validation. The blind human audit decides which judge agrees better with people.
10. **Deterministic metrics need no judge** and are unaffected by v2/v3: searched, invented_id, wrong_id, n_identical_calls, looped, route_ok. They are the primary metrics for M1-M3.
11. **Latency across models is not comparable.** gpt-4.1-mini agent requests hit HTTP 429 (rate limit) in about 46% of conversations, balanced across before/after (data/rate_limit_retries.csv); the client library retried them, which inflates its latency. gpt-5-mini had 0 rate-limited requests. Compare latency only within a model (before vs after), never between models.
12. **Exploratory vs pre-registered.** Metrics marked [exploratory] (e.g. asked_to_confirm_id) were defined after seeing the data. Report them as exploratory, never as hypothesis tests.
13. **Changes to the setup** (models, judge v2, test set v2, tracing fix) are listed with reasons in method/CHANGELOG.md and must be reported in Method or Threats to validity.
"""


def rows_in(p: Path):
    if p.suffix == ".jsonl":
        return sum(1 for l in p.read_text().splitlines() if l.strip())
    if p.suffix == ".csv":
        with p.open() as f:
            return max(0, sum(1 for _ in csv.reader(f)) - 1)
    return None


def cols_in(p: Path):
    if p.suffix == ".jsonl":
        first = next((l for l in p.read_text().splitlines() if l.strip()), "{}")
        return sorted(json.loads(first).keys())
    if p.suffix == ".csv":
        with p.open() as f:
            return next(csv.reader(f), [])
    return None


def write_conditions(path: Path):
    """method/conditions.md, generated from src/config.py at build time (the exact texts being tested)."""
    c = ["# Experimental conditions (generated from src/config.py)", "",
         "Triage, documents, tools and model are identical in both conditions. Agent models: gpt-5-mini 2025-08-07 "
         "(primary, deployment gpt-5-mini-agent, default reasoning effort = medium) and gpt-4.1-mini 2025-04-14 "
         "(robustness arm, deployment gpt-4.1-mini-agent, default settings). Same instructions for both models.",
         f"Fixed date in all prompts: {config.TODAY}. Client tool loop cap: {config.MAX_TOOL_ROUNDS} rounds.", "",
         "## Triage (both conditions)", "", "```", config.TRIAGE_INSTRUCTIONS, "```", ""]
    for title, d in (("Policy agent (M1)", config.POLICY_INSTRUCTIONS), ("Order agent (M2, M3)", config.ORDER_INSTRUCTIONS),
                     ("Tool result when the order system is down (M3)", config.TOOL_ERROR)):
        c += [f"## {title}", ""]
        for cond in config.CONDITIONS:
            c += [f"**{cond}**", "", "```", d[cond], "```", ""]
    c += ["## Handoff text the specialist receives (M2)", ""]
    for cond in config.CONDITIONS:
        c += [f"**{cond}**", "", "```", config.handoff_message(cond, "<triage summary>", "<customer's original message>"), "```", ""]
    path.write_text("\n".join(c))


def main():
    if PKG.exists():
        shutil.rmtree(PKG)
    for d in ("results", "data", "method", "audit"):
        (PKG / d).mkdir(parents=True)
    files = []

    def put(src: Path, dst: str, purpose: str):
        if not src.exists():
            return
        target = PKG / dst
        shutil.copy2(src, target)
        files.append(dict(path=dst, purpose=purpose, rows=rows_in(target),
                          columns=(cols_in(target) if target.suffix in (".csv",) else None)))

    # flat runs.csv per arm from the graded JSONL (one row per conversation)
    tq = {q["id"]: q for q in map(json.loads, (ROOT / "data" / "testset.jsonl").read_text().splitlines()) if q}
    cols = ["model", "qid", "scenario", "subtype", "condition", "rep", "route", "route_ok", "searched", "n_file_search_calls",
            "n_tool_calls", "invented_id", "wrong_id", "id_in_handoff", "id_missing_from_handoff", "asked_for_id",
            "n_identical_calls", "looped", "offered_email", "asked_to_confirm_id", "process_ok", "answer_correct", "task_success", "latency_s",
            "answer_correct_v3", "task_success_v3", "input_tokens", "output_tokens", "n_model_calls", "error", "trace_id",
            "judge_reason", "judge_v3_reason"]
    for stem, label in ARMS:
        gp = R / f"{stem}.graded.jsonl"
        if not gp.exists():
            continue
        j3p = R / f"{stem}.judge3.jsonl"
        j3 = {}
        if j3p.exists():
            for l in j3p.read_text().splitlines():
                if l.strip():
                    x = json.loads(l)
                    j3[(x["qid"], x["condition"], x["rep"])] = x
        with (R / f"{stem}.runs.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for line in gp.read_text().splitlines():
                if line.strip():
                    g = json.loads(line)
                    g["subtype"] = tq.get(g["qid"], {}).get("subtype")
                    g["model"] = label
                    v = j3.get((g["qid"], g["condition"], g["rep"]), {})
                    g["answer_correct_v3"] = v.get("answer_correct_v3")
                    g["judge_v3_reason"] = v.get("judge_v3_reason")
                    g["task_success_v3"] = (bool(g.get("process_ok")) and bool(v["answer_correct_v3"])) if v.get("answer_correct_v3") is not None else None
                    w.writerow([g.get(c) for c in cols])

    pre = R / "paper" / "prereg"
    put(pre / "summary.md", "results/summary.md", "Headline numbers: primary metrics, latency, triage overhead, trace check, evaluator agreement.")
    put(pre / "table_primary.md", "results/table_primary.md", "All pre-registered metrics per scenario: before, after (Wilson 95% CI), difference with item-bootstrap 95% CI, Fisher p.")
    put(pre / "table_primary.csv", "results/table_primary.csv", "Same as table_primary.md, machine-readable (rates as fractions, diff_lo/diff_hi).")
    put(pre / "table_subtypes.md", "results/table_subtypes.md", "Metrics split by item subtype (e.g. prior_conflict vs easy, id_buried vs no_id).")
    put(pre / "table_subtypes.csv", "results/table_subtypes.csv", "Same, machine-readable.")
    put(pre / "table_latency_tokens.md", "results/table_latency_tokens.md", "p50/p95 latency, tokens, share of correct runs over 10 s, per scenario and condition.")
    put(pre / "table_triage.md", "results/table_triage.md", "Triage reasoning overhead (latency, output and reasoning tokens).")
    put(pre / "table_trace_assertions.md", "results/table_trace_assertions.md", "Fig. 3 trace assertions evaluated on exported spans vs client-side metrics; trace completeness.")
    put(pre / "table_evaluators.md", "results/table_evaluators.md", "Foundry built-in evaluators: pass/fail/not applicable per scenario and condition; agreement with deterministic metrics.")
    put(pre / "table_judges.md", "results/table_judges.md", "Judge v2 (pre-registered) vs judge v3 (post hoc) per scenario and condition: rates, agreement, verdict flips.")
    put(pre / "per_item.csv", "results/per_item.csv", "Every metric per item and condition (check whether a few items drive an effect).")
    for f in ("table_main.tex", "fig_success.png", "fig_mistake3_latency.png"):
        put(R / "paper" / f, f"results/{f}", {"table_main.tex": "LaTeX table from src/analyze.py (task success, process, judge, M1-M3 metrics).",
                                               "fig_success.png": "Task success before/after per scenario with Wilson CIs.",
                                               "fig_mistake3_latency.png": "M3 conversation latency before/after."}[f])
    for stem, label in ARMS:
        (PKG / "data" / label).mkdir(parents=True, exist_ok=True)
        tag = f"data/{label}"
        put(R / f"{stem}.runs.csv", f"{tag}/runs.csv", f"[{label} agents] One row per conversation: all metrics, judge verdict, latency, tokens, trace id. See DATA_DICTIONARY.md.")
        put(R / f"{stem}.graded.jsonl", f"{tag}/graded.jsonl", f"[{label} agents] Full record per conversation: messages, handoff, every tool call with arguments and result, steps, answer, metrics.")
        put(R / f"{stem}.foundry_eval.jsonl", f"{tag}/foundry_eval.jsonl", f"[{label} agents] Built-in evaluator results per conversation, joinable on qid, condition, rep.")
        put(R / f"{stem}.spans.csv", f"{tag}/spans.csv", f"[{label} agents] Every exported span (Application Insights) with GenAI attributes.")
        put(R / f"{stem}.trace_check.csv", f"{tag}/trace_check.csv", f"[{label} agents] Per conversation: trace completeness and the two trace assertions from spans.")
        put(R / f"{stem}.judge3.jsonl", f"{tag}/judge3.jsonl", f"[{label} agents] Judge v3 (post hoc) verdicts for every conversation.")
        put(R / f"{stem}.judge2.jsonl", f"{tag}/judge2.jsonl", f"[{label} agents] Second judge (gpt-4.1-mini) verdicts on the audited answers.")
        pr = R / "paper" / ("prereg" if stem == STEM else f"prereg_{label}")
        if stem != STEM and pr.exists():
            (PKG / "results" / label).mkdir(parents=True, exist_ok=True)
            for f in ("summary.md", "table_primary.md", "table_primary.csv", "table_subtypes.md", "table_latency_tokens.md",
                      "table_triage.md", "table_trace_assertions.md", "table_evaluators.md", "table_judges.md", "per_item.csv"):
                put(pr / f, f"results/{label}/{f}", f"[{label} agents] Same as results/{f} for the {label} arm.")
    put(R / "rate_limit_retries.csv", "data/rate_limit_retries.csv", "Per conversation and model: Foundry agent requests and how many got HTTP 429 and were retried by the client library (from App Insights).")
    mo = R / "paper" / "models"
    (PKG / "results" / "models").mkdir(parents=True, exist_ok=True)
    put(mo / "table_models.md", "results/models/table_models.md", "Model comparison: every primary metric per agent model, fix effect per model, and the difference in fix effect between models (paired item bootstrap).")
    put(mo / "table_models.csv", "results/models/table_models.csv", "Same, machine-readable.")
    put(mo / "table_models_efficiency.md", "results/models/table_models_efficiency.md", "Latency, tokens and judged correctness per model and condition.")
    put(mo / "fig_models.png", "results/models/fig_models.png", "Primary metric per scenario, model and condition.")
    put(R / "CHANGELOG.md", "method/CHANGELOG.md", "Every change to the setup with date and reason; the pre-registration.")
    put(ROOT / "data" / "testset.jsonl", "method/testset.jsonl", "The 40 test items with expected behaviour and facts.")
    write_conditions(R / "conditions.generated.md")
    put(R / "conditions.generated.md", "method/conditions.md", "Exact before/after instructions, tool error text and handoff, generated from src/config.py.")
    put(ROOT / "PAPER_NOTES.md", "method/PAPER_NOTES.md", "Method draft, where each number comes from, and threats to validity.")
    put(R / "trace_queries.kql", "method/trace_queries.kql", "The two Fig. 3 trace assertions as KQL queries for Application Insights.")
    put(R / "paper" / "kql_assertions.md", "results/kql_assertions.md", "Fig. 3 queries run in Application Insights vs client-side metrics, per model and condition.")
    put(R / "paper" / "second_judge.md", "results/second_judge.md", "Second judge (gpt-4.1-mini) vs judge v2 and v3 on the 40 audited answers.")
    for p in sorted((ROOT / "data" / "policies").glob("*.md")):
        put(p, f"method/{p.name}", "Policy document searched by the policy agent and given to the judge.")
    audit = R / "audit"
    if (audit / "audit_results.md").exists():
        put(audit / "audit_results.md", "audit/audit_results.md", "Human audit: Cohen's kappa between authors; every grader vs adjudicated labels.")
        put(audit / "audit_labels_joined.csv", "audit/audit_labels_joined.csv", "Both authors' labels, adjudicated label, judge verdict per audited answer.")
    else:
        (PKG / "audit" / "STATUS.md").write_text(
            "# Human audit: PENDING\n\nThe 40 blinded audit sheets have been sent to two authors. Until they are labelled, "
            "judge-human agreement is unknown and must not be reported or estimated.\n")
        files.append(dict(path="audit/STATUS.md", purpose="Human audit status: pending.", rows=None, columns=None))

    # traces.md: 2-3 trace ids per scenario and condition
    runs = [json.loads(l) for l in (R / f"{STEM}.graded.jsonl").read_text().splitlines() if l.strip()]  # primary arm
    runs = [r for r in runs if not r.get("error")]
    t = ["# Trace ids for figures and examples (primary arm, gpt-5-mini agents)\n",
         "Open in the Foundry portal (project agentobs-proj > Agents > Traces, search the id) or in Application Insights Logs: "
         "`union dependencies, requests | where operation_Id == \"<id>\"`.\n"]
    for scen, label in [("mistake1", "M1 missing lookup"), ("mistake2", "M2 lost context"), ("mistake3", "M3 runaway loop"), ("control", "Control")]:
        t.append(f"## {label}")
        for cond, want, desc in (("before", False, "before, task failed"), ("before", True, "before, task succeeded"),
                                 ("after", True, "after, task succeeded"), ("after", False, "after, task failed")):
            pick = [r for r in runs if r["scenario"] == scen and r["condition"] == cond and bool(r.get("task_success")) == want][:3]
            for r in pick:
                t.append(f"- {desc}: {r['qid']} rep{r['rep']} `{r['trace_id']}` ({r['latency_s']} s, {r.get('n_tool_calls', 0)} tool calls, "
                         f"{r.get('n_file_search_calls', 0)} searches, max identical calls {r.get('n_identical_calls', 0)})")
        t.append("")
    (PKG / "traces.md").write_text("\n".join(t))
    files.append(dict(path="traces.md", purpose="2-3 trace ids per scenario, condition and outcome for Fig. 2 and examples.", rows=None, columns=None))

    (PKG / "DATA_DICTIONARY.md").write_text("# Data dictionary (data/<model>/runs.csv and data/<model>/graded.jsonl)\n\n| Column | Definition |\n|---|---|\n"
                                            + "\n".join(f"| `{c}` | {d} |" for c, d in DICT) + "\n")
    n_runs = len(runs)
    start = ["# Support desk observability experiment: data package for writing\n",
             f"Built {date.today().isoformat()} for the CIIT 2027 paper \"Why did my agent do that? Observability for AI agents in "
             "Microsoft Foundry\" (Ivanovski, Cekikj, Doko).\n",
             "## The experiment in one paragraph\n",
             f"A three-agent support desk (triage, policy agent with File Search, order agent with two client-executed function tools) "
             f"runs on Microsoft Foundry Agent Service. Each of three practitioner-reported faults is reproduced in a `before` condition "
             f"and fixed in an `after` condition: M1 missing lookup (\"You can use the policy documents\" vs \"Always search\"), M2 lost "
             f"context (handoff with only triage's summary vs summary plus the original message and \"never guess an ID\"), M3 runaway "
             f"loop (bare \"Error\" vs an actionable error and a retry limit). 40 items x 2 conditions x 5 repetitions per agent model; "
             f"{n_runs} conversations in the primary arm. Primary agent model: gpt-5-mini 2025-08-07 (reasoning effort medium); "
             "robustness arm: gpt-4.1-mini 2025-04-14 (non-reasoning, default settings), same items, instructions and judge. Every "
             "conversation is traced with OpenTelemetry to Application Insights and has a trace id.\n",
             "## Which file answers which question\n",
             "| Question | File |", "|---|---|",
             "| Did each fault appear, and did the fix remove it? | results/table_primary.md (start here), results/summary.md |",
             "| Does the effect depend on the item design? | results/table_subtypes.md, results/per_item.csv |",
             "| Does the effect depend on the agent model? | results/models/table_models.md (start here for this), results/gpt-4.1-mini/ |",
             "| RQ1: can traces show the faults? | results/kql_assertions.md (the Fig. 3 queries run in App Insights), method/trace_queries.kql, results/table_trace_assertions.md, data/gpt-5-mini/spans.csv |",
             "| RQ3: do Foundry's built-in evaluators catch them? | results/table_evaluators.md |",
             "| How reliable is the LLM judge? | results/table_judges.md (v2 vs v3), results/second_judge.md, audit/ (human audit), data/gpt-5-mini/judge2.jsonl (second judge), method/CHANGELOG.md (v1, v2, v3) |",
             "| Latency, tokens, the 10 s guidance, triage overhead | results/table_latency_tokens.md, results/table_triage.md |",
             "| Exact conditions, items, policies | method/ |",
             "| Method section draft and threats to validity | method/PAPER_NOTES.md |",
             "| Examples and figures from real traces | traces.md, results/fig_*.png |",
             "| What a column means | DATA_DICTIONARY.md |",
             "", RULES,
             "## Every file\n", "See manifest.json (path, purpose, row count, columns).\n"]
    (PKG / "START_HERE.md").write_text("\n".join(start))
    manifest = dict(package="support-desk-observability-experiment", built=date.today().isoformat(), entry_point="START_HERE.md",
                    conversations=n_runs, design="40 items x 2 conditions (before/after) x 5 repetitions",
                    agent_models=["gpt-5-mini 2025-08-07 (deployment gpt-5-mini-agent), reasoning effort medium [primary]",
                                  "gpt-4.1-mini 2025-04-14 (deployment gpt-4.1-mini-agent), default settings [robustness arm]"],
                    judge_model="gpt-5-mini 2025-08-07 (deployment gpt-5-mini-judge), reasoning effort medium; judge v2 sees the policy documents",
                    second_judge_model="gpt-4.1-mini 2025-04-14 (deployment gpt-4.1-mini-judge2), temperature 0",
                    human_audit="complete" if (audit / "audit_results.md").exists() else "pending",
                    files=files + [dict(path="START_HERE.md", purpose="Entry point and rules.", rows=None, columns=None),
                                   dict(path="DATA_DICTIONARY.md", purpose="Column definitions.", rows=None, columns=None)])
    (PKG / "manifest.json").write_text(json.dumps(manifest, indent=2))
    z = shutil.make_archive(str(R / f"package_{date.today().isoformat()}"), "zip", PKG)
    print(f"Package: {PKG} ({len(manifest['files'])} files) -> {z}")


if __name__ == "__main__":
    main()
