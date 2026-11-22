#!/usr/bin/env bash
# Everything after the main runs, for both agent-model arms. Safe to re-run: grading and evaluation overwrite
# their own derived files only; raw run files (results/main*.jsonl) are never touched.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
ARMS=("main:gpt-5-mini" "main_gpt41mini:gpt-4.1-mini")

for arm in "${ARMS[@]}"; do
  stem=${arm%%:*}; label=${arm##*:}
  # skip steps whose output is newer than their input (re-runs do not pay for the judge or evaluators twice)
  if [ ! "results/$stem.graded.jsonl" -nt "results/$stem.jsonl" ]; then
    echo "=== $label: grade"; $PY -m src.grade "results/$stem.jsonl"
  fi
  echo "=== $label: built-in evaluators (resumable; repeats until every conversation is evaluated)"
  for pass in 1 2 3 4; do
    $PY -m src.evaluate_foundry "results/$stem.graded.jsonl" --workers 12 2>&1 | grep -v -i "experimental class" \
      | tee "results/$stem.eval.log" | tail -1
    grep -q "evaluator errors" "results/$stem.eval.log" || break
  done
  echo "=== $label: judge v3 (post hoc, resumable)"
  for pass in 1 2 3; do
    $PY -m src.judge_v3 "results/$stem.graded.jsonl" | tee "results/$stem.judge3.log"
    grep -q "without a verdict" "results/$stem.judge3.log" || break
  done
  echo "=== $label: span export"
  $PY -m src.export_spans "results/$stem.graded.jsonl"
  out=results/paper/prereg; [ "$stem" = main ] || out="results/paper/prereg_$label"
  echo "=== $label: pre-registered analysis -> $out"
  $PY -m src.analyze_prereg "results/$stem.graded.jsonl" --trace-check "results/$stem.trace_check.csv" \
      --foundry "results/$stem.foundry_eval.jsonl" --judge3 "results/$stem.judge3.jsonl" --out "$out" > /dev/null
done

echo "=== primary arm: legacy tables and figures"
$PY -m src.analyze results/main.graded.jsonl --foundry results/main.foundry_eval.jsonl > /dev/null
echo "=== human audit sheets (primary arm) and second judge on the audited answers"
[ -f results/audit/audit_key.csv ] || $PY -m src.audit build results/main.graded.jsonl
[ results/main.judge2.jsonl -nt results/audit/audit_key.csv ] || $PY -m src.second_judge results/main.graded.jsonl --keys results/audit/audit_key.csv
echo "=== model comparison"
$PY -m src.compare_models gpt-5-mini=results/main.graded.jsonl gpt-4.1-mini=results/main_gpt41mini.graded.jsonl > /dev/null
echo "=== Fig. 3 trace assertions as KQL in Application Insights"
$PY -m src.kql_assertions gpt-5-mini=results/main.graded.jsonl gpt-4.1-mini=results/main_gpt41mini.graded.jsonl > /dev/null
echo "=== data package"
$PY scripts/build_data_package.py
