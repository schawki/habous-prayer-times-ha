/*
 * Habous prayer card — carte Lovelace livrée avec l'intégration « Prayer times Morocco ».
 * Chargée automatiquement par l'intégration (aucune ressource à ajouter).
 *
 * Configuration :
 *   type: custom:habous-prayer-card
 *   entity: sensor.prayer_times_maison_prochaine_priere   # n'importe quel capteur du lieu
 *   title: Horaires des Prières                            # facultatif
 *   show_sunrise: true                                     # facultatif
 *   show_details: true                                     # ville, distance, source, mise à jour
 *   relative_style: compact                                # compact (+14:25 / −0:14) ou long
 */

const DOMAIN = "habous_prayer_times";
const ORDER = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"];
const ICONS = { fajr: "🌘", sunrise: "🌅", dhuhr: "☀️", asr: "🌤️", maghrib: "🌇", isha: "🌙" };

const TEXT = {
  fr: {
    title: "Horaires des prières",
    prayer: "Prière", time: "Heure", relative: "Relatif",
    names: { fajr: "Fajr", sunrise: "Chourouk", dhuhr: "Dhuhr", asr: "Asr", maghrib: "Maghrib", isha: "Isha" },
    in: "dans", ago: "il y a", now: "maintenant",
    h: ["heure", "heures"], m: ["minute", "minutes"], less: "moins d'une minute",
    city: "Ville Habous", source: "Source", updated: "Mis à jour",
    sources: { repository: "Dépôt de données", local_calculation: "Calcul local" },
    missing: "Choisissez un capteur « Prochaine prière » (ou n'importe quel capteur du lieu).",
    unavailable: "Capteurs indisponibles",
    e_entity: "Capteur du lieu", e_title: "Titre", e_sunrise: "Afficher le lever du soleil",
    e_details: "Afficher ville, distance et source",
    e_relative: "Temps relatif", e_compact: "Condensé (+14:25 / −0:14)", e_long: "Détaillé (il y a 14 heures…)",
  },
  en: {
    title: "Prayer times",
    prayer: "Prayer", time: "Time", relative: "Relative",
    names: { fajr: "Fajr", sunrise: "Sunrise", dhuhr: "Dhuhr", asr: "Asr", maghrib: "Maghrib", isha: "Isha" },
    in: "in", ago: "ago", now: "now",
    h: ["hour", "hours"], m: ["minute", "minutes"], less: "less than a minute",
    city: "Habous city", source: "Source", updated: "Updated",
    sources: { repository: "Data repository", local_calculation: "Local calculation" },
    missing: "Pick a “Next prayer” sensor (or any sensor of the place).",
    unavailable: "Sensors unavailable",
    e_entity: "Place sensor", e_title: "Title", e_sunrise: "Show sunrise",
    e_details: "Show city, distance and source",
    e_relative: "Relative time", e_compact: "Compact (+14:25 / −0:14)", e_long: "Long (14 hours ago…)",
  },
};

const SUFFIX_KEYS = {
  fajr: "fajr", chourouk: "sunrise", sunrise: "sunrise", dhuhr: "dhuhr", asr: "asr",
  maghrib: "maghrib", isha: "isha", prochaine_priere: "next_prayer", next_prayer: "next_prayer",
};

function keyOf(hass, entityId) {
  const reg = hass.entities && hass.entities[entityId];
  if (reg && reg.translation_key) return reg.translation_key;
  const tail = entityId.split(".")[1] || "";
  for (const [suffix, key] of Object.entries(SUFFIX_KEYS)) {
    if (tail.endsWith("_" + suffix)) return key;
  }
  return null;
}

/** Retrouve les capteurs frères (même lieu) à partir d'un capteur quelconque du lieu. */
function placeSensors(hass, entityId) {
  const base = hass.states[entityId];
  if (!base) return null;
  const out = {};
  const reg = hass.entities && hass.entities[entityId];
  const deviceId = reg && reg.device_id;
  const placeId = base.attributes && base.attributes.entity;
  for (const [id, st] of Object.entries(hass.states)) {
    if (!id.startsWith("sensor.")) continue;
    let same = false;
    if (deviceId && hass.entities[id]) same = hass.entities[id].device_id === deviceId;
    else if (placeId) same = st.attributes && st.attributes.entity === placeId && "habous_city" in st.attributes;
    if (!same) continue;
    const key = keyOf(hass, id);
    if (key) out[key] = st;
  }
  return out;
}

