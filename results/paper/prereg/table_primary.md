# Pre-registered metrics

| scenario          | metric                                                         | before                        | after                         | diff_after_minus_before   | fisher_p   |
|:------------------|:---------------------------------------------------------------|:------------------------------|:------------------------------|:--------------------------|:-----------|
| M1 missing lookup | Searched the policy documents [primary]                        | 100.0% [94.0, 100.0] (60/60)  | 100.0% [94.0, 100.0] (60/60)  | +0.0 pp [+0.0, +0.0]      | 1.000      |
| M1 missing lookup | Answer correct (judge v2)                                      | 100.0% [94.0, 100.0] (60/60)  | 98.3% [91.1, 99.7] (59/60)    | -1.7 pp [-5.0, +0.0]      | 1.000      |
| M1 missing lookup | Task success (process ok and answer correct)                   | 100.0% [94.0, 100.0] (60/60)  | 98.3% [91.1, 99.7] (59/60)    | -1.7 pp [-5.0, +0.0]      | 1.000      |
| M1 missing lookup | Routed to the policy agent                                     | 100.0% [94.0, 100.0] (60/60)  | 100.0% [94.0, 100.0] (60/60)  | +0.0 pp [+0.0, +0.0]      | 1.000      |
| M1 missing lookup | Answer correct (judge v3, post hoc)                            | 100.0% [94.0, 100.0] (60/60)  | 100.0% [94.0, 100.0] (60/60)  | +0.0 pp [+0.0, +0.0]      | 1.000      |
| M1 missing lookup | Task success (judge v3, post hoc)                              | 100.0% [94.0, 100.0] (60/60)  | 100.0% [94.0, 100.0] (60/60)  | +0.0 pp [+0.0, +0.0]      | 1.000      |
| M2 lost context   | Tool called with an ID not in the message [primary]            | 0.0% [0.0, 6.0] (0/60)        | 0.0% [0.0, 6.0] (0/60)        | +0.0 pp [+0.0, +0.0]      | 1.000      |
| M2 lost context   | Tool called with any ID other than the expected one [primary]  | 0.0% [0.0, 6.0] (0/60)        | 0.0% [0.0, 6.0] (0/60)        | +0.0 pp [+0.0, +0.0]      | 1.000      |
| M2 lost context   | Order ID present in the handoff (items with an ID)             | 100.0% [91.2, 100.0] (40/40)  | 100.0% [91.2, 100.0] (40/40)  | +0.0 pp [+0.0, +0.0]      | 1.000      |
| M2 lost context   | Invented ID | ID missing from handoff [primary]                | n/a (0 runs)                  | n/a (0 runs)                  | n/a                       | n/a        |
| M2 lost context   | Wrong ID | ID missing from handoff [primary]                   | n/a (0 runs)                  | n/a (0 runs)                  | n/a                       | n/a        |
| M2 lost context   | Asked for the order number (no_id items)                       | 80.0% [58.4, 91.9] (16/20)    | 90.0% [69.9, 97.2] (18/20)    | +10.0 pp [-20.0, +40.0]   | 0.661      |
| M2 lost context   | No tool call (no_id items)                                     | 100.0% [83.9, 100.0] (20/20)  | 100.0% [83.9, 100.0] (20/20)  | +0.0 pp [+0.0, +0.0]      | 1.000      |
| M2 lost context   | Answer correct (judge v2)                                      | 58.3% [45.7, 69.9] (35/60)    | 70.0% [57.5, 80.1] (42/60)    | +11.7 pp [+1.7, +21.7]    | 0.253      |
| M2 lost context   | Task success                                                   | 58.3% [45.7, 69.9] (35/60)    | 70.0% [57.5, 80.1] (42/60)    | +11.7 pp [+1.7, +21.7]    | 0.253      |
| M2 lost context   | Answer correct (judge v3, post hoc)                            | 80.0% [68.2, 88.2] (48/60)    | 88.3% [77.8, 94.2] (53/60)    | +8.3 pp [-1.7, +21.7]     | 0.317      |
| M2 lost context   | Task success (judge v3, post hoc)                              | 80.0% [68.2, 88.2] (48/60)    | 88.3% [77.8, 94.2] (53/60)    | +8.3 pp [-1.7, +21.7]     | 0.317      |
| M3 runaway loop   | Identical tool calls per run [primary]                         | mean 2.42, max 7 (n=40)       | mean 1.00, max 1 (n=40)       | -1.4 [-1.9, -1.0]         | n/a        |
| M3 runaway loop   | Tool calls per run                                             | mean 2.67, max 14 (n=40)      | mean 1.02, max 2 (n=40)       | -1.6 [-2.4, -1.0]         | n/a        |
| M3 runaway loop   | Looped (3+ identical calls or round cap)                       | 22.5% [12.3, 37.5] (9/40)     | 0.0% [0.0, 8.8] (0/40)        | -22.5 pp [-47.5, -5.0]    | 0.002      |
| M3 runaway loop   | Offered an email follow-up                                     | 42.5% [28.5, 57.8] (17/40)    | 100.0% [91.2, 100.0] (40/40)  | +57.5 pp [+35.0, +77.5]   | <0.001     |
| M3 runaway loop   | Asked the customer to confirm a correct order ID [exploratory] | 45.0% [30.7, 60.2] (18/40)    | 0.0% [0.0, 8.8] (0/40)        | -45.0 pp [-62.5, -25.0]   | <0.001     |
| M3 runaway loop   | Answer correct (judge v2)                                      | 75.0% [59.8, 85.8] (30/40)    | 95.0% [83.5, 98.6] (38/40)    | +20.0 pp [+5.0, +35.0]    | 0.025      |
| M3 runaway loop   | Task success                                                   | 62.5% [47.0, 75.8] (25/40)    | 95.0% [83.5, 98.6] (38/40)    | +32.5 pp [+15.0, +55.0]   | <0.001     |
| M3 runaway loop   | Tokens per conversation                                        | mean 2331.70, max 8876 (n=40) | mean 1693.55, max 2324 (n=40) | -638.1 [-1165.8, -168.0]  | n/a        |
| M3 runaway loop   | Latency per conversation (s)                                   | mean 12.60, max 27 (n=40)     | mean 9.53, max 13 (n=40)      | -3.1 [-4.5, -1.6]         | n/a        |
| M3 runaway loop   | Answer correct (judge v3, post hoc)                            | 75.0% [59.8, 85.8] (30/40)    | 95.0% [83.5, 98.6] (38/40)    | +20.0 pp [+7.5, +35.0]    | 0.025      |
| M3 runaway loop   | Task success (judge v3, post hoc)                              | 62.5% [47.0, 75.8] (25/40)    | 95.0% [83.5, 98.6] (38/40)    | +32.5 pp [+15.0, +55.0]   | <0.001     |
| Control           | Routed correctly [primary]                                     | 100.0% [91.2, 100.0] (40/40)  | 100.0% [91.2, 100.0] (40/40)  | +0.0 pp [+0.0, +0.0]      | 1.000      |
| Control           | Answer correct (judge v2) [primary]                            | 70.0% [54.6, 81.9] (28/40)    | 80.0% [65.2, 89.5] (32/40)    | +10.0 pp [+0.0, +25.0]    | 0.439      |
| Control           | No function tool call                                          | 100.0% [91.2, 100.0] (40/40)  | 100.0% [91.2, 100.0] (40/40)  | +0.0 pp [+0.0, +0.0]      | 1.000      |
| Control           | Task success                                                   | 70.0% [54.6, 81.9] (28/40)    | 80.0% [65.2, 89.5] (32/40)    | +10.0 pp [+0.0, +25.0]    | 0.439      |
| Control           | Answer correct (judge v3, post hoc)                            | 70.0% [54.6, 81.9] (28/40)    | 80.0% [65.2, 89.5] (32/40)    | +10.0 pp [+0.0, +25.0]    | 0.439      |
| Control           | Task success (judge v3, post hoc)                              | 70.0% [54.6, 81.9] (28/40)    | 80.0% [65.2, 89.5] (32/40)    | +10.0 pp [+0.0, +25.0]    | 0.439      |
