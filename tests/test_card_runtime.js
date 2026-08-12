const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

class Element {
  constructor() { this.shadowRoot = null; this.handlers = {}; this.renderWrites = 0; }
  attachShadow() {
    const owner = this;
    let markup = "";
    this.shadowRoot = {
      get innerHTML() { return markup; },
      set innerHTML(value) { markup = value; owner.renderWrites += 1; },
      addEventListener(type, callback) { owner.handlers[`shadow:${type}`] = callback; },
      querySelector(selector) {
        return {
          addEventListener(type, callback) {
            owner.handlers[`${selector}:${type}`] = callback;
          },
        };
      },
    };
    return this.shadowRoot;
  }
  dispatchEvent(event) { this.lastEvent = event; }
}

const registry = new Map();
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
  document: { createElement: () => new Element() },
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
assert.match(card.shadowRoot.innerHTML, /Robbie Advanced CC/);
assert.match(card.shadowRoot.innerHTML, /Sunday clean/);
assert.match(card.shadowRoot.innerHTML, /data-card-mode="simple"/);
assert.equal(card.getCardSize(), 4);
assert.equal(Card.getStubConfig(card._hass).entry_id, "entry-1");
const stableRenderWrites = card.renderWrites;
card.hass = {
  ...card._hass,
  states: { ...card._hass.states, "sun.sun": { state: "above_horizon", attributes: {} } },
};
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
assert.match(card.shadowRoot.innerHTML, /mdi:palm-tree/);
assert.match(card.shadowRoot.innerHTML, />Urlaub</);
assert.match(card.shadowRoot.innerHTML, /data-action="run" disabled/);
card.hass = nonVacationHass;
const cardClick = (matches, dataset = {}) => card.handlers["shadow:click"]({
  preventDefault() {}, stopPropagation() {},
  composedPath() { return [{ matches: (selector) => selector === "button" || selector === matches, dataset }]; },
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
assert.match(card.shadowRoot.innerHTML, /Vac\+Mop · kitchen/);
assert.equal(card.getCardSize(), 9);
card._editingMissionId = "new";
card._render();
assert.match(card.shadowRoot.innerHTML, /Live-Auswahl des Roboters/);
assert.match(card.shadowRoot.innerHTML, /<select name="fan">/);
assert.match(card.shadowRoot.innerHTML, /<select name="water">/);
assert.match(card.shadowRoot.innerHTML, /<select name="passes">/);
assert.match(card.shadowRoot.innerHTML, /<select name="areas" multiple/);
assert.doesNotMatch(card.shadowRoot.innerHTML, /<input name="fan"/);
card.handlers["shadow:change"]({
  target: { value: "vacuum.cloud", matches: (selector) => selector === "[data-profile-vacuum]" },
  stopPropagation() {},
});
assert.match(card.shadowRoot.innerHTML, /Cloud Robot/);
assert.match(card.shadowRoot.innerHTML, />Turbo</);
assert.doesNotMatch(card.shadowRoot.innerHTML, /<select name="water">/);

const second = new Card();
second.setConfig({ status_entity: "sensor.planner_status" });
second.hass = { ...card._hass, language: "en" };
assert.match(second.shadowRoot.innerHTML, /Robbie Advanced CC/);
assert.equal(sandbox.window.customCards.length, 1);

const automatic = new Card();
automatic.setConfig({ mode: "simple" });
automatic.hass = card._hass;
assert.match(automatic.shadowRoot.innerHTML, /data-card-mode="simple"/);
assert.match(automatic.shadowRoot.innerHTML, /Sunday clean/);
assert.doesNotMatch(automatic.shadowRoot.innerHTML, /Planerstatus-Entität auswählen/);

const stale = new Card();
stale.setConfig({ status_entity: "sensor.old_planner_status", mode: "advanced" });
stale.hass = card._hass;
assert.match(stale.shadowRoot.innerHTML, /data-card-mode="advanced"/);
assert.match(stale.shadowRoot.innerHTML, /Wochenplan/);

const Badge = registry.get("robbie-vacuum-badge");
assert.equal(Badge.getStubConfig(card._hass).entry_id, "entry-1");
const automaticBadge = new Badge();
automaticBadge.setConfig({ navigation_path: "/lovelace/cleaning" });
automaticBadge.hass = card._hass;
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
assert.match(badge.shadowRoot.innerHTML, /In Station/);
assert.match(badge.shadowRoot.innerHTML, /Nächster Start/);
assert.match(badge.shadowRoot.innerHTML, /ha-badge/);
assert.match(badge.shadowRoot.innerHTML, /--ha-badge-size,36px/);
assert.match(badge.shadowRoot.innerHTML, /class="badge-symbol"/);
assert.match(badge.shadowRoot.innerHTML, /class="robot-symbol"/);
assert.match(badge.shadowRoot.innerHTML, /class="state-marker"/);
assert.match(badge.shadowRoot.innerHTML, /data-mode="docked"/);
assert.match(badge.shadowRoot.innerHTML, /class="next-time"/);
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
