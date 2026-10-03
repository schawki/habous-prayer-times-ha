# Horaires de prière Maroc — Home Assistant

🌐 [English](README.md) · **Français** · [العربية](README.ar.md)

Les horaires de prière du Maroc dans Home Assistant : les cinq prières (Fajr, Dhuhr, Asr, Maghrib, Isha) et le lever du soleil pour votre logement, des zones supplémentaires et **les personnes selon l'endroit où elles se trouvent**. L'intégration crée des capteurs horodatés et un capteur « Prochaine prière » pour déclencher des **notifications** ou l'**adhan sur vos enceintes** (Music Assistant). Les horaires viennent des tableaux du Ministère des Habous et des Affaires islamiques, ou sont calculés localement au besoin.

> **Non officiel.** Ce projet n'est pas affilié au Ministère des Habous et des Affaires islamiques. Les horaires publiés sur https://www.habous.gov.ma font foi.

L'interface existe en anglais, français et arabe (selon la langue de Home Assistant). D'autres langues peuvent être ajoutées : voir [Traductions](#traductions).

## Deux sources d'horaires

| | Dépôt de données (défaut) | Calcul local |
|---|---|---|
| Principe | Fichiers JSON du dépôt [habous-prayer-times-data](https://github.com/schawki/habous-prayer-times-data) (adresse modifiable dans les options) : les horaires publiés par les Habous pour 191 villes. Ville la plus proche, distance affichée. | Calculé par Home Assistant (méthode Maroc : Fajr 19°, Isha 17°), sans connexion, pour les coordonnées exactes. Ajustement possible en minutes par prière. |

**Option « Comparer avec les horaires des Habous »** (activée par défaut, quelle que soit la source). Avec la source *Dépôt de données*, les heures sont celles des Habous et le calcul sert de comparaison. Avec *Calcul local*, c'est l'inverse : les heures affichées sont calculées (avec vos ajustements) et les horaires des Habous ne servent qu'à mesurer l'écart (`repository_time`, `calculated_time`, `difference_min`, `repository_role: comparison`). Décochée, aucune comparaison n'est affichée ; avec *Calcul local*, rien n'est alors téléchargé depuis le dépôt.

**Le calcul local sert aussi de repli** (option, activée par défaut) quand le fichier du dépôt est absent ou périmé. Le dépôt de données se met à jour automatiquement : un passage quotidien ne lit le site des Habous que si les données ne couvrent plus aujourd'hui. La page des Habous ne publie que le mois hijri en cours : juste après un changement de mois, il y a donc une courte fenêtre sans données (voir [Limites connues](#limites-connues)).

**Précision du calcul local, mesurée** sur Casablanca du 13/09 au 12/10/2026 (30 jours, comparé aux horaires des Habous) : écart de −1 à +1 minute pour Fajr, Dhuhr, Asr, Maghrib et Isha ; le lever du soleil est calculé 3 à 4 minutes trop tard, d'où un ajustement par défaut de **−3 min** sur le Chourouk (modifiable). Une seule ville et un seul mois : à vérifier chez vous. Pour comparer vous-même, activez `show_comparison` sur la carte.

## Fonctionnalités

- Ville la plus proche du logement avec sa **distance** (source dépôt).
- **Zones supplémentaires** et **personnes** : les horaires suivent leur position et se mettent à jour quand elles se déplacent (date de dernière mise à jour en attribut).
- **Horaires d'une personne :** dans une zone connue (logement ou zone supplémentaire), elle reçoit les horaires de la zone ; hors zone, ceux de la ville Habous la plus proche **si elle est à moins de _N_ km** (option, 30 km par défaut) ; sinon les horaires **calculés** à sa position. Un calcul n'est refait que si la personne s'est éloignée de plus de _M_ km du point du dernier calcul (option, 5 km par défaut) ou si le jour a changé. La carte indique l'heure du calcul et propose une icône « Actualiser » ; à l'ouverture de la page elle appelle le service `habous_prayer_times.recalculate`, qui ne recalcule que si nécessaire (`force: true` pour forcer, par exemple dans une automatisation). Le recalcul utilise la dernière position connue par Home Assistant.
- Fréquence de mise à jour du dépôt : mensuelle (défaut), hebdomadaire, quotidienne ou manuelle, plus un bouton « Mettre à jour ».
- Capteurs par lieu : Fajr, Chourouk, Dhuhr, Asr, Maghrib, Isha, Prochaine prière. Attributs : `place`, `source`, `last_update`, `mode` (`zone`, `repository` ou `calculated`), `calculated_at` (heure du calcul, quand les horaires sont calculés) et — quand le dépôt couvre le jour — `repository_time` (heure Habous), `calculated_time` (heure calculée) et `difference_min` (calculée − Habous). Les heures du dépôt sont lues avec le `utc_offset` du fichier : elles ne dépendent pas de la base de fuseaux de Home Assistant.

## Blueprints (installés automatiquement)

Au démarrage, l'intégration copie ses blueprints dans `config/blueprints/automation/habous_prayer_times/` (dossier géré par l'intégration : dupliquez un blueprint pour le personnaliser). Les textes des blueprints sont en anglais ; le message de la notification peut être en anglais, français ou arabe.

1. **Prayer notification (notification de prière)** — choisissez la personne (ou la zone), **les prières** voulues, l'heure ou 5/10/15/30 min avant, la langue du message (EN/FR/**AR**) et **n'importe quelle action de notification** (appli mobile, Telegram, persistante…). Variables : `prayer`, `prayer_name`, `prayer_time`, `place`, `message`.
2. **Announce prayer (Music Assistant)** — enceintes, volume, adhan spécial Fajr, uniquement si quelqu'un est à la maison.

## Carte Lovelace

L'intégration livre sa propre carte, **chargée automatiquement** (aucune ressource à ajouter) : *Modifier le tableau de bord → Ajouter une carte → « Prayer times Morocco »*, puis choisissez n'importe quel capteur du lieu (maison, zone ou personne). Elle affiche les six horaires et le temps relatif, met la prochaine prière en évidence et indique ville Habous, distance, source et date de mise à jour. En arabe, elle s'affiche de droite à gauche. Heures affichées dans le fuseau de votre navigateur.

```yaml
type: custom:habous-prayer-card
entity: sensor.prayer_times_maison_prochaine_priere
title: Horaires des prières   # facultatif
show_sunrise: true            # facultatif
show_details: true            # facultatif
relative_style: compact       # compact (+14:25 / −0:14, défaut) ou long
show_comparison: false        # true : « Habous 05:01 · calcul 05:02 (+1) » sous chaque prière
```

## Installation via HACS

1. HACS → ⋮ → *Dépôts personnalisés* → collez `https://github.com/schawki/habous-prayer-times-ha` → catégorie **Intégration**.
2. Installez, redémarrez Home Assistant, puis *Paramètres → Appareils et services → Ajouter une intégration → Prayer times Morocco*.
3. Choisissez la source (« Dépôt de données » par défaut ; « Calcul local » ne demande aucune connexion).

## Limites connues

- Le fuseau horaire de Home Assistant devrait être `Africa/Casablanca`. Les capteurs sont des instants absolus (UTC) ; pour les heures du dépôt, le `utc_offset` du fichier est utilisé, et pour le calcul local aucune base de fuseaux n'intervient.
- **Changement de mois hijri : une courte fenêtre sans données du jour.** La page des Habous ne montre que le mois en cours. Le dépôt de données se met à jour automatiquement (un passage quotidien, et une passe complète seulement quand le mois change), mais les horaires du nouveau mois n'apparaissent qu'après minuit, une fois que la page des Habous les affiche (traitement d'environ 15 à 30 minutes). L'intégration récupère ensuite les nouveaux fichiers lors de sa vérification horaire : au pire, **environ une heure et demie** sans données du jour ; le bouton « Mettre à jour » raccourcit l'attente. Pendant ce temps, si l'option « Calcul local si le fichier du dépôt est absent ou périmé » est cochée (par défaut), les horaires sont **calculés localement** (écart de quelques minutes au maximum) et la carte indique « Calcul local » ; sinon les capteurs restent sans valeur. Si le site des Habous n'a pas changé de mois ou est inaccessible, la mise à jour est retentée le lendemain.
- Mosquées (Mawaqit) : non pris en charge pour l'instant.

## Traductions

Les textes de l'interface (installation, options, service) sont dans `custom_components/habous_prayer_times/translations/` : `en.json` sert de référence, avec `fr.json` et `ar.json`. Pour ajouter une langue, copiez `en.json` en `<code de langue>.json` (par exemple `es.json`) et traduisez les valeurs. La carte a ses propres textes en tête de `frontend/habous-prayer-card.js` (tableau `TEXT`, anglais par défaut). Pour le README, ajoutez un `README.<code>.md` et un lien en haut des autres.

## Tests

```
pip install prayer-times-calculator-offline pyyaml
python -m unittest discover -s tests -v
```
