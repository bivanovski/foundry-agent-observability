#!/usr/bin/env bash
# Deploys the Foundry environment and writes ../.env
# Usage: ./infra/deploy.sh <resource-group> [location] [baseName]
set -euo pipefail

RG="${1:?resource group name required}"
LOCATION="${2:-swedencentral}"
BASE="${3:-agentobs}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"

az account show >/dev/null 2>&1 || az login
echo "Subscription: $(az account show --query name -o tsv)"

USER_ID="$(az ad signed-in-user show --query id -o tsv)"

az group create -n "$RG" -l "$LOCATION" -o none
echo "Deploying (5-10 minutes)..."
OUT="$(az deployment group create -g "$RG" -n support-desk \
  --template-file "$HERE/main.bicep" \
  --parameters baseName="$BASE" location="$LOCATION" userPrincipalId="$USER_ID" \
  --query properties.outputs -o json)"

get() { echo "$OUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['$1']['value'])"; }

cat > "$ROOT/.env" <<EOF
RESOURCE_GROUP=$RG
PROJECT_ENDPOINT=$(get projectEndpoint)
AZURE_OPENAI_ENDPOINT=$(get openAiEndpoint)
AGENT_MODEL_DEPLOYMENT=$(get agentDeployment)
JUDGE_MODEL_DEPLOYMENT=$(get judgeDeployment)
APPINSIGHTS_NAME=$(get appInsightsName)
AZURE_OPENAI_API_VERSION=2025-04-01-preview
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
EOF

echo "Done. Wrote $ROOT/.env"
echo "Role assignments can take up to 10 minutes to apply. If the next step returns 401/403, wait and retry."
