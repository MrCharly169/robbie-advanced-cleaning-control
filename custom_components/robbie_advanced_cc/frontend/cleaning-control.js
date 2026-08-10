const DOMAIN = "robbie_advanced_cc";

const COPY = {
  en: {
    title: "Cleaning Control",
    next: "Next mission",
    noMission: "No mission planned",
    status: "Planner status",
    decision: "Last decision",
    maintenance: "Maintenance",
    run: "Run now",
    skip: "Skip once",
    postpone: "Postpone 60 min",
    areas: "Areas",
    profile: "Profile",
    vacuum: "Vacuum",
    configure: "Open integration",
    missing: "Configure a planner status entity in the card editor.",
  },
  de: {
    title: "Reinigungssteuerung",
    next: "Nächste Mission",
    noMission: "Keine Mission geplant",
    status: "Planerstatus",
    decision: "Letzte Entscheidung",
    maintenance: "Wartung",
    run: "Jetzt starten",
    skip: "Einmal überspringen",
    postpone: "60 Min. verschieben",
    areas: "Bereiche",
    profile: "Profil",
    vacuum: "Saugroboter",
    configure: "Integration öffnen",
    missing: "Bitte eine Planerstatus-Entität im Card-Editor auswählen.",
  },
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

class RobbieAdvancedCleaningCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("robbie-advanced-cleaning-card-editor");
  }

  static getStubConfig(hass) {
    const status = Object.keys(hass?.states ?? {}).find(
      (id) => id.startsWith("sensor.") && hass.states[id]?.attributes?.entry_id,
    );
    return { type: "custom:robbie-advanced-cleaning-card", status_entity: status };
  }

  setConfig(config) {
    if (!config) throw new Error("Card configuration is required");
    this._config = { ...config };
    this._render();
  }

  connectedCallback() {
    const request = new Event("context-request", {
      bubbles: true,
      composed: true,
    });
    Object.assign(request, {
      context: "hassApi",
      contextTarget: this,
      subscribe: false,
      callback: (api) => {
        this._callService = typeof api?.callService === "function"
          ? api.callService.bind(api)
          : undefined;
      },
    });
    this.dispatchEvent(request);
  }

  set hass(value) {
    this._hass = value;
    // Legacy fallback for HA frontends that still pass API methods directly.
    if (!this._callService && typeof value?.callService === "function") {
      this._callService = value.callService.bind(value);
    }
    this._render();
  }

  getCardSize() {
    return 5;
  }

  _copy() {
    return COPY[this._hass?.language?.startsWith("de") ? "de" : "en"];
  }

  _entity(id) {
    return id ? this._hass?.states?.[id] : undefined;
  }

  _discover(suffix) {
    if (this._config?.[`${suffix}_entity`]) return this._config[`${suffix}_entity`];
    const status = this._entity(this._config?.status_entity);
    const entryId = status?.attributes?.entry_id;
    return Object.keys(this._hass?.states ?? {}).find((id) => {
      const state = this._hass.states[id];
      return id.startsWith("sensor.") && state.attributes?.entry_id === entryId &&
        (id.split(".", 2)[1]?.endsWith(suffix) || state.attributes?.translation_key === suffix);
    });
  }

  async _call(service, data = {}) {
    const status = this._entity(this._config?.status_entity);
    const entryId = this._config?.entry_id || status?.attributes?.entry_id;
    if (!entryId) return;
    if (!this._callService) return;
    await this._callService(DOMAIN, service, { entry_id: entryId, ...data });
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const t = this._copy();
    const status = this._entity(this._config.status_entity);
    if (!status) {
      this.shadowRoot.innerHTML = `<ha-card><div class="missing">${escapeHtml(t.missing)}</div></ha-card>${this._styles()}`;
      return;
    }
    const nextId = this._discover("next_mission");
    const decisionId = this._discover("last_decision");
    const maintenanceId = this._discover("maintenance");
    const next = this._entity(nextId);
    const decision = this._entity(decisionId);
    const maintenance = this._entity(maintenanceId);
    const attrs = next?.attributes ?? {};
    const date = next && next.state !== "unknown" && next.state !== "unavailable"
      ? new Intl.DateTimeFormat(this._hass.language || "en", {
          weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
        }).format(new Date(next.state))
      : t.noMission;
    const areas = Array.isArray(attrs.areas) ? attrs.areas : [];
    const profile = attrs.profile ?? {};
    const vacuum = this._entity(attrs.vacuum_entity_id);
    const mission = attrs.mission || t.noMission;
    const accent = ["failed", "blocked"].includes(status.state) ? "danger" :
      status.state === "running" ? "active" : "calm";

    this.shadowRoot.innerHTML = `
      <ha-card class="${accent}">
        <header>
          <div class="robot"><ha-icon icon="mdi:robot-vacuum"></ha-icon></div>
          <div class="heading">
            <span class="eyebrow">${escapeHtml(t.title)}</span>
            <strong>${escapeHtml(mission)}</strong>
            <span class="date">${escapeHtml(date)}</span>
          </div>
          <span class="state">${escapeHtml(status.state)}</span>
        </header>
        <section class="facts">
          <div><span>${escapeHtml(t.vacuum)}</span><b>${escapeHtml(vacuum?.attributes?.friendly_name || attrs.vacuum_entity_id || "—")}</b></div>
          <div><span>${escapeHtml(t.profile)}</span><b>${escapeHtml([profile.mode, profile.fan, profile.water].filter(Boolean).join(" · ") || "—")}</b></div>
          <div><span>${escapeHtml(t.decision)}</span><b>${escapeHtml(decision?.state || "—")}</b></div>
          <div><span>${escapeHtml(t.maintenance)}</span><b>${escapeHtml(maintenance?.state || "—")}</b></div>
        </section>
        ${areas.length ? `<section class="areas"><span>${escapeHtml(t.areas)}</span><div>${areas.map((area) => `<em>${escapeHtml(area)}</em>`).join("")}</div></section>` : ""}
        <footer>
          <button data-action="run"><ha-icon icon="mdi:play"></ha-icon>${escapeHtml(t.run)}</button>
          <button data-action="skip" class="secondary"><ha-icon icon="mdi:skip-next"></ha-icon>${escapeHtml(t.skip)}</button>
          <button data-action="postpone" class="secondary"><ha-icon icon="mdi:clock-plus-outline"></ha-icon>${escapeHtml(t.postpone)}</button>
        </footer>
      </ha-card>
      ${this._styles()}`;
    this.shadowRoot.querySelector('[data-action="run"]')?.addEventListener("click", () => this._call("run_next"));
    this.shadowRoot.querySelector('[data-action="skip"]')?.addEventListener("click", () => this._call("skip_next"));
    this.shadowRoot.querySelector('[data-action="postpone"]')?.addEventListener("click", () => this._call("postpone_next", { minutes: 60 }));
  }

  _styles() {
    return `<style>
      :host{display:block;--racc-accent:var(--primary-color,#4f7cff)}
      ha-card{overflow:hidden;padding:20px;background:linear-gradient(145deg,color-mix(in srgb,var(--ha-card-background,var(--card-background-color)) 94%,var(--racc-accent)),var(--ha-card-background,var(--card-background-color)));border:1px solid color-mix(in srgb,var(--divider-color) 74%,var(--racc-accent));box-shadow:0 14px 36px rgba(20,28,48,.12)}
      ha-card.active{--racc-accent:#27b784}ha-card.danger{--racc-accent:#ee5b64}
      header{display:grid;grid-template-columns:auto 1fr auto;gap:14px;align-items:center}
      .robot{width:50px;height:50px;border-radius:16px;display:grid;place-items:center;background:color-mix(in srgb,var(--racc-accent) 18%,transparent);color:var(--racc-accent)}
      .robot ha-icon{--mdc-icon-size:30px}.heading{display:flex;flex-direction:column;min-width:0}.heading strong{font-size:20px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.eyebrow,.date,.facts span,.areas>span{font-size:12px;color:var(--secondary-text-color);letter-spacing:.03em}.state{padding:6px 10px;border-radius:999px;background:color-mix(in srgb,var(--racc-accent) 16%,transparent);color:var(--racc-accent);font-weight:700;font-size:12px;text-transform:uppercase}
      .facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:18px 0}.facts div{padding:11px;border-radius:13px;background:color-mix(in srgb,var(--secondary-background-color) 72%,transparent);display:flex;flex-direction:column;gap:4px;min-width:0}.facts b{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      .areas{display:flex;align-items:center;gap:12px;margin-bottom:16px}.areas div{display:flex;gap:7px;flex-wrap:wrap}.areas em{font-style:normal;font-size:12px;padding:5px 9px;border:1px solid var(--divider-color);border-radius:999px}
      footer{display:flex;gap:8px;flex-wrap:wrap}button{border:0;border-radius:12px;padding:10px 13px;background:var(--racc-accent);color:#fff;font:inherit;font-weight:650;display:flex;align-items:center;gap:7px;cursor:pointer}button.secondary{background:var(--secondary-background-color);color:var(--primary-text-color)}button ha-icon{--mdc-icon-size:18px}.missing{padding:22px}
      @media(max-width:600px){ha-card{padding:15px}.facts{grid-template-columns:1fr}.state{display:none}footer button{flex:1;justify-content:center;font-size:12px}.heading strong{font-size:17px}}
    </style>`;
  }
}

