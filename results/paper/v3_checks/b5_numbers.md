| # | Claim | Paper | Recomputed | Status | Note |
|---|---|---|---|---|---|
| 1 | Conversations per model | 400 completed, 0 excluded | 5m 400 rows, 0 errors; 41m 400 rows, 0 errors | **MATCH** |  |
| 2 | F1 searched, B and A, both models | 60/60 | {('5m', 'before'): '60/60', ('5m', 'after'): '60/60', ('41m', 'before'): '60/60', ('41m', 'after'): '60/60'} | **MATCH** |  |
| 3 | F2 invented or wrong ID, B and A, both models | 0/60 | {('5m', 'before'): '0/60', ('5m', 'after'): '0/60', ('41m', 'before'): '0/60', ('41m', 'after'): '0/60'} | **MATCH** |  |
| 4 | Order ID in handoff, B runs with an ID, both models | 40/40 | {'5m': '40/40', '41m': '40/40'} | **MATCH** |  |
| 5 | no_id items: no tool call | 20/20 | {('5m', 'before'): '20/20', ('5m', 'after'): '20/20', ('41m', 'before'): '20/20', ('41m', 'after'): '20/20'} | **MATCH** |  |
| 6 | F3 5m identical calls per run | 2.42 (7) -> 1.00 (1); -1.4 [-1.9, -1.0] | mean 2.42 (max 7) -> 1.00 (1); diff -1.42 [-1.95, -1.05] | **MATCH** | CI bounds vary by about +-0.1 between bootstrap runs; the package tables show [-2.0, -1.1] (prereg) and [-1.9, -1.0] (model comparison) |
| 7 | F3 5m looped | 9/40 -> 0/40 | 9/40 -> 0/40 | **MATCH** |  |
| 8 | F3 5m task success (v2) | 62.5% -> 95.0%; +32.5 pp [+15.0, +55.0] | 62.5% -> 95.0%; +32.5 pp [+15.0, +55.0] | **MATCH** | with 8 items, CI bounds move in steps of 2.5 pp between bootstrap runs |
| 9 | F3 5m tokens per conversation | -638 [-1,166, -168] | -638.1 [-1229, -166] | **MATCH** | point estimate exact; CI bounds vary between bootstrap runs (package: [-1,235, -171] prereg, [-1,166, -168] comparison) |
| 10 | F3 5m latency per conversation | -3.1 s [-4.5, -1.6] | -3.07 s [-4.54, -1.67] | **MATCH** | point estimate exact; CI bounds vary by about +-0.1 |
| 11 | F3 5m loops by item | X08 5/5, X07 0/5 | {'X01': '1/5', 'X02': '2/5', 'X03': '0/5', 'X04': '0/5', 'X05': '0/5', 'X06': '1/5', 'X07': '0/5', 'X08': '5/5'} | **MATCH** |  |
| 12 | F3 41m identical calls | mean 1.05, max 2 | mean 1.050, max 2 | **MATCH** |  |
| 13 | Asked to re-confirm a valid ID | 41m 40/40 -> 0/40; 5m 18/40 -> 0/40 | 41m 40/40 -> 0/40; 5m 18/40 -> 0/40 | **MATCH** |  |
| 14 | F3 41m task success (v2) | 2.5% -> 97.5% | 2.5% -> 97.5% | **MATCH** |  |
| 15 | Controls routed correctly | 100% | {('5m', 'before'): '40/40', ('5m', 'after'): '40/40', ('41m', 'before'): '40/40', ('41m', 'after'): '40/40'} | **MATCH** |  |
| 16 | Controls answer correct (v2) | 5m 70.0% -> 80.0%; 41m 75.0% -> 87.5% | {('5m', 'before'): '70.0%', ('5m', 'after'): '80.0%', ('41m', 'before'): '75.0%', ('41m', 'after'): '87.5%'} | **MATCH** |  |
| 17 | Order-agent span, trace 2e0fea3c... | about 18 s (18,458 ms) | 18458 ms | **MATCH** |  |
| 18 | Repetition KQL | 9 hits = 9 client loops; 0 elsewhere | 9 hits, 9 client loops; per row: [['gpt-5-mini', 'after', 0], ['gpt-5-mini', 'before', 0], ['gpt-5-mini', 'after', 0], ['gpt-5-mini', 'before', 0], ['gpt-5-mini', 'after', 0], ['gpt-5-mini', 'before', 0], ['gpt-5-mini', 'after', 0], ['gpt-5-mini', 'before', 9], ['gpt-4.1-mini', 'after', 0], ['gpt-4.1-mini', 'before', 0], ['gpt-4.1-mini', 'after', 0], ['gpt-4.1-mini', 'before', 0], ['gpt-4.1-mini', 'after', 0], ['gpt-4.1-mini', 'before', 0], ['gpt-4.1-mini', 'after', 0], ['gpt-4.1-mini', 'before', 0]] | **MATCH** |  |
| 19 | Omission KQL | 0 hits; policy agent reached in 300 (150 per model) | 0 hits; policy agent reached: {'5m': 150, '41m': 150} | **MATCH** |  |
| 20 | Provenance: function-tool calls, IDs found in the customer message | 411 (246 + 165), all found | 5m 246 calls (246 found); 41m 165 calls (165 found) | **MATCH** |  |
| 21 | Spans with error status | none in 5m; 41m only 557 POST + 557 invoke_agent (HTTP 429) | 5m none; 41m {'POST <http>': 557, 'invoke_agent triage-agent-gpt41mini:<v>': 160, 'invoke_agent order-agent-before-gpt41mini:<v>': 120, 'invoke_agent policy-agent-after-gpt41mini:<v>': 117, 'invoke_agent order-agent-after-gpt41mini:<v>': 88, 'invoke_agent policy-agent-before-gpt41mini:<v>': 72} | **CHECK** |  |
| 22 | 41m HTTP 429 | 557 requests in 183/400 (46%); 214 vs 150 | 557 requests in 183/400 (45.8%); file-search spans 214 vs logged 150 | **MATCH** |  |
| 23 | Correct 5m runs over 10 s | 63.0% of 324; p50 11.3 s, p95 16.5 s | 63.0% of 324; p50 11.3 s, p95 16.5 s | **MATCH** |  |
| 24 | Triage output tokens | mean 282, 71% reasoning (5m); 33 (41m) | 5m mean 282.1, reasoning share 71.3%; 41m mean 33.3 | **MATCH** |  |
| 25 | F3 41m tokens per conversation | +34% (652.7 -> 875.1) | 652.7 -> 875.1 (+34.1%) | **MATCH** |  |
| 26 | Table III F3 5m | tool calls 2.67 -> 1.02; tokens -27%; median latency 11.8 -> 9.2 s | tool calls 2.675 -> 1.025; tokens 2331.7 -> 1693.5 (-27.4%); median latency 11.77 -> 9.20 s | **CHECK** |  |
| 27 | Table III F3 41m tool calls | 1.07 -> 1.00 | 1.0750 -> 1.0000 (= 43/40 -> 40/40) | **MATCH** | 43/40 = 1.075 exactly: '1.07' (round half to even / float) or '1.08' (round half up); consider writing 1.075 or 1.08 |
| 28 | Tool Selection (F1) | 240/240 pass | {'5m': '120/120', '41m': '120/120'}; not_applicable {'5m': 0, '41m': 0} | **MATCH** |  |
| 29 | Task Adherence fails on F1 (B/A) | 5m 14/60, 22/60; 41m 28/60, 29/60 (23-48%); judge v2 F1 correct 98-100% | fails {('5m', 'before'): 14, ('5m', 'after'): 22, ('41m', 'before'): 28, ('41m', 'after'): 29} (= 23.3%-48.3%); judge v2 correct {('5m', 'before'): '100.0%', ('5m', 'after'): '98.3%', ('41m', 'before'): '98.3%', ('41m', 'after'): '100.0%'} | **MATCH** | see B1: these fails are partly caused by our truncation of search results |
| 30 | Tool Input Accuracy and Tool Call Accuracy, runs with a tool call | passed 160/160 | 5m 80 runs: TIA 80, TCA 80; 41m 80 runs: TIA 80, TCA 80; total 160 | **MATCH** |  |
| 31 | Task Completion and Tool Call Success on F3 | 0/40 pass, both conditions, both models | {('5m', 'before'): ('0/40', '0/40'), ('5m', 'after'): ('0/40', '0/40'), ('41m', 'before'): ('0/40', '0/40'), ('41m', 'after'): ('0/40', '0/40')} | **MATCH** |  |
| 32 | Intent Resolution 41m F3 B; content filter | 37/40 pass; 3 blocked (5m O04 B) | 41m F3 B: 37/40; blocked: {'5m': [['O04', 'before', 1], ['O04', 'before', 4], ['O04', 'before', 2]], '41m': []} | **MATCH** |  |
| 33 | Judge v3 on F2 5m | changed 32/120 (28 to correct, 4 to incorrect) | changed 32/120 (28 to correct, 4 to incorrect) | **MATCH** |  |
| 34 | Second judge vs v2 / vs v3 | kappa 0.41 / 0.74 (n = 40) | kappa 0.41 / 0.74 (n = 40) | **MATCH** | aggregate only; no per-answer verdict shown |
| 35 | F2 judged gain | 5m v2 +11.7 [+1.7, +21.7], v3 +8.3 [-1.7, +21.7]; 41m v2 +16.7, v3 0 (83.3% both) | {('5m', 'answer_correct'): '+11.7 pp [+1.7, +21.7] (58.3% -> 70.0%)', ('5m', 'answer_correct_v3'): '+8.3 pp [-1.7, +21.7] (80.0% -> 88.3%)', ('41m', 'answer_correct'): '+16.7 pp [+1.7, +35.0] (50.0% -> 66.7%)', ('41m', 'answer_correct_v3'): '+0.0 pp [+0.0, +0.0] (83.3% -> 83.3%)'} | **MATCH** | point estimates exact; CI bounds move in steps of about 1.7 pp between bootstrap runs |
| 36 | 5m social controls accepted | 15/25 -> 17/25; all rejections R03 or R04 | 15/25 -> 17/25; rejected items ['R03', 'R04'] | **MATCH** |  |
| 37 | F1 omission rate upper bound | below 6% at 95% (Wilson, 0/60) | Wilson upper bound for 0/60 = 6.02%; for 0/120 (both models pooled) = 3.10% | **MISMATCH** | 6.02% is not below 6%; write 'at most 6.0%' per model, or 'below 3.2%' pooled over both models (0/120) |
