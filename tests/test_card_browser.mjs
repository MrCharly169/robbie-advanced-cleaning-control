import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

function loadPlaywright() {
  const localRequire = createRequire(import.meta.url);
  try {
    return localRequire("playwright");
  } catch {
    try {
      return localRequire("playwright-core");
    } catch {
      // Codex' bundled runtime keeps Playwright next to the Node executable.
    }
    const bundledPackage = path.resolve(
      path.dirname(process.execPath), "..", "node_modules", "playwright", "package.json",
    );
    return createRequire(pathToFileURL(bundledPackage))("playwright");
  }
}

const { chromium } = loadPlaywright();
const executablePath = [
  process.env.ROBBIE_BROWSER_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
].find((candidate) => candidate && fs.existsSync(candidate));
const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  hasTouch: true,
  isMobile: true,
});
const page = await context.newPage();

try {
  await page.setContent(`<!doctype html><html><head><style>
    html,body{margin:0}#dashboard{height:420px;overflow:auto}#spacer{height:240px}
    robbie-advanced-cleaning-card{display:block;width:min(620px,100%);margin:0 auto 240px}
    ha-card,ha-icon{display:block}
  </style></head><body><div id="dashboard"><div id="spacer"></div></div></body></html>`);
  await page.evaluate(() => {
    for (const tag of ["ha-card", "ha-icon"]) {
      if (!customElements.get(tag)) customElements.define(tag, class extends HTMLElement {});
    }
    if (!customElements.get("ha-dialog")) customElements.define("ha-dialog", class extends HTMLElement {
      constructor() {
        super();
        this.attachShadow({ mode: "open" }).innerHTML = `<style>:host{display:contents}.overlay{position:fixed;inset:24px;z-index:10;overflow:auto}</style><div class="overlay"><slot></slot></div>`;
      }
    });
  });
  await page.addScriptTag({
    path: path.resolve("custom_components/robbie_advanced_cc/frontend/cleaning-control.js"),
  });
  await page.evaluate(() => {
    const card = document.createElement("robbie-advanced-cleaning-card");
    card.setConfig({ status_entity: "sensor.planner_status", mode: "simple" });
    const mission = {
      id: "weekday", name: "Weekday", vacuum_entity_id: "vacuum.robot",
      weekdays: ["mon"], start_time: "09:00", areas: ["kitchen"], enabled: true,
      profile: { mode: "vacuum", fan: "low", passes: 1 },
      guards: { people_home: "wait" }, all_conditions_met: false,
      conditions: [
        { key: "planner_enabled", enabled: true, passed: true },
        { key: "vacuum_available", enabled: true, passed: true },
        { key: "vacation_inactive", enabled: true, passed: false },
        { key: "mop_attached", enabled: true, passed: true },
        { key: "home_empty", enabled: true, passed: true },
      ],
    };
    const weekendMission = {
      ...mission, id: "weekend", name: "Weekend", weekdays: ["sun"],
      conditions: mission.conditions.map((condition) => ({ ...condition })),
    };
    window.__robbieServiceCalls = [];
    card.hass = {
      language: "en",
      callService: async (...args) => { window.__robbieServiceCalls.push(args); },
      states: {
        "sensor.planner_status": {
          state: "vacation",
          attributes: {
            entry_id: "entry-1", vacation_active: true,
            managed_vacuums: ["vacuum.robot"], missions: [mission, weekendMission],
            profile_options: {
              "vacuum.robot": {
                areas: [{ value: "kitchen", label: "Kitchen" }],
                modes: [{ value: "vacuum", label: "Vacuum" }],
                fan_speeds: [{ value: "low", label: "Low" }], water_levels: [],
                passes: [{ value: "1", label: "1" }],
                current: { mode: "vacuum", fan: "low", passes: "1" },
              },
            },
          },
        },
        "vacuum.robot": { state: "docked", attributes: { friendly_name: "Robbie" } },
      },
    };
    document.querySelector("#dashboard").append(card);
  });
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => resolve())));

  const initial = await page.evaluate(() => {
    const dashboard = document.querySelector("#dashboard");
    const card = document.querySelector("robbie-advanced-cleaning-card");
    dashboard.scrollTop = 180;
    const root = card.shadowRoot.querySelector("ha-card");
    return { root, height: root.getBoundingClientRect().height, scrollTop: dashboard.scrollTop };
  });

  await page.locator("robbie-advanced-cleaning-card button[data-mode-toggle]").tap();
  const controlCenter = await page.evaluate(() => {
    const dashboard = document.querySelector("#dashboard");
    const card = document.querySelector("robbie-advanced-cleaning-card");
    const root = card.shadowRoot.querySelector("[data-card-host] ha-card");
    const dialog = card.shadowRoot.querySelector("ha-dialog[data-dialog-id]");
    const shellRect = dialog.querySelector(".dialog-shell").getBoundingClientRect();
    return {
      root, height: root.getBoundingClientRect().height, scrollTop: dashboard.scrollTop,
      simple: root.dataset.cardMode, dialogOpen: Boolean(dialog?.open),
      summary: dialog.querySelector(".overview-chips").textContent.replace(/\s+/g, " ").trim(),
      text: dialog.textContent.replace(/\s+/g, " ").trim(),
      centerDelta: Math.abs(shellRect.left - (innerWidth - shellRect.right)),
      addPositions: [...dialog.querySelectorAll("button[data-add]")].map((item) => item.dataset.addPosition),
    };
  });
  assert.equal(controlCenter.root, initial.root, "the ha-card root must remain stable");
  assert.equal(controlCenter.height, initial.height, "opening Advanced must not resize the dashboard Card");
  assert.equal(controlCenter.scrollTop, initial.scrollTop, "opening Advanced must not move the dashboard");
  assert.equal(controlCenter.simple, "simple");
  assert.equal(controlCenter.dialogOpen, true);
  assert.match(controlCenter.summary, /4\/5/);
  assert.doesNotMatch(controlCenter.summary, /8\/10/);
  assert.match(controlCenter.text, /Vacation mode active/);
  assert.ok(controlCenter.centerDelta <= 1, `Advanced dialog is off-center by ${controlCenter.centerDelta}px`);
  assert.deepEqual(controlCenter.addPositions.sort(), ["bottom", "top"]);

  await page.locator('robbie-advanced-cleaning-card ha-dialog button[data-add-position="bottom"]').tap();
  const editor = await page.evaluate(() => {
    const dashboard = document.querySelector("#dashboard");
    const card = document.querySelector("robbie-advanced-cleaning-card");
    const root = card.shadowRoot.querySelector("[data-card-host] ha-card");
    const form = card.shadowRoot.querySelector("ha-dialog form[data-mission-form]");
    const name = form.querySelector('input[name="name"]');
    name.value = "Unsaved draft";
    name.focus();
    return {
      root, form, name, height: root.getBoundingClientRect().height,
      scrollTop: dashboard.scrollTop, renders: card._visibleRenderCount,
    };
  });
  assert.equal(editor.root, initial.root);
  assert.equal(editor.height, initial.height, "opening Add run must not resize the dashboard Card");
  assert.equal(editor.scrollTop, initial.scrollTop, "opening Add run must not move the dashboard");

  await page.evaluate(() => {
    const card = document.querySelector("robbie-advanced-cleaning-card");
    for (const state of ["idle", "vacation", "waiting"]) {
      card.hass = {
        ...card._hass,
        states: {
          ...card._hass.states,
          "sensor.planner_status": { ...card._hass.states["sensor.planner_status"], state },
        },
      };
    }
  });
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => resolve())));
  const afterBurst = await page.evaluate(() => {
    const dashboard = document.querySelector("#dashboard");
    const card = document.querySelector("robbie-advanced-cleaning-card");
    const form = card.shadowRoot.querySelector("ha-dialog form[data-mission-form]");
    const name = form.querySelector('input[name="name"]');
    return {
      root: card.shadowRoot.querySelector("[data-card-host] ha-card"), form, name,
      value: name.value, focused: card.shadowRoot.activeElement === name,
      scrollTop: dashboard.scrollTop, renders: card._visibleRenderCount,
    };
  });
  assert.equal(afterBurst.root, initial.root);
  assert.equal(afterBurst.form, editor.form, "the open mission form must remain stable");
  assert.equal(afterBurst.name, editor.name, "the focused input must remain stable");
  assert.equal(afterBurst.value, "Unsaved draft", "unsaved input must survive hass bursts");
  assert.equal(afterBurst.focused, true, "focus must survive hass bursts");
  assert.equal(afterBurst.scrollTop, initial.scrollTop);
  assert.equal(afterBurst.renders, editor.renders + 1, "a hass burst must render at most once per frame");

  await page.evaluate(() => {
    const card = document.querySelector("robbie-advanced-cleaning-card");
    const form = card.shadowRoot.querySelector("ha-dialog form[data-mission-form]");
    form.querySelector('input[name="name"]').value = "Saved browser run";
  });
  await page.locator('robbie-advanced-cleaning-card ha-dialog button[type="submit"]').tap();
  await page.evaluate(() => new Promise((resolve) => setTimeout(resolve, 0)));
  const afterSave = await page.evaluate(() => {
    const dashboard = document.querySelector("#dashboard");
    const card = document.querySelector("robbie-advanced-cleaning-card");
    return {
      root: card.shadowRoot.querySelector("[data-card-host] ha-card"),
      scrollTop: dashboard.scrollTop,
      dialogOpen: Boolean(card.shadowRoot.querySelector("ha-dialog[data-dialog-id]")),
      editorOpen: Boolean(card.shadowRoot.querySelector("form[data-mission-form]")),
      calls: window.__robbieServiceCalls,
    };
  });
  assert.equal(afterSave.root, initial.root, "saving a run must keep the ha-card root stable");
  assert.equal(afterSave.scrollTop, initial.scrollTop, "saving a run must not move the dashboard");
  assert.equal(afterSave.dialogOpen, true, "a successful save returns to the Advanced control center");
  assert.equal(afterSave.editorOpen, false, "a successful save must close the mission editor");
  assert.equal(afterSave.calls.length, 1, "Save run must perform exactly one service call");
  assert.equal(afterSave.calls[0][0], "robbie_advanced_cc");
  assert.equal(afterSave.calls[0][1], "add_mission");
  assert.equal(afterSave.calls[0][2].entry_id, "entry-1");
  assert.equal(afterSave.calls[0][2].mission.name, "Saved browser run");
  assert.equal(afterSave.calls[0][2].mission.vacuum_entity_id, "vacuum.robot");

  console.log("Card browser regression passed");
} finally {
  await browser.close();
}
