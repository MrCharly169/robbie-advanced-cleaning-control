#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE="${HA_E2E_IMAGE:-ghcr.io/home-assistant/home-assistant:2026.8.1}"
PORT="${HA_E2E_PORT:-18123}"
CONTAINER="racc-e2e-${GITHUB_RUN_ID:-local}-$$"
CONFIG="$(mktemp -d)"
STATE="$CONFIG/runner-state.json"
ARTIFACTS="${HA_E2E_ARTIFACT_DIR:-$ROOT/artifacts/ha-e2e}"

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  if ! rm -rf "$CONFIG" 2>/dev/null; then
    sudo rm -rf "$CONFIG" 2>/dev/null || true
  fi
}
trap cleanup EXIT

cp "$ROOT/e2e/ha/configuration.yaml" "$CONFIG/configuration.yaml"
cp "$ROOT/e2e/ha/ui-lovelace.yaml" "$CONFIG/ui-lovelace.yaml"
mkdir -p "$CONFIG/custom_components"
cp -R "$ROOT/custom_components/robbie_advanced_cc" "$CONFIG/custom_components/"
cp -R "$ROOT/e2e/ha/fixture/custom_components/robbie_advanced_cc_test_fixture" \
  "$CONFIG/custom_components/"
mkdir -p "$ARTIFACTS"

docker run -d --name "$CONTAINER" \
  -p "127.0.0.1:$PORT:8123" \
  -v "$CONFIG:/config" \
  "$IMAGE" >/dev/null

python3 "$ROOT/scripts/ha_e2e/run_scenarios.py" \
  --base-url "http://127.0.0.1:$PORT" \
  --phase bootstrap \
  --state-file "$STATE" \
  --output-dir "$ARTIFACTS"

node "$ROOT/scripts/ha_e2e/configure_dashboard.mjs" \
  --base-url "http://127.0.0.1:$PORT" \
  --state-file "$STATE" \
  --card-mode advanced \
  --check-onboarding true

python3 "$ROOT/scripts/ha_e2e/wait_for_config_entry.py" \
  --storage "$CONFIG/.storage/core.config_entries" \
  --entity-registry "$CONFIG/.storage/core.entity_registry" \
  --vacuum vacuum.valetudo_fixture_robot \
  --vacuum vacuum.cloud_fixture_robot \
  --state "$STATE" \
  --wait-seconds 60

docker restart "$CONTAINER" >/dev/null

python3 "$ROOT/scripts/ha_e2e/run_scenarios.py" \
  --base-url "http://127.0.0.1:$PORT" \
  --phase restart \
  --state-file "$STATE" \
  --output-dir "$ARTIFACTS"

LOGS="$(docker logs "$CONTAINER" 2>&1)"
printf '%s\n' "$LOGS"
if grep -Eiq "Setup failed for custom integration 'robbie_advanced_cc'|Error setting up entry .*robbie_advanced_cc|Failed to load services.yaml for integration: robbie_advanced_cc|Unable to install package" <<<"$LOGS"; then
  exit 1
fi
