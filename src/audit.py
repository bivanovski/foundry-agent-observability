"""Human audit of 40 judge verdicts (smoke review plan, step 10).

Step 1, build the sheets (stratified: 10 per scenario, 5 before + 5 after, judge "incorrect" verdicts first):
    python -m src.audit build results/main.graded.jsonl
  -> results/audit/audit_sheet_author_A.csv, audit_sheet_author_B.csv   (blinded: no condition, no verdicts, shuffled)
     results/audit/audit_key.csv                                          (do NOT send to the labellers)

Each author fills `label` with correct / incorrect in their own sheet, independently.

Step 2, after both sheets are filled:
    python -m src.audit score results/main.graded.jsonl [--judge2 results/main.judge2.jsonl] [--judge3 results/main.judge3.jsonl] [--foundry results/main.foundry_eval.jsonl]
  -> results/audit/adjudication.csv  (disagreements; fill `adjudicated` and re-run score)
     results/audit/audit_results.md  (Cohen's kappa, each grader vs the adjudicated label)
"""
import argparse
import json
import random
from pathlib import Path

import pandas as pd

from .grade import load_testset

OUT = Path("results/audit")
SCEN = ["mistake1", "mistake2", "mistake3", "control"]


def build(graded: Path, seed: int = 2027):
    df = pd.read_json(graded, lines=True)
    df = df[df.error.isna() & df.answer_correct.notna()]
    rng = random.Random(seed)
    picks = []
    for s in SCEN:
        for c in ("before", "after"):
            pool = df[(df.scenario == s) & (df.condition == c)]
            idx = list(pool.index)
            rng.shuffle(idx)
            # judge "incorrect" verdicts first (as many as available), then the rest, 5 per cell
            inc = [i for i in idx if not pool.loc[i, "answer_correct"]]
            cor = [i for i in idx if pool.loc[i, "answer_correct"]]
            picks += (inc + cor)[:5]
    s = df.loc[picks].copy()
    tq = load_testset()
    s["item"] = [f"A{n:02d}" for n in range(1, len(s) + 1)]
    s["expected_behavior"] = s.qid.map(lambda q: tq[q]["expected_behavior"])
    s["expected_facts"] = s.qid.map(lambda q: "; ".join(tq[q]["expected_facts"]))
    OUT.mkdir(parents=True, exist_ok=True)
    s[["item", "qid", "condition", "rep", "scenario", "trace_id", "answer_correct", "judge_reason"]].to_csv(
        OUT / "audit_key.csv", index=False)
    blind = s[["item", "message", "expected_behavior", "expected_facts", "answer"]].sample(frac=1, random_state=seed)
    for who in ("A", "B"):
        blind.assign(label="", note="").to_csv(OUT / f"audit_sheet_author_{who}.csv", index=False)
    (OUT / "INSTRUCTIONS.md").write_text(
        "# Judge audit: instructions for the two labellers\n\n"
        "Each of you gets your own sheet (`audit_sheet_author_A.csv` / `_B.csv`). Work independently; do not discuss items "
        "until both sheets are done. Do not open `audit_key.csv`: it contains the condition and the judge's verdict.\n\n"
        "For every row, read the customer message, the expected behaviour and facts, and the answer. Write `correct` or "
        "`incorrect` in `label`. An answer is correct only if it does what the expected behaviour says and does not "
        "contradict the facts or the policy documents (`data/policies/`). Extra detail is fine if it is in the policy documents; "
        "invented rules, numbers, order statuses or promises are not. Use `note` for anything unclear.\n")
    print(f"Wrote {len(s)} items: {OUT}/audit_sheet_author_A.csv, _B.csv, audit_key.csv, INSTRUCTIONS.md")
    print(s.groupby(["scenario", "condition"]).answer_correct.agg(["count", lambda x: int((~x.astype(bool)).sum())])
          .rename(columns={"<lambda_0>": "judge_incorrect"}).to_string())


def kappa(a, b):
    a, b = list(a), list(b)
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(k) / n) * (b.count(k) / n) for k in set(a) | set(b))
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def stats(pred, truth):
    """pred/truth: booleans meaning 'correct'. Positive class = 'incorrect'."""
    tp = sum((not p) and (not t) for p, t in zip(pred, truth))
    fp = sum((not p) and t for p, t in zip(pred, truth))
    fn = sum(p and (not t) for p, t in zip(pred, truth))
    acc = sum(p == t for p, t in zip(pred, truth)) / len(truth)
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    return acc, prec, rec, kappa(pred, truth)


