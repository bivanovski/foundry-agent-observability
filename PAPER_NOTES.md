# Paper notes: from outputs to sections

Status 2026-11-17: both model arms run, graded and analysed. Open: the human audit (two authors, blind). Every decision and change, with date and reason, is in the CHANGELOG (`results/CHANGELOG.md` in the repo, `method/CHANGELOG.md` in the data package); the Method and Threats sections must report them. File paths below are those inside the data package.

## Method (draft; [brackets] = still open)

We implemented the support desk on Microsoft Foundry Agent Service as three prompt agents: a triage agent without tools, a policy agent with File Search over three policy documents (returns, warranty, shipping), and an order agent with two function tools (`get_order_status`, `create_return`) backed by a simulated order system. The triage decision and the handoff are orchestrated in client code so the content of the handoff can be controlled exactly. The primary agent model is GPT-5 mini (gpt-5-mini, version 2025-08-07, default reasoning effort, recorded as medium on every call); as a robustness arm, the identical setup was run with GPT-4.1 mini (gpt-4.1-mini, 2025-04-14, default settings). A third arm (o4-mini) was planned but could not be deployed because the model was being retired.

Each fault is introduced by one change in the `before` condition and removed by a fix in the `after` condition (Table [X], generated from `src/config.py`). M1 (missing lookup): "You can use the policy documents" vs "Always search the policy documents ... if they don't cover the question, say so". M2 (lost context): the specialist receives only triage's summary vs the summary plus the customer's original message and the instruction never to guess an order ID. M3 (runaway loop): the order tool returns a bare "Error" vs an actionable error text, together with instructions not to retry and never to repeat a call more than twice. For M2 and M3 the fix is therefore a package of changes, and effects are attributed to the package, not to a single instruction. Triage instructions, documents, tools and model were identical across conditions.

The test set contains 40 questions with written ground truth: 12 policy questions (8 where a generic answer is wrong for this store, 4 easy), 12 order questions (4 with the order ID in the first sentence, 4 with the ID among other numbers such as a postcode or invoice number, 4 without an ID), 8 questions asked while the order system is unavailable (2 in which the customer insists on retrying), and 8 controls (5 greetings or off-topic requests, 3 policy questions the documents do not cover). Each question was run 5 times per condition in randomised, interleaved order, giving 400 conversations per model (400 completed, 0 excluded, for both models).

The primary metrics were fixed before the main run: whether the policy agent searched (M1), whether a tool was called with an invented or wrong order ID (M2), the number of identical tool calls per conversation (M3), and routing and answer correctness for the controls. They are read deterministically from the recorded runs. Answers were also graded by an LLM judge (gpt-5-mini, separate deployment, fixed medium reasoning effort; reasoning models take no temperature) that sees the expected behaviour, the expected facts and the full policy documents. Because this judge cannot see the tool definitions and tool results the agent saw, a post-hoc variant (judge v3) that also receives them and the fixed date was added after the results were seen; both are reported. A second judge from another model generation (gpt-4.1-mini, temperature 0) re-graded the audited answers. Foundry's built-in agent evaluators were run per scenario (Intent Resolution on all items; Tool Selection and Task Adherence on M1; Tool Input Accuracy and Tool Call Accuracy on M2; Tool Call Success and Task Completion on M3). Two authors independently labelled a stratified sample of 40 answers without seeing the condition or any verdict; inter-rater agreement was [kappa], and the judges' agreement with the adjudicated labels is [table].

We report proportions with Wilson 95% confidence intervals. Because the five repetitions of a question are not independent, the before-after difference is reported with a 95% bootstrap confidence interval that resamples questions (5,000 resamples); Fisher's exact test is reported as a secondary test. Latency is reported as median and 95th percentile.

All conversations were traced with OpenTelemetry to Azure Monitor Application Insights following the GenAI semantic conventions [ref], with sampling disabled (the exporter's default rate-limited sampler had dropped spans in a pilot run). All 400 traces per model were complete. The two trace assertions of Fig. 3 (omission, repetition) were run as KQL queries in Application Insights (`method/trace_queries.kql`).

## Results: where each number comes from

| Section / figure | File (in the data package) |
|---|---|
| Main table, fault by fault | `results/table_primary.md` (gpt-5-mini), `results/gpt-4.1-mini/table_primary.md`; LaTeX: `results/table_main.tex` |
| Model comparison | `results/models/table_models.md`, `results/models/fig_models.png` |
| Item design effects | `results/table_subtypes.md`, `results/per_item.csv` |
| RQ1 traces | `results/table_trace_assertions.md`, `results/kql_assertions.md`, `method/trace_queries.kql` |
| RQ3 built-in evaluators | `results/table_evaluators.md` |
| Judge reliability | `results/table_judges.md` (v2 vs v3), `results/second_judge.md`, audit results [pending] |
| Efficiency, 10 s guidance, triage overhead | `results/table_latency_tokens.md`, `results/table_triage.md`, `results/fig_mistake3_latency.png` |
| Overview figure | `results/fig_success.png` (judge v2 task success; M2 is depressed by the judge v2 limitation, see table_judges) |

## Figures from real traces

`traces.md` lists trace ids per scenario, condition and outcome. Replace the illustrative trace figures with screenshots of those runs; the durations in the old figures must go. The Azure resources stay deployed until the screenshots are taken (traces are deleted with `infra/teardown.sh`).

## Threats to validity

- Two models from one provider, one region, one point in time; model updates can change behaviour. o4-mini could not be tested (retired).
- M1 and M2 did not appear on either model, so their fixes could not be shown to remove anything, and the omission trace query was never tested on a real omission (it returned no false positives).
- The primary judge is the same model as the primary agents. The second judge (another generation) disagreed with judge v2 only by being more lenient (13/40 vs 0/40), which points to v2 strictness rather than self-preference; the human audit decides.
- Judge versions: v1 (expected facts only) was replaced by v2 before the main run; v3 was added after seeing the results and is reported only next to v2.
- Synthetic store, documents and questions written by the authors.
- The handoff is orchestrated in client code, not by Foundry's built-in multi-agent orchestration.
- Several built-in evaluators are in preview; Azure's content filter blocked Intent Resolution on 3 conversations; Tool Selection returns "not applicable" when no tool was called.
- The gpt-4.1-mini arm hit rate limits (HTTP 429, retried automatically) in 46% of conversations, balanced across conditions; its latency is not comparable with gpt-5-mini's.
- Five repetitions per question measure run-to-run variance, not question difficulty; inference uses question-level bootstrap intervals, and the per-question table shows whether a few questions drive an effect.
- Metrics marked exploratory (for example asking the customer to re-confirm a correct order ID) were defined after seeing the data.
