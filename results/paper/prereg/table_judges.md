# Judge v2 (pre-registered) vs judge v3 (post hoc: also sees tool definitions, tool results and the fixed date)

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
