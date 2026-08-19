#!/usr/bin/env node
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
const resourcePath = "/robbie_advanced_cc/cleaning-control.js";
const resources = await call("lovelace/resources/list");
const robbieResources = resources.filter((item) => item.url?.split("?", 1)[0] === resourcePath);
if (robbieResources.length !== 1 || robbieResources[0].url !== resourcePath || robbieResources[0].type !== "module") {
  throw new Error(`Integration did not auto-register its canonical Card resource: ${JSON.stringify(robbieResources)}`);
}
const notifications = await call("persistent_notification/get");
const setupNotification = notifications.find((item) => item.notification_id === `robbie_advanced_cc_setup_${state.entry_id}`);
if (checkOnboarding && (
  !setupNotification?.message?.includes("registered automatically")
  || !setupNotification.message.includes("type: entity")
  || !setupNotification.message.includes("native Visibility tab")
)) {
  throw new Error(`Dashboard setup notification is incomplete: ${JSON.stringify(setupNotification)}`);
}

const dashboard = {
  title: "Robbie Advanced CC Lab",
  views: [{
    title: "Cleaning Control",
    path: "cleaning",
    icon: "mdi:robot-vacuum",
    badges: [
      // Both are standard Home Assistant Entity Badges consuming the canonical
      // Planner enum. Only the second uses native Lovelace Visibility.
      { type: "entity", entity: status.entity_id, show_name: false, show_icon: true, show_state: true, color: "state", tap_action: { action: "navigate", navigation_path: "/lovelace/cleaning" } },
      { type: "entity", entity: status.entity_id, show_name: false, show_icon: true, show_state: true, color: "state", tap_action: { action: "navigate", navigation_path: "/lovelace/cleaning" }, visibility: [{ condition: "state", entity: status.entity_id, state: "waiting" }] },
    ],
    cards: [
      // Deliberately omit status_entity: the Card must discover its planner
      // sensor itself, including after an entity rename or YAML copy/paste.
      { type: "custom:robbie-advanced-cleaning-card", entry_id: status.attributes.entry_id, mode: cardMode },
    ],
  }],
};
await call("lovelace/config/save", { config: dashboard });
const saved = await call("lovelace/config");
if (saved?.views?.[0]?.cards?.[0]?.type !== "custom:robbie-advanced-cleaning-card") {
  throw new Error("Editable Lovelace dashboard was not persisted");
}
if (saved?.views?.[0]?.badges?.[0]?.entity !== status.entity_id) {
  throw new Error("Badge Planner enum entity was not persisted");
}
if (saved?.views?.[0]?.badges?.[1]?.visibility?.[0]?.entity !== status.entity_id) {
  throw new Error("Native Badge Visibility condition was not persisted");
}
socket.close();
console.log(`Editable Lovelace dashboard configured with ${status.entity_id}`);
