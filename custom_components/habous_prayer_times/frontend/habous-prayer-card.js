/*
 * Habous prayer card — Lovelace card bundled with the "Prayer times Morocco" integration.
 * Loaded automatically by the integration (no resource to add).
 *
 * Configuration:
 *   type: custom:habous-prayer-card
 *   entity: sensor.prayer_times_home_next_prayer           # any sensor of the place
 *   title: Prayer times                                     # optional
 *   show_sunrise: true                                     # optional
 *   show_details: true                                     # city, distance, source, last update
 *   relative_style: compact                                # compact (+14:25 / −0:14) or long
 *   show_comparison: false                                 # Habous time and calculated time side by side
 */

const DOMAIN = "habous_prayer_times";
const ORDER = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"];
// Half sun on the horizon (sunrise yellow, Maghrib orange): same look on every device.
const halfSun = (color) => `<svg class="hs" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M5.5 17a6.5 6.5 0 0 1 13 0Z" fill="${color}" stroke="none"/><path d="M2.5 17h19"/><path d="M12 5.2v2.2M4.9 8.1l1.5 1.5M19.1 8.1l-1.5 1.5M2.8 12.2l2 .6M21.2 12.2l-2 .6"/></svg>`;
const ICONS = { fajr: "🌘", sunrise: halfSun("#FFC107"), dhuhr: "☀️", asr: "🌤️", maghrib: halfSun("#FF7043"), isha: "🌙" };

const TEXT = {
  fr: {
    title: "Horaires des prières",
    prayer: "Prière", time: "Heure", relative: "Relatif",
    names: { fajr: "Fajr", sunrise: "Chourouk", dhuhr: "Dhuhr", asr: "Asr", maghrib: "Maghrib", isha: "Isha" },
    in: "dans", ago: "il y a", now: "maintenant",
    h: ["heure", "heures"], m: ["minute", "minutes"], less: "moins d'une minute",
    city: "Ville Habous", source: "Source", updated: "Mis à jour", calc_at: "Calculé à", refresh: "Actualiser",
    sources: { repository: "Dépôt de données", local_calculation: "Calcul local" },
    missing: "Choisissez un capteur « Prochaine prière » (ou n'importe quel capteur du lieu).",
    unavailable: "Capteurs indisponibles",
    e_entity: "Capteur du lieu", e_title: "Titre", e_sunrise: "Afficher le lever du soleil",
    e_details: "Afficher ville, distance et source",
    e_relative: "Temps relatif", e_compact: "Condensé (+14:25 / −0:14)", e_long: "Détaillé (il y a 14 heures…)",
    cmp_repo: "Habous", cmp_calc: "calcul", e_comparison: "Comparer l'heure Habous et l'heure calculée",
  },
  en: {
    title: "Prayer times",
    prayer: "Prayer", time: "Time", relative: "Relative",
    names: { fajr: "Fajr", sunrise: "Sunrise", dhuhr: "Dhuhr", asr: "Asr", maghrib: "Maghrib", isha: "Isha" },
    in: "in", ago: "ago", now: "now",
    h: ["hour", "hours"], m: ["minute", "minutes"], less: "less than a minute",
    city: "Habous city", source: "Source", updated: "Updated", calc_at: "Calculated at", refresh: "Refresh",
    sources: { repository: "Data repository", local_calculation: "Local calculation" },
    missing: "Pick a “Next prayer” sensor (or any sensor of the place).",
    unavailable: "Sensors unavailable",
    e_entity: "Place sensor", e_title: "Title", e_sunrise: "Show sunrise",
    e_details: "Show city, distance and source",
    e_relative: "Relative time", e_compact: "Compact (+14:25 / −0:14)", e_long: "Long (14 hours ago…)",
    cmp_repo: "Habous", cmp_calc: "calculated", e_comparison: "Compare Habous time and calculated time",
  },
};

TEXT.ar = {
  title: "أوقات الصلاة",
  prayer: "الصلاة", time: "الوقت", relative: "الفارق",
  names: { fajr: "الفجر", sunrise: "الشروق", dhuhr: "الظهر", asr: "العصر", maghrib: "المغرب", isha: "العشاء" },
  in: "بعد", ago: "منذ", now: "الآن",
  h: ["ساعة", "ساعات", "ساعتان"], m: ["دقيقة", "دقائق", "دقيقتان"], less: "أقل من دقيقة",
  city: "مدينة الأوقاف", source: "المصدر", updated: "آخر تحديث", calc_at: "تم الحساب عند", refresh: "تحديث",
  sources: { repository: "مستودع البيانات", local_calculation: "الحساب المحلي" },
  missing: "اختر مستشعر «الصلاة القادمة» (أو أي مستشعر للمكان).",
  unavailable: "المستشعرات غير متاحة",
  e_entity: "مستشعر المكان", e_title: "العنوان", e_sunrise: "إظهار الشروق",
  e_details: "إظهار المدينة والمسافة والمصدر",
  e_relative: "الوقت النسبي", e_compact: "مختصر (+14:25 / −0:14)", e_long: "مفصّل (منذ 14 ساعة…)",
  cmp_repo: "الأوقاف", cmp_calc: "حساب", e_comparison: "مقارنة وقت الأوقاف بالوقت المحسوب",
};

