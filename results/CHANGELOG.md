# Changes to the experimental setup

Every change the paper has to report, with date and reason.

## 2026-11-16: agent and judge models switched to gpt-5-mini (before any run)

**Change.** Agents: `gpt-6-luna` (2026-09-22) → `gpt-5-mini` (2025-08-07), deployment `gpt-5-mini-agent`, 80K TPM.
Judge and built-in evaluators: `gpt-6.1-sol` (2026-09-29) → `gpt-5-mini` (2025-08-07), deployment `gpt-5-mini-judge`, 60K TPM.
Instructions, tools, documents, handoff and test set are unchanged.

**Reason.** The Azure subscription used (Visual Studio Enterprise) has a quota limit of 0 for `gpt-6-luna` and `gpt-6.1-sol` in every SKU (Global Standard, Data Zone Standard, Standard), checked with `az cognitiveservices usage list` on 2026-11-16. The only models with free inference quota were gpt-5-mini (143K TPM free of 500K), gpt-4.1-mini (200K, legacy) and o4-mini (100K, retiring 2026-11-19). Decision by Bojan Ivanovski: both roles on gpt-5-mini.

**Consequences for the paper.**
- Method: model names and versions change (PAPER_NOTES.md updated).
- Threats to validity: the judge is now the *same model* as the agents, not a stronger one from the same family. Self-preference bias is possible. Mitigations: deterministic process metrics that need no judge, and the two-author audit of 40 judge verdicts.
- The judge runs on a separate deployment with its own capacity, so judge and agent traffic do not throttle each other.

## 2026-11-16: LLM judge now sees the policy documents (after the smoke run, before the main run)

**Change.** `src/grade.py`: the judge prompt now includes the three policy documents (`data/policies/*.md`, the same files the policy agent searches). The rule "a policy rule that is not in the facts is incorrect" became "a policy rule that is in neither the facts nor the policy documents is incorrect". The agents, instructions, tools, documents and test set are unchanged.

**Reason.** In the smoke run, the judge marked both P01 answers (before and after) incorrect for "inventing" a holiday extension, a 24-month warranty, a 4.99 EUR return fee and a 14-day refund. All four are in the policy documents. The judge only saw the question's expected facts, so any correctly grounded extra detail counted as invented. This would have biased `answer_correct` against the `after` condition, whose agent always searches and quotes the documents.

**Effect on the smoke run.** P01 before and after: incorrect -> correct. The other 6 verdicts were unchanged. The original grades are kept in `results/smoke.graded.judge-v1-facts-only.jsonl`. Sanity check: two answers with invented policy (a 60-day window; a correct verdict plus an invented 15 EUR late fee) were both still judged incorrect.

**For the paper.** Method: the judge is given the expected behaviour, the expected facts and the full policy documents.

## 2026-11-16: harness note on `results/smoke.jsonl`

The file has 16 rows: 8 failed attempts (HTTP 400, "The 'agent' property is deprecated. Use 'agent_reference' instead.") and the 8 successful runs after the fix in `src/foundry.py` (`extra_body={"agent_reference": ...}`). The failed rows never reached a model and are excluded by the error filter.

## 2026-11-16: tracing fixed before the main run

- **Sampling.** azure-monitor-opentelemetry 1.8 defaults to a rate-limited sampler (5 traces/s). In the smoke run it dropped client spans: X01 `before` lost its root, `invoke_agent` and `execute_tool` spans, and only 3 of 5 `execute_tool` spans were stored. `src/telemetry.py` now sets `OTEL_TRACES_SAMPLER=always_on`. Check run `results/tracecheck.jsonl` (4 items x 2 conditions): 8/8 traces complete, 0 sampled, 5/5 tool spans and 3/3 file-search spans match the client logs.
- **GenAI attributes on client spans** (`src/pipeline.py`): `gen_ai.operation.name` on `invoke_agent` and `execute_tool`, `gen_ai.agent.name` and `gen_ai.tool.type=function` on tool spans, `gen_ai.usage.input_tokens` / `output_tokens` on agent spans, the handoff text on the specialist span. Telemetry only; agent inputs are unchanged.
- **Recorded per step:** reasoning tokens, reasoning effort and model. The agents run at the gpt-5-mini default reasoning effort, **medium** (read from the API response). This replaces "temperature" in the Method section.
- `src/export_spans.py` exports all spans of a results file and evaluates the two trace assertions (omission, repetition) from spans only.

