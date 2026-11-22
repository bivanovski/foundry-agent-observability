#!/usr/bin/env bash
# Live, read-only view of the post-run pipeline. Stop with Ctrl-C (this does not stop the pipeline).
cd "$(dirname "$0")/.."
while true; do
  clear
  echo "Support desk experiment: post-run pipeline        $(date '+%H:%M:%S')"
  echo "Folder: $(pwd)"
  echo
  echo "Processes on this Mac (they call the Azure judge deployment gpt-5-mini-judge in rg-agentobs, Sweden Central):"
  ps -eo pid,etime,command | grep -E "after_runs|src\.(evaluate_foundry|grade|export_spans|analyze|audit|second_judge|compare_models)|build_data_package" \
    | grep -v grep | sed -E 's#/opt/homebrew/.*/MacOS/Python#python#; s#^ *##' | cut -c1-110 | sed 's/^/  /'
  echo
  echo "Built-in evaluators (conversations saved):"
  for arm in "main:gpt-5-mini" "main_gpt41mini:gpt-4.1-mini"; do
    stem=${arm%%:*}; label=${arm##*:}
    f="results/$stem.foundry_eval.partial.jsonl"
    n=0; [ -f "$f" ] && n=$(grep -c . "$f")
    bar=$(printf '%*s' $((n / 10)) '' | tr ' ' '#')
    printf "  %-13s %3d/400  %s\n" "$label" "$n" "$bar"
  done
  echo
  echo "Judge v3, post hoc (answers judged):"
  for arm in "main:gpt-5-mini" "main_gpt41mini:gpt-4.1-mini"; do
    stem=${arm%%:*}; label=${arm##*:}
    f="results/$stem.judge3_cache.jsonl"
    n=0; [ -f "$f" ] && n=$(grep -c . "$f")
    bar=$(printf '%*s' $((n / 10)) '' | tr ' ' '#')
    printf "  %-13s %3d/400  %s\n" "$label" "$n" "$bar"
  done
  echo
  echo "Pipeline log (results/after_runs.log):"
  tail -8 results/after_runs.log 2>/dev/null | sed 's/^/  /'
  if ! pgrep -f "scripts/after_runs.sh" >/dev/null; then echo; echo "Pipeline is not running (finished or stopped)."; fi
  sleep 10
done
