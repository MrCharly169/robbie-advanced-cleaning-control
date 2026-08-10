#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE="${HA_E2E_IMAGE:-ghcr.io/home-assistant/home-assistant:stable}"
CONTAINER="racc-e2e-${GITHUB_RUN_ID:-local}-$$"
CONFIG="$(mktemp -d)"

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  rm -rf "$CONFIG"
}
trap cleanup EXIT

cp "$ROOT/e2e/ha/configuration.yaml" "$CONFIG/configuration.yaml"
mkdir -p "$CONFIG/custom_components"
cp -R "$ROOT/custom_components/robbie_advanced_cc" "$CONFIG/custom_components/"

docker run -d --name "$CONTAINER" \
  -v "$CONFIG:/config" \
  "$IMAGE" >/dev/null

for _ in $(seq 1 90); do
  if docker logs "$CONTAINER" 2>&1 | grep -q "Home Assistant initialized"; then
    break
  fi
  if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q true; then
    docker logs "$CONTAINER"
    exit 1
  fi
  sleep 2
done

LOGS="$(docker logs "$CONTAINER" 2>&1)"
printf '%s\n' "$LOGS"
if grep -Eiq "Setup failed for custom integration 'robbie_advanced_cc'|Error setting up entry .*robbie_advanced_cc|Unable to install package" <<<"$LOGS"; then
  exit 1
fi
grep -q "Home Assistant initialized" <<<"$LOGS"
