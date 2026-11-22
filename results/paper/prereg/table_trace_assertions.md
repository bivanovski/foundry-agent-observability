# Trace assertions (spans only) vs client-side metrics

Traces: 400; complete: 400; with root span: 400; sampled: 0. Tool spans 246 vs logged tool calls 246; file-search spans 157 vs logged 157.


## Omission (policy agent invoked, no file_search span) vs client `searched == False`

| trace_omission   |   False |
|:-----------------|--------:|
| False            |     150 |

By condition: after: 0/75 omissions, before: 0/75 omissions

## Repetition (3+ identical execute_tool spans) vs client `looped`

| trace_repetition   |   False |   True |
|:-------------------|--------:|-------:|
| False              |     391 |      0 |
| True               |       0 |      9 |

Max identical calls, trace vs client, equal in 400/400 runs.
