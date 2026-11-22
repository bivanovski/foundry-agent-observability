| scenario           | evaluator           | before                       | after                        |   p_value |
|:-------------------|:--------------------|:-----------------------------|:-----------------------------|----------:|
| M1: missing lookup | intent_resolution   | 100.0% [94.0, 100.0] (60/60) | 100.0% [94.0, 100.0] (60/60) |     1     |
| M1: missing lookup | task_adherence      | 76.7% [64.6, 85.6] (46/60)   | 63.3% [50.7, 74.4] (38/60)   |     0.163 |
| M1: missing lookup | tool_selection      | 100.0% [94.0, 100.0] (60/60) | 100.0% [94.0, 100.0] (60/60) |     1     |
| M2: lost context   | intent_resolution   | 100.0% [93.7, 100.0] (57/57) | 100.0% [94.0, 100.0] (60/60) |     1     |
| M2: lost context   | tool_input_accuracy | 100.0% [91.2, 100.0] (40/40) | 100.0% [91.2, 100.0] (40/40) |     1     |
| M2: lost context   | tool_call_accuracy  | 100.0% [91.2, 100.0] (40/40) | 100.0% [91.2, 100.0] (40/40) |     1     |
| M3: runaway loop   | intent_resolution   | 100.0% [91.2, 100.0] (40/40) | 100.0% [91.2, 100.0] (40/40) |     1     |
| M3: runaway loop   | task_completion     | 0.0% [0.0, 8.8] (0/40)       | 0.0% [0.0, 8.8] (0/40)       |     1     |
| M3: runaway loop   | tool_call_success   | 0.0% [0.0, 8.8] (0/40)       | 0.0% [0.0, 8.8] (0/40)       |     1     |
| Control            | intent_resolution   | 90.0% [76.9, 96.0] (36/40)   | 85.0% [70.9, 92.9] (34/40)   |     0.737 |