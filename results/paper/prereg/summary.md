# Main run: pre-registered results

Runs: 400 recorded, 0 errored (excluded), 400 analysed. Items: 40. Reps per item and condition: 5-5.

Differences are after minus before, with 95% bootstrap CIs over items (5000 resamples).

## Primary metrics

| scenario          | metric                                                        | before                       | after                        | diff_after_minus_before   | fisher_p   |
|:------------------|:--------------------------------------------------------------|:-----------------------------|:-----------------------------|:--------------------------|:-----------|
| M1 missing lookup | Searched the policy documents [primary]                       | 100.0% [94.0, 100.0] (60/60) | 100.0% [94.0, 100.0] (60/60) | +0.0 pp [+0.0, +0.0]      | 1.000      |
| M2 lost context   | Tool called with an ID not in the message [primary]           | 0.0% [0.0, 6.0] (0/60)       | 0.0% [0.0, 6.0] (0/60)       | +0.0 pp [+0.0, +0.0]      | 1.000      |
| M2 lost context   | Tool called with any ID other than the expected one [primary] | 0.0% [0.0, 6.0] (0/60)       | 0.0% [0.0, 6.0] (0/60)       | +0.0 pp [+0.0, +0.0]      | 1.000      |
| M2 lost context   | Invented ID | ID missing from handoff [primary]               | n/a (0 runs)                 | n/a (0 runs)                 | n/a                       | n/a        |
| M2 lost context   | Wrong ID | ID missing from handoff [primary]                  | n/a (0 runs)                 | n/a (0 runs)                 | n/a                       | n/a        |
| M3 runaway loop   | Identical tool calls per run [primary]                        | mean 2.42, max 7 (n=40)      | mean 1.00, max 1 (n=40)      | -1.4 [-1.9, -1.0]         | n/a        |
| Control           | Routed correctly [primary]                                    | 100.0% [91.2, 100.0] (40/40) | 100.0% [91.2, 100.0] (40/40) | +0.0 pp [+0.0, +0.0]      | 1.000      |
| Control           | Answer correct (judge v2) [primary]                           | 70.0% [54.6, 81.9] (28/40)   | 80.0% [65.2, 89.5] (32/40)   | +10.0 pp [+0.0, +25.0]    | 0.439      |

## Judge v2 vs v3 (post hoc)

| scenario          | condition   |   n | judge_v2_correct   | judge_v3_correct   | agreement   |   v2_incorrect_to_v3_correct |   v2_correct_to_v3_incorrect |
|:------------------|:------------|----:|:-------------------|:-------------------|:------------|-----------------------------:|-----------------------------:|
| M1 missing lookup | before      |  60 | 100.0%             | 100.0%             | 100.0%      |                            0 |                            0 |
| M1 missing lookup | after       |  60 | 98.3%              | 100.0%             | 98.3%       |                            1 |                            0 |
| M2 lost context   | before      |  60 | 58.3%              | 80.0%              | 68.3%       |                           16 |                            3 |
| M2 lost context   | after       |  60 | 70.0%              | 88.3%              | 78.3%       |                           12 |                            1 |
| M3 runaway loop   | before      |  40 | 75.0%              | 75.0%              | 95.0%       |                            1 |                            1 |
| M3 runaway loop   | after       |  40 | 95.0%              | 95.0%              | 95.0%       |                            1 |                            1 |
| Control           | before      |  40 | 70.0%              | 70.0%              | 100.0%      |                            0 |                            0 |
| Control           | after       |  40 | 80.0%              | 80.0%              | 100.0%      |                            0 |                            0 |

## Latency

Correct runs over 10 s: 63.0% of 324 (p50 11.3 s, p95 16.5 s).

## Triage overhead

|   triage_calls |   latency_p50_s |   latency_p95_s |   output_tokens_mean |   reasoning_tokens_mean | reasoning_share_of_output   | reasoning_effort   |
|---------------:|----------------:|----------------:|---------------------:|------------------------:|:----------------------------|:-------------------|
|            400 |            3.28 |            4.85 |                282.1 |                   208.6 | 71.3%                       | medium             |

Traces: 400; complete: 400; with root span: 400; sampled: 0. Tool spans 246 vs logged tool calls 246; file-search spans 157 vs logged 157.

## Built-in evaluators vs deterministic metrics

| Evaluator | Reference | Agreement | n | Not applicable |
|---|---|---|---|---|
| tool_selection | searched | 100.0% | 120 | 0 |
| task_adherence | answer_correct | 69.2% | 120 | 0 |
| tool_input_accuracy | not wrong_id | 100.0% | 80 | 40 |
| tool_call_accuracy | not wrong_id | 100.0% | 80 | 40 |
| tool_call_success | task_success | 21.2% | 80 | 0 |
| task_completion | answer_correct | 15.0% | 80 | 0 |
| intent_resolution | answer_correct | 78.8% | 397 | 0 |

