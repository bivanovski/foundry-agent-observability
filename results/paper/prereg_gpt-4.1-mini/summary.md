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
| M3 runaway loop   | Identical tool calls per run [primary]                        | mean 1.05, max 2 (n=40)      | mean 1.00, max 1 (n=40)      | -0.1 [-0.1, +0.0]         | n/a        |
| Control           | Routed correctly [primary]                                    | 100.0% [91.2, 100.0] (40/40) | 100.0% [91.2, 100.0] (40/40) | +0.0 pp [+0.0, +0.0]      | 1.000      |
| Control           | Answer correct (judge v2) [primary]                           | 75.0% [59.8, 85.8] (30/40)   | 87.5% [73.9, 94.5] (35/40)   | +12.5 pp [+0.0, +32.5]    | 0.252      |

## Judge v2 vs v3 (post hoc)

| scenario          | condition   |   n | judge_v2_correct   | judge_v3_correct   | agreement   |   v2_incorrect_to_v3_correct |   v2_correct_to_v3_incorrect |
|:------------------|:------------|----:|:-------------------|:-------------------|:------------|-----------------------------:|-----------------------------:|
| M1 missing lookup | before      |  60 | 98.3%              | 98.3%              | 100.0%      |                            0 |                            0 |
| M1 missing lookup | after       |  60 | 100.0%             | 100.0%             | 100.0%      |                            0 |                            0 |
| M2 lost context   | before      |  60 | 50.0%              | 83.3%              | 66.7%       |                           20 |                            0 |
| M2 lost context   | after       |  60 | 66.7%              | 83.3%              | 83.3%       |                           10 |                            0 |
| M3 runaway loop   | before      |  40 | 2.5%               | 5.0%               | 92.5%       |                            2 |                            1 |
| M3 runaway loop   | after       |  40 | 97.5%              | 97.5%              | 100.0%      |                            0 |                            0 |
| Control           | before      |  40 | 75.0%              | 72.5%              | 97.5%       |                            0 |                            1 |
| Control           | after       |  40 | 87.5%              | 87.5%              | 100.0%      |                            0 |                            0 |

## Latency

Correct runs over 10 s: 17.3% of 294 (p50 4.5 s, p95 15.4 s).

## Triage overhead

|   triage_calls |   latency_p50_s |   latency_p95_s |   output_tokens_mean |   reasoning_tokens_mean | reasoning_share_of_output   | reasoning_effort   |
|---------------:|----------------:|----------------:|---------------------:|------------------------:|:----------------------------|:-------------------|
|            400 |            1.22 |            2.28 |                 33.3 |                       0 | 0.0%                        | None               |

Traces: 400; complete: 400; with root span: 400; sampled: 0. Tool spans 165 vs logged tool calls 165; file-search spans 214 vs logged 150.

## Built-in evaluators vs deterministic metrics

| Evaluator | Reference | Agreement | n | Not applicable |
|---|---|---|---|---|
| tool_selection | searched | 100.0% | 120 | 0 |
| task_adherence | answer_correct | 53.3% | 120 | 0 |
| tool_input_accuracy | not wrong_id | 100.0% | 80 | 40 |
| tool_call_accuracy | not wrong_id | 100.0% | 80 | 40 |
| tool_call_success | task_success | 50.0% | 80 | 0 |
| task_completion | answer_correct | 50.0% | 80 | 0 |
| intent_resolution | answer_correct | 66.8% | 400 | 0 |