class RobbieAdvancedCleaningCardEditor extends HTMLElement {
  setConfig(config) { this._config = { ...config }; this._render(); }
  set hass(value) { this._hass = value; this._render(); }
  _render() {
    if (!this._hass || !this._config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const sensors = Object.keys(this._hass.states).filter((id) => id.startsWith("sensor."));
    this.shadowRoot.innerHTML = `<label>Planner status entity<select>${sensors.map((id) => `<option value="${escapeHtml(id)}" ${id === this._config.status_entity ? "selected" : ""}>${escapeHtml(id)}</option>`).join("")}</select></label><style>label{display:grid;gap:8px;padding:16px}select{padding:10px;border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color)}</style>`;
    this.shadowRoot.querySelector("select")?.addEventListener("change", (event) => {
      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: { ...this._config, status_entity: event.target.value } }, bubbles: true, composed: true }));
    });
  }
}

if (!customElements.get("robbie-advanced-cleaning-card")) customElements.define("robbie-advanced-cleaning-card", RobbieAdvancedCleaningCard);
if (!customElements.get("robbie-advanced-cleaning-card-editor")) customElements.define("robbie-advanced-cleaning-card-editor", RobbieAdvancedCleaningCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "robbie-advanced-cleaning-card")) {
  window.customCards.push({
    type: "robbie-advanced-cleaning-card",
    name: "Robbie Advanced Cleaning Control",
    description: "Vendor-neutral mission planning for Home Assistant vacuum cleaners",
  });
}