/** Locale d'affichage : chiffres latins pour l'arabe (usage au Maroc). */
const localeOf = (lang) => (lang === "ar" ? "ar-MA-u-nu-latn" : lang);
/** Isolate a number/time so it is not reversed inside right-to-left text. */
const ltr = (txt) => `<bdi dir="ltr">${txt}</bdi>`;
/** Mot au singulier/pluriel (et duel pour l'arabe quand le texte le fournit). */
const word = (forms, n) => (n === 2 && forms[2] ? forms[2] : forms[n > 1 ? 1 : 0]);

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

/** Find the sibling sensors (same place) from any sensor of the place. */
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
    // Page visible again: ask for a recalculation (the server ignores it if up to date).
    this._vis = () => { if (!document.hidden) { this._autoDone = false; this._render(); } };
    document.addEventListener("visibilitychange", this._vis);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    document.removeEventListener("visibilitychange", this._vis);
  }

  /** recalculate service: only recalculates if the place moved beyond the tolerance or the day changed. */
  _recalc(entity, manual) {
    if (!this._hass || !entity) return;
    const now = Date.now();
    if (!manual && this._lastCall && now - this._lastCall < 30000) return;
    this._lastCall = now;
    this._hass.callService("habous_prayer_times", "recalculate", { entity_id: entity }).catch(() => {});
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
    return new Intl.DateTimeFormat(localeOf(lang), opts).format(date);
  }

  _relative(date, t) {
    const diff = date.getTime() - Date.now();
    const mins = Math.round(Math.abs(diff) / 60000);
    if (this._config.relative_style !== "long") {
      // Compact: +14:25 = passed 14 h 25 ago; −0:14 = in 14 min.
      const hm = `${Math.floor(mins / 60)}:${String(mins % 60).padStart(2, "0")}`;
      return ltr(`${diff >= 0 && mins > 0 ? "−" : "+"}${hm}`);
    }
    if (mins < 1) return t.now;
    const h = Math.floor(mins / 60), m = mins % 60;
    const parts = [];
    if (h) parts.push(`${h} ${word(t.h, h)}`);
    if (m) parts.push(`${m} ${word(t.m, m)}`);
    const body = parts.join(" ");
    if (t === TEXT.fr || t === TEXT.ar) return diff >= 0 ? `${t.in} ${body}` : `${t.ago} ${body}`;
    return diff >= 0 ? `${t.in} ${body}` : `${body} ${t.ago}`;
  }

  /** Line "Habous 05:01 · calc 05:02 (+1)" (show_comparison option). */
  _comparison(st, shown, t, lang) {
    if (!this._config.show_comparison || !st || !st.attributes) return "";
    const a = st.attributes;
    if (!a.repository_time || !a.calculated_time) return "";
    // The attributes describe the sensor's day: only show them for that date
    // (not for "tomorrow" when the next prayer is tomorrow's).
    if (!st.state || new Date(st.state).getTime() !== shown.getTime()) return "";
    const repo = new Date(a.repository_time), calc = new Date(a.calculated_time);
    if (isNaN(repo) || isNaN(calc)) return "";
    const diff = a.difference_min;
    const sign = diff > 0 ? "+" : diff < 0 ? "−" : "";
    const tail = typeof diff === "number" ? ` ${ltr(`(${sign}${Math.abs(diff)})`)}` : "";
    return `<div class="cmp">${t.cmp_repo} ${ltr(this._fmtTime(repo, lang))} · ${t.cmp_calc} ${ltr(this._fmtTime(calc, lang))}${tail}</div>`;
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
        th{text-align:start;color:var(--secondary-text-color);font-weight:500;font-size:14px;padding:8px 8px 10px;border-bottom:3px solid var(--divider-color)}
        td{padding:12px 8px;border-bottom:1px solid var(--divider-color);color:var(--primary-text-color);vertical-align:middle}
        tr:last-child td{border-bottom:none}
        td.ic{width:40px;font-size:22px;text-align:center}
        td.ic .hs{width:26px;height:26px;display:block;margin:0 auto}
        td.nm{font-weight:600;font-size:16px}
        td.tm{font-variant-numeric:tabular-nums}
        td.rel{color:var(--secondary-text-color)}
        .cmp{font-weight:400;font-size:12px;color:var(--secondary-text-color);margin-top:2px;font-variant-numeric:tabular-nums}
        tr.next td{background:color-mix(in srgb,var(--primary-color) 14%,transparent)}
        tr.next td.rel{color:var(--primary-color);font-weight:600}
        tr.next td:first-child{border-start-start-radius:10px;border-end-start-radius:10px}
        tr.next td:last-child{border-start-end-radius:10px;border-end-end-radius:10px}
        .msg{color:var(--secondary-text-color);padding:8px 0}
        .rf{background:none;border:none;color:var(--secondary-text-color);cursor:pointer;padding:2px 4px;vertical-align:middle;border-radius:6px}
        .rf:hover{color:var(--primary-color)}
      </style><ha-card><div id="c"></div></ha-card>`;
    }
    const { t, lang } = this._t();
    this._root.querySelector("ha-card").setAttribute("dir", lang === "ar" ? "rtl" : "ltr");
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
        const dist = attrs.distance_km != null ? ` (${ltr(`${attrs.distance_km} km`)})` : "";
        details.push(`${t.city} : ${attrs.habous_city}${dist}`);
      }
      if (attrs.source) details.push(`${t.source} : ${t.sources[attrs.source] || attrs.source}`);
      if (attrs.last_update) {
        const d = new Date(attrs.last_update);
        if (!isNaN(d)) details.push(`${t.updated} : ${ltr(d.toLocaleDateString(lang === "ar" ? "fr-FR" : lang))}`);
      }
    }

    const calcAt = attrs.mode === "calculated" && attrs.calculated_at ? new Date(attrs.calculated_at) : null;
    const calcValid = calcAt && !isNaN(calcAt);
    if (calcValid) details.push(`${t.calc_at} ${ltr(this._fmtTime(calcAt, lang))}`);
    const refresh = calcValid
      ? ` <button class="rf" id="rf" type="button" title="${t.refresh}" aria-label="${t.refresh}"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg></button>`
      : "";

    const rows = ORDER.filter((p) => cfg.show_sunrise || p !== "sunrise").map((p) => {
      const st = sensors[p];
      let d = st && st.state && !["unknown", "unavailable"].includes(st.state) ? new Date(st.state) : null;
      // The next prayer can be tomorrow's (after Isha): the "Next prayer"
      // sensor then carries the right date, not the day's sensor.
      if (p === nextPrayer && next && next.state && !["unknown", "unavailable"].includes(next.state)) {
        const nd = new Date(next.state);
        if (!isNaN(nd)) d = nd;
      }
      const ok = d && !isNaN(d);
      return `<tr class="${p === nextPrayer ? "next" : ""}">
        <td class="ic">${ICONS[p]}</td><td class="nm">${t.names[p]}${ok ? this._comparison(st, d, t, lang) : ""}</td>
        <td class="tm">${ok ? ltr(this._fmtTime(d, lang)) : "–"}</td>
        <td class="rel">${ok ? this._relative(d, t) : ""}</td></tr>`;
    }).join("");

    el.innerHTML = `<h2>${title}</h2>
      ${details.length ? `<div class="sub">${details.join(" · ")}${refresh}</div>` : ""}
      <table><thead><tr><th></th><th>${t.prayer}</th><th>${t.time}</th><th>${t.relative}</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
    const rf = el.querySelector("#rf");
    if (rf) rf.addEventListener("click", () => this._recalc(attrs.entity, true));
    // Page opened: a single automatic call for a calculated place.
    if (!this._autoDone && attrs.mode === "calculated") {
      this._autoDone = true;
      this._recalc(attrs.entity, false);
    }
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
      relative_style: t.e_relative, show_comparison: t.e_comparison,
    };
    this._form.hass = this._hass;
    this._form.data = { show_sunrise: true, show_details: true, ...this._config };
    this._form.schema = [
      { name: "entity", required: true, selector: { entity: { domain: "sensor", integration: DOMAIN } } },
      { name: "title", selector: { text: {} } },
      { name: "show_sunrise", selector: { boolean: {} } },
      { name: "show_details", selector: { boolean: {} } },
      { name: "show_comparison", selector: { boolean: {} } },
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
    description: "Prayer times of a place (Prayer times Morocco integration).",
    preview: false,
  });
}
