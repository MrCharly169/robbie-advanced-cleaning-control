const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

class Element {
  constructor() {
    this.shadowRoot = null;
    this.handlers = {};
    this.renderWrites = 0;
    this.shellWrites = 0;
    this.isConnected = true;
  }
  attachShadow() {
    const owner = this;
    let markup = "";
    const roots = new Map();
    const renderedRoot = (tag) => {
      if (!roots.has(tag)) {
        roots.set(tag, {
          tag,
          listeners: {},
          addEventListener(type, callback) {
            this.listeners[type] = callback;
            owner.handlers[`${tag}:${type}`] = callback;
          },
          style: { setProperty(name, value) { owner.lastStyle = { name, value }; } },
        });
      }
      return roots.get(tag);
    };
    const mount = (tag) => {
      let content = "";
      return {
        get innerHTML() { return content; },
        set innerHTML(value) { content = value; owner.renderWrites += 1; },
        querySelector(selector) {
          return selector.includes("ha-badge") ? renderedRoot("ha-badge") : renderedRoot("ha-card");
        },
      };
    };
    const cardMount = mount("ha-card");
    const badgeMount = mount("ha-badge");
    const dialogMount = mount("ha-dialog");
    this.shadowRoot = {
      get innerHTML() { return `${markup}${cardMount.innerHTML}${dialogMount.innerHTML}${badgeMount.innerHTML}`; },
      set innerHTML(value) { markup = value; owner.shellWrites += 1; },
      addEventListener(type, callback) { owner.handlers[`shadow:${type}`] = callback; },
      querySelector(selector) {
        if (selector === "[data-card-host]") return cardMount;
        if (selector === "[data-dialog-host]") return dialogMount;
        if (selector === "[data-badge-host]") return badgeMount;
        if (selector.includes("ha-dialog")) return renderedRoot("ha-dialog");
        if (selector === "ha-badge") return renderedRoot("ha-badge");
        return { addEventListener(type, callback) { owner.handlers[`${selector}:${type}`] = callback; } };
      },
    };
    return this.shadowRoot;
  }
  addEventListener(type, callback) { this.handlers[`host:${type}`] = callback; }
  dispatchEvent(event) { this.lastEvent = event; }
}

let nextFrame = 1;
const frameQueue = new Map();
let nextTimer = 1;
const timerQueue = new Map();
function requestAnimationFrame(callback) {
  const handle = nextFrame++;
  frameQueue.set(handle, callback);
  return handle;
}
function cancelAnimationFrame(handle) { frameQueue.delete(handle); }
function flushFrame() {
  const pending = [...frameQueue.values()];
  frameQueue.clear();
  for (const callback of pending) callback();
  return pending.length;
}
function setTimeout(callback) {
  const handle = nextTimer++;
  timerQueue.set(handle, callback);
  return handle;
}
function clearTimeout(handle) { timerQueue.delete(handle); }
function flushTimers() {
  const pending = [...timerQueue.values()];
  timerQueue.clear();
  for (const callback of pending) callback();
  return pending.length;
}

const registry = new Map();
let homeAssistant;
const sandbox = {
  HTMLElement: Element,
  customElements: {
    define(name, constructor) { registry.set(name, constructor); },
    get(name) { return registry.get(name); },
  },
  window: {
    history: { pushState(_state, _title, path) { sandbox.navigatedTo = path; } },
    dispatchEvent(event) { sandbox.windowEvent = event; },
  },
  document: {
    createElement: (tag) => tag === "template" ? {} : new Element(),
    querySelector: (selector) => selector === "home-assistant" ? homeAssistant : undefined,
  },
  requestAnimationFrame,
  cancelAnimationFrame,
  setTimeout,
  clearTimeout,
  CustomEvent: class {
    constructor(type, options = {}) { this.type = type; this.detail = options.detail; Object.assign(this, options); }
  },
  Event: class {
    constructor(type, options) { this.type = type; Object.assign(this, options); }
  },
  Intl,
  Date,
  console,
};
vm.createContext(sandbox);
const source = fs.readFileSync(
  "custom_components/robbie_advanced_cc/frontend/cleaning-control.js",
  "utf8",
);
vm.runInContext(source, sandbox);

assert.ok(registry.has("robbie-advanced-cleaning-card"));
assert.ok(registry.has("robbie-advanced-cleaning-card-editor"));
assert.ok(registry.has("robbie-vacuum-badge"));
assert.equal(sandbox.window.customCards.length, 1);
assert.equal(sandbox.window.customBadges.length, 1);

