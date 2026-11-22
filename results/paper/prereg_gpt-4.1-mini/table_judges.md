# Judge v2 (pre-registered) vs judge v3 (post hoc: also sees tool definitions, tool results and the fixed date)

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
