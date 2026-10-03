# Prayer times Morocco — Home Assistant

🌐 **English** · [Français](README.fr.md) · [العربية](README.ar.md)

Prayer times for Morocco in Home Assistant: the five daily prayers (Fajr, Dhuhr, Asr, Maghrib, Isha) and sunrise for your home, extra zones, and **people wherever they currently are**. It creates timestamp sensors and a "Next prayer" sensor to trigger **notifications** or the **adhan on your speakers** (Music Assistant). Times come from the tables of the Ministry of Habous and Islamic Affairs, or are calculated locally when needed.

> **Unofficial.** This project is not affiliated with the Ministry of Habous and Islamic Affairs. The times published on https://www.habous.gov.ma are authoritative.

The interface is available in English, French and Arabic (it follows the language of Home Assistant). Other languages can be added: see [Translations](#translations).

## Two sources of times

| | Data repository (default) | Local calculation |
|---|---|---|
| What it is | JSON files of the [habous-prayer-times-data](https://github.com/schawki/habous-prayer-times-data) repository (editable address in the options): the times published by the Habous for 191 cities. Nearest city, distance shown. | Computed by Home Assistant (Morocco method: Fajr 19°, Isha 17°), offline, for the exact coordinates. Per-prayer minute adjustment. |

**Option "Compare with the Habous times"** (on by default, whichever the source). With the *Data repository* source, times are the Habous ones and the calculation is the comparison. With *Local calculation* it is the reverse: displayed times are calculated (with your adjustments) and the Habous times are only used to measure the gap (`repository_time`, `calculated_time`, `difference_min`, `repository_role: comparison`). Unticked, no comparison is shown, and with *Local calculation* nothing is downloaded from the repository.

**Local calculation also acts as a fallback** (option, on by default) when the repository file is missing or outdated. The data repository updates itself automatically: a daily check reads the Habous site only when the data no longer covers today. The Habous page only publishes the current Hijri month, so right after a month change there is a short window without data (see [Known limits](#known-limits)).

**Accuracy of the local calculation, measured** on Casablanca from 13/09 to 12/10/2026 (30 days, compared with the Habous times): within −1 to +1 minute for Fajr, Dhuhr, Asr, Maghrib and Isha; sunrise is calculated 3 to 4 minutes too late, hence a default adjustment of **−3 min** on sunrise (editable). One city and one month only: check on your side. To compare yourself, enable `show_comparison` on the card.

## Features

- Nearest city to the home with its **distance** (repository source).
- **Extra zones** and **people**: times follow their position and update when they move (last update date as an attribute).
- **A person's times:** in a known zone (home or an extra zone) they get that zone's times; outside, the nearest Habous city **if it is within _N_ km** (option, default 30 km); otherwise times **calculated** at their position. A calculation is only redone if the person moved more than _M_ km from the point of the last calculation (option, default 5 km) or if the day changed. The card shows the calculation time and a refresh icon; when the page opens it calls the `habous_prayer_times.recalculate` service, which only recalculates when needed (`force: true` to force, e.g. in an automation). Recalculation uses the last position known to Home Assistant.
- Repository update frequency: monthly (default), weekly, daily or manual, plus an "Update" button.
- Sensors per place: Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha, Next prayer. Attributes: `place`, `source`, `last_update`, `mode` (`zone`, `repository` or `calculated`), `calculated_at` (time of the calculation, when times are calculated) and — when the repository covers the day — `repository_time` (Habous time), `calculated_time` and `difference_min` (calculated − Habous). Repository times are read with the file's `utc_offset`: they do not depend on Home Assistant's timezone database.

## Blueprints (installed automatically)

At startup the integration copies its blueprints to `config/blueprints/automation/habous_prayer_times/` (a folder managed by the integration: duplicate a blueprint to customise it). Blueprint text is in English; the notification message itself can be in English, French or Arabic.

1. **Prayer notification** — choose the person (or zone), **the prayers**, the time or 5/10/15/30 min before, the message language (EN/FR/**AR**) and **any notification action** (mobile app, Telegram, persistent…). Variables: `prayer`, `prayer_name`, `prayer_time`, `place`, `message`.
2. **Announce prayer (Music Assistant)** — speakers, volume, a special Fajr adhan, only when someone is home.

## Lovelace card

The integration ships its own card, **loaded automatically** (no resource to add): *Edit dashboard → Add card → "Prayer times Morocco"*, then pick any sensor of the place (home, zone or person). It shows the six times and the relative time, highlights the next prayer, and shows the Habous city, distance, source and last update. It is right-to-left in Arabic. Times are shown in your browser's timezone.

```yaml
type: custom:habous-prayer-card
entity: sensor.prayer_times_home_next_prayer
title: Prayer times        # optional
show_sunrise: true         # optional
show_details: true         # optional
relative_style: compact    # compact (+14h25 / −0h14 in French and Arabic, +14:25 in English; default) or long
show_comparison: false     # true: "Habous 05:01 · calculated 05:02 (+1)" under each prayer
```

## Installation via HACS

1. HACS → ⋮ → *Custom repositories* → paste `https://github.com/schawki/habous-prayer-times-ha` → category **Integration**.
2. Install, restart Home Assistant, then *Settings → Devices & services → Add integration → Prayer times Morocco*.
3. Choose the source ("Data repository" by default; "Local calculation" needs no connection).

## Known limits

- Home Assistant's timezone should be `Africa/Casablanca`. Sensors are absolute instants (UTC); for repository times the file's `utc_offset` is used, and the local calculation uses no timezone database.
- **At each Hijri month change there is a short window without data for the day.** The Habous page only shows the current month. The data repository updates itself automatically (a daily check, and a full pass only when the month changes), but the new month's times only appear after midnight, once the Habous page shows them (about 15–30 minutes of processing). The integration then picks up the new files at its hourly check: worst case **about an hour and a half** without data for the day; the "Update" button shortens the wait. Meanwhile, if the option "Local calculation when the repository file is missing or outdated" is ticked (default), times are **calculated locally** (a few minutes' difference at most) and the card says "Local calculation"; otherwise the sensors have no value. If the Habous site has not changed month or is unreachable, the update is retried the next day.
- Mosques (Mawaqit): not supported for now.

## Translations

The texts of the interface (setup, options, service) are in `custom_components/habous_prayer_times/translations/`: `en.json` is the reference, with `fr.json` and `ar.json`. To add a language, copy `en.json` to `<language code>.json` (for example `es.json`) and translate the values. The card has its own texts at the top of `frontend/habous-prayer-card.js` (`TEXT` table, English by default). For the README, add a `README.<code>.md` and a link at the top of the others.

## Tests

```
pip install prayer-times-calculator-offline pyyaml
python -m unittest discover -s tests -v
```
