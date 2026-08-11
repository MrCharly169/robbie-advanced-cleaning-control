#!/usr/bin/env node
import fs from "node:fs/promises";

const args = Object.fromEntries(process.argv.slice(2).reduce((items, value, index, all) => {
  if (value.startsWith("--")) items.push([value.slice(2), all[index + 1]]);
  return items;
}, []));
const baseUrl = (args["base-url"] || "http://127.0.0.1:18123").replace(/\/$/, "");
const cardMode = args["card-mode"] === "advanced" ? "advanced" : "simple";
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
const resourceUrl = "/robbie_advanced_cc/cleaning-control.js?lab=2026.8.6";
const resources = await call("lovelace/resources/list");
for (const resource of resources.filter((item) => item.url.startsWith("/robbie_advanced_cc/"))) {
  if (resource.url !== resourceUrl) await call("lovelace/resources/delete", { resource_id: resource.id });
}
if (!resources.some((item) => item.url === resourceUrl)) {
  await call("lovelace/resources/create", { res_type: "module", url: resourceUrl });
}

const dashboard = {
  title: "Robbie Advanced CC Lab",
  views: [{
    title: "Cleaning Control",
    path: "cleaning",
    icon: "mdi:robot-vacuum",
    badges: [
      { type: "custom:robbie-vacuum-badge", vacuum_entity: "vacuum.valetudo_fixture_robot", status_entity: status.entity_id, navigation_path: "/lovelace/cleaning" },
      { type: "custom:robbie-vacuum-badge", vacuum_entity: "vacuum.cloud_fixture_robot", status_entity: status.entity_id, navigation_path: "/lovelace/cleaning" },
    ],
    cards: [{ type: "custom:robbie-advanced-cleaning-card", status_entity: status.entity_id, mode: cardMode }],
  }],
};
await call("lovelace/config/save", { config: dashboard });
const saved = await call("lovelace/config");
if (saved?.views?.[0]?.cards?.[0]?.type !== "custom:robbie-advanced-cleaning-card") {
  throw new Error("Editable Lovelace dashboard was not persisted");
}
socket.close();
console.log(`Editable Lovelace dashboard configured with ${status.entity_id}`);
