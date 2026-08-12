#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs/promises";

const args = Object.fromEntries(process.argv.slice(2).reduce((items, value, index, all) => {
  if (value.startsWith("--")) items.push([value.slice(2), all[index + 1]]);
  return items;
}, []));
const baseUrl = (args["base-url"] || "http://127.0.0.1:18123").replace(/\/$/, "");
const cardMode = args["card-mode"] === "advanced" ? "advanced" : "simple";
const checkOnboarding = args["check-onboarding"] === "true";
const state = JSON.parse(await fs.readFile(args["state-file"], "utf8"));
const token = state.token;
if (!token) throw new Error("Runner state does not contain a Home Assistant token");

const statesResponse = await fetch(`${baseUrl}/api/states`, {
  headers: { Authorization: `Bearer ${token}` },
});
if (!statesResponse.ok) throw new Error(`Could not read HA states: ${statesResponse.status}`);
const states = await statesResponse.json();
const status = states.find((item) =>
  item.entity_id.startsWith("sensor.") && item.attributes?.entry_id === state.entry_id
  && Array.isArray(item.attributes?.managed_vacuums));
if (!status) throw new Error("Planner status entity was not found");
const simulator = states.find((item) => item.entity_id === "input_select.badge_state_simulator");
const simulatorStates = ["live", "docked", "idle", "cleaning", "returning", "paused", "waiting", "error", "unavailable"];
if (!simulator || simulatorStates.some((value) => !simulator.attributes?.options?.includes(value))) {
  throw new Error("Badge state simulator does not expose every supported badge state");
}

const wsUrl = `${baseUrl.replace(/^http/, "ws")}/api/websocket`;
const socket = new WebSocket(wsUrl);
let nextId = 1;
const pending = new Map();

const ready = new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(new Error("Home Assistant WebSocket timed out")), 20000);
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "auth_required") {
      socket.send(JSON.stringify({ type: "auth", access_token: token }));
      return;
    }
    if (message.type === "auth_ok") {
      clearTimeout(timer);
      resolve();
      return;
    }
    if (message.type === "auth_invalid") {
      clearTimeout(timer);
      reject(new Error(`Home Assistant authentication failed: ${message.message}`));
      return;
    }
    if (message.id && pending.has(message.id)) {
      const { resolve: done, reject: fail } = pending.get(message.id);
      pending.delete(message.id);
      if (message.success) done(message.result);
      else fail(new Error(`${message.error?.code || "ws_error"}: ${message.error?.message || "Unknown error"}`));
    }
  });
  socket.addEventListener("error", () => reject(new Error("Home Assistant WebSocket connection failed")));
});

function call(type, payload = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, type, ...payload }));
  });
}

await ready;
const manifest = JSON.parse(await fs.readFile("custom_components/robbie_advanced_cc/manifest.json", "utf8"));
const resourcePath = "/robbie_advanced_cc/cleaning-control.js";
const cardSource = await fs.readFile("custom_components/robbie_advanced_cc/frontend/cleaning-control.js");
const assetDigest = crypto.createHash("sha256").update(cardSource).digest("hex").slice(0, 10);
const resourceUrl = `${resourcePath}?v=${manifest.version}-${assetDigest}`;
const resources = await call("lovelace/resources/list");
const robbieResources = resources.filter((item) => item.url?.split("?", 1)[0] === resourcePath);
if (robbieResources.length !== 1 || robbieResources[0].url !== resourceUrl || robbieResources[0].type !== "module") {
  throw new Error(`Integration did not auto-register its canonical Card resource: ${JSON.stringify(robbieResources)}`);
}
const notifications = await call("persistent_notification/get");
const setupNotification = notifications.find((item) => item.notification_id === `robbie_advanced_cc_setup_${state.entry_id}`);
if (checkOnboarding && (!setupNotification?.message?.includes("registered automatically") || !setupNotification.message.includes("custom:robbie-vacuum-badge"))) {
  throw new Error(`Dashboard setup notification is incomplete: ${JSON.stringify(setupNotification)}`);
}

const dashboard = {
  title: "Robbie Advanced CC Lab",
  views: [{
    title: "Cleaning Control",
    path: "cleaning",
    icon: "mdi:robot-vacuum",
    badges: [
      { type: "custom:robbie-vacuum-badge", vacuum_entity: "vacuum.valetudo_fixture_robot", status_entity: status.entity_id, state_override_entity: "input_select.badge_state_simulator", navigation_path: "/lovelace/cleaning" },
      { type: "custom:robbie-vacuum-badge", vacuum_entity: "vacuum.cloud_fixture_robot", status_entity: status.entity_id, navigation_path: "/lovelace/cleaning" },
    ],
    cards: [
      // Deliberately omit status_entity: the Card must discover its planner
      // sensor itself, including after an entity rename or YAML copy/paste.
      { type: "custom:robbie-advanced-cleaning-card", mode: cardMode },
      {
        type: "entities",
        title: "Badge Simulator · Lab only",
        show_header_toggle: false,
        entities: [{ entity: "input_select.badge_state_simulator", name: "Valetudo badge state" }],
      },
    ],
  }],
};
await call("lovelace/config/save", { config: dashboard });
const saved = await call("lovelace/config");
if (saved?.views?.[0]?.cards?.[0]?.type !== "custom:robbie-advanced-cleaning-card") {
  throw new Error("Editable Lovelace dashboard was not persisted");
}
if (saved?.views?.[0]?.badges?.[0]?.state_override_entity !== "input_select.badge_state_simulator") {
  throw new Error("Badge state simulator was not persisted");
}
socket.close();
console.log(`Editable Lovelace dashboard configured with ${status.entity_id}`);
