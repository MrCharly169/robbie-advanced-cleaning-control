# Skip the current cleaning occurrence

Development acceptance: 22 September 2026. Project-local change; no public
release or production installation is claimed.

## Behavior

The existing `skip_next` action selects the active physical run first, then
the oldest pending occurrence, then the next scheduled mission. Waiting
occurrences are removed from persistent pending state. Future repetitions stay
configured. Active runs receive the adapter's native `vacuum.return_to_base`
command and stay tracked until that same robot reports `docked`. They finish
as `skipped` without a cleaning-success notification. Repeated Skip while
returning is idempotent. Failed return commands preserve the identity for retry;
device errors remain visible.

Start and Skip share an async lock; presence retries recheck queue membership
under it. Consuming a future skip also removes legacy pending state. Returning
cancellations survive HA restart without replaying device commands. Normal
resumable mop docking retains its completion grace and notification behavior.
The change reuses native adapter, service, storage and timer APIs; no new
device-control wrapper or scheduler was introduced. Existing customer-language
work in the working tree was preserved.

## Evidence

- HA 2026.9.3 image: 62 Python tests passed, including 13 controller tests with
  controlled adapters/events for waiting/active/external runs, concurrent
  start/skip, stale presence callbacks, failed commands, future repetition,
  resumable docking and restoration of cancellation state.
- Disposable HA HTTP lab: bootstrap passed in 56.19 seconds; restart passed.
  Added real service scenarios cover waiting -> Skip -> home becomes empty
  without starting, a subsequent run, repeated Skip during cleaning, one return
  command and skipped completion without a success notification.
- Card runtime and Chromium regression passed. German skipped text was rendered
  at 390 px and English at 1280 px. Browser fixtures use simulated HA elements;
  screenshots do not establish production frontend or hardware parity.
- Source syntax, package structure, whitespace and ecosystem audit passed.
  Policy 1.19.1: eight registered projects, no findings.

Reproduce the lab with:

```sh
HA_E2E_ENGINE=podman HA_E2E_IMAGE=ghcr.io/home-assistant/home-assistant:2026.9.3 bash scripts/ha_e2e/run_lab.sh
```

The engine defaults to Docker for existing CI. Controller tests run inside the
selected HA image; a host without HA skips this module. The existing smoke
workflow includes the new test path. Lab containers, configuration and test
identities were cleaned up by the existing trap. No production credentials,
backups or sessions were used.

## Documentation and recurring tasks

English/German integration guides and the unreleased changelog were updated.
The existing `robbie-advanced` Master Documentation entry was reviewed in all
five languages. Its generic skip guidance remains unchanged until installation
and live verification; development tests must not become an installed-capability
claim. At promotion, extend that same entry with current-run cancellation and
the actual physical acceptance outcome.

Local Codex automation configurations and repository CI were checked. The
existing “MeyersHaff Master Doc & News Review” already requires maintaining this
entry in five languages; no prompt or schedule change is needed for local
development. Only repository smoke tests and their runner were extended. No
new task, frequency, notification or activation change was made. ChatGPT cloud
tasks and production HA automations/timers were not inspected or modified.

## Installation boundary

No production installation or publication was performed. Before installation,
audit all pending work in the selected release, verify actual production
versions/configuration and backup authority, and apply the exact-version local
frontend gate. Physical return-to-dock and non-resumption need controlled live
acceptance; simulated robots cannot prove either. Local changes remain
reviewable. Production requires no rollback; no rights or secret destinations
were added.

## Release preparation: 2026.9.2b0

The release tree includes all published 2026.9.1b0 app-language fixes and
policy 1.19.1. The older local checkout was reconciled against current develop;
no published failure-localization or unknown-reason protection is removed.
The return phase now has explicit English/German copy instead of Unknown.

A native HA 2026.9.3 frontend lab additionally passed at 390/1280 px, including
real Card clicks, waiting, skipped, running, returning and the control menu,
with zero browser errors. The lab uses its own native storage dashboard because
modern HA redirects the old Overview path to Home. Test hardware remains
simulated. Enable this check with HA_E2E_BROWSER=1 and a Playwright-capable Node
executable in HA_E2E_BROWSER_NODE. Production installation is recorded separately
in the owning HA workspace's versioned installation receipt.