def score(graded: Path, judge2: str | None, foundry: str | None, judge3: str | None = None):
    key = pd.read_csv(OUT / "audit_key.csv")
    lab = {}
    for who in ("A", "B"):
        sh = pd.read_csv(OUT / f"audit_sheet_author_{who}.csv")
        sh["label"] = sh["label"].astype(str).str.strip().str.lower()
        if not sh["label"].isin(["correct", "incorrect"]).all():
            raise SystemExit(f"Author {who}: every row needs `correct` or `incorrect` in `label`.")
        lab[who] = dict(zip(sh["item"], sh["label"] == "correct"))
    key["author_A"] = key.item.map(lab["A"])
    key["author_B"] = key.item.map(lab["B"])
    adj_path = OUT / "adjudication.csv"
    dis = key[key.author_A != key.author_B]
    if adj_path.exists():
        adj = pd.read_csv(adj_path)
        adj = dict(zip(adj["item"], adj["adjudicated"].astype(str).str.strip().str.lower()))
    else:
        adj = {}
    missing = [i for i in dis.item if adj.get(i) not in ("correct", "incorrect")]
    if missing:
        dis.assign(adjudicated=dis.item.map(lambda i: adj.get(i, "")))[
            ["item", "qid", "author_A", "author_B", "adjudicated"]].to_csv(adj_path, index=False)
        print(f"{len(dis)} disagreements. Fill `adjudicated` (correct / incorrect) in {adj_path}, then re-run score.")
    key["adjudicated"] = [a if a == b else (adj.get(i) == "correct" if adj.get(i) in ("correct", "incorrect") else None)
                          for i, a, b in zip(key.item, key.author_A, key.author_B)]
    lines = ["# Judge audit results\n", f"Items: {len(key)}. Cohen's kappa between the two authors: "
             f"{kappa(key.author_A, key.author_B):.2f} (raw agreement {100*(key.author_A == key.author_B).mean():.1f}%).\n"]
    done = key[key.adjudicated.notna()].copy()
    if len(done) < len(key):
        lines.append(f"Adjudication incomplete: {len(key) - len(done)} items open. Grader comparison uses {len(done)} items.\n")
    graders = {"LLM judge v2 (gpt-5-mini)": done.answer_correct.astype(bool)}
    if judge2 and Path(judge2).exists():
        j2 = pd.read_json(judge2, lines=True)
        done = done.merge(j2[["qid", "condition", "rep", "answer_correct_judge2"]], on=["qid", "condition", "rep"], how="left")
        graders["Second judge (gpt-4.1-mini)"] = done.answer_correct_judge2
    if judge3 and Path(judge3).exists():
        j3 = pd.read_json(judge3, lines=True)
        done = done.merge(j3[["qid", "condition", "rep", "answer_correct_v3"]], on=["qid", "condition", "rep"], how="left")
        graders["LLM judge v3, post hoc (gpt-5-mini)"] = done.answer_correct_v3
    if foundry and Path(foundry).exists():
        fe = pd.read_json(foundry, lines=True)
        for col in [c for c in fe.columns if c.endswith("_pass")]:
            d = done.merge(fe[["qid", "condition", "rep", col]], on=["qid", "condition", "rep"], how="left")
            graders[f"Built-in: {col.removesuffix('_pass')}"] = d[col]
    lines += ["| Grader vs adjudicated human label | n | Accuracy | Precision (incorrect) | Recall (incorrect) | Cohen's kappa |",
              "|---|---|---|---|---|---|"]
    for name, pred in graders.items():
        ok = pred.notna().values & done.adjudicated.notna().values
        if ok.sum() == 0:
            continue
        p = [bool(x) for x in pred[ok]]
        t = [bool(x) for x in done.adjudicated[ok]]
        acc, prec, rec, k = stats(p, t)
        lines.append(f"| {name} | {ok.sum()} | {100*acc:.1f}% | {100*prec:.1f}% | {100*rec:.1f}% | {k:.2f} |")
    key.to_csv(OUT / "audit_labels_joined.csv", index=False)
    (OUT / "audit_results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "score"])
    ap.add_argument("graded")
    ap.add_argument("--judge2")
    ap.add_argument("--foundry")
    ap.add_argument("--judge3")
    a = ap.parse_args()
    if a.cmd == "build":
        build(Path(a.graded))
    else:
        score(Path(a.graded), a.judge2, a.foundry, a.judge3)


if __name__ == "__main__":
    main()
