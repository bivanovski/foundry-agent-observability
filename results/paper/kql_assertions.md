# Fig. 3 trace assertions run as KQL in Application Insights

The queries are in `trace_queries.kql` (copy into Application Insights > Logs, time range 30 days). Each query is compared with the client-side metric for the same conversations.

| Model | Condition | Conversations | Omission query hits | Client: policy agent did not search | Repetition query hits | Client: looped (3+ identical calls) | Query = client, every conversation |
|---|---|---|---|---|---|---|---|
| gpt-5-mini | before | 200 | 0 | 0 | 9 | 9 | yes |
| gpt-5-mini | after | 200 | 0 | 0 | 0 | 0 | yes |
| gpt-4.1-mini | before | 200 | 0 | 0 | 0 | 0 | yes |
| gpt-4.1-mini | after | 200 | 0 | 0 | 0 | 0 | yes |
