#!/usr/bin/env bash
# Chama o porteiro do Supabase com o token OIDC do GitHub (sem senha guardada).
# Uso: api.sh '{"action":"peek"}'
set -euo pipefail
TOKEN=$(curl -sS --fail -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=factor-reels" | jq -r .value)
curl -sS --retry 3 --retry-delay 5 -X POST "$FN_URL" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$1"
