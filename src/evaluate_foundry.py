"""Runs Foundry's built-in agent evaluators over a results file.

These are the evaluators the article names (Intent Resolution, Task Adherence,
Task Completion, Tool Selection, Tool Input Accuracy, Tool Output Utilization,
Tool Call Success). Several are in preview and their class names have changed
between SDK releases, so each one is loaded by name and skipped with a warning
if it is missing. Check `pip show azure-ai-evaluation` and the built-in
evaluators reference if many are skipped.

    python -m src.evaluate_foundry results/main.jsonl            -> results/main.foundry_eval.jsonl
    python -m src.evaluate_foundry results/main.jsonl --upload   also logs one evaluation run per condition
                                                                  to the Foundry portal (Evaluations, then Compare)
"""
import argparse
import importlib
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .config import AZURE_OPENAI_API_VERSION, AZURE_OPENAI_ENDPOINT, JUDGE_MODEL, PROJECT_ENDPOINT
from .tools import TOOL_DEFINITIONS

EVALUATORS = [
    # (short name, class name, uses tool_definitions)
    ("intent_resolution", "IntentResolutionEvaluator", True),
    ("task_adherence", "TaskAdherenceEvaluator", True),
    ("task_completion", "TaskCompletionEvaluator", True),
    ("tool_selection", "ToolSelectionEvaluator", True),
    ("tool_input_accuracy", "ToolInputAccuracyEvaluator", True),
    ("tool_output_utilization", "ToolOutputUtilizationEvaluator", True),
    ("tool_call_success", "ToolCallSuccessEvaluator", True),
    ("tool_call_accuracy", "ToolCallAccuracyEvaluator", True),  # older combined evaluator, kept as a fallback
]

# Which evaluators run on which scenario (smoke review plan, step 9). Intent Resolution runs on every item.
EVAL_PLAN = {
    "mistake1": ["intent_resolution", "tool_selection", "task_adherence"],
    "mistake2": ["intent_resolution", "tool_input_accuracy", "tool_call_accuracy"],
    "mistake3": ["intent_resolution", "tool_call_success", "task_completion"],
    "control": ["intent_resolution"],
}

FILE_SEARCH_DEF = {"name": "file_search", "description": "Search the store's policy documents.",
                   "parameters": {"type": "object", "properties": {"queries": {"type": "array", "items": {"type": "string"}}}}}


def to_agent_messages(r: dict):
    """Converts one recorded run into the query/response/tool_definitions shape the agent evaluators expect.
    The query is the customer's original message, so tool arguments are judged against what the customer said."""
    query = [{"role": "user", "content": [{"type": "text", "text": r["message"]}]}]
    response, n = [], 0
    for fs in r.get("file_search", []):
        n += 1
        cid = f"fs_{n}"
        response.append({"role": "assistant", "content": [{"type": "tool_call", "tool_call_id": cid, "name": "file_search",
                                                            "arguments": {"queries": fs.get("queries", [])}}]})
        response.append({"role": "tool", "tool_call_id": cid,
                         "content": [{"type": "tool_result", "tool_result": fs.get("top_text", [])}]})
    for tc in r.get("tool_calls", []):
        n += 1
        cid = f"call_{n}"
        response.append({"role": "assistant", "content": [{"type": "tool_call", "tool_call_id": cid, "name": tc["name"],
                                                            "arguments": tc["args"]}]})
        response.append({"role": "tool", "tool_call_id": cid, "content": [{"type": "tool_result", "tool_result": tc["output"]}]})
    response.append({"role": "assistant", "content": [{"type": "text", "text": r.get("answer") or ""}]})
    spec = r.get("specialist") or ""
    if spec.startswith("policy"):
        defs = [FILE_SEARCH_DEF]
    elif spec.startswith("order"):
        defs = [{k: d[k] for k in ("name", "description", "parameters")} for d in TOOL_DEFINITIONS]
    else:
        defs = []
    return query, response, defs


