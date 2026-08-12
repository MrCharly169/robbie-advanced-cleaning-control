const DOMAIN = "robbie_advanced_cc";
const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

const COPY = {
  en: {
    brand: "Robbie Advanced CC", title: "Cleaning Planner", simple: "Simple", advanced: "Advanced",
    next: "Next run", noMission: "No run planned", ready: "All conditions met", blocked: "Conditions pending",
    weekly: "Weekly runs", missions: "Runs & conditions", run: "Run now", skip: "Skip once",
    postpone: "Postpone", add: "Add run", edit: "Edit", remove: "Remove", save: "Save run", cancel: "Cancel",
    vacuum: "Robot", schedule: "HA Schedule helper", time: "Start time", weekdays: "Weekdays",
    condition: "When somebody is home", profile: "Cleaning mode", areas: "Rooms / segments", passes: "Passes",
    fan: "Vacuum strength", water: "Water level", dayRun: "Run for", perDayHint: "Each run keeps its own rooms and cleaning settings. Use the + on a weekday for a precise day profile.",
    liveChoices: "Live robot choices", unsupported: "Unsupported settings are hidden",
    enabled: "Enabled", name: "Run name", nativeSchedule: "Native HA schedule", weeklySchedule: "Weekly schedule",
    planner_enabled: "Planner and run enabled", vacuum_available: "Robot available", vacation_inactive: "Vacation mode off", vacation: "Vacation",
    mop_attached: "Mop attached", home_empty: "Nobody home", allow: "Start anyway", wait: "Wait until empty",
    skipPolicy: "Skip run", noConditions: "No additional conditions", configure: "Configure the planner status entity.",
    days: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
  },
  de: {
    brand: "Robbie Advanced CC", title: "Reinigungsplaner", simple: "Simple", advanced: "Advanced",
    next: "Nächster Lauf", noMission: "Kein Lauf geplant", ready: "Alle Bedingungen erfüllt", blocked: "Bedingungen noch offen",
    weekly: "Wochenplan", missions: "Läufe & Bedingungen", run: "Jetzt starten", skip: "Einmal überspringen",
    postpone: "Verschieben", add: "Lauf hinzufügen", edit: "Bearbeiten", remove: "Entfernen", save: "Lauf speichern", cancel: "Abbrechen",
    vacuum: "Roboter", schedule: "HA-Zeitplan-Helper", time: "Startzeit", weekdays: "Wochentage",
    condition: "Wenn jemand zu Hause ist", profile: "Reinigungsmodus", areas: "Räume / Segmente", passes: "Durchgänge",
    fan: "Saugstärke", water: "Wasserstufe", dayRun: "Lauf für", perDayHint: "Jeder Lauf speichert eigene Räume und Reinigungseinstellungen. Nutze das + am Wochentag für ein präzises Tagesprofil.",
    liveChoices: "Live-Auswahl des Roboters", unsupported: "Nicht unterstützte Einstellungen sind ausgeblendet",
    enabled: "Aktiviert", name: "Name des Laufs", nativeSchedule: "Nativer HA-Zeitplan", weeklySchedule: "Wochenplan",
    planner_enabled: "Planer und Lauf aktiviert", vacuum_available: "Roboter verfügbar", vacation_inactive: "Urlaubsmodus aus", vacation: "Urlaub",
    mop_attached: "Wischmodul eingesetzt", home_empty: "Niemand zu Hause", allow: "Trotzdem starten",
    wait: "Auf leeres Zuhause warten", skipPolicy: "Lauf auslassen", noConditions: "Keine zusätzlichen Bedingungen",
    configure: "Bitte die Planerstatus-Entität auswählen.", days: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
  },
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function icon(name, className = "") {
  return `<span class="icon-box ${className}"><ha-icon icon="${name}"></ha-icon></span>`;
}

const frameRequest = globalThis.requestAnimationFrame?.bind(globalThis)
  || ((callback) => globalThis.setTimeout(callback, 0));
const frameCancel = globalThis.cancelAnimationFrame?.bind(globalThis)
  || ((handle) => globalThis.clearTimeout(handle));

function domKey(node) {
  if (node?.nodeType !== 1) return "";
  const keys = [
    "data-mission-id", "data-id", "data-edit", "data-add-day", "data-action",
    "data-run", "data-remove", "data-mode-toggle", "data-add", "data-cancel",
    "name", "data-day",
  ];
  for (const name of keys) {
    if (node.hasAttribute?.(name)) return `${node.tagName}:${name}:${node.getAttribute(name)}`;
  }
  return "";
}

function syncAttributes(current, desired) {
  for (const attribute of [...(current.attributes || [])]) {
    if (!desired.hasAttribute(attribute.name)) current.removeAttribute(attribute.name);
  }
  for (const attribute of [...(desired.attributes || [])]) {
    if (current.getAttribute(attribute.name) !== attribute.value) {
      current.setAttribute(attribute.name, attribute.value);
    }
  }
}

function morphNode(current, desired, options = {}) {
  if (!current || !desired || current.nodeType !== desired.nodeType
      || (current.nodeType === 1 && current.tagName !== desired.tagName)) {
    const replacement = desired.cloneNode(true);
    current?.replaceWith?.(replacement);
    return replacement;
  }
  if (current.nodeType === 3) {
    if (current.nodeValue !== desired.nodeValue) current.nodeValue = desired.nodeValue;
    return current;
  }
  syncAttributes(current, desired);
  if (options.preserveEditor && current.matches?.("form[data-mission-form]")
      && current.getAttribute("data-id") === desired.getAttribute("data-id")) {
    return current;
  }

  const existing = [...current.childNodes];
  const keyed = new Map(existing.map((node) => [domKey(node), node]).filter(([key]) => key));
  const used = new Set();
  let position = 0;
  for (const desiredChild of [...desired.childNodes]) {
    const key = domKey(desiredChild);
    let candidate = key ? keyed.get(key) : existing[position];
    if (candidate && used.has(candidate)) candidate = undefined;
    if (candidate && (candidate.nodeType !== desiredChild.nodeType
        || (candidate.nodeType === 1 && candidate.tagName !== desiredChild.tagName))) {
      candidate = undefined;
    }
    if (!candidate) {
      candidate = desiredChild.cloneNode(true);
      current.insertBefore(candidate, current.childNodes[position] || null);
    } else {
      const reference = current.childNodes[position];
      if (reference !== candidate) current.insertBefore(candidate, reference || null);
      candidate = morphNode(candidate, desiredChild, options);
    }
    used.add(candidate);
    position += 1;
  }
  for (const child of [...current.childNodes].slice(position)) {
    if (!used.has(child)) child.remove();
  }
  return current;
}

function patchHost(host, markup, options = {}) {
  const template = document.createElement("template");
  // The lightweight Node contract runner has no HTML parser. Production HA
  // and browser regression tests always take the keyed morphing path.
  if (!template.content) {
    host.innerHTML = markup;
    return host.querySelector?.("ha-card,ha-badge");
  }
  template.innerHTML = markup;
  const desired = template.content.firstElementChild;
  const current = host.firstElementChild;
  if (!current) host.append(desired.cloneNode(true));
  else morphNode(current, desired, options);
  return host.firstElementChild;
}

class RobbieAdvancedCleaningCard extends HTMLElement {
  constructor() {
    super();
    this._renderFrame = null;
    this._lastRenderSignature = "";
    this._visibleRenderCount = 0;
  }

  static getConfigElement() { return document.createElement("robbie-advanced-cleaning-card-editor"); }

  static getStubConfig(hass) {
    const status = Object.values(hass?.states ?? {}).find((state) =>
      Array.isArray(state.attributes?.managed_vacuums));
    return { entry_id: status?.attributes?.entry_id, mode: "simple" };
  }

  setConfig(config) {
    if (!config) throw new Error("Card configuration is required");
    this._config = { mode: "simple", ...config };
    this._displayMode = this._config.mode === "advanced" ? "advanced" : "simple";
    this._lastRenderSignature = "";
    if (this._hass) this._scheduleRender();
  }

  connectedCallback() {
    const request = new Event("context-request", { bubbles: true, composed: true });
    Object.assign(request, {
      context: "hassApi", contextTarget: this, subscribe: false,
      callback: (api) => {
        this._callService = typeof api?.callService === "function" ? api.callService.bind(api) : undefined;
      },
    });
    this.dispatchEvent(request);
    // A freshly fingerprinted Lovelace resource can finish loading after HA
    // already created an unresolved custom-card element. HA then upgrades the
    // element without replaying setConfig/hass. Request one view rebuild only
    // for that narrow startup race; ordinary state renders never reach here.
    if (!this.shadowRoot && !globalThis.__robbieCardRecoveryRequested) {
      this._recoveryTimer = globalThis.setTimeout(() => {
        this._recoveryTimer = null;
        if (this.shadowRoot || !this.isConnected || globalThis.__robbieCardRecoveryRequested) return;
        const host = this.parentElement;
        const recoveredConfig = this._config || host?.config || host?._config;
        const recoveredHass = this._hass || document.querySelector("home-assistant")?.hass;
        if (!this._config && recoveredConfig) this.setConfig(recoveredConfig);
        if (!this._hass && recoveredHass) this.hass = recoveredHass;
        if (this._config && this._hass) this._render();
        if (this.shadowRoot) return;
        globalThis.__robbieCardRecoveryRequested = true;
        this.dispatchEvent(new Event("ll-rebuild", { bubbles: true, composed: true }));
      }, 250);
    }
  }

  disconnectedCallback() {
    if (this._renderFrame !== null) frameCancel(this._renderFrame);
    if (this._recoveryTimer != null) globalThis.clearTimeout(this._recoveryTimer);
    this._renderFrame = null;
    this._recoveryTimer = null;
  }

  set hass(value) {
    this._hass = value;
    if (!this._callService && typeof value?.callService === "function") this._callService = value.callService.bind(value);
    this._scheduleRender();
  }

  _scheduleRender() {
    if (this._renderFrame !== null) return;
    this._renderFrame = frameRequest(() => {
      this._renderFrame = null;
      this._commitRender();
    });
  }

  _render() {
    if (this._renderFrame !== null) frameCancel(this._renderFrame);
    this._renderFrame = null;
    this._commitRender();
  }

  getCardSize() { return this._displayMode === "advanced" ? 9 : 4; }
  _copy() { return COPY[this._hass?.language?.startsWith("de") ? "de" : "en"]; }
  _entity(id) { return id ? this._hass?.states?.[id] : undefined; }

  _plannerStatusEntry() {
    const configured = this._config?.status_entity;
    const configuredState = this._entity(configured);
    if (configuredState && Array.isArray(configuredState.attributes?.managed_vacuums)) {
      return [configured, configuredState];
    }
    const candidates = Object.entries(this._hass?.states ?? {}).filter(([id, state]) =>
      id.startsWith("sensor.") && Array.isArray(state.attributes?.managed_vacuums));
    const entryId = this._config?.entry_id;
    return candidates.find(([, state]) => !entryId || state.attributes?.entry_id === entryId)
      || candidates[0];
  }

  _plannerStatus() { return this._plannerStatusEntry()?.[1]; }

  _discover(suffix) {
    if (this._config?.[`${suffix}_entity`]) return this._config[`${suffix}_entity`];
    const entryId = this._plannerStatus()?.attributes?.entry_id;
    return Object.keys(this._hass?.states ?? {}).find((id) => {
      const state = this._hass.states[id];
      return id.startsWith("sensor.") && state.attributes?.entry_id === entryId &&
        (id.split(".", 2)[1]?.endsWith(suffix) || state.attributes?.translation_key === suffix);
    });
  }

  _viewModel(status, next, missions) {
    const visibleMission = (mission) => ({
      id: mission.id, name: mission.name, vacuum_entity_id: mission.vacuum_entity_id,
      weekdays: mission.weekdays || [], start_time: mission.start_time,
      schedule_entity_id: mission.schedule_entity_id || null, areas: mission.areas || [],
      profile: {
        mode: mission.profile?.mode || "vacuum", fan: mission.profile?.fan || null,
        water: mission.profile?.water || null, passes: mission.profile?.passes || 1,
      },
      all_conditions_met: mission.all_conditions_met, next_run: mission.next_run || null,
      conditions: (mission.conditions || []).map((condition) => ({
        key: condition.key, enabled: condition.enabled !== false,
        passed: Boolean(condition.passed),
        entity_name: condition.entity_name || "", entity_state: condition.entity_state,
      })),
    });
    const managed = (status?.attributes?.managed_vacuums || []).map((id) => ({
      id, name: this._entity(id)?.attributes?.friendly_name || id,
    }));
    const selectedVacuum = this._editingVacuumId
      || missions.find((mission) => mission.id === this._editingMissionId)?.vacuum_entity_id
      || managed[0]?.id;
    const options = this._editingMissionId
      ? status?.attributes?.profile_options?.[selectedVacuum] || {}
      : {};
    const choices = (items) => (items || []).map((item) => typeof item === "object"
      ? [String(item.value), String(item.label || item.value)] : [String(item), String(item)]);
    const schedules = this._editingMissionId
      ? Object.entries(this._hass?.states || {}).filter(([id]) => id.startsWith("schedule."))
        .map(([id, state]) => [id, state.attributes?.friendly_name || id])
      : [];
    return {
      language: this._hass?.language?.startsWith("de") ? "de" : "en",
      config: {
        entry_id: this._config?.entry_id || "", status_entity: this._config?.status_entity || "",
        title: this._config?.title || "", mode: this._config?.mode || "simple",
      },
      ui: {
        mode: this._displayMode, mission: this._editingMissionId || "",
        weekday: this._editingWeekday || "", vacuum: this._editingVacuumId || "",
        robotChanged: Boolean(this._editingRobotChanged),
      },
      status: status ? { state: status.state, entry_id: status.attributes?.entry_id || "" } : null,
      next: next ? {
        state: next.state, mission: next.attributes?.mission || "",
        mission_id: next.attributes?.mission_id || "",
        vacuum_entity_id: next.attributes?.vacuum_entity_id || "",
      } : null,
      managed,
      missions: missions.map(visibleMission),
      editor: this._editingMissionId ? {
        selectedVacuum,
        areas: choices(options.areas), modes: choices(options.modes),
        fan: choices(options.fan_speeds), water: choices(options.water_levels),
        passes: choices(options.passes),
        current: {
          mode: options.current?.mode || "", fan: options.current?.fan || "",
          water: options.current?.water || "", passes: options.current?.passes || "",
        },
        schedules,
        source: (() => {
          const mission = missions.find((item) => item.id === this._editingMissionId) || {};
          return {
            id: mission.id || "", name: mission.name || "",
            vacuum_entity_id: mission.vacuum_entity_id || "",
            weekdays: mission.weekdays || [], start_time: mission.start_time || "",
            schedule_entity_id: mission.schedule_entity_id || "", areas: mission.areas || [],
            enabled: mission.enabled !== false,
            profile: {
              mode: mission.profile?.mode || "", fan: mission.profile?.fan || "",
              water: mission.profile?.water || "", passes: mission.profile?.passes || "",
            },
            people_home: mission.guards?.people_home || "wait",
          };
        })(),
      } : null,
    };
  }

  async _call(service, data = {}) {
    const status = this._plannerStatus();
    const entryId = this._config?.entry_id || status?.attributes?.entry_id;
    if (!entryId || !this._callService) return;
    await this._callService(DOMAIN, service, { entry_id: entryId, ...data });
  }

  _date(value, short = false) {
    if (!value) return this._copy().noMission;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return this._copy().noMission;
    return new Intl.DateTimeFormat(this._hass?.language || "en", short
      ? { weekday: "short", hour: "2-digit", minute: "2-digit" }
      : { weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(date);
  }

  _statusInfo(status) {
    const state = status?.state || "unavailable";
    const map = {
      running: ["mdi:robot-vacuum", "active"], preparing: ["mdi:progress-wrench", "active"],
      waiting: ["mdi:account-clock-outline", "waiting"], blocked: ["mdi:shield-alert-outline", "danger"],
      failed: ["mdi:alert", "danger"], postponed: ["mdi:clock-plus-outline", "muted"],
      vacation: ["mdi:palm-tree", "vacation"],
      idle: ["mdi:robot-vacuum-variant", "calm"], completed: ["mdi:check-circle-outline", "calm"],
    };
    return { state, icon: (map[state] || ["mdi:robot-vacuum", "muted"])[0], tone: (map[state] || ["", "muted"])[1] };
  }

  _condition(condition, t) {
    const visible = condition.enabled !== false;
    if (!visible) return "";
    const label = t[condition.key] || condition.key;
    const entity = condition.entity_name
      ? ` · ${condition.entity_name}: ${condition.entity_state ?? "unknown"}` : "";
    return `<span class="condition ${condition.passed ? "passed" : "pending"}">
      ${icon(condition.passed ? "mdi:check-circle" : "mdi:clock-alert-outline", "condition-icon")}
      <span>${escapeHtml(label + entity)}</span>
    </span>`;
  }

  _simple(status, next, missions, t) {
    const info = this._statusInfo(status);
    const attrs = next?.attributes || {};
    const mission = missions.find((item) => item.id === attrs.mission_id) || missions[0];
    const conditions = (mission?.conditions || []).filter((item) => item.enabled !== false);
    const conditionsReady = !conditions.length || conditions.every((item) => item.passed);
    const vacuum = this._entity(attrs.vacuum_entity_id || mission?.vacuum_entity_id);
    const missionName = attrs.mission || mission?.name || t.noMission;
    const nextValue = next && !["unknown", "unavailable"].includes(next.state) ? next.state : mission?.next_run;
    return `<ha-card data-card-mode="simple" class="${info.tone}">
      <div class="easy-wrap">
        <div class="easy-header">
          <div class="heading"><div class="easy-brand">${escapeHtml(this._config.title || t.brand)}</div>
            <div class="easy-room">${escapeHtml(vacuum?.attributes?.friendly_name || missionName)}</div></div>
          <div class="easy-status">${icon(info.icon, "status-icon")}<span>${escapeHtml(t[info.state] || info.state)}</span></div>
        </div>
        <div class="easy-next">
          ${icon("mdi:calendar-clock", "next-icon")}
          <span class="easy-next-copy"><small>${escapeHtml(t.next)}</small><strong>${escapeHtml(missionName)}</strong><span>${escapeHtml(this._date(nextValue))}</span></span>
          <span class="condition-summary ${conditionsReady ? "passed" : "pending"}">${icon(conditionsReady ? "mdi:check-all" : "mdi:clock-alert-outline", "summary-icon")}<span>${escapeHtml(conditionsReady ? t.ready : t.blocked)}</span></span>
        </div>
        <div class="easy-actions">
          <button class="easy-action primary" data-action="run" ${info.state === "vacation" ? "disabled" : ""}>${icon("mdi:play", "action-icon")}<span>${escapeHtml(t.run)}</span></button>
          <button class="round" data-action="skip" title="${escapeHtml(t.skip)}">${icon("mdi:skip-next", "action-icon")}</button>
          <button class="round" data-action="postpone" title="${escapeHtml(t.postpone)}">${icon("mdi:clock-plus-outline", "action-icon")}</button>
          <button class="round advanced-button" data-mode-toggle title="${escapeHtml(t.advanced)}">${icon("mdi:tune-variant", "action-icon")}</button>
        </div>
      </div>
    </ha-card>`;
  }

  _week(missions, t) {
    return `<div class="week-grid">${DAYS.map((day, index) => {
      const entries = missions.filter((mission) => !mission.schedule_entity_id && mission.weekdays?.includes(day));
      return `<div class="week-day ${entries.length ? "active" : ""}"><strong>${t.days[index]}</strong>
        <div>${entries.map((mission) => {
          const profile = mission.profile || {};
          const detail = [profile.mode === "vacuum" ? "Vac" : profile.mode === "mop" ? "Mop" : "Vac+Mop", (mission.areas || [])[0]].filter(Boolean).join(" · ");
          return `<button data-edit="${escapeHtml(mission.id)}" title="${escapeHtml(`${mission.name} · ${detail}`)}"><b>${escapeHtml(mission.start_time || "—")}</b><small>${escapeHtml(detail)}</small></button>`;
        }).join("") || "<span>—</span>"}<button class="day-add" data-add-day="${day}" title="${escapeHtml(`${t.add} · ${t.days[index]}`)}">+</button></div></div>`;
    }).join("")}</div>`;
  }

  _missionCard(mission, t) {
    const vacuum = this._entity(mission.vacuum_entity_id);
    const profile = mission.profile || {};
    const conditions = (mission.conditions || []).filter((item) => item.enabled !== false);
    const scheduleText = mission.schedule_entity_id ? t.nativeSchedule :
      `${(mission.weekdays || []).map((day) => t.days[DAYS.indexOf(day)]).join(" · ")} · ${mission.start_time || "—"}`;
    return `<article data-mission-id="${escapeHtml(mission.id)}" class="mission ${mission.all_conditions_met ? "ready" : "pending"}">
      <div class="mission-head"><div><strong>${escapeHtml(mission.name)}</strong><small>${escapeHtml(scheduleText)}</small></div>
        <span class="mission-state">${icon(mission.all_conditions_met ? "mdi:check-circle" : "mdi:clock-alert-outline", "state-icon")}${escapeHtml(mission.all_conditions_met ? t.ready : t.blocked)}</span></div>
      <div class="mission-chips">
        <span>${icon("mdi:robot-vacuum", "chip-icon")}${escapeHtml(vacuum?.attributes?.friendly_name || mission.vacuum_entity_id)}</span>
        <span>${icon(profile.mode?.includes("mop") ? "mdi:water" : "mdi:fan", "chip-icon")}${escapeHtml([profile.mode, profile.fan, profile.water, profile.passes ? `${profile.passes}×` : ""].filter(Boolean).join(" · "))}</span>
        ${(mission.areas || []).length ? `<span>${icon("mdi:floor-plan", "chip-icon")}${escapeHtml(mission.areas.join(", "))}</span>` : ""}
      </div>
      <div class="conditions">${conditions.map((item) => this._condition(item, t)).join("") || `<span class="muted">${escapeHtml(t.noConditions)}</span>`}</div>
      <div class="mission-actions">
        <button data-run="${escapeHtml(mission.id)}" ${this._plannerStatus()?.state === "vacation" ? "disabled" : ""}>${icon("mdi:play", "mini-icon")}${escapeHtml(t.run)}</button>
        <button data-edit="${escapeHtml(mission.id)}">${icon("mdi:pencil", "mini-icon")}${escapeHtml(t.edit)}</button>
        <button data-remove="${escapeHtml(mission.id)}" class="danger-button">${icon("mdi:delete-outline", "mini-icon")}${escapeHtml(t.remove)}</button>
      </div>
    </article>`;
  }

  _editor(mission, status, t) {
    const value = mission || {};
    const profile = this._editingRobotChanged ? {} : value.profile || {};
    const guards = value.guards || {};
    const vacuums = status?.attributes?.managed_vacuums || [];
    const selectedVacuum = this._editingVacuumId || value.vacuum_entity_id || vacuums[0];
    const available = status?.attributes?.profile_options?.[selectedVacuum] || {};
    const detected = available.current || {};
    const schedules = Object.keys(this._hass?.states || {}).filter((id) => id.startsWith("schedule."));
    const defaultDays = this._editingWeekday ? [this._editingWeekday] : DAYS;
    const defaultName = this._editingWeekday ? `${t.dayRun} ${t.days[DAYS.indexOf(this._editingWeekday)]}` : "";
    const option = (item, selected) => `<option value="${escapeHtml(item)}" ${item === selected ? "selected" : ""}>${escapeHtml(this._entity(item)?.attributes?.friendly_name || item)}</option>`;
    const choices = (items, selected, saved = []) => {
      const normalized = (items || []).map((item) => typeof item === "object" ? item : { value: String(item), label: String(item) });
      for (const savedValue of saved || []) {
        if (savedValue != null && !normalized.some((item) => String(item.value) === String(savedValue))) {
          normalized.push({ value: String(savedValue), label: String(savedValue) });
        }
      }
      const selectedValues = Array.isArray(selected) ? selected.map(String) : [String(selected ?? "")];
      return normalized.map((item) => `<option value="${escapeHtml(item.value)}" ${selectedValues.includes(String(item.value)) ? "selected" : ""}>${escapeHtml(item.label || item.value)}</option>`).join("");
    };
    const selectedAreas = this._editingRobotChanged ? [] : value.areas || [];
    const selectedMode = profile.mode || detected.mode || available.modes?.[0]?.value || "vacuum";
    const selectedFan = profile.fan || detected.fan || "";
    const selectedWater = profile.water || detected.water || "";
    const selectedPasses = String(profile.passes || detected.passes || "1");
    return `<form class="mission-editor" data-mission-form data-id="${escapeHtml(value.id || "")}">
      <div class="form-head"><strong>${escapeHtml(value.id ? t.edit : t.add)}</strong><button type="button" class="round" data-cancel>${icon("mdi:close", "action-icon")}</button></div>
      <div class="form-grid">
        <label><span>${escapeHtml(t.name)}</span><input name="name" required value="${escapeHtml(value.name || defaultName)}"></label>
        <label><span>${escapeHtml(t.vacuum)}</span><select name="vacuum_entity_id" data-profile-vacuum required>${vacuums.map((id) => option(id, selectedVacuum)).join("")}</select></label>
        <label><span>${escapeHtml(t.time)}</span><input name="start_time" type="time" value="${escapeHtml(value.start_time || "09:00")}"></label>
        <label><span>${escapeHtml(t.schedule)}</span><select name="schedule_entity_id"><option value="">${escapeHtml(t.weeklySchedule)}</option>${schedules.map((id) => option(id, value.schedule_entity_id)).join("")}</select></label>
      </div>
      <fieldset><legend>${escapeHtml(t.weekdays)}</legend><div class="day-picker">${DAYS.map((day, index) => `<label class="day-choice"><input type="checkbox" data-day="${day}" ${(value.weekdays || defaultDays).includes(day) ? "checked" : ""}><span>${t.days[index]}</span></label>`).join("")}</div></fieldset>
      <div class="form-hint">${icon("mdi:calendar-edit", "mini-icon")}${escapeHtml(t.perDayHint)}</div>
      <div class="form-hint capability-hint">${icon("mdi:robot-vacuum", "mini-icon")}<span><strong>${escapeHtml(t.liveChoices)}</strong> · ${escapeHtml(this._entity(selectedVacuum)?.attributes?.friendly_name || selectedVacuum)} · ${escapeHtml(t.unsupported)}</span></div>
      <div class="form-grid profile-grid">
        <label><span>${escapeHtml(t.condition)}</span><select name="people_home"><option value="wait" ${guards.people_home === "wait" ? "selected" : ""}>${escapeHtml(t.wait)}</option><option value="allow" ${guards.people_home === "allow" ? "selected" : ""}>${escapeHtml(t.allow)}</option><option value="skip" ${guards.people_home === "skip" ? "selected" : ""}>${escapeHtml(t.skipPolicy)}</option></select></label>
        <label><span>${escapeHtml(t.profile)}</span><select name="profile_mode">${choices(available.modes, selectedMode, [selectedMode])}</select></label>
        ${(available.fan_speeds || []).length ? `<label><span>${escapeHtml(t.fan)}</span><select name="fan">${choices(available.fan_speeds, selectedFan, [selectedFan])}</select></label>` : ""}
        ${(available.water_levels || []).length ? `<label><span>${escapeHtml(t.water)}</span><select name="water">${choices(available.water_levels, selectedWater, [selectedWater])}</select></label>` : ""}
        <label><span>${escapeHtml(t.passes)}</span><select name="passes">${choices(available.passes || ["1", "2", "3"], selectedPasses, [selectedPasses])}</select></label>
        ${(available.areas || []).length || selectedAreas.length ? `<label><span>${escapeHtml(t.areas)}</span><select name="areas" multiple size="${Math.min(4, Math.max(2, (available.areas || []).length))}">${choices(available.areas, selectedAreas, selectedAreas)}</select></label>` : ""}
        <label class="enabled-choice"><span>${escapeHtml(t.enabled)}</span><input name="enabled" type="checkbox" ${value.enabled !== false ? "checked" : ""}></label>
      </div>
      <div class="form-actions"><button type="submit" class="save">${icon("mdi:content-save", "mini-icon")}${escapeHtml(t.save)}</button><button type="button" data-cancel>${escapeHtml(t.cancel)}</button></div>
    </form>`;
  }

  _advanced(status, missions, t) {
    const info = this._statusInfo(status);
    const passed = missions.reduce((count, mission) => count + (mission.conditions || []).filter((item) => item.enabled && item.passed).length, 0);
    const total = missions.reduce((count, mission) => count + (mission.conditions || []).filter((item) => item.enabled).length, 0);
    const editing = this._editingMissionId === "new" ? {} : missions.find((item) => item.id === this._editingMissionId);
    return `<ha-card data-card-mode="advanced" class="${info.tone}"><div class="advanced-wrap">
      <div class="advanced-header"><div><div class="title">${escapeHtml(this._config.title || t.title)}</div><div class="subtitle">${escapeHtml(t.advanced)} · ${missions.length} ${escapeHtml(t.missions)}</div></div>
        <div class="mode-pill">${icon(info.icon, "status-icon")}<span>${escapeHtml(t[info.state] || info.state)}</span></div></div>
      <div class="overview-chips"><span>${icon("mdi:robot-vacuum", "chip-icon")}${status?.attributes?.managed_vacuums?.length || 0}</span><span>${icon("mdi:calendar-check", "chip-icon")}${missions.length}</span><span class="${passed === total ? "good" : "warn"}">${icon(passed === total ? "mdi:check-all" : "mdi:clock-alert-outline", "chip-icon")}${passed}/${total}</span></div>
      <section><div class="section-title"><strong>${escapeHtml(t.weekly)}</strong><button class="round" data-add title="${escapeHtml(t.add)}">${icon("mdi:plus", "action-icon")}</button></div>${this._week(missions, t)}</section>
      <section><div class="section-title"><strong>${escapeHtml(t.missions)}</strong></div><div class="mission-list">${missions.map((mission) => this._missionCard(mission, t)).join("") || `<div class="empty">${escapeHtml(t.noMission)}</div>`}</div></section>
      ${this._editingMissionId ? this._editor(editing, status, t) : ""}
      <div class="advanced-footer"><button class="round" data-mode-toggle title="${escapeHtml(t.simple)}">${icon("mdi:view-dashboard-outline", "action-icon")}</button><button class="advanced-add" data-add>${icon("mdi:plus", "mini-icon")}${escapeHtml(t.add)}</button></div>
    </div></ha-card>`;
  }

  async _saveForm(form) {
    const data = Object.fromEntries(new FormData(form).entries());
    const status = this._plannerStatus();
    const missions = status?.attributes?.missions || [];
    const existing = missions.find((item) => item.id === form.dataset.id) || {};
    const weekdays = [...form.querySelectorAll("[data-day]:checked")].map((item) => item.dataset.day);
    const id = existing.id || globalThis.crypto?.randomUUID?.().replaceAll("-", "") || `run_${Date.now()}`;
    const mission = {
      ...existing, id, name: data.name, vacuum_entity_id: data.vacuum_entity_id,
      weekdays, start_time: data.start_time || "09:00", schedule_entity_id: data.schedule_entity_id || null,
      areas: [...form.querySelectorAll('[name="areas"] option:checked')].map((item) => item.value), enabled: data.enabled === "on",
      profile: { ...(existing.profile || {}), mode: data.profile_mode || "vacuum", fan: data.fan || null, water: data.profile_mode === "vacuum" ? null : data.water || null, passes: Number(data.passes || 1) },
      guards: { ...(existing.guards || {}), people_home: data.people_home || "wait" },
    };
    await this._call("add_mission", { mission });
    this._editingMissionId = null;
    this._editingWeekday = null;
    this._editingVacuumId = null;
    this._editingRobotChanged = false;
    this._render();
  }

  _bind() {
    const root = this.shadowRoot;
    if (this._interactionRoot === root) return;
    this._interactionRoot = root;
    root.addEventListener("click", (event) => {
      const control = event.composedPath?.().find((item) => item?.matches?.("button"));
      if (!control) return;
      event.preventDefault?.();
      event.stopPropagation?.();
      if (control.matches('[data-action="run"]')) return void this._call("run_next");
      if (control.matches('[data-action="skip"]')) return void this._call("skip_next");
      if (control.matches('[data-action="postpone"]')) return void this._call("postpone_next", { minutes: 60 });
      if (control.matches("[data-mode-toggle]")) {
        this._displayMode = this._displayMode === "advanced" ? "simple" : "advanced";
        this._editingMissionId = null;
        return void this._render();
      }
      if (control.matches("[data-add]")) {
        this._editingMissionId = "new";
        this._editingWeekday = null;
        this._editingVacuumId = null;
        this._editingRobotChanged = false;
        return void this._render();
      }
      if (control.matches("[data-add-day]")) {
        this._editingMissionId = "new";
        this._editingWeekday = control.dataset.addDay;
        this._editingVacuumId = null;
        this._editingRobotChanged = false;
        return void this._render();
      }
      if (control.matches("[data-edit]")) {
        this._editingMissionId = control.dataset.edit;
        this._editingVacuumId = null;
        this._editingRobotChanged = false;
        return void this._render();
      }
      if (control.matches("[data-run]")) return void this._call("run_next", { mission_id: control.dataset.run });
      if (control.matches("[data-remove]")) return void this._call("remove_mission", { mission_id: control.dataset.remove });
      if (control.matches("[data-cancel]")) {
        this._editingMissionId = null;
        this._editingWeekday = null;
        this._editingVacuumId = null;
        this._editingRobotChanged = false;
        return void this._render();
      }
    });
    root.addEventListener("change", (event) => {
      if (!event.target?.matches?.("[data-profile-vacuum]")) return;
      event.stopPropagation?.();
      this._editingVacuumId = event.target.value;
      this._editingRobotChanged = true;
      this._refreshEditor = true;
      this._render();
    });
    root.addEventListener("submit", (event) => {
      if (!event.target?.matches?.("[data-mission-form]")) return;
      event.preventDefault();
      event.stopPropagation?.();
      this._saveForm(event.target);
    });
  }

  _styles() {
    return `<style>
      :host{display:block;width:100%;min-width:0;font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif);container-type:inline-size;container-name:robbie-card}[data-card-host]{display:contents}*{box-sizing:border-box;min-width:0}
      ha-card{width:100%;overflow:hidden;border-radius:22px;border:1px solid rgba(255,255,255,.09);box-shadow:none;background:var(--ha-card-background,var(--card-background-color,#202020));color:var(--primary-text-color,#fff)}ha-card.active{background:linear-gradient(135deg,rgba(32,184,154,.16),rgba(24,34,31,.97))}ha-card.waiting{background:linear-gradient(135deg,rgba(242,169,59,.18),rgba(34,30,24,.97))}ha-card.vacation{background:linear-gradient(135deg,rgba(126,87,194,.25),rgba(29,25,39,.97))}ha-card.danger{background:linear-gradient(135deg,rgba(238,91,100,.23),rgba(36,24,26,.97))}
      .icon-box{width:18px;height:18px;display:grid;place-items:center;flex:0 0 18px;line-height:0}.icon-box>ha-icon{--mdc-icon-size:16px}.status-icon{width:17px;height:17px}.status-icon>ha-icon{--mdc-icon-size:15px}.chip-icon,.mini-icon,.condition-icon{width:15px;height:15px}.chip-icon>ha-icon,.mini-icon>ha-icon,.condition-icon>ha-icon{--mdc-icon-size:13px}.next-icon{width:34px;height:34px}.next-icon>ha-icon{--mdc-icon-size:27px}.action-icon>ha-icon{--mdc-icon-size:16px}
      button,input,select{font:inherit}.easy-wrap,.advanced-wrap{padding:16px;display:grid;gap:12px}.easy-header,.advanced-header{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.easy-brand{font-size:9px;font-weight:850;letter-spacing:.12em;text-transform:uppercase;opacity:.45}.easy-room,.title{margin-top:3px;font-size:19px;font-weight:850;line-height:1.08;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.subtitle{font-size:10px;opacity:.56;margin-top:4px}.easy-status,.mode-pill{height:30px;max-width:48%;display:inline-flex;align-items:center;gap:6px;padding:0 10px;border-radius:999px;background:rgba(255,255,255,.085);font-size:10px;font-weight:850;text-transform:uppercase;white-space:nowrap}
      .easy-next{position:relative;border-radius:17px;padding:11px 12px;background:rgba(255,255,255,.048);display:grid;grid-template-columns:34px minmax(0,1fr) auto;align-items:center;gap:10px}.easy-next-copy{display:grid;gap:1px}.easy-next-copy small{font-size:9px;text-transform:uppercase;letter-spacing:.08em;opacity:.48}.easy-next-copy strong{font-size:12px}.easy-next-copy>span{font-size:10px;opacity:.62}.condition-summary{display:inline-flex;align-items:center;gap:5px;font-size:9px;font-weight:760;padding:6px 8px;border-radius:999px;background:rgba(255,255,255,.07)}.condition-summary.passed{color:var(--success-color,#4caf50)}.condition-summary.pending{color:var(--warning-color,#f2a93b)}
      .easy-actions,.advanced-footer{display:flex;align-items:center;justify-content:flex-end;gap:7px}.easy-action,.advanced-add,.mission-actions button,.form-actions button{height:36px;border:0;border-radius:12px;padding:0 11px;display:inline-flex;align-items:center;justify-content:center;gap:6px;background:rgba(255,255,255,.075);color:inherit;font-size:10px;font-weight:760;cursor:pointer}.easy-action.primary,.advanced-add,.form-actions .save{background:var(--primary-color,#41bdf5);color:var(--text-primary-color,#fff)}button:disabled{opacity:.38;cursor:not-allowed}.round{width:36px;height:36px;border:0;border-radius:50%;display:grid;place-items:center;background:rgba(255,255,255,.075);color:inherit;cursor:pointer;padding:0}.round:hover,.mission-actions button:hover{background:rgba(255,255,255,.14)}
      .overview-chips,.mission-chips{display:flex;flex-wrap:wrap;gap:6px}.overview-chips>span,.mission-chips>span{min-height:26px;display:inline-flex;align-items:center;gap:5px;padding:4px 8px;border-radius:999px;background:rgba(255,255,255,.065);font-size:10px}.overview-chips .good{color:var(--success-color,#4caf50)}.overview-chips .warn{color:var(--warning-color,#f2a93b)}section{display:grid;gap:8px}.section-title{display:flex;align-items:center;justify-content:space-between}.section-title>strong{font-size:13px}
      .week-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px}.week-day{min-height:79px;padding:7px 4px;border-radius:12px;background:rgba(255,255,255,.028);text-align:center}.week-day.active{background:rgba(65,189,245,.08)}.week-day>strong{font-size:9px;text-transform:uppercase;opacity:.55}.week-day>div{display:grid;gap:3px;margin-top:5px}.week-day button{border:0;border-radius:9px;padding:4px 3px;background:rgba(65,189,245,.16);color:inherit;font-size:8px;cursor:pointer;display:grid;gap:1px}.week-day button b{font-size:8px}.week-day button small{font-size:7px;opacity:.62;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.week-day span{font-size:9px;opacity:.25}.week-day .day-add{width:20px;height:20px;margin:2px auto 0;border-radius:50%;padding:0;display:grid;place-items:center;background:rgba(255,255,255,.06);font-size:12px}
      .mission-list{display:grid;gap:7px}.mission{padding:11px;border-radius:15px;background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.045);display:grid;gap:9px}.mission.pending{border-color:rgba(242,169,59,.24)}.mission-head{display:flex;justify-content:space-between;gap:10px}.mission-head>div{display:grid;gap:2px}.mission-head strong{font-size:12px}.mission-head small{font-size:9px;opacity:.58}.mission-state{display:inline-flex;align-items:center;gap:4px;font-size:9px;white-space:nowrap}.mission.ready .mission-state{color:var(--success-color,#4caf50)}.mission.pending .mission-state{color:var(--warning-color,#f2a93b)}.conditions{display:flex;flex-wrap:wrap;gap:5px}.condition{display:inline-flex;align-items:center;gap:4px;padding:5px 7px;border-radius:999px;background:rgba(255,255,255,.05);font-size:9px}.condition.passed{color:var(--success-color,#4caf50)}.condition.pending{color:var(--warning-color,#f2a93b)}.muted,.empty{font-size:10px;opacity:.52}.mission-actions{display:flex;justify-content:flex-end;gap:6px}.mission-actions button{height:30px;border-radius:10px}.mission-actions .danger-button{color:var(--error-color,#ee5b64)}
      .mission-editor{padding:13px;border-radius:17px;background:rgba(255,255,255,.045);display:grid;gap:12px}.form-head{display:flex;align-items:center;justify-content:space-between}.form-head>strong{font-size:13px}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.form-grid label{display:grid;gap:5px}.form-grid label>span,fieldset legend{font-size:9px;text-transform:uppercase;letter-spacing:.06em;opacity:.55}.form-grid input,.form-grid select{width:100%;height:36px;border:1px solid rgba(255,255,255,.10);border-radius:10px;padding:0 9px;background:rgba(0,0,0,.14);color:inherit}.form-grid select[multiple]{height:auto;min-height:72px;padding:5px 7px}.form-grid select[multiple] option{padding:5px 4px;border-radius:5px}fieldset{margin:0;padding:0;border:0;display:grid;gap:7px}.day-picker{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}.day-choice input{position:absolute;opacity:0}.day-choice span{height:31px;display:grid;place-items:center;border-radius:9px;background:rgba(255,255,255,.045);font-size:9px;cursor:pointer}.day-choice input:checked+span{background:rgba(65,189,245,.20);color:var(--primary-color,#41bdf5);font-weight:800}.form-hint{display:flex;align-items:flex-start;gap:6px;font-size:9px;line-height:1.4;opacity:.62}.capability-hint{padding:8px;border-radius:10px;background:rgba(65,189,245,.08);color:var(--primary-color,#41bdf5);opacity:1}.enabled-choice{grid-template-columns:1fr auto!important;align-items:center}.enabled-choice input{width:20px!important;height:20px!important}.form-actions{display:flex;justify-content:flex-end;gap:7px}
      @container robbie-card (max-width:520px){.easy-wrap,.advanced-wrap{padding:13px}.condition-summary span:last-child{display:none}.easy-next{grid-template-columns:30px minmax(0,1fr) auto}.week-grid{gap:3px}.week-day{padding:6px 2px}.form-grid{grid-template-columns:1fr}.mission-state{font-size:0}.mission-state .icon-box{display:grid}.mission-actions button{font-size:0;padding:0;width:30px}.mission-actions .icon-box{margin:0}.profile-grid{grid-template-columns:1fr 1fr}.easy-room,.title{font-size:17px}}
    </style>`;
  }

  _ensureShell() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    if (this._mount) return;
    this.shadowRoot.innerHTML = `${this._styles()}<div data-card-host></div>`;
    this._mount = this.shadowRoot.querySelector("[data-card-host]");
    this._bind();
  }

  _commitRender() {
    if (!this._config || !this._hass) return;
    this._ensureShell();
    const t = this._copy();
    const status = this._plannerStatus();
    const next = status ? this._entity(this._discover("next_mission")) : undefined;
    const missions = Array.isArray(status?.attributes?.missions) ? status.attributes.missions : [];
    const signature = JSON.stringify(this._viewModel(status, next, missions));
    if (signature === this._lastRenderSignature) return;
    this._lastRenderSignature = signature;
    const preserveEditor = Boolean(this._editingMissionId) && !this._refreshEditor;
    this._refreshEditor = false;
    let content;
    if (!status) {
      content = `<ha-card><div class="empty-card">${escapeHtml(t.configure)}</div></ha-card>`;
    } else {
      content = this._displayMode === "advanced"
        ? this._advanced(status, missions, t) : this._simple(status, next, missions, t);
    }
    this._cardRoot = patchHost(this._mount, content, { preserveEditor });
    this._visibleRenderCount += 1;
  }
}

class RobbieAdvancedCleaningCardEditor extends HTMLElement {
  setConfig(config) { this._config = { mode: "simple", ...config }; this._render(); }
  set hass(value) { this._hass = value; this._render(); }
  _emit(key, value) {
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: { ...this._config, [key]: value } }, bubbles: true, composed: true }));
  }
  _render() {
    if (!this._hass || !this._config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const sensors = Object.keys(this._hass.states).filter((id) => id.startsWith("sensor.") && Array.isArray(this._hass.states[id]?.attributes?.managed_vacuums));
    this.shadowRoot.innerHTML = `<div class="editor"><label>Planner status<select data-status><option value="">Automatic from setup</option>${sensors.map((id) => `<option value="${escapeHtml(id)}" ${id === this._config.status_entity ? "selected" : ""}>${escapeHtml(id)}</option>`).join("")}</select></label><label>Default mode<select data-mode><option value="simple" ${this._config.mode !== "advanced" ? "selected" : ""}>Simple</option><option value="advanced" ${this._config.mode === "advanced" ? "selected" : ""}>Advanced</option></select></label></div><style>.editor{display:grid;gap:14px;padding:16px}label{display:grid;gap:6px}select{padding:10px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color)}</style>`;
    this.shadowRoot.querySelector("[data-status]")?.addEventListener("change", (event) => this._emit("status_entity", event.target.value));
    this.shadowRoot.querySelector("[data-mode]")?.addEventListener("change", (event) => this._emit("mode", event.target.value));
  }
}

