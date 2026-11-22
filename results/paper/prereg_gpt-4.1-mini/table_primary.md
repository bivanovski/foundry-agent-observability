# Pre-registered metrics

| scenario          | metric                                                         | before                       | after                        | diff_after_minus_before    | fisher_p   |
|:------------------|:---------------------------------------------------------------|:-----------------------------|:-----------------------------|:---------------------------|:-----------|
| M1 missing lookup | Searched the policy documents [primary]                        | 100.0% [94.0, 100.0] (60/60) | 100.0% [94.0, 100.0] (60/60) | +0.0 pp [+0.0, +0.0]       | 1.000      |
| M1 missing lookup | Answer correct (judge v2)                                      | 98.3% [91.1, 99.7] (59/60)   | 100.0% [94.0, 100.0] (60/60) | +1.7 pp [+0.0, +5.0]       | 1.000      |
| M1 missing lookup | Task success (process ok and answer correct)                   | 98.3% [91.1, 99.7] (59/60)   | 100.0% [94.0, 100.0] (60/60) | +1.7 pp [+0.0, +5.0]       | 1.000      |
| M1 missing lookup | Routed to the policy agent                                     | 100.0% [94.0, 100.0] (60/60) | 100.0% [94.0, 100.0] (60/60) | +0.0 pp [+0.0, +0.0]       | 1.000      |
| M1 missing lookup | Answer correct (judge v3, post hoc)                            | 98.3% [91.1, 99.7] (59/60)   | 100.0% [94.0, 100.0] (60/60) | +1.7 pp [+0.0, +5.0]       | 1.000      |
| M1 missing lookup | Task success (judge v3, post hoc)                              | 98.3% [91.1, 99.7] (59/60)   | 100.0% [94.0, 100.0] (60/60) | +1.7 pp [+0.0, +5.0]       | 1.000      |
| M2 lost context   | Tool called with an ID not in the message [primary]            | 0.0% [0.0, 6.0] (0/60)       | 0.0% [0.0, 6.0] (0/60)       | +0.0 pp [+0.0, +0.0]       | 1.000      |
| M2 lost context   | Tool called with any ID other than the expected one [primary]  | 0.0% [0.0, 6.0] (0/60)       | 0.0% [0.0, 6.0] (0/60)       | +0.0 pp [+0.0, +0.0]       | 1.000      |
| M2 lost context   | Order ID present in the handoff (items with an ID)             | 100.0% [91.2, 100.0] (40/40) | 100.0% [91.2, 100.0] (40/40) | +0.0 pp [+0.0, +0.0]       | 1.000      |
| M2 lost context   | Invented ID | ID missing from handoff [primary]                | n/a (0 runs)                 | n/a (0 runs)                 | n/a                        | n/a        |
| M2 lost context   | Wrong ID | ID missing from handoff [primary]                   | n/a (0 runs)                 | n/a (0 runs)                 | n/a                        | n/a        |
| M2 lost context   | Asked for the order number (no_id items)                       | 100.0% [83.9, 100.0] (20/20) | 100.0% [83.9, 100.0] (20/20) | +0.0 pp [+0.0, +0.0]       | 1.000      |
| M2 lost context   | No tool call (no_id items)                                     | 100.0% [83.9, 100.0] (20/20) | 100.0% [83.9, 100.0] (20/20) | +0.0 pp [+0.0, +0.0]       | 1.000      |
| M2 lost context   | Answer correct (judge v2)                                      | 50.0% [37.7, 62.3] (30/60)   | 66.7% [54.1, 77.3] (40/60)   | +16.7 pp [+1.7, +35.0]     | 0.095      |
| M2 lost context   | Task success                                                   | 50.0% [37.7, 62.3] (30/60)   | 66.7% [54.1, 77.3] (40/60)   | +16.7 pp [+1.7, +35.0]     | 0.095      |
| M2 lost context   | Answer correct (judge v3, post hoc)                            | 83.3% [72.0, 90.7] (50/60)   | 83.3% [72.0, 90.7] (50/60)   | +0.0 pp [+0.0, +0.0]       | 1.000      |
| M2 lost context   | Task success (judge v3, post hoc)                              | 83.3% [72.0, 90.7] (50/60)   | 83.3% [72.0, 90.7] (50/60)   | +0.0 pp [+0.0, +0.0]       | 1.000      |
| M3 runaway loop   | Identical tool calls per run [primary]                         | mean 1.05, max 2 (n=40)      | mean 1.00, max 1 (n=40)      | -0.1 [-0.1, +0.0]          | n/a        |
| M3 runaway loop   | Tool calls per run                                             | mean 1.07, max 2 (n=40)      | mean 1.00, max 1 (n=40)      | -0.1 [-0.1, -0.0]          | n/a        |
| M3 runaway loop   | Looped (3+ identical calls or round cap)                       | 0.0% [0.0, 8.8] (0/40)       | 0.0% [0.0, 8.8] (0/40)       | +0.0 pp [+0.0, +0.0]       | 1.000      |
| M3 runaway loop   | Offered an email follow-up                                     | 0.0% [0.0, 8.8] (0/40)       | 100.0% [91.2, 100.0] (40/40) | +100.0 pp [+100.0, +100.0] | <0.001     |
| M3 runaway loop   | Asked the customer to confirm a correct order ID [exploratory] | 100.0% [91.2, 100.0] (40/40) | 0.0% [0.0, 8.8] (0/40)       | -100.0 pp [-100.0, -100.0] | <0.001     |
| M3 runaway loop   | Answer correct (judge v2)                                      | 2.5% [0.4, 12.9] (1/40)      | 97.5% [87.1, 99.6] (39/40)   | +95.0 pp [+90.0, +100.0]   | <0.001     |
| M3 runaway loop   | Task success                                                   | 2.5% [0.4, 12.9] (1/40)      | 97.5% [87.1, 99.6] (39/40)   | +95.0 pp [+87.5, +100.0]   | <0.001     |
| M3 runaway loop   | Tokens per conversation                                        | mean 652.70, max 980 (n=40)  | mean 875.08, max 946 (n=40)  | +222.4 [+201.2, +242.2]    | n/a        |
| M3 runaway loop   | Latency per conversation (s)                                   | mean 6.51, max 19 (n=40)     | mean 5.90, max 10 (n=40)     | -0.6 [-2.1, +0.4]          | n/a        |
| M3 runaway loop   | Answer correct (judge v3, post hoc)                            | 5.0% [1.4, 16.5] (2/40)      | 97.5% [87.1, 99.6] (39/40)   | +92.5 pp [+82.5, +100.0]   | <0.001     |
| M3 runaway loop   | Task success (judge v3, post hoc)                              | 5.0% [1.4, 16.5] (2/40)      | 97.5% [87.1, 99.6] (39/40)   | +92.5 pp [+82.5, +100.0]   | <0.001     |
| Control           | Routed correctly [primary]                                     | 100.0% [91.2, 100.0] (40/40) | 100.0% [91.2, 100.0] (40/40) | +0.0 pp [+0.0, +0.0]       | 1.000      |
| Control           | Answer correct (judge v2) [primary]                            | 75.0% [59.8, 85.8] (30/40)   | 87.5% [73.9, 94.5] (35/40)   | +12.5 pp [+0.0, +32.5]     | 0.252      |
| Control           | No function tool call                                          | 100.0% [91.2, 100.0] (40/40) | 100.0% [91.2, 100.0] (40/40) | +0.0 pp [+0.0, +0.0]       | 1.000      |
| Control           | Task success                                                   | 75.0% [59.8, 85.8] (30/40)   | 87.5% [73.9, 94.5] (35/40)   | +12.5 pp [+0.0, +32.5]     | 0.252      |
| Control           | Answer correct (judge v3, post hoc)                            | 72.5% [57.2, 83.9] (29/40)   | 87.5% [73.9, 94.5] (35/40)   | +15.0 pp [+2.5, +35.0]     | 0.161      |
| Control           | Task success (judge v3, post hoc)                              | 72.5% [57.2, 83.9] (29/40)   | 87.5% [73.9, 94.5] (35/40)   | +15.0 pp [+2.5, +35.0]     | 0.161      |