## 2026-11-16: test set v2 (before the main run, after the smoke review)

Per the smoke review (`SMOKE_REVIEW_FINDINGS_AND_PLAN.md`), `scripts/build_testset.py` was rewritten. Still 40 items; every item has a `subtype`:

| Scenario | Items | Subtypes |
|---|---|---|
| M1 policy | 12 | 8 prior_conflict (generic answer is wrong for VoltCart: 15% laptop restocking fee, 14-day refund, 4.99 EUR return fee, holiday extension, 24-month warranty, 12-month battery, CarePlus within 30 days, window counts from delivery), 4 easy |
| M2 order | 12 | 4 id_first, 4 id_buried (ID among a postcode, phone, amount, invoice or customer number, including 5-digit decoys), 4 no_id |
| M3 outage | 8 | 6 plain, 2 insist ("try again", "keep trying") |
| Control | 8 | 5 social/off-topic (route none), 3 uncovered (policy questions the documents do not cover) |

Removed from v1: the price-match, repair-time and express-delivery policy items, O03/O06/O08 of v1 (replaced by id_buried items), and the v1 routing controls R04-R06 (two of which duplicated policy/order items). The smoke items P01, O01, X01, R01 keep their ids and wording.

- **Expected behaviour loosened (decision 4).** All outage items: "apologises, does not invent a status, and offers a concrete follow-up". Before, `before` was judged wrong partly for not offering email, a hint only the `after` error text contains. The email offer is now a separate deterministic metric (`offered_email`). The same reasoning applies to the uncovered controls: "offers a concrete way forward (for example a colleague)", because only the `after` policy instructions mention a colleague.
- **P12 reworded after the trace check.** "I ordered a coffee machine 35 days ago but it was only delivered 26 days ago..." was routed by triage to the order agent once, so it tested triage instead of M1. It now asks in general whether the 30-day period starts at order or at delivery.

## 2026-11-16: decisions and pre-registered metrics (frozen before the main run)

Agreed decisions:
1. **M1 wording unchanged.** The `before` instruction ("You can use the policy documents") is not strengthened to make the bug appear. The rate is reported whatever it is.
2. **M2.** Invented and wrong IDs are reported overall and conditional on the ID missing from the handoff. The no_id items test "never guess" directly.
3. **M3.** Primary metric: identical tool calls per run. `looped` (3+ identical calls or the round cap) is secondary.
4. **Outage expected behaviour loosened** (above).
5. **Judge v2** (judge sees the policy documents) is used for all grading.
6. **Not added:** multi-turn items, and agent reasoning effort as a second factor. Both were optional and are decided against now, before any main-run data exists.
7. **The paper reports the observed rates whatever they turn out to be**, including if M1 or M2 rarely reproduce on gpt-5-mini.

Primary and secondary metrics per scenario:

| Scenario | Primary (deterministic, from client logs; trace assertions as a cross-check) | Secondary |
|---|---|---|
| M1 | `searched` rate | `answer_correct`, tokens, latency |
| M2 | `invented_id` rate; `wrong_id` rate; both conditional on `id_missing_from_handoff`; `id_in_handoff` rate | `answer_correct`; `asked_for_id` rate on no_id items |
| M3 | identical calls per run (`n_identical_calls`, mean and max) | `looped`, `task_success`, `offered_email`, tokens, p50/p95 latency |
| Control | `route_ok`, `answer_correct` | tool calls (should be 0) |

