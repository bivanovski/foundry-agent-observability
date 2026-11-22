# Second judge on the 40 audited answers (self-preference check)

Second judge: gpt-4.1-mini (2025-04-14), temperature 0, same prompt as judge v2 (sees the policy documents, not the tool results). The 40 answers are the stratified audit sample (judge-v2 'incorrect' verdicts oversampled), so rates are not population rates. These are judge-vs-judge agreements; agreement with humans comes from the audit.

| Pair | n | Agreement | Cohen's kappa | Both say correct | Only first says correct | Only second says correct |
|---|---|---|---|---|---|---|
| Judge v2 (gpt-5-mini) vs second judge (gpt-4.1-mini) | 40 | 67.5% | 0.41 | 12 | 0 | 13 |
| Judge v3 (gpt-5-mini, post hoc) vs second judge (gpt-4.1-mini) | 40 | 87.5% | 0.74 | 21 | 1 | 4 |
| Judge v2 vs judge v3 | 40 | 75.0% | 0.52 | 12 | 0 | 10 |

Agreement v2 vs second judge by scenario: control: 100.0%, mistake1: 90.0%, mistake2: 30.0%, mistake3: 50.0%
