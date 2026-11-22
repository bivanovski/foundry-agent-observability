# Trace ids for figures

Open the project in the Foundry portal, then Agents > Traces (or App Insights > Transaction search) and search by trace id.

## M1: missing lookup
- after, succeeded: P08 rep5 trace `cfdb4cc3d244fa8cece61c185455b95f` (12.986s, 0 tool calls)
- after, succeeded: P03 rep2 trace `45b12d11ce506725387247da9c9d06cd` (14.994s, 0 tool calls)
- after, succeeded: P07 rep2 trace `1c5904e9852d33a67f3015df6020aef1` (10.959s, 0 tool calls)

## M2: lost context
- before, failed: O02 rep5 trace `e9ba1f16ba57ff46113a5f9e8222644a` (9.883000000000001s, 1 tool calls)
- before, failed: O02 rep3 trace `39e6077ec59ef291cd6fb7168acb21a7` (9.201s, 1 tool calls)
- before, failed: O04 rep3 trace `6ef9ea82a73b9c4d91f4ce0b89ed67c4` (13.711s, 2 tool calls)
- after, succeeded: O09 rep4 trace `3a9cfdc2ba06fcbca0f65abb2a83c222` (8.968s, 0 tool calls)
- after, succeeded: O03 rep2 trace `5f1c6af4ec55624484f62d6c4aaa626c` (11.576s, 1 tool calls)
- after, succeeded: O01 rep4 trace `6027da3092b535a49c2743075b68a937` (8.806s, 1 tool calls)

## M3: runaway loop
- before, failed: X04 rep1 trace `0a04d0fa8a548b3c16ea3f5db473c374` (13.942s, 2 tool calls)
- before, failed: X07 rep1 trace `54275b141678c31df0770e896b523edd` (12.339s, 2 tool calls)
- before, failed: X08 rep4 trace `abb877f81286b2a799a4da08b65b5c6e` (16.103s, 3 tool calls)
- after, succeeded: X06 rep5 trace `b3176d20e97db05d646316a8894002c1` (9.634s, 1 tool calls)
- after, succeeded: X07 rep3 trace `2ea750f6cc6c8dbbdfb83d500b28a7bd` (11.521s, 1 tool calls)
- after, succeeded: X07 rep1 trace `32de7f7dadcfae633db2b35d19198699` (13.138s, 1 tool calls)

## Control
- before, failed: R07 rep1 trace `ac3727019215fc038afc71229fb30267` (13.22s, 0 tool calls)
- before, failed: R04 rep2 trace `462b4e1288ecfc6dabd5982ea022500c` (2.967s, 0 tool calls)
- before, failed: R07 rep5 trace `db993d24f4752ff697292e8be5be27f8` (13.211s, 0 tool calls)
- after, succeeded: R08 rep5 trace `0dc675638560fa9d614ebef51494354e` (15.245s, 0 tool calls)
- after, succeeded: R05 rep5 trace `0053bbd0e733810333ae4c7da7bedc04` (3.77s, 0 tool calls)
- after, succeeded: R07 rep4 trace `7d058691cff22ee6b6250262daa4c1a7` (17.464s, 0 tool calls)
