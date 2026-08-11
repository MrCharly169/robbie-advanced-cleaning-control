const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

class Element {
  constructor() { this.shadowRoot = null; this.handlers = {}; }
  attachShadow() {
    const owner = this;
    this.shadowRoot = {
      innerHTML: "",
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
        managed_vacuums: ["vacuum.robot"],
        waiting_vacuums: [],
        next_runs: {"vacuum.robot": {mission: "Sunday clean", scheduled: "2026-08-16T05:00:00+02:00"}},
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
    "vacuum.robot": { state: "docked", attributes: { friendly_name: "Robbie" } },
  },
};
assert.match(card.shadowRoot.innerHTML, /Reinigungssteuerung/);
assert.match(card.shadowRoot.innerHTML, /Sunday clean/);
assert.match(card.shadowRoot.innerHTML, /kitchen/);
assert.equal(card.getCardSize(), 5);
card.handlers['[data-action="postpone"]:click']();
assert.equal(JSON.stringify(serviceCalls), JSON.stringify([{
  domain: "robbie_advanced_cc",
  service: "postpone_next",
  data: { entry_id: "entry-1", minutes: 60 },
}]));

const second = new Card();
second.setConfig({ status_entity: "sensor.planner_status" });
second.hass = { ...card._hass, language: "en" };
assert.match(second.shadowRoot.innerHTML, /Cleaning Control/);
assert.equal(sandbox.window.customCards.length, 1);

const Badge = registry.get("robbie-vacuum-badge");
const badge = new Badge();
badge.setConfig({
  vacuum_entity: "vacuum.robot",
  status_entity: "sensor.planner_status",
  navigation_path: "/lovelace/cleaning",
});
badge.hass = card._hass;
assert.match(badge.shadowRoot.innerHTML, /In Station/);
assert.match(badge.shadowRoot.innerHTML, /Nächster Start/);
assert.match(badge.shadowRoot.innerHTML, /home-import-outline/);
badge.handlers["button:click"]();
assert.equal(sandbox.navigatedTo, "/lovelace/cleaning");
assert.equal(sandbox.windowEvent.constructor.name, "CustomEvent");

console.log("Card runtime contract passed");