def load_evaluators():
    mod = importlib.import_module("azure.ai.evaluation")
    from azure.ai.evaluation import AzureOpenAIModelConfiguration
    model_config = AzureOpenAIModelConfiguration(azure_endpoint=AZURE_OPENAI_ENDPOINT, azure_deployment=JUDGE_MODEL,
                                                 api_version=AZURE_OPENAI_API_VERSION)
    loaded = {}
    for short, cls_name, uses_defs in EVALUATORS:
        cls = getattr(mod, cls_name, None)
        if cls is None:
            # azure-ai-evaluation 1.18 ships several agent evaluators only as preview classes with a
            # leading underscore, e.g. azure.ai.evaluation._evaluators._tool_selection._ToolSelectionEvaluator.
            try:
                sub = importlib.import_module(f"azure.ai.evaluation._evaluators._{short}")
                cls = getattr(sub, f"_{cls_name}", None) or getattr(sub, cls_name, None)
            except ImportError:
                cls = None
        if cls is None:
            print(f"[skip] {cls_name} not in this azure-ai-evaluation version")
            continue
        # The judge is a reasoning model (gpt-5-mini): evaluators must not send temperature/max_tokens.
        # Newer SDKs take is_reasoning_model=True; older ones don't, so try the richest signature first.
        from azure.identity import DefaultAzureCredential
        attempts = [dict(credential=DefaultAzureCredential(), is_reasoning_model=True),
                    dict(is_reasoning_model=True), dict(credential=DefaultAzureCredential()), {}]
        try:
            for extra in attempts:
                try:
                    loaded[short] = (cls(model_config=model_config, **extra), uses_defs)
                    break
                except TypeError:
                    continue
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {cls_name}: {e}")
    print(f"Loaded evaluators: {', '.join(loaded) or 'none'}")
    return loaded


def summarize(short: str, raw: dict) -> dict:
    out = {}
    for k, v in (raw or {}).items():
        if k.endswith("_result"):
            # "not_applicable" (e.g. Tool Selection when no tool was called) is not a fail: keep it as None
            res = str(v).lower()
            out[f"{short}_result"] = res
            out[f"{short}_pass"] = True if res == "pass" else False if res == "fail" else None
        elif k.endswith("_reason"):
            out[f"{short}_reason"] = v
        elif k == short or k.endswith("_score"):
            out[f"{short}_score"] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--all-evaluators", action="store_true", help="run every evaluator on every row instead of EVAL_PLAN")
    ap.add_argument("--upload-only", action="store_true", help="skip the local evaluation, only log runs to the portal")
    ap.add_argument("--upload-limit", type=int, help="conversations per portal run (for a quick test)")
    a = ap.parse_args()

    src = Path(a.results)
    rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if not r.get("error")]
    evals = load_evaluators()
    if not evals:
        raise SystemExit("No evaluators loaded. pip install -U azure-ai-evaluation and check class names.")
    if a.upload_only:
        upload(rows, evals, src.name.replace(".graded.jsonl", "").replace(".jsonl", ""), a.upload_limit)
        return

    def run_row(r):
        q, resp, defs = to_agent_messages(r)
        res = {"qid": r["qid"], "condition": r["condition"], "rep": r["rep"], "scenario": r["scenario"],
               "trace_id": r.get("trace_id")}
        wanted = list(evals) if a.all_evaluators else EVAL_PLAN.get(r["scenario"], ["intent_resolution"])
        for short, (ev, uses_defs) in evals.items():
            if short not in wanted:
                continue
            try:
                kwargs = dict(query=q, response=resp)
                if uses_defs and defs:
                    kwargs["tool_definitions"] = defs
                res.update(summarize(short, ev(**kwargs)))
            except Exception as e:  # noqa: BLE001
                if "content management policy" in str(e) or "content_filter" in str(e):
                    # Azure's content filter blocked the evaluator prompt: a final outcome, not retried
                    res[f"{short}_result"] = "blocked_content_filter"
                    res[f"{short}_pass"] = None
                else:
                    res[f"{short}_error"] = f"{type(e).__name__}: {str(e)[:200]}"
        return res

    # Results are saved per conversation as they complete, so an interrupted run resumes. A conversation with any
    # evaluator error is not saved and is retried on the next run.
    import threading
    stem = src.name.replace(".graded.jsonl", "").replace(".jsonl", "")
    partial = src.parent / f"{stem}.foundry_eval.partial.jsonl"
    done = {}
    if partial.exists():
        for l in partial.read_text(encoding="utf-8").splitlines():
            if l.strip():
                d = json.loads(l)
                done[(d["qid"], d["condition"], d["rep"])] = d
    todo = [r for r in rows if (r["qid"], r["condition"], r["rep"]) not in done]
    print(f"{len(done)} conversations already evaluated, {len(todo)} to go ({a.workers} workers)")
    lock = threading.Lock()
    n_err = 0

    def run_and_save(r):
        nonlocal n_err
        res = run_row(r)
        with lock:
            if any(k.endswith("_error") for k in res):
                n_err += 1
            else:
                with partial.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(res, ensure_ascii=False) + "\n")
                done[(res["qid"], res["condition"], res["rep"])] = res
        return res

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(run_and_save, todo))
    results = [done[(r["qid"], r["condition"], r["rep"])] for r in rows if (r["qid"], r["condition"], r["rep"]) in done]
    out = src.parent / f"{stem}.foundry_eval.jsonl"
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n", encoding="utf-8")
    print(f"Wrote {out}: {len(results)}/{len(rows)} conversations evaluated"
          + (f"; {n_err} had evaluator errors: re-run the same command" if n_err else ""))

    if a.upload:
        upload(rows, evals, stem, a.upload_limit)


