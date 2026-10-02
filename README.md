# Horaires de prière Maroc / Prayer times Morocco — Home Assistant

🇫🇷 **À quoi sert cette intégration ?** Elle donne dans Home Assistant les horaires des cinq prières (Fajr, Dhuhr, Asr, Maghrib, Isha) et du lever du soleil pour votre logement, des zones supplémentaires et **les personnes selon l'endroit où elles se trouvent**. Elle crée des capteurs horodatés et un capteur « Prochaine prière » pour déclencher des **notifications** ou l'**adhan sur vos enceintes** (Music Assistant).

🇬🇧 **What is it for?** It provides the five daily prayer times (Fajr, Dhuhr, Asr, Maghrib, Isha) and sunrise for your home, extra zones, and **people wherever they currently are**. It creates timestamp sensors and a "Next prayer" sensor to trigger **notifications** or the **adhan on your speakers** (Music Assistant).

Interface : français et anglais (selon la langue de Home Assistant) · UI: French and English.

## Deux sources d'horaires / Two sources

| | Dépôt de données (défaut) | Calcul local |
|---|---|---|
| FR | Fichiers JSON d'un dépôt GitHub, adresse **modifiable** dans les options. Ville Habous la plus proche, distance affichée. | Calculé par Home Assistant (méthode Maroc : Fajr 19°, Isha 17°), sans connexion, pour les coordonnées exactes. Ajustement possible en minutes par prière. |
| EN | JSON files from a GitHub repository, **editable** address in the options. Nearest Habous city, distance shown. | Computed by Home Assistant (Morocco method: Fajr 19°, Isha 17°), offline, for exact coordinates. Per-prayer minute adjustment. |

Le calcul local sert aussi de **repli** quand le fichier du dépôt est absent ou périmé (option). Il peut s'écarter de quelques minutes des tableaux officiels : un test sur Rabat, Marrakech et Mohammedia (31/08/2026) donne les mêmes minutes qu'un site tiers citant les Habous, sauf l'Asr à ±1 min — un seul jour, une seule référence : à vérifier avec vos horaires.
The local calculation is also the **fallback** when the repository file is missing or outdated. It may differ by a few minutes from the official tables.

## Fonctionnalités / Features

- Ville la plus proche du logement avec **distance** (source dépôt) / nearest city with **distance**.
- **Zones supplémentaires** et **personnes** (horaires selon leur position, mis à jour quand elles se déplacent ; la date de dernière mise à jour est en attribut).
- Fréquence de mise à jour du dépôt : mensuelle (défaut), hebdomadaire, quotidienne ou manuelle + bouton « Mettre à jour ».
- Capteurs par lieu : Fajr, Chourouk/Sunrise, Dhuhr, Asr, Maghrib, Isha, Prochaine prière (attributs `prayer`, `place`, `source`, `last_update`).

## Blueprints (installés automatiquement / installed automatically)

Au démarrage, l'intégration copie ses blueprints dans `config/blueprints/automation/habous_prayer_times/` (dossier géré par l'intégration : dupliquez un blueprint pour le personnaliser).

1. **Notification de prière** — choisissez la personne (ou la zone), **les prières** voulues, l'heure ou 5/10/15/30 min avant, la langue FR/EN et **n'importe quelle action de notification** (appli mobile, Telegram, persistante…). Variables : `prayer`, `prayer_name`, `prayer_time`, `place`, `message`.
2. **Annonce de l'adhan (Music Assistant)** — enceintes, volume, adhan spécial Fajr, uniquement si quelqu'un est à la maison.

## Carte Lovelace / Lovelace card

🇫🇷 L'intégration livre sa propre carte, **chargée automatiquement** (aucune ressource à ajouter) : *Modifier le tableau de bord → Ajouter une carte → « Prayer times Morocco »*, puis choisissez n'importe quel capteur du lieu (maison, zone ou personne). Elle affiche les six horaires, le temps relatif, met la prochaine prière en évidence et indique ville Habous, distance, source et date de mise à jour. Heures affichées dans le fuseau de votre navigateur.

🇬🇧 The integration ships its own card, **loaded automatically** (no resource to add): *Edit dashboard → Add card → “Prayer times Morocco”*, then pick any sensor of the place.

```yaml
type: custom:habous-prayer-card
entity: sensor.prayer_times_maison_prochaine_priere
title: Horaires des Prières   # facultatif
show_sunrise: true            # facultatif
show_details: true            # facultatif
relative_style: compact       # compact (+14:25 / −0:14, défaut) ou long
```

## Installation via HACS

1. HACS → ⋮ → *Dépôts personnalisés* → collez `https://github.com/schawki/habous-prayer-times-ha` → catégorie **Intégration**.
2. Installez, redémarrez Home Assistant, puis *Paramètres → Appareils et services → Ajouter une intégration → Horaires de prière Maroc*.
3. Choisissez la source. **Sans dépôt de données, choisissez « Calcul local »** : aucune autre étape.

## Dépôt de données (source par défaut)

`tools/build_data.py` + le workflow `update-data.yml` construisent `data/` (villes géocodées via OpenStreetMap Nominatim, horaires par ville). C'est **le seul composant qui lit habous.gov.ma**, et le workflow est **manuel** (aucune lecture tant que vous ne le lancez pas ; environ une passe par mois suffit, pauses de 2 s) ; l'intégration, elle, ne scrape jamais. Le `robots.txt` du site interdit l'accès automatisé : si vous préférez ne pas l'utiliser, supprimez le workflow et utilisez le calcul local.

## Limites connues / Known limits

- Le parseur du dépôt n'a été testé que sur une page synthétique ; l'intégration n'a pas encore tourné dans une vraie instance Home Assistant.
- Le fuseau horaire de Home Assistant doit être `Africa/Casablanca`. Les capteurs sont des instants absolus (UTC) : si l'heure affichée par HA est décalée d'une heure, c'est la règle de fuseau du système, pas le calcul.
- Mosquées (Mawaqit) : non pris en charge pour l'instant.

## Tests

```
pip install prayer-times-calculator-offline pyyaml
python -m unittest discover -s tests -v
```
