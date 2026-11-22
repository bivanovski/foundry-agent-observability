# Latency and tokens

| scenario          | condition   |   runs |   latency_p50_s |   latency_p95_s |   correct_runs | correct_runs_over_10s   |   specialist_calls_p50_s |   tokens_mean |   tokens_p95 |   model_calls_mean |
|:------------------|:------------|-------:|----------------:|----------------:|---------------:|:------------------------|-------------------------:|--------------:|-------------:|-------------------:|
| M1 missing lookup | before      |     60 |            5.04 |           14.07 |             59 | 18.6%                   |                     3.08 |          2470 |         2543 |               2    |
| M1 missing lookup | after       |     60 |            4.58 |           22.78 |             60 | 25.0%                   |                     3.06 |          2550 |         2615 |               2    |
| M2 lost context   | before      |     60 |            5.19 |           11.46 |             30 | 26.7%                   |                     1.68 |           631 |          790 |               2.7  |
| M2 lost context   | after       |     60 |            4.55 |           12.78 |             40 | 12.5%                   |                     1.65 |           815 |         1111 |               2.67 |
| M3 runaway loop   | before      |     40 |            4.68 |           16.54 |              1 | 0.0%                    |                     1.6  |           653 |          915 |               3.08 |
| M3 runaway loop   | after       |     40 |            5.07 |           10.22 |             39 | 12.8%                   |                     1.68 |           875 |          927 |               3    |
| Control           | before      |     40 |            1.6  |            8.14 |             30 | 3.3%                    |                     3.29 |          1053 |         2541 |               1.38 |
| Control           | after       |     40 |            1.46 |           20.67 |             35 | 17.1%                   |                     2.98 |          1074 |         2602 |               1.38 |