def upload(rows, evals, stem, limit=None):
    """Logs one evaluation run per (scenario, condition) to the Foundry portal (Evaluations, then compare runs).
    Each run uses only that scenario's evaluators (EVAL_PLAN). A local copy of every run goes to results/portal_eval/."""
    from azure.ai.evaluation import evaluate
    label = {"main": "gpt-5-mini", "main_gpt41mini": "gpt-4.1-mini"}.get(stem, stem)
    outdir = Path("results/portal_eval")
    outdir.mkdir(parents=True, exist_ok=True)
    links = []
    for scen in ("mistake1", "mistake2", "mistake3", "control"):
        names = [n for n in EVAL_PLAN[scen] if n in evals]
        for cond in ("before", "after"):
            part = [r for r in rows if r["scenario"] == scen and r["condition"] == cond]
            part = part[:limit] if limit else part
            if not part:
                continue
            name = f"{'TEST ' if limit else ''}support-desk {label} {scen} {cond}"
            with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as fh:
                for r in part:
                    q, resp, defs = to_agent_messages(r)
                    fh.write(json.dumps({"qid": r["qid"], "condition": cond, "rep": r["rep"], "trace_id": r.get("trace_id"),
                                         "query": q, "response": resp, "tool_definitions": defs}) + "\n")
                path = fh.name
            print(f"Uploading '{name}' ({len(part)} conversations, evaluators: {', '.join(names)}) ...", flush=True)
            res = evaluate(data=path, evaluators={k: evals[k][0] for k in names},
                           evaluator_config={k: {"column_mapping": {"query": "${data.query}", "response": "${data.response}",
                                                                    "tool_definitions": "${data.tool_definitions}"}} for k in names},
                           azure_ai_project=PROJECT_ENDPOINT, evaluation_name=name,
                           tags={"model": label, "scenario": scen, "condition": cond, "experiment": "support-desk-v2"},
                           output_path=str(outdir / f"{'TEST_' if limit else ''}{stem}_{scen}_{cond}.json"))
            url = (res or {}).get("studio_url")
            links.append((name, len(part), url))
            print(f"  -> {url}", flush=True)
            if limit:  # test mode: a single small run is enough
                break
        if limit and links:
            break
    lines = ["# Evaluation runs uploaded to the Foundry portal\n", "| Run | Conversations | Portal link |", "|---|---|---|"]
    lines += [f"| {n} | {k} | {u or 'n/a'} |" for n, k, u in links]
    (outdir / f"{'TEST_' if limit else ''}{stem}_links.md").write_text("\n".join(lines) + "\n")
    print(f"Links: {outdir / (('TEST_' if limit else '') + stem + '_links.md')}")

if __name__ == "__main__":
    main()
