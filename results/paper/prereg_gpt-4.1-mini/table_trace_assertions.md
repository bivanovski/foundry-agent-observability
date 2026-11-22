# Trace assertions (spans only) vs client-side metrics

Traces: 400; complete: 400; with root span: 400; sampled: 0. Tool spans 165 vs logged tool calls 165; file-search spans 214 vs logged 150.

Note: file-search spans exceed the logged searches because Foundry ran the search in agent requests that then returned HTTP 429 (rate limit) and were retried automatically by the client library. The client log only records the successful attempt; the trace shows the retried work too (data/rate_limit_retries.csv).

## Omission (policy agent invoked, no file_search span) vs client `searched == False`

| trace_omission   |   False |
|:-----------------|--------:|
| False            |     150 |

By condition: after: 0/75 omissions, before: 0/75 omissions

## Repetition (3+ identical execute_tool spans) vs client `looped`

| trace_repetition   |   False |
|:-------------------|--------:|
| False              |     400 |

Max identical calls, trace vs client, equal in 400/400 runs.