class RobbieVacuumBadge extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this._lastRenderSignature = "";
    this._renderFrame = null;
    this._visibleRenderCount = 0;
  }

  static async getConfigElement() { return document.createElement("robbie-vacuum-badge-editor"); }
  static getStubConfig(hass) {
    const status = Object.values(hass?.states ?? {}).find((state) =>
      Array.isArray(state.attributes?.managed_vacuums));
    return { entry_id: status?.attributes?.entry_id, navigation_path: "/lovelace/cleaning" };
  }

  setConfig(config = {}) {
    if (!config || typeof config !== "object") throw new Error("Badge configuration must be an object");
    this._config = { navigation_path: "/lovelace/cleaning", ...config };
    this._lastRenderSignature = "";
    if (this._hass) this._scheduleRender();
  }

  set hass(hass) {
    this._hass = hass;
    this._scheduleRender();
  }

  disconnectedCallback() {
    if (this._renderFrame !== null) frameCancel(this._renderFrame);
    this._renderFrame = null;
  }

  _scheduleRender() {
    if (this._renderFrame !== null) return;
    this._renderFrame = frameRequest(() => {
      this._renderFrame = null;
      this._commitRender();
    });
  }

  _render() {
    if (this._renderFrame !== null) frameCancel(this._renderFrame);
    this._renderFrame = null;
    this._commitRender();
  }

  _status() {
    const configured = this._hass?.states?.[this._config?.status_entity];
    if (configured && Array.isArray(configured.attributes?.managed_vacuums)) return configured;
    const candidates = Object.values(this._hass?.states ?? {}).filter((state) =>
      Array.isArray(state.attributes?.managed_vacuums));
    const entryId = this._config?.entry_id;
    const vacuumEntityId = this._config?.vacuum_entity;
    return candidates.find((state) => entryId && state.attributes?.entry_id === entryId)
      || candidates.find((state) => vacuumEntityId && state.attributes.managed_vacuums.includes(vacuumEntityId))
      || candidates[0];
  }

  _vacuumEntityId(status = this._status()) {
    const configured = this._config?.vacuum_entity;
    if (configured && this._hass?.states?.[configured]) return configured;
    const managed = status?.attributes?.managed_vacuums || [];
    return managed.find((id) => this._hass?.states?.[id])
      || Object.keys(this._hass?.states ?? {}).find((id) => id.startsWith("vacuum."))
      || configured;
  }

  _stateOverride() {
    const value = this._hass?.states?.[this._config?.state_override_entity]?.state;
    return ["docked", "idle", "cleaning", "returning", "paused", "waiting", "vacation", "error", "unavailable"].includes(value) ? value : "";
  }

  _navigate() {
    const path = this._config?.navigation_path;
    if (!path) return;
    if (window.history?.pushState) window.history.pushState(null, "", path);
    if (typeof window.dispatchEvent === "function") window.dispatchEvent(new CustomEvent("location-changed"));
  }

  _bindInteraction() {
    const badge = this.shadowRoot?.querySelector?.("ha-badge");
    if (!badge || !this._vacuumEntityId()) return;
    if (this._interactionBadge === badge) return;
    this._interactionBadge = badge;
    badge.addEventListener?.("click", (event) => {
      event.stopPropagation?.();
      this._navigate();
    });
    badge.addEventListener?.("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault?.();
      this._navigate();
    });
  }

  _labels() {
    const de = String(this._hass?.language || "en").toLowerCase().startsWith("de");
    const states = de ? {
      docked: "In Station", idle: "Schläft", cleaning: "Reinigt", returning: "Rückfahrt",
      paused: "Pausiert", waiting: "Wartet", vacation: "Urlaub", error: "Fehler", unavailable: "Nicht verfügbar",
    } : {
      docked: "Docked", idle: "Sleeping", cleaning: "Cleaning", returning: "Returning",
      paused: "Paused", waiting: "Waiting", vacation: "Vacation", error: "Error", unavailable: "Unavailable",
    };
    return de
      ? { states, next: "Nächster Start", choose: "Saugroboter auswählen" }
      : { states, next: "Next run", choose: "Select a vacuum" };
  }

  _stateIcon(state) {
    return ({
      docked: "mdi:home", idle: "mdi:power-sleep", cleaning: "mdi:play",
      returning: "mdi:home-import-outline", paused: "mdi:pause",
      waiting: "mdi:account-clock-outline", vacation: "mdi:palm-tree", error: "mdi:alert",
      unavailable: "mdi:alert-circle-outline",
    })[state] || "mdi:information-outline";
  }

  _color(state) {
    return ({
      cleaning: "var(--success-color,var(--green-color,#4caf50))",
      returning: "var(--info-color,var(--primary-color,#039be5))",
      paused: "var(--info-color,var(--primary-color,#039be5))",
      waiting: "var(--warning-color,var(--amber-color,#f2a93b))",
      vacation: "var(--purple-color,#7e57c2)",
      error: "var(--error-color,var(--red-color,#db4437))",
      unavailable: "var(--error-color,var(--red-color,#db4437))",
    })[state] || "var(--state-inactive-color,var(--secondary-text-color,#727272))";
  }

  _formatTime(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat(this._hass?.language || "en", { hour: "2-digit", minute: "2-digit" }).format(date);
  }

  _badgeStyles() {
    return `<style>
      :host{display:block;width:var(--ha-badge-size,36px);height:var(--ha-badge-size,36px)}
      [data-badge-host]{display:contents}
      .badge-symbol{position:relative;display:grid;place-items:center;width:22px;height:22px;color:var(--badge-color)}
      .next-time{position:absolute;left:50%;bottom:-1px;transform:translateX(-50%);font-size:6px;font-weight:850;line-height:1;letter-spacing:-.05em;white-space:nowrap;color:var(--badge-color)}
      .state-marker{position:absolute;right:-4px;bottom:-4px;display:grid;place-items:center;width:12px;height:12px;border-radius:50%;background:var(--ha-card-background,var(--card-background-color,#fff));box-shadow:0 0 0 1px var(--ha-card-border-color,var(--divider-color,#ddd));color:var(--badge-color)}
      .state-marker ha-icon{--mdc-icon-size:9px}
    </style>`;
  }

  _ensureShell() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    if (this._mount) return;
    this.shadowRoot.innerHTML = `${this._badgeStyles()}<span data-badge-host></span>`;
    this._mount = this.shadowRoot.querySelector("[data-badge-host]");
  }

  _badgeViewModel() {
    const status = this._status();
    const vacuumEntityId = this._vacuumEntityId(status);
    const vacuum = this._hass?.states?.[vacuumEntityId];
    const waiting = status?.attributes?.waiting_vacuums?.includes(vacuumEntityId);
    const vacation = status?.state === "vacation" || status?.attributes?.vacation_active === true;
    const raw = vacuum?.state || "unavailable";
    const state = vacation ? "vacation" : this._stateOverride() || (waiting ? "waiting" : raw);
    const nextRun = status?.attributes?.next_runs?.[vacuumEntityId];
    return {
      language: String(this._hass?.language || "en").toLowerCase().startsWith("de") ? "de" : "en",
      vacuumEntityId: vacuumEntityId || "", available: Boolean(vacuum), state,
      name: this._config.name || vacuum?.attributes?.friendly_name || vacuumEntityId || "",
      nextScheduled: nextRun?.scheduled || "", nextMission: nextRun?.mission || "",
      navigation: this._config.navigation_path || "",
    };
  }

  _commitRender() {
    if (!this._config || !this._hass) return;
    this._ensureShell();
    const view = this._badgeViewModel();
    const signature = JSON.stringify(view);
    if (signature === this._lastRenderSignature) return;
    this._lastRenderSignature = signature;
    const L = this._labels();
    if (!view.available) {
      const tooltip = L.choose;
      this._badgeRoot = patchHost(this._mount, `
        <ha-badge icon-only data-mode="unavailable" title="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}" style="--badge-color:var(--error-color,var(--red-color,#db4437))">
          <span slot="icon" class="badge-symbol">
            <ha-icon class="robot-symbol" style="--mdc-icon-size:20px" icon="mdi:robot-vacuum"></ha-icon>
            <span class="state-marker"><ha-icon icon="mdi:alert-circle-outline"></ha-icon></span>
          </span>
        </ha-badge>`);
      this._bindInteraction();
      this._visibleRenderCount += 1;
      return;
    }
    const state = view.state;
    const time = this._formatTime(view.nextScheduled);
    const label = L.states[state] || state;
    const tooltip = [view.name, label, time ? `${L.next} ${time}` : "", view.nextMission].filter(Boolean).join(" · ");
    const showTime = state === "docked" && Boolean(time);
    this._badgeRoot = patchHost(this._mount, `
      <ha-badge type="button" icon-only data-mode="${escapeHtml(state)}" title="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}">
        <span slot="icon" class="badge-symbol">
          <ha-icon class="robot-symbol" style="--mdc-icon-size:${showTime ? "15px" : "20px"};${showTime ? "transform:translateY(-3px)" : ""}" icon="mdi:robot-vacuum${state === "docked" ? "-variant" : ""}"></ha-icon>
          ${showTime ? `<small class="next-time">${escapeHtml(time)}</small>` : ""}
          <span class="state-marker"><ha-icon icon="${escapeHtml(this._stateIcon(state))}"></ha-icon></span>
        </span>
      </ha-badge>`);
    this._badgeRoot.style?.setProperty?.("--badge-color", this._color(state));
    this._bindInteraction();
    this._visibleRenderCount += 1;
  }
}

