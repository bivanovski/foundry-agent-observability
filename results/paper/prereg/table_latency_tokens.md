# Latency and tokens

| scenario          | condition   |   runs |   latency_p50_s |   latency_p95_s |   correct_runs | correct_runs_over_10s   |   specialist_calls_p50_s |   tokens_mean |   tokens_p95 |   model_calls_mean |
|:------------------|:------------|-------:|----------------:|----------------:|---------------:|:------------------------|-------------------------:|--------------:|-------------:|-------------------:|
| M1 missing lookup | before      |     60 |           12.55 |           16.7  |             60 | 93.3%                   |                     9.31 |          4524 |         5042 |               2    |
| M1 missing lookup | after       |     60 |           13.29 |           17.88 |             59 | 94.9%                   |                     9.39 |          4633 |         5120 |               2    |
| M2 lost context   | before      |     60 |            9.29 |           13.49 |             35 | 42.9%                   |                     3.17 |          1546 |         2440 |               2.78 |
| M2 lost context   | after       |     60 |            8.99 |           13.43 |             42 | 33.3%                   |                     3.47 |          1729 |         2584 |               2.75 |
| M3 runaway loop   | before      |     40 |           11.77 |           16.9  |             30 | 83.3%                   |                     1.96 |          2332 |         4429 |               4.5  |
| M3 runaway loop   | after       |     40 |            9.2  |           12.53 |             38 | 26.3%                   |                     3.28 |          1694 |         2146 |               3    |
| Control           | before      |     40 |            4.13 |           16.57 |             28 | 46.4%                   |                    10.67 |          2259 |         6465 |               1.38 |
| Control           | after       |     40 |            5.08 |           16.73 |             32 | 46.9%                   |                    10.46 |          2065 |         5001 |               1.38 |
