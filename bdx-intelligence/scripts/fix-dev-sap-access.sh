#!/usr/bin/env bash
# fix-dev-sap-access.sh — Collector-Refresh auf dem DEV-Host (192.168.82.33).
#
# Der SQL-Login-Reset braucht Windows-Sysadmin auf LDSAP → siehe
# scripts/Fix-DevSapAccess.ps1 (empfohlen). Dieses Bash-Skript läuft ON dem
# Docker-Host und macht nur diagnose + collect --once (optional --full).
#
#   cd /home/docadm/bdx-intelligence
#   bash /path/to/fix-dev-sap-access.sh
#   bash /path/to/fix-dev-sap-access.sh --full
#
set -euo pipefail

DEPLOY_PATH="${DEPLOY_PATH:-/home/docadm/bdx-intelligence}"
FULL=0
for arg in "$@"; do
  case "$arg" in
    --full) FULL=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg" >&2
      exit 2
      ;;
  esac
done

cd "$DEPLOY_PATH"
if [[ ! -f docker-compose.yml || ! -f .env ]]; then
  echo "Expected docker-compose.yml + .env in $DEPLOY_PATH" >&2
  exit 1
fi

echo "==> diagnose"
docker compose --env-file .env exec -T collector bdx-collect diagnose

if [[ "$FULL" -eq 1 ]]; then
  echo "==> collect --once --full"
  docker compose --env-file .env exec -T collector bdx-collect collect --once --full
else
  echo "==> collect --once"
  docker compose --env-file .env exec -T collector bdx-collect collect --once
fi

echo "OK  Check Dashboard: http://192.168.82.33:8085/dashboard"
