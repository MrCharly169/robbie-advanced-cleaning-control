const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

class Element {
  constructor() { this.shadowRoot = null; }
  attachShadow() {
    this.shadowRoot = {
      innerHTML: "",
      querySelector() { return null; },
    };
    return this.shadowRoot;
  }
  dispatchEvent() {}
}

const registry = new Map();
const sandbox = {
  HTMLElement: Element,
  customElements: {
    define(name, constructor) { registry.set(name, constructor); },
    get(name) { return registry.get(name); },
  },
  window: {},
  document: { createElement: () => new Element() },
  CustomEvent: class {},
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
assert.equal(sandbox.window.customCards.length, 1);

const Card = registry.get("robbie-advanced-cleaning-card");
const card = new Card();
card.setConfig({ status_entity: "sensor.planner_status" });
card.hass = {
  language: "de-DE",
  states: {
    "sensor.planner_status": {
      state: "idle",
      attributes: { entry_id: "entry-1" },
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
  callService: async () => {},
};
assert.match(card.shadowRoot.innerHTML, /Reinigungssteuerung/);
assert.match(card.shadowRoot.innerHTML, /Sunday clean/);
assert.match(card.shadowRoot.innerHTML, /kitchen/);
assert.equal(card.getCardSize(), 5);

const second = new Card();
second.setConfig({ status_entity: "sensor.planner_status" });
second.hass = { ...card._hass, language: "en" };
assert.match(second.shadowRoot.innerHTML, /Cleaning Control/);
assert.equal(sandbox.window.customCards.length, 1);

console.log("Card runtime contract passed");
