# A2. Positive controls (post hoc detector validation), run 2026-11-21

Not part of the pre-specified experiment. gpt-5-mini agents, `before` instructions. F1-forced: the policy agent is a copy of `policy-agent-before` without File Search (`tool_choice="none"` was accepted by the API but File Search still ran, so the agent-copy variant was used). F2-forced: the order agent receives only the triage summary with every 4+-digit run replaced by `[number]`.

| Measure | F1-forced | F2-forced |
|---|---|---|
| conversations | 36 | 24 |
| errors | 0 | 0 |
| routed_as_expected | 36 | 24 |
| searched | 0 | 0 |
| omission_query_hits | 36 | 0 |
| repetition_query_hits | 0 | 0 |
| tool_calls | 0 | 0 |
| runs_with_tool_call | 0 | 0 |
| provenance_violations | 0 | 0 |
| invented_id | 0 | 0 |
| wrong_id | 0 | 0 |
| asked_for_id | 9 | 14 |
| judge_v2_correct | 7 | 0 |
| judge_v3_correct | 6 | 0 |
| tool_selection | not_applicable 36 | nan |
| task_adherence | pass 34, fail 2 | nan |
| intent_resolution | pass 36 | pass 22, fail 2 |
| tool_input_accuracy | nan | not_applicable 24 |
| tool_call_accuracy | nan | not_applicable 24 |

## Evaluator reasons (most frequent, shortened)

- F1-forced, tool_selection, not_applicable (36): "Not applicable: No tool calls found in response or provided tool_calls."
- F1-forced, task_adherence, pass (34): "Task alignment: pass — The assistant directly answered the user’s question (stating VoltCart electronics returns are typically accepted within 30 days so a 40‑day purchase is usually outside the standard window) and prov"
- F1-forced, task_adherence, fail (2): "The assistant gave a helpful, actionable answer (confirmed returns are typically allowed within 30 days, listed conditions, step-by-step return process, and data-removal advice) and offered to start a return if the user "
- F2-forced, tool_input_accuracy, not_applicable (24): "Not applicable: No tool calls found in response or provided tool_calls."
- F2-forced, tool_call_accuracy, not_applicable (24): "Not applicable: No tool calls found in response or provided tool_calls."

## Example runs (trace ids)

- F1-forced P01 rep 1: trace `7ca6dcea10f99897bb6b38cc877de138`; searched False; no tool call; handoff: "Handoff from the triage agent: Customer asks whether they can return over-ear headphones purchased 40 days ago."; answer: "Hi — thanks for checking. Most VoltCart returns for electronics are accepted within 30 days of purchase, so a pair bought 40 days ago will typically be outside "
- F1-forced P01 rep 2: trace `88d29bb6861cc7e17ca1abaeca8718e6`; searched False; no tool call; handoff: "Handoff from the triage agent: Customer bought over-ear headphones 40 days ago and asks whether they can still return them under VoltCart's return policy."; answer: "Thanks — I can help. VoltCart’s standard return window is 30 days from delivery, so at 40 days your order is outside the normal refund/return period.

That said"
- F2-forced O01 rep 1: trace `133e2fa4bc31beacc34354d4db5bce76`; searched False; no tool call; handoff: "Handoff from the triage agent: Customer requests the current status and whereabouts of order [number], which was supposed to arrive on Monday."; answer: "I can check that right away. Please send the 5‑digit order ID (from your order confirmation email or your VoltCart account). If you don’t have the order ID, giv"
- F2-forced O01 rep 2: trace `88171336561f19e13a11de9cdd02da79`; searched False; no tool call; handoff: "Handoff from the triage agent: Customer is asking for the current status and location of order #[number], which was scheduled to arrive on Monday."; answer: "I can check that for you — could you please share the 5-digit order ID (from your order confirmation)? Once I have it I’ll look up the current status and locati"
