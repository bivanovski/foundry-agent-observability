# Built-in evaluators

| evaluator           | scenario          | condition   |   pass |   fail |   not_applicable |   blocked_by_content_filter | pass_rate                    |
|:--------------------|:------------------|:------------|-------:|-------:|-----------------:|----------------------------:|:-----------------------------|
| intent_resolution   | M1 missing lookup | before      |     60 |      0 |                0 |                           0 | 100.0% [94.0, 100.0] (60/60) |
| intent_resolution   | M1 missing lookup | after       |     60 |      0 |                0 |                           0 | 100.0% [94.0, 100.0] (60/60) |
| intent_resolution   | M2 lost context   | before      |     57 |      0 |                0 |                           3 | 100.0% [93.7, 100.0] (57/57) |
| intent_resolution   | M2 lost context   | after       |     60 |      0 |                0 |                           0 | 100.0% [94.0, 100.0] (60/60) |
| intent_resolution   | M3 runaway loop   | before      |     40 |      0 |                0 |                           0 | 100.0% [91.2, 100.0] (40/40) |
| intent_resolution   | M3 runaway loop   | after       |     40 |      0 |                0 |                           0 | 100.0% [91.2, 100.0] (40/40) |
| intent_resolution   | Control           | before      |     36 |      4 |                0 |                           0 | 90.0% [76.9, 96.0] (36/40)   |
| intent_resolution   | Control           | after       |     34 |      6 |                0 |                           0 | 85.0% [70.9, 92.9] (34/40)   |
| tool_input_accuracy | M2 lost context   | before      |     40 |      0 |               20 |                           0 | 100.0% [91.2, 100.0] (40/40) |
| tool_input_accuracy | M2 lost context   | after       |     40 |      0 |               20 |                           0 | 100.0% [91.2, 100.0] (40/40) |
| tool_call_accuracy  | M2 lost context   | before      |     40 |      0 |               20 |                           0 | 100.0% [91.2, 100.0] (40/40) |
| tool_call_accuracy  | M2 lost context   | after       |     40 |      0 |               20 |                           0 | 100.0% [91.2, 100.0] (40/40) |
| task_adherence      | M1 missing lookup | before      |     46 |     14 |                0 |                           0 | 76.7% [64.6, 85.6] (46/60)   |
| task_adherence      | M1 missing lookup | after       |     38 |     22 |                0 |                           0 | 63.3% [50.7, 74.4] (38/60)   |
| tool_selection      | M1 missing lookup | before      |     60 |      0 |                0 |                           0 | 100.0% [94.0, 100.0] (60/60) |
| tool_selection      | M1 missing lookup | after       |     60 |      0 |                0 |                           0 | 100.0% [94.0, 100.0] (60/60) |
| task_completion     | M3 runaway loop   | before      |      0 |     40 |                0 |                           0 | 0.0% [0.0, 8.8] (0/40)       |
| task_completion     | M3 runaway loop   | after       |      0 |     40 |                0 |                           0 | 0.0% [0.0, 8.8] (0/40)       |
| tool_call_success   | M3 runaway loop   | before      |      0 |     40 |                0 |                           0 | 0.0% [0.0, 8.8] (0/40)       |
| tool_call_success   | M3 runaway loop   | after       |      0 |     40 |                0 |                           0 | 0.0% [0.0, 8.8] (0/40)       |

## Agreement with deterministic metrics (runs where the evaluator gave a verdict)

| Evaluator | Reference | Agreement | n | Not applicable |
|---|---|---|---|---|
| tool_selection | searched | 100.0% | 120 | 0 |
| task_adherence | answer_correct | 69.2% | 120 | 0 |
| tool_input_accuracy | not wrong_id | 100.0% | 80 | 40 |
| tool_call_accuracy | not wrong_id | 100.0% | 80 | 40 |
| tool_call_success | task_success | 21.2% | 80 | 0 |
| task_completion | answer_correct | 15.0% | 80 | 0 |
| intent_resolution | answer_correct | 78.8% | 397 | 0 |
