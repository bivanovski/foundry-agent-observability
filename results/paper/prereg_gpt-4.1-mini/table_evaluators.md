# Built-in evaluators

| evaluator           | scenario          | condition   |   pass |   fail |   not_applicable |   blocked_by_content_filter | pass_rate                    |
|:--------------------|:------------------|:------------|-------:|-------:|-----------------:|----------------------------:|:-----------------------------|
| intent_resolution   | M1 missing lookup | before      |     60 |      0 |                0 |                           0 | 100.0% [94.0, 100.0] (60/60) |
| intent_resolution   | M1 missing lookup | after       |     60 |      0 |                0 |                           0 | 100.0% [94.0, 100.0] (60/60) |
| intent_resolution   | M2 lost context   | before      |     60 |      0 |                0 |                           0 | 100.0% [94.0, 100.0] (60/60) |
| intent_resolution   | M2 lost context   | after       |     60 |      0 |                0 |                           0 | 100.0% [94.0, 100.0] (60/60) |
| intent_resolution   | M3 runaway loop   | before      |     37 |      3 |                0 |                           0 | 92.5% [80.1, 97.4] (37/40)   |
| intent_resolution   | M3 runaway loop   | after       |     40 |      0 |                0 |                           0 | 100.0% [91.2, 100.0] (40/40) |
| intent_resolution   | Control           | before      |     25 |     15 |                0 |                           0 | 62.5% [47.0, 75.8] (25/40)   |
| intent_resolution   | Control           | after       |     25 |     15 |                0 |                           0 | 62.5% [47.0, 75.8] (25/40)   |
| task_adherence      | M1 missing lookup | before      |     32 |     28 |                0 |                           0 | 53.3% [40.9, 65.4] (32/60)   |
| task_adherence      | M1 missing lookup | after       |     31 |     29 |                0 |                           0 | 51.7% [39.3, 63.8] (31/60)   |
| tool_selection      | M1 missing lookup | before      |     60 |      0 |                0 |                           0 | 100.0% [94.0, 100.0] (60/60) |
| tool_selection      | M1 missing lookup | after       |     60 |      0 |                0 |                           0 | 100.0% [94.0, 100.0] (60/60) |
| tool_input_accuracy | M2 lost context   | before      |     40 |      0 |               20 |                           0 | 100.0% [91.2, 100.0] (40/40) |
| tool_input_accuracy | M2 lost context   | after       |     40 |      0 |               20 |                           0 | 100.0% [91.2, 100.0] (40/40) |
| tool_call_accuracy  | M2 lost context   | before      |     40 |      0 |               20 |                           0 | 100.0% [91.2, 100.0] (40/40) |
| tool_call_accuracy  | M2 lost context   | after       |     40 |      0 |               20 |                           0 | 100.0% [91.2, 100.0] (40/40) |
| task_completion     | M3 runaway loop   | before      |      0 |     40 |                0 |                           0 | 0.0% [0.0, 8.8] (0/40)       |
| task_completion     | M3 runaway loop   | after       |      0 |     40 |                0 |                           0 | 0.0% [0.0, 8.8] (0/40)       |
| tool_call_success   | M3 runaway loop   | before      |      0 |     40 |                0 |                           0 | 0.0% [0.0, 8.8] (0/40)       |
| tool_call_success   | M3 runaway loop   | after       |      0 |     40 |                0 |                           0 | 0.0% [0.0, 8.8] (0/40)       |

## Agreement with deterministic metrics (runs where the evaluator gave a verdict)

| Evaluator | Reference | Agreement | n | Not applicable |
|---|---|---|---|---|
| tool_selection | searched | 100.0% | 120 | 0 |
| task_adherence | answer_correct | 53.3% | 120 | 0 |
| tool_input_accuracy | not wrong_id | 100.0% | 80 | 40 |
| tool_call_accuracy | not wrong_id | 100.0% | 80 | 40 |
| tool_call_success | task_success | 50.0% | 80 | 0 |
| task_completion | answer_correct | 50.0% | 80 | 0 |
| intent_resolution | answer_correct | 66.8% | 400 | 0 |
