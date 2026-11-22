# B1 rerun: Task Adherence on F1 with full File Search results

Runs: 240; errors: 0; logged searches not matched to a span: 0.

| Model | Condition | Runs | Old pass | New pass | Old fail | New fail | Judge v2 correct |
|---|---|---|---|---|---|---|---|
| gpt-5-mini | before | 60 | 46 | 60 | 14 | 0 | 60 |
| gpt-5-mini | after | 60 | 38 | 60 | 22 | 0 | 59 |
| gpt-4.1-mini | before | 60 | 32 | 60 | 28 | 0 | 59 |
| gpt-4.1-mini | after | 60 | 31 | 59 | 29 | 1 | 60 |

The 53 runs whose answer mentions the holiday extension: old fail 31, new fail 1.
Verdict changes overall: fail -> pass 93, pass -> fail 1.