class HabousPrayerCard extends HTMLElement {
  static getConfigElement() { return document.createElement("habous-prayer-card-editor"); }

  static getStubConfig(hass) {
    const id = Object.keys(hass.states).find(
      (e) => e.startsWith("sensor.") && hass.states[e].attributes && "habous_city" in hass.states[e].attributes
        && hass.states[e].attributes.prayer !== undefined,
    );
    return { type: "custom:habous-prayer-card", entity: id || "" };
  }

  setConfig(config) {
    this._config = { show_sunrise: true, show_details: true, ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._timer = setInterval(() => this._render(), 30000);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
  }

  getCardSize() { return 7; }

  getGridOptions() { return { columns: 12, rows: 6, min_columns: 6, min_rows: 4 }; }

  _t() {
    const lang = ((this._hass && (this._hass.locale?.language || this._hass.language)) || "en").slice(0, 2);
    return { t: TEXT[lang] || TEXT.en, lang: TEXT[lang] ? lang : "en" };
  }

  _fmtTime(date, lang) {
    const tf = this._hass.locale && this._hass.locale.time_format;
    const opts = { hour: "2-digit", minute: "2-digit" };
    if (tf === "12") opts.hour12 = true;
    else if (tf === "24" || tf === undefined) opts.hour12 = false;
    return new Intl.DateTimeFormat(lang, opts).format(date);
  }

  _relative(date, t) {
    const diff = date.getTime() - Date.now();
    const mins = Math.round(Math.abs(diff) / 60000);
    if (this._config.relative_style !== "long") {
      // Condensé : +14:25 = passée depuis 14 h 25 ; −0:14 = dans 14 min.
      const hm = `${Math.floor(mins / 60)}:${String(mins % 60).padStart(2, "0")}`;
      return `${diff >= 0 && mins > 0 ? "−" : "+"}${hm}`;
    }
    if (mins < 1) return t.now;
    const h = Math.floor(mins / 60), m = mins % 60;
    const parts = [];
    if (h) parts.push(`${h} ${t.h[h > 1 ? 1 : 0]}`);
    if (m) parts.push(`${m} ${t.m[m > 1 ? 1 : 0]}`);
    const body = parts.join(" ");
    if (t === TEXT.fr) return diff >= 0 ? `${t.in} ${body}` : `${t.ago} ${body}`;
    return diff >= 0 ? `${t.in} ${body}` : `${body} ${t.ago}`;
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this._root) {
      this._root = this.attachShadow({ mode: "open" });
      this._root.innerHTML = `<style>
        ha-card{padding:16px}
        h2{margin:0 0 4px;font-size:var(--ha-card-header-font-size,24px);font-weight:400;color:var(--primary-text-color)}
        .sub{color:var(--secondary-text-color);font-size:13px;margin-bottom:12px;line-height:1.4}
        table{width:100%;border-collapse:collapse}
        th{text-align:left;color:var(--secondary-text-color);font-weight:500;font-size:14px;padding:8px 8px 10px;border-bottom:3px solid var(--divider-color)}
        td{padding:12px 8px;border-bottom:1px solid var(--divider-color);color:var(--primary-text-color);vertical-align:middle}
        tr:last-child td{border-bottom:none}
        td.ic{width:40px;font-size:22px;text-align:center}
        td.nm{font-weight:600;font-size:16px}
        td.tm{font-variant-numeric:tabular-nums}
        td.rel{color:var(--secondary-text-color)}
        tr.next td{background:color-mix(in srgb,var(--primary-color) 14%,transparent)}
        tr.next td.rel{color:var(--primary-color);font-weight:600}
        tr.next td:first-child{border-radius:10px 0 0 10px}
        tr.next td:last-child{border-radius:0 10px 10px 0}
        .msg{color:var(--secondary-text-color);padding:8px 0}
      </style><ha-card><div id="c"></div></ha-card>`;
    }
    const { t, lang } = this._t();
    const el = this._root.getElementById("c");
    const cfg = this._config;
    if (!cfg.entity) { el.innerHTML = `<div class="msg">${t.missing}</div>`; return; }
    const sensors = placeSensors(this._hass, cfg.entity);
    if (!sensors) { el.innerHTML = `<div class="msg">${t.unavailable} (${cfg.entity})</div>`; return; }

    const next = sensors.next_prayer;
    const attrs = (next || sensors.fajr || {}).attributes || {};
    const nextPrayer = next && next.attributes ? next.attributes.prayer : null;
    const title = cfg.title || (attrs.place ? `${t.title} – ${attrs.place}` : t.title);

    const details = [];
    if (cfg.show_details) {
      if (attrs.habous_city) {
        const dist = attrs.distance_km != null ? ` (${attrs.distance_km} km)` : "";
        details.push(`${t.city} : ${attrs.habous_city}${dist}`);
      }
      if (attrs.source) details.push(`${t.source} : ${t.sources[attrs.source] || attrs.source}`);
      if (attrs.last_update) {
        const d = new Date(attrs.last_update);
        if (!isNaN(d)) details.push(`${t.updated} : ${d.toLocaleDateString(lang)}`);
      }
    }

    const rows = ORDER.filter((p) => cfg.show_sunrise || p !== "sunrise").map((p) => {
      const st = sensors[p];
      const d = st && st.state && !["unknown", "unavailable"].includes(st.state) ? new Date(st.state) : null;
      const ok = d && !isNaN(d);
      return `<tr class="${p === nextPrayer ? "next" : ""}">
        <td class="ic">${ICONS[p]}</td><td class="nm">${t.names[p]}</td>
        <td class="tm">${ok ? this._fmtTime(d, lang) : "–"}</td>
        <td class="rel">${ok ? this._relative(d, t) : ""}</td></tr>`;
    }).join("");

    el.innerHTML = `<h2>${title}</h2>
      ${details.length ? `<div class="sub">${details.join(" · ")}</div>` : ""}
      <table><thead><tr><th></th><th>${t.prayer}</th><th>${t.time}</th><th>${t.relative}</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
  }
}

class HabousPrayerCardEditor extends HTMLElement {
  setConfig(config) { this._config = config; this._update(); }

  set hass(hass) { this._hass = hass; this._update(); }

  _update() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        this.dispatchEvent(new CustomEvent("config-changed", {
          detail: { config: ev.detail.value }, bubbles: true, composed: true,
        }));
      });
      this.appendChild(this._form);
    }
    const lang = ((this._hass.locale?.language || this._hass.language) || "en").slice(0, 2);
    const t = TEXT[lang] || TEXT.en;
    const labels = {
      entity: t.e_entity, title: t.e_title, show_sunrise: t.e_sunrise, show_details: t.e_details,
      relative_style: t.e_relative,
    };
    this._form.hass = this._hass;
    this._form.data = { show_sunrise: true, show_details: true, ...this._config };
    this._form.schema = [
      { name: "entity", required: true, selector: { entity: { domain: "sensor", integration: DOMAIN } } },
      { name: "title", selector: { text: {} } },
      { name: "show_sunrise", selector: { boolean: {} } },
      { name: "show_details", selector: { boolean: {} } },
      {
        name: "relative_style",
        selector: { select: { mode: "dropdown", options: [
          { value: "compact", label: t.e_compact }, { value: "long", label: t.e_long },
        ] } },
      },
    ];
    this._form.computeLabel = (s) => labels[s.name] || s.name;
  }
}

if (!customElements.get("habous-prayer-card")) {
  customElements.define("habous-prayer-card", HabousPrayerCard);
  customElements.define("habous-prayer-card-editor", HabousPrayerCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "habous-prayer-card",
    name: "Prayer times Morocco",
    description: "Horaires de prière d'un lieu (intégration Prayer times Morocco / Horaires de prière Maroc).",
    preview: false,
  });
}
