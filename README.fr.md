# HA Régie Essence QC

[Français](./README.fr.md) | [English](./README.md)

[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

Intégration personnalisée Home Assistant permettant de suivre les prix de l'essence au Québec à partir du flux public de [Régie Essence Québec](https://regieessencequebec.ca/).

Cette intégration crée un appareil par station configurée et un capteur par type de carburant disponible. Plusieurs stations peuvent être ajoutées depuis l'interface de Home Assistant, tandis qu'un coordinateur partagé optimise les rafraîchissements du flux.

## Fonctionnalités

- Intégration Home Assistant native avec assistant de configuration
- Structure du dépôt compatible avec HACS
- Un appareil par station-service configurée
- Une entité capteur par type de carburant disponible pour chaque station configurée
- Interrogation mutualisée du flux de Régie Essence Québec pour toutes les stations configurées
- Intervalle de rafraîchissement configurable avec un minimum de 5 minutes
- Prise en charge de plusieurs stations suivies simultanément

## Installation via HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gabrielbergeron&repository=ha-regie-essence-quebec)

1. Suivez le guide des dépôts personnalisés HACS disponible [ici](https://hacs.xyz/docs/faq/custom_repositories/).
2. Ajoutez l'URL du dépôt : `https://github.com/gabrielbergeron/ha-regie-essence-quebec`
3. Sélectionnez la catégorie `Integration`
4. Installez l'intégration depuis HACS
5. Redémarrez Home Assistant
6. Ouvrez `Paramètres -> Appareils et services`
7. Cliquez sur `+ Ajouter une intégration`, puis recherchez `Régie Essence Québec`

## Configuration

Chaque entrée configurée représente une station. Vous pouvez en ajouter autant que vous le souhaitez.

Pour chaque station, l'intégration crée des capteurs distincts pour les types de carburant renvoyés par le flux, par exemple `Regulier`, `Super` ou `Diesel`.

L'assistant de configuration prend en charge les champs suivants :

- `name` obligatoire
- `address` facultatif, mais recommandé
- `postal_code` facultatif, mais fortement recommandé lorsque le nom de la station est courant
- `brand` facultatif
- `entity_name` facultatif

Après l'ajout d'une station, vous pouvez ouvrir les options de l'intégration pour modifier l'intervalle de mise à jour. La valeur minimale autorisée est de 5 minutes.

L'intervalle de mise à jour est global pour toute l'intégration. Le modifier depuis n'importe quelle station configurée applique la même valeur à toutes les stations configurées.

## Correspondance des stations

La correspondance est insensible aux accents et s'appuie sur des comparaisons exactes des valeurs fournies.

Pour obtenir les meilleurs résultats :

- Utilisez le nom exact de la station tel qu'il apparaît dans le flux de Régie Essence Québec
- Ajoutez `address` lorsque le nom de la station est courant
- Ajoutez `postal_code` pour distinguer des stations voisines aux noms similaires
- Ajoutez `brand` lorsqu'un même nom de station apparaît sous plusieurs bannières

Si une station ne peut pas être associée de manière exacte, l'intégration affiche une erreur lors de la configuration et propose des correspondances candidates lorsque c'est possible.

## Source des données

Les données proviennent du flux officiel de Régie Essence Québec :

`https://regieessencequebec.ca/stations.geojson.gz`

La source amont est mise à jour environ toutes les 5 minutes.

Chaque capteur de carburant expose aussi des attributs de mise à jour du fournisseur, dont l'horodatage du dernier flux reçu et le nombre de minutes écoulées depuis la dernière mise à jour amont.

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Gabriel%20Bergeron-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/gabrielbergeron/ha-regie-essence-quebec.svg?style=for-the-badge
[releases]: https://github.com/gabrielbergeron/ha-regie-essence-quebec/releases
