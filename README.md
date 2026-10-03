# Horaires de prière Maroc / Prayer times Morocco — Home Assistant

🇫🇷 **À quoi sert cette intégration ?** Elle donne dans Home Assistant les horaires des cinq prières (Fajr, Dhuhr, Asr, Maghrib, Isha) et du lever du soleil pour votre logement, des zones supplémentaires et **les personnes selon l'endroit où elles se trouvent**. Elle crée des capteurs horodatés et un capteur « Prochaine prière » pour déclencher des **notifications** ou l'**adhan sur vos enceintes** (Music Assistant).

🇬🇧 **What is it for?** It provides the five daily prayer times (Fajr, Dhuhr, Asr, Maghrib, Isha) and sunrise for your home, extra zones, and **people wherever they currently are**. It creates timestamp sensors and a "Next prayer" sensor to trigger **notifications** or the **adhan on your speakers** (Music Assistant).

🇲🇦 **ما هذه الإضافة؟** توفّر في Home Assistant أوقات الصلوات الخمس (الفجر، الظهر، العصر، المغرب، العشاء) ووقت الشروق لمنزلك ولمناطق إضافية **وللأشخاص بحسب مكان وجودهم**، مع مستشعر «الصلاة القادمة» لتشغيل **الإشعارات** أو **الأذان على مكبرات الصوت** (Music Assistant). الأوقات مأخوذة من جداول وزارة الأوقاف والشؤون الإسلامية، أو محسوبة محليًا عند الحاجة. **هذه الإضافة غير رسمية وغير تابعة للوزارة.**

Interface : français, anglais et arabe (selon la langue de Home Assistant) · UI: French, English and Arabic.

> **Non officiel / Unofficial.** Ce projet n'est pas affilié au Ministère des Habous et des Affaires islamiques. Les horaires font foi sur https://www.habous.gov.ma. / This project is not affiliated with the Ministry; its website is authoritative.

## Deux sources d'horaires / Two sources

