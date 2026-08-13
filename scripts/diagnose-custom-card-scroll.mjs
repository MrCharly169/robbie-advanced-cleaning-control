import assert from "node:assert/strict";
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require("playwright"));
} catch (_error) {
  const bundled = path.join(
    process.env.USERPROFILE || "",
    ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright",
  );
  ({ chromium } = require(bundled));
}

const sourcePath = path.resolve(
  "custom_components/robbie_advanced_cc/frontend/cleaning-control.js",
);
const browserPath = [
  process.env.ROBBIE_BROWSER_PATH,
  chromium.executablePath(),
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "/usr/bin/chromium",
  "/usr/bin/google-chrome",
].find((candidate) => candidate && fs.existsSync(candidate));
if (!browserPath) throw new Error("No Chromium browser found; set ROBBIE_BROWSER_PATH");
const browser = await chromium.launch({
  headless: true,
  executablePath: browserPath,
});
const page = await browser.newPage({ viewport: { width: 700, height: 500 } });
const consoleErrors = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => consoleErrors.push(error.message));

try {
  await page.setContent(`<!doctype html><style>
    #dashboard{height:260px;overflow:auto}#before,#after{height:420px}
    .mission-list{max-height:90px;overflow:auto}
  </style><div id="dashboard"><div id="before"></div><div id="card"></div><div id="badge"></div><div id="after"></div></div>`);
  await page.addScriptTag({ path: sourcePath });
  const result = await page.evaluate(async () => {
    const waitFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const mission = {
      id: "monday", name: "Monday kitchen", vacuum_entity_id: "vacuum.robot",
      weekdays: ["mon"], start_time: "09:00", areas: ["kitchen"], enabled: true,
      profile: { mode: "vacuum", fan: "low", passes: 1 },
      guards: { people_home: "wait" }, next_run: "2026-08-17T09:00:00+02:00",
      all_conditions_met: true,
      conditions: [{ key: "vacuum_available", enabled: true, passed: true }],
    };
    const status = (state = "idle", extra = {}) => ({
      state,
      attributes: {
        entry_id: "entry-1", managed_vacuums: ["vacuum.robot"], missions: [mission],
        waiting_vacuums: [],
        next_runs: { "vacuum.robot": { mission: mission.name, scheduled: mission.next_run } },
        maintenance: { brush: 90 },
        profile_options: {
          "vacuum.robot": {
            areas: [{ value: "kitchen", label: "Kitchen" }],
            modes: [{ value: "vacuum", label: "Vacuum" }],
            fan_speeds: [{ value: "low", label: "Low" }], water_levels: [],
            passes: [{ value: "1", label: "1" }],
            current: { mode: "vacuum", fan: "low", passes: "1" },
          },
        },
        ...extra,
      },
    });
    const makeHass = (planner = status(), vacuumState = "docked") => ({
      language: "en",
      states: {
        "sensor.planner_status": planner,
        "sensor.next_mission": {
          state: mission.next_run,
          attributes: { entry_id: "entry-1", mission: mission.name, mission_id: mission.id, vacuum_entity_id: "vacuum.robot" },
        },
        "vacuum.robot": { state: vacuumState, attributes: { friendly_name: "Robbie" } },
      },
    });

    const card = document.createElement("robbie-advanced-cleaning-card");
    card.setConfig({ status_entity: "sensor.planner_status", mode: "simple" });
    document.querySelector("#card").append(card);
    card.hass = makeHass();
    await waitFrame();
    const firstRoot = card.shadowRoot.querySelector("ha-card");
    card.shadowRoot.querySelector("[data-mode-toggle]").click();
    const advancedRoot = card.shadowRoot.querySelector("ha-card");
    // Safari/HA Mobile can lose a delegated click while retargeting nested
    // Shadow DOM. Disable delegation here so this assertion exercises the
    // direct listener attached to the stable button itself.
    card._handleClick = () => {};
    const bottomAdd = card.shadowRoot.querySelector('[data-add-position="bottom"]');
    bottomAdd.click();
    const addRunOpened = card._editingMissionId === "new"
      && card._editingPlacement === "bottom"
      && Boolean(card.shadowRoot.querySelector('form[data-mission-form][data-id=""]'));
    card.shadowRoot.querySelector("[data-cancel]").click();
    card.shadowRoot.querySelector(`[data-edit="${mission.id}"]`).click();

    const dashboard = document.querySelector("#dashboard");
    dashboard.scrollTop = 430;
    const form = card.shadowRoot.querySelector("form[data-mission-form]");
    const input = form.querySelector('[name="name"]');
    input.focus();
    input.value = "Unsaved customer input";
    const missionList = card.shadowRoot.querySelector(".mission-list");
    missionList.scrollTop = 17;
    const before = {
      dashboard: dashboard.scrollTop,
      list: missionList.scrollTop,
      renders: card._visibleRenderCount,
    };

    card.hass = makeHass(status("waiting"));
    card.hass = makeHass(status("running", { maintenance: { brush: 80 } }));
    const updatedMission = {
      ...mission, name: "Monday kitchen updated", all_conditions_met: false,
      conditions: [{ key: "vacuum_available", enabled: true, passed: false }],
    };
    card.hass = makeHass(status("waiting", {
      waiting_vacuums: ["vacuum.robot"], missions: [updatedMission],
    }));
    await waitFrame();
    const afterBurst = {
      oneRender: card._visibleRenderCount - before.renders === 1,
      dashboardStable: dashboard.scrollTop === before.dashboard,
      rootStable: card.shadowRoot.querySelector("ha-card") === firstRoot,
      advancedRootStable: advancedRoot === firstRoot,
      formStable: card.shadowRoot.querySelector("form[data-mission-form]") === form,
      focusStable: card.shadowRoot.activeElement === input,
      inputStable: input.value === "Unsaved customer input",
      selectionStable: card._editingMissionId === mission.id,
      listStable: card.shadowRoot.querySelector(".mission-list") === missionList
        && missionList.scrollTop === before.list,
      missionUpdated: missionList.textContent.includes("Monday kitchen updated"),
    };

    const invisibleBefore = card._visibleRenderCount;
    card.hass = makeHass(status("waiting", {
      maintenance: { brush: 10 }, waiting_vacuums: [],
      next_runs: { "vacuum.robot": { mission: "Hidden change", scheduled: "2026-08-17T10:00:00+02:00" } },
      missions: [updatedMission],
    }));
    await waitFrame();
    const narrowSignature = card._visibleRenderCount === invisibleBefore;

    const badge = document.createElement("robbie-vacuum-badge");
    badge.setConfig({ vacuum_entity: "vacuum.robot", status_entity: "sensor.planner_status" });
    document.querySelector("#badge").append(badge);
    badge.hass = makeHass();
    await waitFrame();
    const badgeRoot = badge.shadowRoot.querySelector("ha-badge");
    const badgeRenders = badge._visibleRenderCount;
    badge.hass = makeHass(status("idle", { waiting_vacuums: ["vacuum.robot"] }), "idle");
    badge.hass = makeHass(status("vacation", { vacation_active: true }), "cleaning");
    badge.hass = makeHass(status("idle", {
      next_runs: { "vacuum.robot": { mission: "Changed", scheduled: "2026-08-17T11:00:00+02:00" } },
    }), "error");
    await waitFrame();
    const badgeResult = {
      oneRender: badge._visibleRenderCount - badgeRenders === 1,
      rootStable: badge.shadowRoot.querySelector("ha-badge") === badgeRoot,
      finalState: badge.shadowRoot.querySelector("ha-badge").dataset.mode === "error",
      dashboardStable: dashboard.scrollTop === before.dashboard,
    };

    return { addRunOpened, afterBurst, narrowSignature, badgeResult };
  });

  assert.equal(result.addRunOpened, true);
  assert.deepEqual(result.afterBurst, {
    oneRender: true, dashboardStable: true, rootStable: true, advancedRootStable: true,
    formStable: true, focusStable: true, inputStable: true, selectionStable: true,
    listStable: true, missionUpdated: true,
  });
  assert.equal(result.narrowSignature, true);
  assert.deepEqual(result.badgeResult, {
    oneRender: true, rootStable: true, finalState: true, dashboardStable: true,
  });
  assert.deepEqual(consoleErrors, []);
  console.log(JSON.stringify({ ok: true, ...result }, null, 2));
} finally {
  await browser.close();
}
