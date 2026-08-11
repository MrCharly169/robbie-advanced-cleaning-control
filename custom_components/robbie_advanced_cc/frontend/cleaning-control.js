const DOMAIN = "robbie_advanced_cc";
const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

const COPY = {
  en: {
    brand: "Robbie Advanced CC", title: "Cleaning Planner", simple: "Simple", advanced: "Advanced",
    next: "Next run", noMission: "No run planned", ready: "All conditions met", blocked: "Conditions pending",
    weekly: "Weekly runs", missions: "Runs & conditions", run: "Run now", skip: "Skip once",
    postpone: "Postpone", add: "Add run", edit: "Edit", remove: "Remove", save: "Save run", cancel: "Cancel",
    vacuum: "Robot", schedule: "HA Schedule helper", time: "Start time", weekdays: "Weekdays",
    condition: "When somebody is home", profile: "Cleaning profile", areas: "Areas", passes: "Passes",
    enabled: "Enabled", name: "Run name", nativeSchedule: "Native HA schedule", weeklySchedule: "Weekly schedule",
    planner_enabled: "Planner and run enabled", vacuum_available: "Robot available", vacation_inactive: "Vacation mode off",
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
    condition: "Wenn jemand zu Hause ist", profile: "Reinigungsprofil", areas: "Bereiche", passes: "Durchgänge",
    enabled: "Aktiviert", name: "Name des Laufs", nativeSchedule: "Nativer HA-Zeitplan", weeklySchedule: "Wochenplan",
    planner_enabled: "Planer und Lauf aktiviert", vacuum_available: "Roboter verfügbar", vacation_inactive: "Urlaubsmodus aus",
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

class RobbieAdvancedCleaningCard extends HTMLElement {
  static getConfigElement() { return document.createElement("robbie-advanced-cleaning-card-editor"); }

  static getStubConfig(hass) {
    const status = Object.keys(hass?.states ?? {}).find((id) =>
      id.startsWith("sensor.") && Array.isArray(hass.states[id]?.attributes?.managed_vacuums));
    return { status_entity: status, mode: "simple" };
  }

  setConfig(config) {
    if (!config) throw new Error("Card configuration is required");
    this._config = { mode: "simple", ...config };
    this._displayMode = this._config.mode === "advanced" ? "advanced" : "simple";
    this._render();
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
  }

  set hass(value) {
    this._hass = value;
    if (!this._callService && typeof value?.callService === "function") this._callService = value.callService.bind(value);
    this._render();
  }

  getCardSize() { return this._displayMode === "advanced" ? 9 : 4; }
  _copy() { return COPY[this._hass?.language?.startsWith("de") ? "de" : "en"]; }
  _entity(id) { return id ? this._hass?.states?.[id] : undefined; }

  _discover(suffix) {
    if (this._config?.[`${suffix}_entity`]) return this._config[`${suffix}_entity`];
    const entryId = this._entity(this._config?.status_entity)?.attributes?.entry_id;
    return Object.keys(this._hass?.states ?? {}).find((id) => {
      const state = this._hass.states[id];
      return id.startsWith("sensor.") && state.attributes?.entry_id === entryId &&
        (id.split(".", 2)[1]?.endsWith(suffix) || state.attributes?.translation_key === suffix);
    });
  }

  async _call(service, data = {}) {
    const status = this._entity(this._config?.status_entity);
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
      idle: ["mdi:robot-vacuum-variant", "calm"], completed: ["mdi:check-circle-outline", "calm"],
    };
    return { state, icon: (map[state] || ["mdi:robot-vacuum", "muted"])[0], tone: (map[state] || ["", "muted"])[1] };
  }

  _condition(condition, t) {
    const visible = condition.enabled !== false;
    if (!visible) return "";
    const label = t[condition.key] || condition.key;
    return `<span class="condition ${condition.passed ? "passed" : "pending"}">
      ${icon(condition.passed ? "mdi:check-circle" : "mdi:clock-alert-outline", "condition-icon")}
      <span>${escapeHtml(label)}</span>
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
          <div class="easy-status">${icon(info.icon, "status-icon")}<span>${escapeHtml(info.state)}</span></div>
        </div>
        <div class="easy-next">
          ${icon("mdi:calendar-clock", "next-icon")}
          <span class="easy-next-copy"><small>${escapeHtml(t.next)}</small><strong>${escapeHtml(missionName)}</strong><span>${escapeHtml(this._date(nextValue))}</span></span>
          <span class="condition-summary ${conditionsReady ? "passed" : "pending"}">${icon(conditionsReady ? "mdi:check-all" : "mdi:clock-alert-outline", "summary-icon")}<span>${escapeHtml(conditionsReady ? t.ready : t.blocked)}</span></span>
        </div>
        <div class="easy-actions">
          <button class="easy-action primary" data-action="run">${icon("mdi:play", "action-icon")}<span>${escapeHtml(t.run)}</span></button>
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
        <div>${entries.map((mission) => `<button data-edit="${escapeHtml(mission.id)}" title="${escapeHtml(mission.name)}">${escapeHtml(mission.start_time || "—")}</button>`).join("") || "<span>—</span>"}</div></div>`;
    }).join("")}</div>`;
  }

  _missionCard(mission, t) {
    const vacuum = this._entity(mission.vacuum_entity_id);
    const profile = mission.profile || {};
    const conditions = (mission.conditions || []).filter((item) => item.enabled !== false);
    const scheduleText = mission.schedule_entity_id ? t.nativeSchedule :
      `${(mission.weekdays || []).map((day) => t.days[DAYS.indexOf(day)]).join(" · ")} · ${mission.start_time || "—"}`;
    return `<article class="mission ${mission.all_conditions_met ? "ready" : "pending"}">
      <div class="mission-head"><div><strong>${escapeHtml(mission.name)}</strong><small>${escapeHtml(scheduleText)}</small></div>
        <span class="mission-state">${icon(mission.all_conditions_met ? "mdi:check-circle" : "mdi:clock-alert-outline", "state-icon")}${escapeHtml(mission.all_conditions_met ? t.ready : t.blocked)}</span></div>
      <div class="mission-chips">
        <span>${icon("mdi:robot-vacuum", "chip-icon")}${escapeHtml(vacuum?.attributes?.friendly_name || mission.vacuum_entity_id)}</span>
        <span>${icon(profile.mode?.includes("mop") ? "mdi:water" : "mdi:fan", "chip-icon")}${escapeHtml([profile.mode, profile.fan, profile.water, profile.passes ? `${profile.passes}×` : ""].filter(Boolean).join(" · "))}</span>
        ${(mission.areas || []).length ? `<span>${icon("mdi:floor-plan", "chip-icon")}${escapeHtml(mission.areas.join(", "))}</span>` : ""}
      </div>
      <div class="conditions">${conditions.map((item) => this._condition(item, t)).join("") || `<span class="muted">${escapeHtml(t.noConditions)}</span>`}</div>
      <div class="mission-actions">
        <button data-run="${escapeHtml(mission.id)}">${icon("mdi:play", "mini-icon")}${escapeHtml(t.run)}</button>
        <button data-edit="${escapeHtml(mission.id)}">${icon("mdi:pencil", "mini-icon")}${escapeHtml(t.edit)}</button>
        <button data-remove="${escapeHtml(mission.id)}" class="danger-button">${icon("mdi:delete-outline", "mini-icon")}${escapeHtml(t.remove)}</button>
      </div>
    </article>`;
  }

  _editor(mission, status, t) {
    const value = mission || {};
    const profile = value.profile || {};
    const guards = value.guards || {};
    const vacuums = status?.attributes?.managed_vacuums || [];
    const schedules = Object.keys(this._hass?.states || {}).filter((id) => id.startsWith("schedule."));
    const option = (item, selected) => `<option value="${escapeHtml(item)}" ${item === selected ? "selected" : ""}>${escapeHtml(this._entity(item)?.attributes?.friendly_name || item)}</option>`;
    return `<form class="mission-editor" data-mission-form data-id="${escapeHtml(value.id || "")}">
      <div class="form-head"><strong>${escapeHtml(value.id ? t.edit : t.add)}</strong><button type="button" class="round" data-cancel>${icon("mdi:close", "action-icon")}</button></div>
      <div class="form-grid">
        <label><span>${escapeHtml(t.name)}</span><input name="name" required value="${escapeHtml(value.name || "")}"></label>
        <label><span>${escapeHtml(t.vacuum)}</span><select name="vacuum_entity_id" required>${vacuums.map((id) => option(id, value.vacuum_entity_id || vacuums[0])).join("")}</select></label>
        <label><span>${escapeHtml(t.time)}</span><input name="start_time" type="time" value="${escapeHtml(value.start_time || "09:00")}"></label>
        <label><span>${escapeHtml(t.schedule)}</span><select name="schedule_entity_id"><option value="">${escapeHtml(t.weeklySchedule)}</option>${schedules.map((id) => option(id, value.schedule_entity_id)).join("")}</select></label>
      </div>
      <fieldset><legend>${escapeHtml(t.weekdays)}</legend><div class="day-picker">${DAYS.map((day, index) => `<label class="day-choice"><input type="checkbox" data-day="${day}" ${(value.weekdays || DAYS).includes(day) ? "checked" : ""}><span>${t.days[index]}</span></label>`).join("")}</div></fieldset>
      <div class="form-grid profile-grid">
        <label><span>${escapeHtml(t.condition)}</span><select name="people_home"><option value="wait" ${guards.people_home === "wait" ? "selected" : ""}>${escapeHtml(t.wait)}</option><option value="allow" ${guards.people_home === "allow" ? "selected" : ""}>${escapeHtml(t.allow)}</option><option value="skip" ${guards.people_home === "skip" ? "selected" : ""}>${escapeHtml(t.skipPolicy)}</option></select></label>
        <label><span>${escapeHtml(t.profile)}</span><select name="profile_mode"><option value="vacuum" ${profile.mode === "vacuum" ? "selected" : ""}>Vacuum</option><option value="mop" ${profile.mode === "mop" ? "selected" : ""}>Mop</option><option value="vacuum_and_mop" ${profile.mode === "vacuum_and_mop" ? "selected" : ""}>Vacuum + Mop</option></select></label>
        <label><span>Fan</span><input name="fan" value="${escapeHtml(profile.fan || "")}" placeholder="auto / low / high"></label>
        <label><span>Water</span><input name="water" value="${escapeHtml(profile.water || "")}" placeholder="low / medium / high"></label>
        <label><span>${escapeHtml(t.passes)}</span><input name="passes" type="number" min="1" max="3" value="${escapeHtml(profile.passes || 1)}"></label>
        <label><span>${escapeHtml(t.areas)}</span><input name="areas" value="${escapeHtml((value.areas || []).join(", "))}" placeholder="kitchen, living_room"></label>
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
        <div class="mode-pill">${icon(info.icon, "status-icon")}<span>${escapeHtml(info.state)}</span></div></div>
      <div class="overview-chips"><span>${icon("mdi:robot-vacuum", "chip-icon")}${status?.attributes?.managed_vacuums?.length || 0}</span><span>${icon("mdi:calendar-check", "chip-icon")}${missions.length}</span><span class="${passed === total ? "good" : "warn"}">${icon(passed === total ? "mdi:check-all" : "mdi:clock-alert-outline", "chip-icon")}${passed}/${total}</span></div>
      <section><div class="section-title"><strong>${escapeHtml(t.weekly)}</strong><button class="round" data-add title="${escapeHtml(t.add)}">${icon("mdi:plus", "action-icon")}</button></div>${this._week(missions, t)}</section>
      <section><div class="section-title"><strong>${escapeHtml(t.missions)}</strong></div><div class="mission-list">${missions.map((mission) => this._missionCard(mission, t)).join("") || `<div class="empty">${escapeHtml(t.noMission)}</div>`}</div></section>
      ${this._editingMissionId ? this._editor(editing, status, t) : ""}
      <div class="advanced-footer"><button class="round" data-mode-toggle title="${escapeHtml(t.simple)}">${icon("mdi:view-dashboard-outline", "action-icon")}</button><button class="advanced-add" data-add>${icon("mdi:plus", "mini-icon")}${escapeHtml(t.add)}</button></div>
    </div></ha-card>`;
  }

  async _saveForm(form) {
    const data = Object.fromEntries(new FormData(form).entries());
    const status = this._entity(this._config.status_entity);
    const missions = status?.attributes?.missions || [];
    const existing = missions.find((item) => item.id === form.dataset.id) || {};
    const weekdays = [...form.querySelectorAll("[data-day]:checked")].map((item) => item.dataset.day);
    const id = existing.id || globalThis.crypto?.randomUUID?.().replaceAll("-", "") || `run_${Date.now()}`;
    const mission = {
      ...existing, id, name: data.name, vacuum_entity_id: data.vacuum_entity_id,
      weekdays, start_time: data.start_time || "09:00", schedule_entity_id: data.schedule_entity_id || null,
      areas: String(data.areas || "").split(",").map((item) => item.trim()).filter(Boolean), enabled: true,
      profile: { ...(existing.profile || {}), mode: data.profile_mode || "vacuum", fan: data.fan || null, water: data.water || null, passes: Number(data.passes || 1) },
      guards: { ...(existing.guards || {}), people_home: data.people_home || "wait" },
    };
    await this._call("add_mission", { mission });
    this._editingMissionId = null;
    this._render();
  }

  _bind() {
    const root = this.shadowRoot;
    root.querySelector('[data-action="run"]')?.addEventListener("click", () => this._call("run_next"));
    root.querySelector('[data-action="skip"]')?.addEventListener("click", () => this._call("skip_next"));
    root.querySelector('[data-action="postpone"]')?.addEventListener("click", () => this._call("postpone_next", { minutes: 60 }));
    root.querySelector("[data-mode-toggle]")?.addEventListener("click", () => {
      this._displayMode = this._displayMode === "advanced" ? "simple" : "advanced"; this._editingMissionId = null; this._render();
    });
    root.querySelectorAll?.("[data-add]").forEach((button) => button.addEventListener("click", () => { this._editingMissionId = "new"; this._render(); }));
    root.querySelectorAll?.("[data-edit]").forEach((button) => button.addEventListener("click", () => { this._editingMissionId = button.dataset.edit; this._render(); }));
    root.querySelectorAll?.("[data-run]").forEach((button) => button.addEventListener("click", () => this._call("run_next", { mission_id: button.dataset.run })));
    root.querySelectorAll?.("[data-remove]").forEach((button) => button.addEventListener("click", () => this._call("remove_mission", { mission_id: button.dataset.remove })));
    root.querySelectorAll?.("[data-cancel]").forEach((button) => button.addEventListener("click", () => { this._editingMissionId = null; this._render(); }));
    root.querySelector("[data-mission-form]")?.addEventListener("submit", (event) => { event.preventDefault(); this._saveForm(event.currentTarget); });
  }

  _styles() {
    return `<style>
      :host{display:block;width:100%;min-width:0;font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif);container-type:inline-size;container-name:robbie-card}*{box-sizing:border-box;min-width:0}
      ha-card{width:100%;overflow:hidden;border-radius:22px;border:1px solid rgba(255,255,255,.09);box-shadow:none;background:var(--ha-card-background,var(--card-background-color,#202020));color:var(--primary-text-color,#fff)}ha-card.active{background:linear-gradient(135deg,rgba(32,184,154,.16),rgba(24,34,31,.97))}ha-card.waiting{background:linear-gradient(135deg,rgba(242,169,59,.18),rgba(34,30,24,.97))}ha-card.danger{background:linear-gradient(135deg,rgba(238,91,100,.23),rgba(36,24,26,.97))}
      .icon-box{width:18px;height:18px;display:grid;place-items:center;flex:0 0 18px;line-height:0}.icon-box>ha-icon{--mdc-icon-size:16px}.status-icon{width:17px;height:17px}.status-icon>ha-icon{--mdc-icon-size:15px}.chip-icon,.mini-icon,.condition-icon{width:15px;height:15px}.chip-icon>ha-icon,.mini-icon>ha-icon,.condition-icon>ha-icon{--mdc-icon-size:13px}.next-icon{width:34px;height:34px}.next-icon>ha-icon{--mdc-icon-size:27px}.action-icon>ha-icon{--mdc-icon-size:16px}
      button,input,select{font:inherit}.easy-wrap,.advanced-wrap{padding:16px;display:grid;gap:12px}.easy-header,.advanced-header{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.easy-brand{font-size:9px;font-weight:850;letter-spacing:.12em;text-transform:uppercase;opacity:.45}.easy-room,.title{margin-top:3px;font-size:19px;font-weight:850;line-height:1.08;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.subtitle{font-size:10px;opacity:.56;margin-top:4px}.easy-status,.mode-pill{height:30px;max-width:48%;display:inline-flex;align-items:center;gap:6px;padding:0 10px;border-radius:999px;background:rgba(255,255,255,.085);font-size:10px;font-weight:850;text-transform:uppercase;white-space:nowrap}
      .easy-next{position:relative;border-radius:17px;padding:11px 12px;background:rgba(255,255,255,.048);display:grid;grid-template-columns:34px minmax(0,1fr) auto;align-items:center;gap:10px}.easy-next-copy{display:grid;gap:1px}.easy-next-copy small{font-size:9px;text-transform:uppercase;letter-spacing:.08em;opacity:.48}.easy-next-copy strong{font-size:12px}.easy-next-copy>span{font-size:10px;opacity:.62}.condition-summary{display:inline-flex;align-items:center;gap:5px;font-size:9px;font-weight:760;padding:6px 8px;border-radius:999px;background:rgba(255,255,255,.07)}.condition-summary.passed{color:var(--success-color,#4caf50)}.condition-summary.pending{color:var(--warning-color,#f2a93b)}
      .easy-actions,.advanced-footer{display:flex;align-items:center;justify-content:flex-end;gap:7px}.easy-action,.advanced-add,.mission-actions button,.form-actions button{height:36px;border:0;border-radius:12px;padding:0 11px;display:inline-flex;align-items:center;justify-content:center;gap:6px;background:rgba(255,255,255,.075);color:inherit;font-size:10px;font-weight:760;cursor:pointer}.easy-action.primary,.advanced-add,.form-actions .save{background:var(--primary-color,#41bdf5);color:var(--text-primary-color,#fff)}.round{width:36px;height:36px;border:0;border-radius:50%;display:grid;place-items:center;background:rgba(255,255,255,.075);color:inherit;cursor:pointer;padding:0}.round:hover,.mission-actions button:hover{background:rgba(255,255,255,.14)}
      .overview-chips,.mission-chips{display:flex;flex-wrap:wrap;gap:6px}.overview-chips>span,.mission-chips>span{min-height:26px;display:inline-flex;align-items:center;gap:5px;padding:4px 8px;border-radius:999px;background:rgba(255,255,255,.065);font-size:10px}.overview-chips .good{color:var(--success-color,#4caf50)}.overview-chips .warn{color:var(--warning-color,#f2a93b)}section{display:grid;gap:8px}.section-title{display:flex;align-items:center;justify-content:space-between}.section-title>strong{font-size:13px}
      .week-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px}.week-day{min-height:63px;padding:7px 4px;border-radius:12px;background:rgba(255,255,255,.028);text-align:center}.week-day.active{background:rgba(65,189,245,.08)}.week-day>strong{font-size:9px;text-transform:uppercase;opacity:.55}.week-day>div{display:grid;gap:3px;margin-top:5px}.week-day button{border:0;border-radius:999px;padding:3px;background:rgba(65,189,245,.16);color:inherit;font-size:8px;cursor:pointer}.week-day span{font-size:9px;opacity:.25}
      .mission-list{display:grid;gap:7px}.mission{padding:11px;border-radius:15px;background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.045);display:grid;gap:9px}.mission.pending{border-color:rgba(242,169,59,.24)}.mission-head{display:flex;justify-content:space-between;gap:10px}.mission-head>div{display:grid;gap:2px}.mission-head strong{font-size:12px}.mission-head small{font-size:9px;opacity:.58}.mission-state{display:inline-flex;align-items:center;gap:4px;font-size:9px;white-space:nowrap}.mission.ready .mission-state{color:var(--success-color,#4caf50)}.mission.pending .mission-state{color:var(--warning-color,#f2a93b)}.conditions{display:flex;flex-wrap:wrap;gap:5px}.condition{display:inline-flex;align-items:center;gap:4px;padding:5px 7px;border-radius:999px;background:rgba(255,255,255,.05);font-size:9px}.condition.passed{color:var(--success-color,#4caf50)}.condition.pending{color:var(--warning-color,#f2a93b)}.muted,.empty{font-size:10px;opacity:.52}.mission-actions{display:flex;justify-content:flex-end;gap:6px}.mission-actions button{height:30px;border-radius:10px}.mission-actions .danger-button{color:var(--error-color,#ee5b64)}
      .mission-editor{padding:13px;border-radius:17px;background:rgba(255,255,255,.045);display:grid;gap:12px}.form-head{display:flex;align-items:center;justify-content:space-between}.form-head>strong{font-size:13px}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.form-grid label{display:grid;gap:5px}.form-grid label>span,fieldset legend{font-size:9px;text-transform:uppercase;letter-spacing:.06em;opacity:.55}.form-grid input,.form-grid select{width:100%;height:36px;border:1px solid rgba(255,255,255,.10);border-radius:10px;padding:0 9px;background:rgba(0,0,0,.14);color:inherit}fieldset{margin:0;padding:0;border:0;display:grid;gap:7px}.day-picker{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}.day-choice input{position:absolute;opacity:0}.day-choice span{height:31px;display:grid;place-items:center;border-radius:9px;background:rgba(255,255,255,.045);font-size:9px;cursor:pointer}.day-choice input:checked+span{background:rgba(65,189,245,.20);color:var(--primary-color,#41bdf5);font-weight:800}.form-actions{display:flex;justify-content:flex-end;gap:7px}
      @container robbie-card (max-width:520px){.easy-wrap,.advanced-wrap{padding:13px}.condition-summary span:last-child{display:none}.easy-next{grid-template-columns:30px minmax(0,1fr) auto}.week-grid{gap:3px}.week-day{padding:6px 2px}.form-grid{grid-template-columns:1fr}.mission-state{font-size:0}.mission-state .icon-box{display:grid}.mission-actions button{font-size:0;padding:0;width:30px}.mission-actions .icon-box{margin:0}.profile-grid{grid-template-columns:1fr 1fr}.easy-room,.title{font-size:17px}}
    </style>`;
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const t = this._copy();
    const status = this._entity(this._config.status_entity);
    if (!status) {
      this.shadowRoot.innerHTML = `<ha-card><div class="empty-card">${escapeHtml(t.configure)}</div></ha-card>${this._styles()}`;
      return;
    }
    const next = this._entity(this._discover("next_mission"));
    const missions = Array.isArray(status.attributes?.missions) ? status.attributes.missions : [];
    const content = this._displayMode === "advanced" ? this._advanced(status, missions, t) : this._simple(status, next, missions, t);
    this.shadowRoot.innerHTML = `${content}${this._styles()}`;
    this._bind();
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
    this.shadowRoot.innerHTML = `<div class="editor"><label>Planner status<select data-status>${sensors.map((id) => `<option value="${escapeHtml(id)}" ${id === this._config.status_entity ? "selected" : ""}>${escapeHtml(id)}</option>`).join("")}</select></label><label>Default mode<select data-mode><option value="simple" ${this._config.mode !== "advanced" ? "selected" : ""}>Simple</option><option value="advanced" ${this._config.mode === "advanced" ? "selected" : ""}>Advanced</option></select></label></div><style>.editor{display:grid;gap:14px;padding:16px}label{display:grid;gap:6px}select{padding:10px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color)}</style>`;
    this.shadowRoot.querySelector("[data-status]")?.addEventListener("change", (event) => this._emit("status_entity", event.target.value));
    this.shadowRoot.querySelector("[data-mode]")?.addEventListener("change", (event) => this._emit("mode", event.target.value));
  }
}

class RobbieVacuumBadge extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._lastRenderSignature = "";
  }

  static async getConfigElement() { return document.createElement("robbie-vacuum-badge-editor"); }
  static getStubConfig(hass) {
    const vacuum = Object.keys(hass?.states ?? {}).find((id) => id.startsWith("vacuum."));
    const status = Object.keys(hass?.states ?? {}).find((id) => id.startsWith("sensor.") && hass.states[id]?.attributes?.managed_vacuums?.includes(vacuum));
    return { vacuum_entity: vacuum, status_entity: status, navigation_path: "/lovelace/cleaning" };
  }

  setConfig(config = {}) {
    if (!config || typeof config !== "object" || !config.vacuum_entity) throw new Error("vacuum_entity is required");
    this._config = { navigation_path: "/lovelace/cleaning", ...config };
    this._lastRenderSignature = "";
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const vacuum = hass?.states?.[this._config.vacuum_entity];
    const status = this._status();
    const override = this._stateOverride();
    let signature;
    try {
      signature = JSON.stringify([
        this._config, hass?.language || "en", vacuum?.state, vacuum?.attributes,
        status?.state, status?.attributes, override,
      ]);
    } catch (_error) {
      signature = `${this._config.vacuum_entity || ""}:${vacuum?.state || ""}:${vacuum?.last_changed || ""}`;
    }
    if (signature === this._lastRenderSignature) return;
    this._lastRenderSignature = signature;
    this._render();
  }

  _status() {
    if (this._config?.status_entity) return this._hass?.states?.[this._config.status_entity];
    return Object.values(this._hass?.states ?? {}).find((state) => state.attributes?.managed_vacuums?.includes(this._config.vacuum_entity));
  }

  _stateOverride() {
    const value = this._hass?.states?.[this._config?.state_override_entity]?.state;
    return ["docked", "idle", "cleaning", "returning", "paused", "waiting", "error", "unavailable"].includes(value) ? value : "";
  }

  _navigate() {
    const path = this._config?.navigation_path;
    if (!path) return;
    if (window.history?.pushState) window.history.pushState(null, "", path);
    if (typeof window.dispatchEvent === "function") window.dispatchEvent(new CustomEvent("location-changed"));
  }

  _bindInteraction() {
    const badge = this.shadowRoot?.querySelector?.("ha-badge");
    if (!badge || !this._config.vacuum_entity) return;
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
      paused: "Pausiert", waiting: "Wartet", error: "Fehler", unavailable: "Nicht verfügbar",
    } : {
      docked: "Docked", idle: "Sleeping", cleaning: "Cleaning", returning: "Returning",
      paused: "Paused", waiting: "Waiting", error: "Error", unavailable: "Unavailable",
    };
    return de
      ? { states, next: "Nächster Start", choose: "Saugroboter auswählen" }
      : { states, next: "Next run", choose: "Select a vacuum" };
  }

  _stateIcon(state) {
    return ({
      docked: "mdi:home", idle: "mdi:power-sleep", cleaning: "mdi:play",
      returning: "mdi:home-import-outline", paused: "mdi:pause",
      waiting: "mdi:account-clock-outline", error: "mdi:alert",
      unavailable: "mdi:alert-circle-outline",
    })[state] || "mdi:information-outline";
  }

  _color(state) {
    return ({
      cleaning: "var(--success-color,var(--green-color,#4caf50))",
      returning: "var(--info-color,var(--primary-color,#039be5))",
      paused: "var(--info-color,var(--primary-color,#039be5))",
      waiting: "var(--warning-color,var(--amber-color,#f2a93b))",
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

  _render() {
    if (!this.shadowRoot) return;
    const L = this._labels();
    const vacuum = this._hass?.states?.[this._config.vacuum_entity];
    if (!this._config.vacuum_entity || !vacuum) {
      this.shadowRoot.innerHTML = `
        <style>
          :host{display:block;width:var(--ha-badge-size,36px);height:var(--ha-badge-size,36px)}
          ha-badge{--badge-color:var(--error-color,var(--red-color,#db4437))}
          .badge-symbol{position:relative;display:grid;place-items:center;width:22px;height:22px;color:var(--badge-color)}
          .robot-symbol{--mdc-icon-size:20px}
          .state-marker{position:absolute;right:-4px;bottom:-4px;display:grid;place-items:center;width:12px;height:12px;border-radius:50%;background:var(--ha-card-background,var(--card-background-color,#fff));box-shadow:0 0 0 1px var(--ha-card-border-color,var(--divider-color,#ddd));color:var(--badge-color)}
          .state-marker ha-icon{--mdc-icon-size:9px}
        </style>
        <ha-badge icon-only title="${escapeHtml(L.choose)}" aria-label="${escapeHtml(L.choose)}">
          <span slot="icon" class="badge-symbol">
            <ha-icon class="robot-symbol" icon="mdi:robot-vacuum"></ha-icon>
            <span class="state-marker"><ha-icon icon="mdi:alert-circle-outline"></ha-icon></span>
          </span>
        </ha-badge>`;
      return;
    }
    const status = this._status();
    const waiting = status?.attributes?.waiting_vacuums?.includes(this._config.vacuum_entity);
    const raw = vacuum?.state || "unavailable";
    const state = this._stateOverride() || (waiting ? "waiting" : raw);
    const nextRun = status?.attributes?.next_runs?.[this._config.vacuum_entity];
    const time = this._formatTime(nextRun?.scheduled);
    const name = this._config.name || vacuum?.attributes?.friendly_name || this._config.vacuum_entity;
    const label = L.states[state] || state;
    const tooltip = [name, label, time ? `${L.next} ${time}` : "", nextRun?.mission || ""].filter(Boolean).join(" · ");
    const showTime = state === "docked" && Boolean(time);
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;width:var(--ha-badge-size,36px);height:var(--ha-badge-size,36px)}
        ha-badge{--badge-color:${escapeHtml(this._color(state))}}
        .badge-symbol{position:relative;display:grid;place-items:center;width:22px;height:22px;color:var(--badge-color)}
        .robot-symbol{--mdc-icon-size:${showTime ? "15px" : "20px"};${showTime ? "transform:translateY(-3px)" : ""}}
        .next-time{position:absolute;left:50%;bottom:-1px;transform:translateX(-50%);font-size:6px;font-weight:850;line-height:1;letter-spacing:-.05em;white-space:nowrap;color:var(--badge-color)}
        .state-marker{position:absolute;right:-4px;bottom:-4px;display:grid;place-items:center;width:12px;height:12px;border-radius:50%;background:var(--ha-card-background,var(--card-background-color,#fff));box-shadow:0 0 0 1px var(--ha-card-border-color,var(--divider-color,#ddd));color:var(--badge-color)}
        .state-marker ha-icon{--mdc-icon-size:9px}
      </style>
      <ha-badge type="button" icon-only data-mode="${escapeHtml(state)}" title="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}">
        <span slot="icon" class="badge-symbol">
          <ha-icon class="robot-symbol" icon="mdi:robot-vacuum${state === "docked" ? "-variant" : ""}"></ha-icon>
          ${showTime ? `<small class="next-time">${escapeHtml(time)}</small>` : ""}
          <span class="state-marker"><ha-icon icon="${escapeHtml(this._stateIcon(state))}"></ha-icon></span>
        </span>
      </ha-badge>`;
    this._bindInteraction();
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
    this.shadowRoot.innerHTML = `<div class="editor"><label>Vacuum<select data-vacuum>${options(vacuums, this._config.vacuum_entity)}</select></label><label>Planner status<select data-status>${options(statuses, this._config.status_entity)}</select></label><label>State override (optional)<select data-override><option value="">Live robot state</option>${options(overrides, this._config.state_override_entity)}</select></label><label>Navigation path<input data-path value="${escapeHtml(this._config.navigation_path)}"></label><small>Native 36 px Home Assistant badge with robot symbol, colored status marker and next docked run.</small></div><style>.editor{display:grid;gap:13px;padding:16px}label{display:grid;gap:6px}select,input{padding:10px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color)}small{opacity:.58}</style>`;
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