class RobbieVacuumBadgeEditor extends HTMLElement {
  setConfig(config) { this._config = { navigation_path: "/lovelace/cleaning", ...config }; this._render(); }
  set hass(value) { this._hass = value; this._render(); }
  _emit(key, value) { this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: { ...this._config, [key]: value } }, bubbles: true, composed: true })); }
  _render() {
    if (!this._hass || !this._config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const vacuums = Object.keys(this._hass.states).filter((id) => id.startsWith("vacuum."));
    const statuses = Object.keys(this._hass.states).filter((id) => id.startsWith("sensor.") && Array.isArray(this._hass.states[id]?.attributes?.managed_vacuums));
    const overrides = Object.keys(this._hass.states).filter((id) => id.startsWith("input_select.") || id.startsWith("select."));
    const options = (items, selected) => items.map((id) => `<option value="${escapeHtml(id)}" ${id === selected ? "selected" : ""}>${escapeHtml(this._hass.states[id]?.attributes?.friendly_name || id)}</option>`).join("");
    this.shadowRoot.innerHTML = `<div class="editor"><label>Vacuum<select data-vacuum><option value="">Automatic from setup</option>${options(vacuums, this._config.vacuum_entity)}</select></label><label>Planner status<select data-status><option value="">Automatic from setup</option>${options(statuses, this._config.status_entity)}</select></label><label>State override (optional)<select data-override><option value="">Live robot state</option>${options(overrides, this._config.state_override_entity)}</select></label><label>Navigation path<input data-path value="${escapeHtml(this._config.navigation_path)}"></label><small>Card and Badge automatically use the entities selected in the setup assistant. Choose a robot only when this planner manages several robots.</small></div><style>.editor{display:grid;gap:13px;padding:16px}label{display:grid;gap:6px}select,input{padding:10px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color)}small{opacity:.58}</style>`;
    this.shadowRoot.querySelector("[data-vacuum]")?.addEventListener("change", (event) => this._emit("vacuum_entity", event.target.value));
    this.shadowRoot.querySelector("[data-status]")?.addEventListener("change", (event) => this._emit("status_entity", event.target.value));
    this.shadowRoot.querySelector("[data-override]")?.addEventListener("change", (event) => this._emit("state_override_entity", event.target.value || undefined));
    this.shadowRoot.querySelector("[data-path]")?.addEventListener("change", (event) => this._emit("navigation_path", event.target.value));
  }
}

if (!customElements.get("robbie-advanced-cleaning-card")) customElements.define("robbie-advanced-cleaning-card", RobbieAdvancedCleaningCard);
if (!customElements.get("robbie-advanced-cleaning-card-editor")) customElements.define("robbie-advanced-cleaning-card-editor", RobbieAdvancedCleaningCardEditor);
if (!customElements.get("robbie-vacuum-badge")) customElements.define("robbie-vacuum-badge", RobbieVacuumBadge);
if (!customElements.get("robbie-vacuum-badge-editor")) customElements.define("robbie-vacuum-badge-editor", RobbieVacuumBadgeEditor);

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "robbie-advanced-cleaning-card")) window.customCards.push({ type: "robbie-advanced-cleaning-card", name: "Robbie Advanced Cleaning Control", description: "Simple and Advanced robot cleaning planner", preview: true });
window.customBadges = window.customBadges || [];
if (!window.customBadges.some((badge) => badge.type === "robbie-vacuum-badge")) window.customBadges.push({ type: "robbie-vacuum-badge", name: "Robbie Vacuum Status", description: "Native round robot badge with live state marker and next run", preview: true, documentationURL: "https://github.com/MrCharly169/robbie-advanced-cleaning-control" });