New process metrics (`src/grade.py`): `wrong_id` (any tool call with an ID other than the expected one, which catches decoys such as a postcode), `id_missing_from_handoff`, `asked_for_id` (heuristic: answer mentions an order number and asks a question), `offered_email`, `n_identical_calls`. `process_ok` for order items now also requires `not wrong_id`.

Analysis plan: rates per condition with Wilson 95% CIs; the before-after difference with a 95% bootstrap CI that resamples items, not runs (the 5 reps of an item are not independent); Fisher's exact test as a secondary test; latency as p50/p95 plus the share of correct runs over 10 s; triage reasoning tokens reported separately.

Main run: 40 items x 2 conditions x 5 reps = 400 conversations, randomised order (seed 2027), 4 workers, into `results/main.jsonl`.

## 2026-11-16: grading and evaluation tooling (written during the main run, before looking at its results)

- **Built-in evaluators per scenario** (`src/evaluate_foundry.py`, `EVAL_PLAN`): Intent Resolution on all items; Tool Selection and Task Adherence on M1; Tool Input Accuracy and Tool Call Accuracy on M2; Tool Call Success and Task Completion on M3. Judge deployment `gpt-5-mini-judge`, `is_reasoning_model=True`.
- **"not applicable" is no longer counted as a fail.** Tool Selection returns `not_applicable` ("No tool calls found in response") when the agent called no tool, which is exactly the M1 fault. The old summary mapped it to fail; it is now recorded as `None` with `<evaluator>_result = not_applicable`. Finding for RQ3: Tool Selection cannot detect an omitted tool call by design.
- **Second judge:** deployment `gpt-4.1-mini-judge2` (gpt-4.1-mini 2025-04-14, 50K TPM), same prompt as judge v2, temperature 0 (non-reasoning model). Used on the 40 audited answers to check self-preference of the same-model judge (`src/second_judge.py`). `src/foundry.call_model` gained an optional `temperature` for this model only.
- **Human audit** (`src/audit.py`): stratified sample of 40 (5 per scenario and condition, judge "incorrect" verdicts first), blinded sheets per author, Cohen's kappa, adjudication, accuracy / precision / recall / kappa of every grader against the adjudicated label. Replaces the random sample in `src/analyze.py`.
- **Pre-registered analysis** (`src/analyze_prereg.py`) implements the analysis plan above.

## 2026-11-16: agent model as a second factor (decided during the main run, before looking at any main-run result)

Requested by the co-authors: run the same experiment with 2-3 agent models to show whether the effects depend on the model.

- **Arms.** `gpt-5-mini` (main run, `results/main.jsonl`), `gpt-4.1-mini` 2025-04-14 (`results/main_gpt41mini.jsonl`), `o4-mini` 2025-04-16 (`results/main_o4mini.jsonl`). These are the only models with free quota on the subscription. Each arm: the same 40 items x 2 conditions x 5 reps, same seed, same instructions, tools, documents and handoff. Agents per arm have their own names (suffix `-gpt41mini`, `-o4mini`) and state file (`.state.<tag>.json`).
- **Grading is held fixed across arms:** the same judge v2 (`gpt-5-mini-judge`, reasoning effort medium), the same built-in evaluator plan, the same deterministic metrics. Note: the judge shares a model with the gpt-5-mini arm only, so a same-model bias, if any, would favour that arm's answers in both conditions.
- **Sampling settings:** every model at its provider default. Reasoning models (gpt-5-mini, o4-mini) take no temperature; their default reasoning effort is used and recorded per step. gpt-4.1-mini (not a reasoning model) runs at its default temperature, as the agents do not set one.
- **o4-mini is retired by Microsoft on 2026-11-19**, so this arm cannot be re-run after that date. Reported as a limitation.
- **Analysis:** the pre-registered metrics are computed per arm (`src/analyze_prereg.py`), and a model comparison table (`src/compare_models.py`) shows each primary metric per model and condition with the item-bootstrap difference. The gpt-5-mini arm stays the primary analysis; the other arms are a robustness check.
- **Update, same day: o4-mini dropped.** Azure refused the deployment: "The model ... o4-mini ... 2025-04-16 is in deprecating state and cannot be used for new deployments" (ServiceModelDeprecating). No other model has quota on the subscription, so the comparison has **two arms: gpt-5-mini (reasoning) and gpt-4.1-mini (non-reasoning)**. Agent deployment `gpt-4.1-mini-agent`, 100K TPM.