| | Dépôt de données (défaut) | Calcul local |
|---|---|---|
| FR | Fichiers JSON du dépôt [habous-prayer-times-data](https://github.com/schawki/habous-prayer-times-data), adresse **modifiable** dans les options. Ce sont les horaires publiés par les Habous pour 191 villes. Ville la plus proche, distance affichée. | Calculé par Home Assistant (méthode Maroc : Fajr 19°, Isha 17°), sans connexion, pour les coordonnées exactes. Ajustement possible en minutes par prière. |
| EN | JSON files from the [habous-prayer-times-data](https://github.com/schawki/habous-prayer-times-data) repository, **editable** address in the options. These are the times published by the Habous for 191 cities. Nearest city, distance shown. | Computed by Home Assistant (Morocco method: Fajr 19°, Isha 17°), offline, for exact coordinates. Per-prayer minute adjustment. |

**Le calcul local sert aussi de repli** (option, activée par défaut) quand le fichier du dépôt est absent ou périmé. **Honnêteté sur les données :** le dépôt de données est mis à jour par un workflow GitHub **manuel** (voir ce dépôt) ; la page des Habous ne publie qu'un mois hijri à la fois, donc entre deux mises à jour l'intégration retombe sur le calcul local. / The data repository is refreshed by a **manual** GitHub workflow and the Habous page only publishes one Hijri month at a time: between two refreshes the integration falls back to the local calculation.

**Précision du calcul local, mesurée** sur Casablanca du 13/09 au 12/10/2026 (30 jours, comparé aux horaires Habous) : écart de −1 à +1 minute pour Fajr, Dhuhr, Asr, Maghrib et Isha ; le lever du soleil est calculé 3 à 4 minutes trop tard, d'où un ajustement par défaut de **−3 min** sur le Chourouk (modifiable). Une seule ville et un seul mois : à vérifier chez vous. Pour comparer vous-même, activez `show_comparison` sur la carte. / Local calculation measured on Casablanca (30 days): within ±1 min except sunrise (+3 to +4 min, hence a default −3 min adjustment). One city, one month: check on your side.

## Fonctionnalités / Features

- Ville la plus proche du logement avec **distance** (source dépôt) / nearest city with **distance**.
- **Zones supplémentaires** et **personnes** (horaires selon leur position, mis à jour quand elles se déplacent ; date de dernière mise à jour en attribut).
- **Horaires d'une personne** / *a person's times* — 🇫🇷 : dans une zone connue (logement ou zone supplémentaire), elle reçoit les horaires de la zone ; hors zone, ceux de la ville Habous la plus proche **si elle est à moins de _N_ km** (option, 30 km par défaut) ; sinon les horaires **calculés** à sa position. Un calcul n'est refait que si la personne s'est éloignée de plus de _M_ km du point du dernier calcul (option, 5 km par défaut) ou si le jour a changé. La carte indique l'heure du calcul et propose une icône « Actualiser » ; à l'ouverture de la page elle appelle le service `habous_prayer_times.recalculate`, qui ne recalcule que si nécessaire (`force: true` pour forcer, par exemple dans une automatisation). Le recalcul utilise la dernière position connue par Home Assistant. 🇬🇧: in a known zone a person gets that zone's times; outside, the nearest Habous city if within _N_ km (option, default 30), otherwise times calculated at their position. A calculation is only redone after moving more than _M_ km (option, default 5) or on a new day; the card shows the calculation time and a refresh icon, and calls the `habous_prayer_times.recalculate` service when the page opens (`force: true` to force). 🇸🇦: داخل منطقة معروفة يحصل الشخص على أوقات المنطقة؛ خارجها تُستخدم أقرب مدينة للأوقاف إن كانت ضمن المسافة المحددة (٣٠ كم افتراضيًا)، وإلا تُحسب الأوقات في موقعه. لا يُعاد الحساب إلا بعد تحرك يتجاوز الهامش (٥ كم افتراضيًا) أو عند يوم جديد، وتعرض البطاقة وقت الحساب وأيقونة للتحديث.
- Fréquence de mise à jour du dépôt : mensuelle (défaut), hebdomadaire, quotidienne ou manuelle + bouton « Mettre à jour ».
- Capteurs par lieu : Fajr, Chourouk/Sunrise, Dhuhr, Asr, Maghrib, Isha, Prochaine prière. Attributs : `place`, `source`, `last_update`, `mode` (`zone`, `repository` ou `calculated`), `calculated_at` (heure du calcul, quand les horaires sont calculés), et — quand le dépôt couvre le jour — `repository_time` (heure Habous), `calculated_time` (heure calculée) et `difference_min` (calculée − Habous). Les heures du dépôt sont lues avec le `utc_offset` du fichier : elles ne dépendent pas de la base de fuseaux de Home Assistant.

## Blueprints (installés automatiquement / installed automatically)

Au démarrage, l'intégration copie ses blueprints dans `config/blueprints/automation/habous_prayer_times/` (dossier géré par l'intégration : dupliquez un blueprint pour le personnaliser).

1. **Notification de prière** — choisissez la personne (ou la zone), **les prières** voulues, l'heure ou 5/10/15/30 min avant, la langue FR/EN/**AR** et **n'importe quelle action de notification** (appli mobile, Telegram, persistante…). Variables : `prayer`, `prayer_name`, `prayer_time`, `place`, `message`.
2. **Annonce de l'adhan (Music Assistant)** — enceintes, volume, adhan spécial Fajr, uniquement si quelqu'un est à la maison.

## Carte Lovelace / Lovelace card

🇫🇷 L'intégration livre sa propre carte, **chargée automatiquement** (aucune ressource à ajouter) : *Modifier le tableau de bord → Ajouter une carte → « Prayer times Morocco »*, puis choisissez n'importe quel capteur du lieu (maison, zone ou personne). Elle affiche les six horaires, le temps relatif, met la prochaine prière en évidence et indique ville Habous, distance, source et date de mise à jour. En arabe, elle s'affiche de droite à gauche. Heures affichées dans le fuseau de votre navigateur.

🇬🇧 The integration ships its own card, **loaded automatically** (no resource to add): *Edit dashboard → Add card → “Prayer times Morocco”*, then pick any sensor of the place. Right-to-left in Arabic.

```yaml
type: custom:habous-prayer-card
entity: sensor.prayer_times_maison_prochaine_priere
title: Horaires des Prières   # facultatif
show_sunrise: true            # facultatif
show_details: true            # facultatif
relative_style: compact       # compact (+14:25 / −0:14, défaut) ou long
show_comparison: false        # true : « Habous 05:01 · calcul 05:02 (+1) » sous chaque prière
```

## Installation via HACS

1. HACS → ⋮ → *Dépôts personnalisés* → collez `https://github.com/schawki/habous-prayer-times-ha` → catégorie **Intégration**.
2. Installez, redémarrez Home Assistant, puis *Paramètres → Appareils et services → Ajouter une intégration → Horaires de prière Maroc*.
3. Choisissez la source (« Dépôt de données » par défaut ; « Calcul local » ne demande aucune connexion).

## Limites connues / Known limits

- Le fuseau horaire de Home Assistant devrait être `Africa/Casablanca`. Les capteurs sont des instants absolus (UTC) ; pour les heures du dépôt, le `utc_offset` du fichier est utilisé, et pour le calcul local aucune base de fuseaux n'intervient.
- **Changement de mois hijri : une courte fenêtre sans données du jour.** La page des Habous ne montre que le mois en cours ; le dépôt de données se met à jour automatiquement (passage quotidien, passe complète seulement quand le mois change), mais les horaires du nouveau mois n'apparaissent qu'après minuit, une fois que la page des Habous les affiche (traitement d'environ 15 à 30 minutes). L'intégration récupère ensuite les nouveaux fichiers lors de sa vérification horaire : au pire, **environ une heure et demie** sans données du jour ; le bouton « Mettre à jour » raccourcit l'attente. Pendant ce temps, si l'option « Calcul local si le fichier du dépôt est absent ou périmé » est cochée (par défaut), les horaires sont **calculés localement** (écart de quelques minutes au maximum) et la carte indique « Calcul local » ; sinon les capteurs restent sans valeur. Si le site des Habous n'a pas changé de mois ou est inaccessible, la mise à jour est retentée le lendemain. / **At each Hijri month change there is a short window without data for the day.** The Habous page only shows the current month; the data repository updates itself automatically, but the new month's times only appear shortly after midnight, once the Habous page shows them (about 15–30 minutes of processing), then the integration picks them up at its hourly check: worst case about 1.5 hours; the “Update” button shortens the wait. Meanwhile, if “Local calculation when the repository file is missing or outdated” is ticked (default), times are calculated locally (a few minutes' difference at most) and the card says “Local calculation”; otherwise the sensors have no value. / **عند تغيّر الشهر الهجري توجد فترة قصيرة بلا بيانات لليوم.** تعرض صفحة الأوقاف الشهر الحالي فقط؛ تُحدَّث بيانات المستودع تلقائيًا، لكن أوقات الشهر الجديد لا تظهر إلا بعد منتصف الليل بوقت قصير، ثم تلتقطها الإضافة عند فحصها كل ساعة (في أسوأ الحالات حوالي ساعة ونصف؛ زر «تحديث» يختصر الانتظار). خلال ذلك، إن كان خيار «الحساب المحلي عند غياب ملف المستودع أو قِدمه» مفعّلًا (افتراضيًا)، تُحسب الأوقات محليًا (بفارق دقائق قليلة على الأكثر) وتشير البطاقة إلى «الحساب المحلي»؛ وإلا تبقى المستشعرات بلا قيمة.
- Mosquées (Mawaqit) : non pris en charge pour l'instant.

## Tests

```
pip install prayer-times-calculator-offline pyyaml
python -m unittest discover -s tests -v
```
