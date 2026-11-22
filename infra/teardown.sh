#!/usr/bin/env bash
# Deletes everything. Export your results first: traces in App Insights go with it.
set -euo pipefail
RG="${1:?resource group name required}"
read -r -p "Delete resource group $RG and everything in it? [y/N] " ok
[[ "$ok" == "y" ]] && az group delete -n "$RG" --yes --no-wait && echo "Deletion started."
# Foundry accounts are soft-deleted. Purge so the name can be reused:
echo "To purge: az cognitiveservices account list-deleted -o table ; az cognitiveservices account purge -g $RG -n <account> -l <location>"
