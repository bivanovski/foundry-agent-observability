"""Runs the test set N times per condition. Resumable: re-running the same
command skips (question, condition, rep) triples already in the output file.

    python -m src.run_experiment --reps 5 --out results/main.jsonl
    python -m src.run_experiment --reps 1 --limit 6 --out results/smoke.jsonl   # quick check
"""
import argparse
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from . import foundry, telemetry
from .config import AGENT_MODEL, CONDITIONS, DATA, RESULTS
from .pipeline import run_conversation


def load_testset(only=None, limit=None):
    qs = [json.loads(l) for l in (DATA / "testset.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if only:
        qs = [q for q in qs if q["id"] in only or q["scenario"] in only]
    return qs[:limit] if limit else qs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--conditions", nargs="+", default=list(CONDITIONS))
    ap.add_argument("--only", nargs="*", help="question ids or scenario names")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(RESULTS / "main.jsonl"))
    ap.add_argument("--no-telemetry", action="store_true")
    ap.add_argument("--seed", type=int, default=2027)
    a = ap.parse_args()

    telemetry.setup(enable=not a.no_telemetry)
    state = foundry.load_state()
    qs = load_testset(a.only, a.limit)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for l in out.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                if not r.get("error"):
                    done.add((r["qid"], r["condition"], r["rep"]))

    jobs = [(q, c, r) for r in range(1, a.reps + 1) for c in a.conditions for q in qs
            if (q["id"], c, r) not in done]
    # Interleave conditions in random order so time-of-day effects (load, throttling) hit both equally.
    random.Random(a.seed).shuffle(jobs)
    print(f"{len(qs)} questions x {len(a.conditions)} conditions x {a.reps} reps: "
          f"{len(jobs)} to run, {len(done)} already done -> {out}")

    meta = dict(agent_model=AGENT_MODEL, agents=state.get("agents"), vector_store_id=state.get("vector_store_id"),
                started=datetime.now(timezone.utc).isoformat())
    lock = threading.Lock()
    n_err = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex, out.open("a", encoding="utf-8") as fh:
        futs = {ex.submit(run_conversation, q, c, r): (q["id"], c, r) for q, c, r in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            rec = f.result()
            rec["agent_model"] = meta["agent_model"]
            rec["agent_versions"] = {k: v.get("version") for k, v in (meta["agents"] or {}).items()}
            with lock:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
            n_err += bool(rec["error"])
            print(f"[{i}/{len(jobs)}] {rec['qid']} {rec['condition']} rep{rec['rep']} "
                  f"route={rec.get('route')} tools={rec['n_tool_calls']} fs={rec['n_file_search_calls']} "
                  f"{rec['latency_s']}s{' ERROR ' + rec['error'] if rec['error'] else ''}")
    telemetry.flush()
    print(f"Done. {n_err} errors (re-run the same command to retry them).")


if __name__ == "__main__":
    main()