const Card = registry.get("robbie-advanced-cleaning-card");
const serviceCalls = [];
const scheduledAfterDays = (days, hour = 6) => {
  const date = new Date();
  date.setDate(date.getDate() + days);
  date.setHours(hour, 0, 0, 0);
  return date.toISOString();
};
const laterScheduledRun = scheduledAfterDays(10);
const card = new Card();
card.connectedCallback();
assert.equal(card.lastEvent.type, "context-request");
assert.equal(card.lastEvent.context, "hassApi");
card.lastEvent.callback({
  callService: async (domain, service, data) => serviceCalls.push({ domain, service, data }),
});
card.setConfig({ status_entity: "sensor.planner_status" });
card.hass = {
  language: "de-DE",
  states: {
    "sensor.planner_status": {
      state: "idle",
      attributes: {
        entry_id: "entry-1",
        active_mission_id: null,
        last_reason: "not_evaluated",
        managed_vacuums: ["vacuum.robot", "vacuum.cloud"],
        profile_options: {
          "vacuum.robot": {
            areas: [{ value: "kitchen", label: "Kitchen" }, { value: "bathroom", label: "Bathroom" }],
            modes: [{ value: "vacuum_and_mop", label: "Vacuum + Mop" }, { value: "mop", label: "Mop" }, { value: "vacuum", label: "Vacuum" }],
            fan_speeds: [{ value: "low", label: "Low" }, { value: "high", label: "High" }],
            water_levels: [{ value: "low", label: "Low" }, { value: "high", label: "High" }],
            passes: [{ value: "1", label: "1" }, { value: "2", label: "2" }],
            current: { mode: "vacuum_and_mop", fan: "low", water: "low", passes: "1" },
          },
          "vacuum.cloud": {
            areas: [{ value: "hall", label: "Hall" }],
            modes: [{ value: "vacuum", label: "Vacuum" }],
            fan_speeds: [{ value: "quiet", label: "Quiet" }, { value: "turbo", label: "Turbo" }],
            water_levels: [], passes: [{ value: "1", label: "1" }],
            current: { mode: "vacuum", fan: "quiet", passes: "1" },
          },
        },
        waiting_vacuums: [],
        next_runs: {"vacuum.robot": {mission: "Sunday clean", scheduled: laterScheduledRun}},
        missions: [{
          id: "sunday", name: "Sunday clean", vacuum_entity_id: "vacuum.robot",
          weekdays: ["sun"], start_time: "05:00", areas: ["kitchen"],
          profile: { mode: "vacuum_and_mop", fan: "low", passes: 1 },
          guards: { people_home: "wait" }, next_run: "2026-08-16T05:00:00+02:00",
          all_conditions_met: true,
          conditions: [
            { key: "vacuum_available", enabled: true, passed: true },
            { key: "home_empty", enabled: true, passed: true, entity_name: "Home Zone", entity_state: "0" },
          ],
        }],
      },
    },
    "sensor.next_mission": {
      state: "2026-08-16T05:00:00+02:00",
      attributes: {
        entry_id: "entry-1",
        mission: "Sunday clean",
        mission_id: "sunday",
        vacuum_entity_id: "vacuum.robot",
        areas: ["kitchen"],
        profile: { mode: "vacuum_and_mop", fan: "low" },
      },
    },
    "sensor.last_decision": {
      state: "ready",
      attributes: { entry_id: "entry-1" },
    },
    "vacuum.robot": { state: "docked", attributes: { friendly_name: "Robbie" } },
    "vacuum.cloud": { state: "docked", attributes: { friendly_name: "Cloud Robot" } },
  },
};
flushFrame();
assert.equal(card._visibleRenderCount, 1, "the initial Card state should render once");
assert.equal(flushTimers(), 1, "the configured Card should consume its startup recovery timer");
assert.match(card.shadowRoot.innerHTML, /Robbie Advanced CC/);
assert.match(card.shadowRoot.innerHTML, /Sunday clean/);
assert.match(card.shadowRoot.innerHTML, /data-card-mode="simple"/);
assert.equal(card.getCardSize(), 4);
assert.equal(Card.getStubConfig(card._hass).entry_id, "entry-1");
const stableCardRoot = card._cardRoot;
const beforeBurst = card._visibleRenderCount;
const burstBase = card._hass;
for (const state of ["waiting", "running", "waiting"]) {
  card.hass = {
    ...burstBase,
    states: {
      ...burstBase.states,
      "sensor.planner_status": { ...burstBase.states["sensor.planner_status"], state },
    },
  };
}
assert.equal(frameQueue.size, 1, "a Card update burst must queue only one animation frame");
assert.equal(flushFrame(), 1);
assert.equal(card._visibleRenderCount, beforeBurst + 1, "a visible Card burst must render once");
assert.equal(card._cardRoot, stableCardRoot, "the ha-card root must remain stable");
assert.equal(card.shellWrites, 1, "the Card shadow shell must only be created once");
card.hass = burstBase;
flushFrame();
const stableRenderWrites = card.renderWrites;
card.hass = {
  ...card._hass,
  states: { ...card._hass.states, "sun.sun": { state: "above_horizon", attributes: {} } },
};
assert.equal(flushFrame(), 1);
assert.equal(card.renderWrites, stableRenderWrites, "unrelated HA updates must not rebuild the Card DOM");
const nonVacationHass = card._hass;
card.hass = {
  ...nonVacationHass,
  states: {
    ...nonVacationHass.states,
    "sensor.planner_status": {
      ...nonVacationHass.states["sensor.planner_status"],
      state: "vacation",
      attributes: { ...nonVacationHass.states["sensor.planner_status"].attributes, vacation_active: true },
    },
  },
};
flushFrame();
assert.match(card.shadowRoot.innerHTML, /mdi:palm-tree/);
assert.match(card.shadowRoot.innerHTML, />Urlaub</);
assert.match(card.shadowRoot.innerHTML, /data-action="run" disabled/);
card.hass = nonVacationHass;
flushFrame();
const cardClick = (matches, dataset = {}) => card._activateControl({
  matches: (selector) => selector === matches,
  dataset,
}, {
  preventDefault() {}, stopPropagation() {},
});
cardClick('[data-action="postpone"]');
assert.equal(JSON.stringify(serviceCalls), JSON.stringify([{
  domain: "robbie_advanced_cc",
  service: "postpone_next",
  data: { entry_id: "entry-1", minutes: 60 },
}]));
cardClick('[data-mode-toggle]');
assert.match(card.shadowRoot.innerHTML, /data-card-mode="advanced"/);
assert.match(card.shadowRoot.innerHTML, /Wochenplan/);
assert.match(card.shadowRoot.innerHTML, /kitchen/);
assert.match(card.shadowRoot.innerHTML, /Roboter verfügbar/);
assert.match(card.shadowRoot.innerHTML, /Home Zone: 0/);
assert.match(card.shadowRoot.innerHTML, /data-add-day="mon"/);
assert.match(card.shadowRoot.innerHTML, /data-add-position="top"/);
assert.match(card.shadowRoot.innerHTML, /Saugen \+ Wischen · kitchen/);
assert.equal(card.getCardSize(), 4, "the Advanced control center must not resize the dashboard Card");
cardClick("[data-add]", { addPosition: "bottom" });
assert.equal(card._editingMissionId, "new");
assert.equal(card._editingPlacement, "bottom");
assert.match(card.shadowRoot.innerHTML, /Live-Auswahl des Roboters/);
assert.match(card.shadowRoot.innerHTML, /class="robbie-mark /);
assert.match(card.shadowRoot.innerHTML, /class="robbie-machine"/);
assert.match(source, /_bindInteractiveNodes\(\)/);
assert.match(source, /button\.onclick = \(event\) => this\._activateControl\(button, event\)/);
assert.doesNotMatch(source, /_bindHostClick/);
assert.match(source, /<ha-dialog data-dialog-id="control-center" open/);
assert.match(card.shadowRoot.innerHTML, /<select name="fan">/);
assert.match(card.shadowRoot.innerHTML, /<select name="water">/);
assert.match(card.shadowRoot.innerHTML, /<select name="passes">/);
assert.match(card.shadowRoot.innerHTML, /<select name="areas" multiple/);
assert.doesNotMatch(card.shadowRoot.innerHTML, /<input name="fan"/);
assert.match(card.shadowRoot.innerHTML, /<option value="vacuum" selected>Vacuum<\/option>/, "a new run must default to vacuum even when the robot currently mops");

const staleFailureHass = {
  ...card._hass,
  states: {
    ...card._hass.states,
    "sensor.planner_status": {
      ...card._hass.states["sensor.planner_status"],
      state: "failed",
      attributes: {
        ...card._hass.states["sensor.planner_status"].attributes,
        active_mission_id: null,
        last_reason: "vacuum_unavailable",
        waiting_mission_ids: ["sunday"],
        missions: card._hass.states["sensor.planner_status"].attributes.missions.map((mission) => ({
          ...mission, waiting: true, all_conditions_met: false,
          conditions: mission.conditions.map((condition) => condition.key === "home_empty"
            ? { ...condition, passed: false, resolution: "wait", entity_state: "2" } : condition),
        })),
      },
    },
  },
};
card.hass = staleFailureHass;
flushFrame();
assert.match(card.shadowRoot.innerHTML, />Wartet</);
assert.match(card.shadowRoot.innerHTML, /Wartet, bis niemand zu Hause ist/);
assert.doesNotMatch(card.shadowRoot.innerHTML, />Fehler</);

card.hass = {
  ...staleFailureHass,
  states: {
    ...staleFailureHass.states,
    "sensor.planner_status": {
      ...staleFailureHass.states["sensor.planner_status"],
      attributes: {
        ...staleFailureHass.states["sensor.planner_status"].attributes,
        active_mission_id: "sunday", last_reason: "vacuum_error",
      },
    },
  },
};
flushFrame();
assert.match(card.shadowRoot.innerHTML, />Fehler</);
assert.match(card.shadowRoot.innerHTML, /Der Roboter meldet einen Fehler/);

card.hass = {
  ...staleFailureHass,
  states: {
    ...staleFailureHass.states,
    "sensor.planner_status": {
      ...staleFailureHass.states["sensor.planner_status"],
      attributes: {
        ...staleFailureHass.states["sensor.planner_status"].attributes,
        active_mission_id: null,
        has_robot_error: true,
        robot_errors: {
          "vacuum.robot": {
            entity_id: "sensor.robot_error",
            message: "Auto-empty dock is blocked",
          },
        },
      },
    },
  },
};
flushFrame();
assert.match(card.shadowRoot.innerHTML, />Fehler</);
assert.match(card.shadowRoot.innerHTML, /Auto-empty dock is blocked/);
card.hass = nonVacationHass;
flushFrame();
card._handleProfileChange({ stopPropagation() {} }, {
  value: "vacuum.cloud", matches: (selector) => selector === "[data-profile-vacuum]",
});
assert.match(card.shadowRoot.innerHTML, /Cloud Robot/);
assert.match(card.shadowRoot.innerHTML, />Turbo</);
assert.doesNotMatch(card.shadowRoot.innerHTML, /<select name="water">/);

const second = new Card();
second.setConfig({ status_entity: "sensor.planner_status" });
second.hass = { ...card._hass, language: "en" };
flushFrame();
assert.match(second.shadowRoot.innerHTML, /Robbie Advanced CC/);
assert.equal(sandbox.window.customCards.length, 1);

const automatic = new Card();
automatic.setConfig({ mode: "simple" });
automatic.hass = card._hass;
flushFrame();
assert.match(automatic.shadowRoot.innerHTML, /data-card-mode="simple"/);
assert.match(automatic.shadowRoot.innerHTML, /Sunday clean/);
assert.doesNotMatch(automatic.shadowRoot.innerHTML, /Planerstatus-Entität auswählen/);

const stale = new Card();
stale.setConfig({ status_entity: "sensor.old_planner_status", mode: "advanced" });
stale.hass = card._hass;
flushFrame();
assert.match(stale.shadowRoot.innerHTML, /data-card-mode="advanced"/);
assert.match(stale.shadowRoot.innerHTML, /Wochenplan/);

homeAssistant = { hass: card._hass };
const recovered = new Card();
recovered.parentElement = { _config: { entry_id: "entry-1", mode: "advanced" } };
recovered.connectedCallback();
assert.equal(flushTimers(), 1);
assert.match(recovered.shadowRoot.innerHTML, /data-card-mode="advanced"/);
assert.match(recovered.shadowRoot.innerHTML, /Sunday clean/);
assert.equal(recovered._visibleRenderCount, 1, "a late-upgraded Card should recover exactly once");
homeAssistant = undefined;

const Badge = registry.get("robbie-vacuum-badge");
assert.equal(Badge.getStubConfig(card._hass).entity, "sensor.planner_status");
assert.equal(Badge.getStubConfig(card._hass).tap_action.action, "navigate");
const automaticBadge = new Badge();
automaticBadge.setConfig({ entity: "sensor.planner_status", tap_action: { action: "navigate", navigation_path: "/lovelace/cleaning" } });
automaticBadge.hass = card._hass;
flushFrame();
assert.match(automaticBadge.shadowRoot.innerHTML, /data-mode="docked"/);
assert.match(automaticBadge.shadowRoot.innerHTML, /Robbie/);
const attentionBadge = new Badge();
attentionBadge.setConfig({ entity: "sensor.planner_status", display_mode: "attention" });
attentionBadge.hass = card._hass;
flushFrame();
assert.notEqual(attentionBadge.hasAttribute?.("data-robbie-hidden"), true, "legacy display_mode must not hide the Badge internally");
attentionBadge.hass = {
  ...card._hass,
  states: {
    ...card._hass.states,
    "vacuum.robot": { ...card._hass.states["vacuum.robot"], state: "cleaning" },
  },
};
flushFrame();
assert.notEqual(attentionBadge.hasAttribute?.("data-robbie-hidden"), true, "Badge visibility belongs to Home Assistant");
const badge = new Badge();
badge.setConfig({
  entity: "sensor.planner_status",
  state_override_entity: "input_select.badge_state_simulator",
  navigation_path: "/lovelace/cleaning",
  hold_action: { action: "more-info" },
  visibility: [{ condition: "state", entity: "sensor.planner_status", state: "waiting" }],
});
badge.hass = card._hass;
flushFrame();
assert.match(badge.shadowRoot.innerHTML, /data-mode="docked"/, "legacy state overrides must be ignored");
assert.match(badge.shadowRoot.innerHTML, /In Station/);
assert.match(badge.shadowRoot.innerHTML, /Nächster Start/);
assert.match(badge.shadowRoot.innerHTML, /ha-badge/);
assert.match(badge.shadowRoot.innerHTML, /--ha-badge-size,36px/);
assert.match(badge.shadowRoot.innerHTML, /class="badge-symbol"/);
assert.match(badge.shadowRoot.innerHTML, /class="robot-symbol"/);
assert.doesNotMatch(badge.shadowRoot.innerHTML, /class="state-marker"/, "a next-run label must not compete with the dock marker");
assert.match(badge.shadowRoot.innerHTML, /data-mode="docked"/);
assert.match(badge.shadowRoot.innerHTML, /class="next-time"/);
assert.notEqual(badge._formatNextRun(scheduledAfterDays(0)).short, "", "today must show a time");
assert.equal(badge._formatNextRun(scheduledAfterDays(1)).short, "Morgen", "tomorrow must be explicit in German");
assert.doesNotMatch(badge._formatNextRun(scheduledAfterDays(3)).short, /:/, "this week must show a weekday, not only a time");
assert.doesNotMatch(badge._formatNextRun(laterScheduledRun).short, /:/, "later runs must show a date, not only a time");
assert.match(badge._formatNextRun(laterScheduledRun).full, /06:00/, "the tooltip must retain the exact time");
const stableBadgeRoot = badge._badgeRoot;
const badgeBeforeBurst = badge._visibleRenderCount;
for (const [state, scheduled] of [["idle", scheduledAfterDays(2, 5)], ["cleaning", scheduledAfterDays(2, 5)]]) {
  badge.hass = {
    ...card._hass,
    states: {
      ...card._hass.states,
      "vacuum.robot": { ...card._hass.states["vacuum.robot"], state },
      "sensor.planner_status": {
        ...card._hass.states["sensor.planner_status"],
        attributes: {
          ...card._hass.states["sensor.planner_status"].attributes,
          next_runs: { "vacuum.robot": { mission: "Sunday clean", scheduled } },
        },
      },
    },
  };
}
assert.equal(frameQueue.size, 1, "a Badge update burst must queue only one animation frame");
flushFrame();
assert.equal(badge._visibleRenderCount, badgeBeforeBurst + 1, "a visible Badge burst must render once");
assert.equal(badge._badgeRoot, stableBadgeRoot, "the ha-badge root must remain stable");
assert.equal(badge.shellWrites, 1, "the Badge shadow shell must only be created once");
const plannerStates = {
  announced: ["docked", null],
  preparing: ["cleaning", "mdi:play"],
  running: ["cleaning", "mdi:play"],
  dock_service: ["returning", "mdi:home-import-outline"],
  waiting: ["waiting", "mdi:account-clock-outline"],
  vacation: ["vacation", "mdi:palm-tree"],
  blocked: ["error", "mdi:alert"],
  failed: ["error", "mdi:alert"],
};
for (const [plannerState, [badgeState, stateIcon]] of Object.entries(plannerStates)) {
  badge.hass = {
    ...card._hass,
    states: {
      ...card._hass.states,
      "sensor.planner_status": {
        ...card._hass.states["sensor.planner_status"],
        state: plannerState,
      },
    },
  };
  flushFrame();
  assert.match(badge.shadowRoot.innerHTML, new RegExp(`data-mode="${badgeState}"`));
  if (stateIcon) assert.match(badge.shadowRoot.innerHTML, new RegExp(`icon="${stateIcon}"`));
  else {
    assert.match(badge.shadowRoot.innerHTML, /class="next-time"/);
    assert.doesNotMatch(badge.shadowRoot.innerHTML, /class="state-marker"/);
  }
}
badge.hass = {
  ...card._hass,
  states: {
    ...card._hass.states,
    "sensor.planner_status": {
      ...card._hass.states["sensor.planner_status"],
      state: "vacation",
      attributes: { ...card._hass.states["sensor.planner_status"].attributes, vacation_active: true },
    },
  },
};
flushFrame();
assert.match(badge.shadowRoot.innerHTML, /data-mode="vacation"/);
assert.match(badge.shadowRoot.innerHTML, /Urlaub/);
let clickStopped = false;
badge.handlers["ha-badge:click"]({ stopPropagation() { clickStopped = true; } });
assert.equal(clickStopped, true);
assert.equal(sandbox.navigatedTo, undefined, "Badge must not navigate outside Home Assistant's action contract");
assert.equal(badge.lastEvent.type, "hass-action");
assert.equal(badge.lastEvent.detail.action, "tap");
assert.equal(badge.lastEvent.detail.config.entity, "sensor.planner_status");
assert.equal(badge.lastEvent.detail.config.tap_action.action, "navigate");
assert.equal(badge.lastEvent.detail.config.tap_action.navigation_path, "/lovelace/cleaning");
assert.equal(badge.lastEvent.detail.config.hold_action.action, "more-info");
assert.equal(badge.lastEvent.detail.config.visibility[0].state, "waiting");
badge.handlers["ha-badge:pointerdown"]({});
assert.equal(flushTimers(), 1);
assert.equal(badge.lastEvent.type, "hass-action");
assert.equal(badge.lastEvent.detail.action, "hold");
assert.equal(badge.lastEvent.detail.config.entity, "sensor.planner_status");
badge.handlers["ha-badge:click"]({ stopPropagation() {} });
assert.equal(badge.lastEvent.detail.action, "hold", "the synthetic click after a hold must be ignored");
badge.handlers["ha-badge:click"]({ stopPropagation() {} });
badge.handlers["ha-badge:touchstart"]({});
assert.equal(flushTimers(), 1);
assert.equal(badge.lastEvent.detail.action, "hold", "touch fallback must dispatch a native hold");
badge.handlers["ha-badge:click"]({ stopPropagation() {} });
let contextPrevented = false;
let contextStopped = false;
badge.handlers["ha-badge:contextmenu"]({
  preventDefault() { contextPrevented = true; },
  stopPropagation() { contextStopped = true; },
});
assert.equal(contextPrevented, true);
assert.equal(contextStopped, true);
assert.equal(badge.lastEvent.detail.action, "hold", "iOS context-menu fallback must dispatch a native hold");
badge.handlers["ha-badge:click"]({ stopPropagation() {} });
badge.setConfig({
  entity: "sensor.planner_status",
  tap_action: { action: "navigate", navigation_path: "/lovelace/cleaning" },
  hold_action: { action: "more-info" },
  double_tap_action: { action: "more-info" },
});
badge.handlers["ha-badge:click"]({ stopPropagation() {} });
badge.handlers["ha-badge:click"]({ stopPropagation() {} });
assert.equal(badge.lastEvent.detail.action, "double_tap");
let keyPrevented = false;
badge.handlers["ha-badge:keydown"]({ key: "Enter", preventDefault() { keyPrevented = true; } });
assert.equal(keyPrevented, true);

console.log("Card runtime contract passed");
