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
  CustomEvent: class {},
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
        managed_vacuums: ["vacuum.robot", "vacuum.cloud"],
        profile_options: {
          "vacuum.robot": {
            areas: [{ value: "kitchen", label: "Kitchen" }, { value: "bathroom", label: "Bathroom" }],
            modes: [{ value: "vacuum", label: "Vacuum" }, { value: "vacuum_and_mop", label: "Vacuum + Mop" }],
            fan_speeds: [{ value: "low", label: "Low" }, { value: "high", label: "High" }],
            water_levels: [{ value: "low", label: "Low" }, { value: "high", label: "High" }],
            passes: [{ value: "1", label: "1" }, { value: "2", label: "2" }],
            current: { mode: "vacuum", fan: "low", water: "low", passes: "1" },
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
        next_runs: {"vacuum.robot": {mission: "Sunday clean", scheduled: "2026-08-16T05:00:00+02:00"}},
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
        vacuum_entity_id: "vacuum.robot",
        areas: ["kitchen"],
        profile: { mode: "vacuum_and_mop", fan: "low" },
      },
    },
    "sensor.last_decision": {
      state: "ready",
      attributes: { entry_id: "entry-1" },
    },
    "input_select.badge_state_simulator": {
      state: "live",
      attributes: { friendly_name: "Badge State Simulator" },
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
assert.match(card.shadowRoot.innerHTML, /Vac\+Mop · kitchen/);
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
assert.equal(Badge.getStubConfig(card._hass).entry_id, "entry-1");
const automaticBadge = new Badge();
automaticBadge.setConfig({ navigation_path: "/lovelace/cleaning" });
automaticBadge.hass = card._hass;
flushFrame();
assert.match(automaticBadge.shadowRoot.innerHTML, /data-mode="docked"/);
assert.match(automaticBadge.shadowRoot.innerHTML, /Robbie/);
const badge = new Badge();
badge.setConfig({
  vacuum_entity: "vacuum.robot",
  status_entity: "sensor.planner_status",
  state_override_entity: "input_select.badge_state_simulator",
  navigation_path: "/lovelace/cleaning",
});
badge.hass = card._hass;
flushFrame();
assert.match(badge.shadowRoot.innerHTML, /In Station/);
assert.match(badge.shadowRoot.innerHTML, /Nächster Start/);
assert.match(badge.shadowRoot.innerHTML, /ha-badge/);
assert.match(badge.shadowRoot.innerHTML, /--ha-badge-size,36px/);
assert.match(badge.shadowRoot.innerHTML, /class="badge-symbol"/);
assert.match(badge.shadowRoot.innerHTML, /class="robot-symbol"/);
assert.match(badge.shadowRoot.innerHTML, /class="state-marker"/);
assert.match(badge.shadowRoot.innerHTML, /data-mode="docked"/);
assert.match(badge.shadowRoot.innerHTML, /class="next-time"/);
const stableBadgeRoot = badge._badgeRoot;
const badgeBeforeBurst = badge._visibleRenderCount;
for (const [state, scheduled] of [["idle", "2026-08-16T05:05:00+02:00"], ["cleaning", "2026-08-16T05:10:00+02:00"]]) {
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
const simulatedStates = {
  docked: "mdi:home",
  idle: "mdi:power-sleep",
  cleaning: "mdi:play",
  returning: "mdi:home-import-outline",
  paused: "mdi:pause",
  waiting: "mdi:account-clock-outline",
  vacation: "mdi:palm-tree",
  error: "mdi:alert",
  unavailable: "mdi:alert-circle-outline",
};
for (const [state, stateIcon] of Object.entries(simulatedStates)) {
  badge.hass = {
    ...card._hass,
    states: {
      ...card._hass.states,
      "input_select.badge_state_simulator": {
        state,
        attributes: { friendly_name: "Badge State Simulator" },
      },
    },
  };
  flushFrame();
  assert.match(badge.shadowRoot.innerHTML, new RegExp(`data-mode="${state}"`));
  assert.match(badge.shadowRoot.innerHTML, new RegExp(`icon="${stateIcon}"`));
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
    "input_select.badge_state_simulator": { state: "cleaning", attributes: {} },
  },
};
flushFrame();
assert.match(badge.shadowRoot.innerHTML, /data-mode="vacation"/);
assert.match(badge.shadowRoot.innerHTML, /Urlaub/);
let clickStopped = false;
badge.handlers["ha-badge:click"]({ stopPropagation() { clickStopped = true; } });
assert.equal(clickStopped, true);
assert.equal(sandbox.navigatedTo, "/lovelace/cleaning");
assert.equal(sandbox.windowEvent.constructor.name, "CustomEvent");
let keyPrevented = false;
badge.handlers["ha-badge:keydown"]({ key: "Enter", preventDefault() { keyPrevented = true; } });
assert.equal(keyPrevented, true);

console.log("Card runtime contract passed");
