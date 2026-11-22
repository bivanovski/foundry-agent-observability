"""Post-hoc positive controls for the F1 and F2 detectors (CHANGELOG 2026-11-21, approved by Bojan).

F1 and F2 never occurred in the main runs, so the omission query, the provenance check and the evaluators that should
catch them were never tested on a true positive. This script forces both faults on gpt-5-mini with the `before`
instructions, reusing src/pipeline.run_conversation unchanged except for two substitutions:

  F1-forced  P01-P12 x 3 reps  the policy agent is a copy of policy-agent-before WITHOUT File Search
             (policy-agent-before-nofs). tool_choice="none" on the agent request was tried first: Foundry accepted
             it but still ran File Search, so the agent-copy variant is used.
  F2-forced  O01-O08 x 3 reps  the handoff is the triage summary with every digit run of 4+ digits replaced by
             "[number]", without the customer's original message.

    python -m src.positive_controls            -> results/paper/v3_checks/positive_controls.jsonl (resumable)
"""
import argparse
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config, foundry, pipeline, telemetry

OUT = Path("results/paper/v3_checks/positive_controls.jsonl")
NOFS = "policy-agent-before-nofs"
F1_ITEMS = [f"P{i:02d}" for i in range(1, 13)]
F2_ITEMS = [f"O{i:02d}" for i in range(1, 9)]


def ensure_nofs_agent():
    """Creates (once) the copy of the before policy agent without File Search, same model and instructions."""
    state = Path(".state.positive_controls.json")
    if state.exists():
        return json.loads(state.read_text())
    a = foundry.create_prompt_agent(NOFS, config.AGENT_MODEL, config.POLICY_INSTRUCTIONS["before"], tools=[])
    info = {"name": a.name, "version": getattr(a, "version", None), "model": config.AGENT_MODEL,
            "instructions": config.POLICY_INSTRUCTIONS["before"], "tools": []}
    state.write_text(json.dumps(info, indent=2))
    return info


def masked_handoff(condition, summary, original):
    return "Handoff from the triage agent: " + re.sub(r"\d{4,}", "[number]", summary or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if config.AGENT_TAG:
        raise SystemExit("Run the positive controls on the primary arm only (AGENT_TAG must be unset).")
    telemetry.setup()
    nofs = ensure_nofs_agent()
    tq = {q["id"]: q for q in map(json.loads, (config.DATA / "testset.jsonl").read_text().splitlines()) if q}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if OUT.exists():
        for l in OUT.read_text().splitlines():
            r = json.loads(l)
            if not r.get("error"):
                done.add((r["variant"], r["qid"], r["rep"]))
    lock = threading.Lock()
    orig_agent_name, orig_handoff = pipeline.agent_name, pipeline.handoff_message

    def f1_agent_name(role, condition=None):
        return NOFS if (role == "policy" and condition == "before") else orig_agent_name(role, condition)

    for variant, items in (("F1-forced", F1_ITEMS), ("F2-forced", F2_ITEMS)):
        # one variant at a time, so the module-level substitution is the same for every worker thread
        pipeline.agent_name = f1_agent_name if variant == "F1-forced" else orig_agent_name
        pipeline.handoff_message = masked_handoff if variant == "F2-forced" else orig_handoff
        jobs = [(tq[q], r) for r in range(1, a.reps + 1) for q in items if (variant, q, r) not in done]
        print(f"{variant}: {len(jobs)} conversations to run", flush=True)

        def one(job):
            q, rep = job
            rec = pipeline.run_conversation(q, "before", rep)
            rec.update(variant=variant, agent_model=config.AGENT_MODEL,
                       forced_agent=NOFS if variant == "F1-forced" else None, nofs_agent_version=nofs.get("version"))
            with lock, OUT.open("a") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"  {variant} {rec['qid']} rep{rep} route={rec.get('route')} specialist={rec.get('specialist')} "
                  f"tools={rec['n_tool_calls']} fs={rec['n_file_search_calls']} {rec['latency_s']}s"
                  f"{' ERROR ' + rec['error'] if rec['error'] else ''}", flush=True)

        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            list(ex.map(one, jobs))
    pipeline.agent_name, pipeline.handoff_message = orig_agent_name, orig_handoff
    telemetry.flush()
    print("Done.")


if __name__ == "__main__":
    main()