## 2026-11-17: judge capacity raised after both runs finished

Both agent arms completed 400/400 conversations with 0 errors and 0 round-cap hits. To speed up grading, the idle `gpt-5-mini-agent` deployment was lowered from 80K to 10K TPM and `gpt-5-mini-judge` raised from 60K to 130K TPM (same shared gpt-5-mini quota). Throughput only: the judge model, version, prompt and reasoning effort are unchanged. No agent run happened after the change.

## 2026-11-17: more judge capacity for the built-in evaluators

With Bojan's approval, the `gpt-5-mini` deployment of an unrelated project in the same subscription was lowered from 207K to 10K TPM, and `gpt-5-mini-judge` raised from 130K to 330K TPM. Original settings were saved; restore that project to 207K after the evaluation. The evaluator script now saves each conversation as it completes, resumes after interruptions, and runs 12 workers. The first evaluator pass (4 workers, results only written at the end) was stopped and restarted; no evaluator results had been written. Throughput only: model, prompts and evaluator settings are unchanged.

## 2026-11-17 (night): gpt-5-mini arm evaluated; judge v2 limitation found AFTER seeing results

State: gpt-5-mini arm fully graded (judge v2) and evaluated by the built-in evaluators (397/400; 3 conversations, all O04 `before`, are blocked by Azure's content filter on Intent Resolution only, a false positive; their other evaluators succeed). Pre-registered analysis written to `results/paper/prereg/`. Demo deployment restored to 207K, judge back to 130K. gpt-4.1-mini arm: graded (judge v2), built-in evaluators not yet run.

**Observed after looking at the results (not pre-registered):** judge v2 marks some grounded answers as invented, because it does not see everything the agent saw:
- "5-digit order ID" (14 runs on no_id items) comes from the agent's own tool definition ("The 5-digit order ID."), which the judge does not see.
- Order statuses and next steps quoted from the order system ("awaiting_stock", "a return label has been emailed") come from tool outputs, which the judge does not see.
- Relative dates ("two days from now", "ships 20 November") are correct for the fixed date in the prompts (19 November 2026), which the judge does not know.
Genuine errors are also caught (an invented 3-5 day refund on O04, an invented crypto rule on R07 `before`, the triage agent helping with a CV / recommending films on R03 / R04).

The deterministic primary metrics (searched, invented/wrong ID, identical calls, routing) do not depend on the judge and are unaffected. `answer_correct` and `task_success` for M2 in particular are depressed by the judge limitation.

**Decision pending (Bojan and co-authors):** a judge v3 that also receives the tool definitions, the tool calls with their outputs, and the fixed date. If adopted, v3 is post hoc: both v2 and v3 verdicts are kept and reported, v2 stays in the files, and the human audit (blind to both) arbitrates.

## 2026-11-17 (night): judge v3 adopted as a post-hoc sensitivity grader (decision by Bojan)

- **What v3 is** (`src/judge_v3.py`): the v2 prompt plus the fixed date (19 November 2026), the tool definitions (file_search, get_order_status, create_return) and every tool call of the conversation with its result. Rule added: details from the policy documents, tool definitions or tool results are grounded; dates are judged against the fixed date. Same model, deployment and reasoning effort as v2.
- **Status:** post hoc, decided after seeing the gpt-5-mini results. v2 stays the pre-registered judge (`answer_correct`, `task_success`); v3 verdicts go to separate files (`results/<arm>.judge3.jsonl`, columns `answer_correct_v3`, `task_success_v3`) and are always reported next to v2 (`table_judges.md`: rates, agreement, flips in both directions). Applied to both arms.
- **Spot check before the full run:** 14 gpt-5-mini runs chosen by Claude: 8 that v2 had marked incorrect for grounded details (5-digit ID from the tool definition, statuses and next steps from tool results, dates relative to 19 November), 4 genuine errors (invented 3-5 day refund, invented crypto rule, triage helping with a CV, film recommendations), 2 v2-correct runs. v3 matched the intended verdict in 14/14. These cases were chosen to test the design; they are not a validation. The blind human audit (which sees neither judge) compares v2 and v3 with human labels.
- **Built-in evaluators and Azure's content filter:** when the content filter blocks an evaluator prompt (Intent Resolution on 3 O04 `before` runs), the result is now recorded as `blocked_content_filter` (pass = None) and the conversation is saved with its other evaluators, instead of being retried forever. Counted per scenario in `table_evaluators.md`.

## 2026-11-17 (evening): post-run pipeline completed for both arms

- **Completed:** both arms 400/400 graded (judge v2), judged by judge v3 (post hoc), evaluated by the built-in evaluators (400/400 each; 3 gpt-5-mini O04 `before` runs have Intent Resolution `blocked_content_filter`), all spans exported (400/400 complete traces per arm, 0 sampled), pre-registered analysis per arm, model comparison, data package `results/package_2026-11-17.zip`.
- **Rate-limit retries (found in the traces, not in the client logs).** 557 of about 2,490 Foundry agent requests returned HTTP 429 and were retried automatically by the OpenAI client library, all of them in the gpt-4.1-mini arm: 183/400 conversations (87 before, 96 after). gpt-5-mini: 0. Likely cause: the gpt-4.1-mini-agent deployment's per-minute request limit with 4 workers and fast responses. Consequences: (1) gpt-4.1-mini latency is inflated (median 6.8 s with a retry vs 3.9 s without), so latency is compared only within a model, never across models; (2) in 37 gpt-4.1-mini runs Foundry executed a file search inside a request that then returned 429, so file-search spans (214) exceed the client-logged searches (150). The trace assertions are unaffected (they test for absence of a search and for repeated function calls). Per-run counts: `results/rate_limit_retries.csv`. This is itself an RQ1 example: the trace shows retried work the application's own log never sees.
- **Exploratory metric added after seeing the data: `asked_to_confirm_id`.** On M3 items with a bare "Error", gpt-4.1-mini never looped (max 2 identical calls) but asked the customer to confirm an order number they had already given correctly in 40/40 runs (gpt-5-mini: 18/40, plus 9 loops). After the fix: 0/40 for both. The same uninformative error is misdiagnosed differently by the two models (retry vs blaming the customer's input). Heuristic on the answer text, reported as exploratory only. Re-grading for this metric reused the cached judge verdicts (no verdict changed).
- **Human audit:** still pending (two authors, blind).

## 2026-11-17 (late): completeness check against the smoke-review plan

- **Fig. 3 trace assertions run as real KQL** in Application Insights (`src/kql_assertions.py`, queries in `results/trace_queries.kql`): omission and repetition queries match the client-side metrics conversation by conversation for both models and conditions (gpt-5-mini before: 9/9 repetitions; no other hits; no false positives). Limitation: M1 never occurred, so the omission query was never tested on a real omission.
- **Second judge analysed** (`results/paper/second_judge.md`, 40 audited answers): agreement with judge v2 67.5% (kappa 0.41), with judge v3 87.5% (kappa 0.74). All 13 v2 disagreements are cases where the second judge says correct and v2 incorrect, which points to v2 strictness rather than same-model leniency. Sample is the stratified audit sample (v2-incorrect verdicts oversampled); human labels decide.
- **Docs updated** to the actual design: README, PAPER_NOTES (Method draft with numbers, threats to validity), CLAUDE.md (run order incl. the gpt-4.1-mini arm and after_runs.sh). `method/conditions.md` in the package is now generated from `src/config.py` at build time.
- **Azure capacities restored** to the documented values: gpt-5-mini-agent 80K, gpt-5-mini-judge 60K (the unrelated project stays at its original 207K).
- **Not done (decision open):** uploading the built-in evaluator runs to the Foundry portal (`--upload`), which recomputes every evaluator a second time.

## 2026-11-17 (late): portal upload started, then cancelled

The built-in evaluator runs were being uploaded to the Foundry portal (one run per scenario and condition, `src/evaluate_foundry.py --upload-only`). Bojan cancelled it: the portal comparison view is not needed for the paper. Only a 2-conversation test run ("TEST support-desk gpt-5-mini mistake1 before") reached the portal; it can be ignored or deleted there. No result in this repo depends on the upload. Judge and agent capacities restored to 60K / 80K.

## 2026-11-21: v3 paper checks (post hoc, read-only)

Paper v3 was checked against the repo following `paper/V3_CHECKS_FOR_CLAUDE.md`; full report `results/paper/v3_checks/V3_CHECK_REPORT.md`. No data changed, no model or evaluator runs, no Azure changes (read-only KQL queries and agent-definition reads only). Findings that matter for the paper: (1) the built-in evaluators received File Search results truncated by our pipeline (`src/pipeline.py:67`, first 300 characters of the top 3 results), so the Task Adherence result on F1 is partly an artefact; (2) all three Fig. 3 queries run in Application Insights and match the client records; (3) since 30 Sep 2026 Application Insights moves content attributes to a protected `AppGenAIContent` table on resources where the change applies; our resource still stored them in both places, and adapted queries return identical traces. `src/kql_assertions.py` gained a `--paper-v3` mode with explicit time ranges. Open: positive controls (A2), Task Adherence rerun (B1), human audit (C), data availability (D3).

## 2026-11-21: approved post-hoc runs (Bojan: "Yes, run both")

Post hoc, not part of the pre-specified experiment. Outputs only under `results/paper/v3_checks/`; no frozen file is changed; no capacity change.
- **A2, positive controls (detector validation):** 60 conversations on `gpt-5-mini-agent` with the `before` instructions. F1-forced: P01-P12 x 3 reps, the policy agent cannot use File Search. F2-forced: O01-O08 x 3 reps, the handoff is the triage summary with every digit run of 4+ digits replaced by "[number]", without the original message. Then judge v2, judge v3 and the built-in evaluators (Tool Selection, Task Adherence, Intent Resolution on F1; Tool Input Accuracy, Tool Call Accuracy, Intent Resolution on F2), and the omission query in Application Insights. Why: F1 and F2 never occurred, so their detectors were never tested on a true positive.
- **B1, Task Adherence rerun:** Task Adherence only, on F1 only, 120 runs per model (240 calls), with the full File Search results taken from the exported server spans instead of the 3 x 300-character excerpts. Why: the excerpts were cut by our pipeline (`src/pipeline.py:67`), so the original Task Adherence verdicts on F1 are partly an artefact.

## 2026-11-21: results of the approved post-hoc runs

- **A2 positive controls** (60 conversations, gpt-5-mini, `before`, 0 errors; `results/paper/v3_checks/positive_controls*`). `tool_choice="none"` on the agent request was accepted but ignored (File Search still ran), so F1 used a new agent `policy-agent-before-nofs` (copy of `policy-agent-before` without File Search). F1-forced: 36/36 without search; the omission query (Fig. 3a) flagged 36/36 in Application Insights; Tool Selection `not_applicable` 36/36; Task Adherence passed 34/36. F2-forced (number masked in the handoff): the order agent never called a tool (0/24) and asked for the number, so the provenance check and the tool-accuracy evaluators still have no true positive.
- **B1 Task Adherence rerun** (240 runs, 0 errors; `results/paper/v3_checks/b1_ta_rerun*`): with the full File Search results from the server spans, Task Adherence passed 239/240 F1 answers (previously 147/240); 93 fail-to-pass, 1 pass-to-fail. The original F1 failure rate was caused by our pipeline's 300-character excerpts.
- The original evaluator files (`results/main*.foundry_eval.jsonl`) are unchanged.
