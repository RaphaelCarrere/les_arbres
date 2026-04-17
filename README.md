# Analyse des arbres et des ilôts de chaleurs à Paris

Ce dépôt contient le projet final de Python pour la Datascience de Raphaël CARRERE, Camille SIMONNOT et Maxine VOINSON.
Lisez ce Readme avant de lancer le projet. 

## Objectif

Ce projet a pour objectif d'analyser les ilôts de chaleurs à Paris en fonction des arbres sur la commune. 

---

## Installation des données
Pour faire fonctionner ce projet, vous devez :
1. Télécharger les contours IRIS sur https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_CONTOURS-IRIS?redirected_from=geoservices.ign.fr.
2. Dans Téléchargements et flux, choisissez le fichier Contours...IRIS en téléchargement. 
3. Réglez les filtres tels que : 
ZONE = FXX France métropolitaine
FORMAT = GPKG (Geopackage)
CRS = RGF93 v1 / Lambert-93 -- France
4. Téléchargez le fichier : CONTOURS-IRIS_3-0__GPKG_LAMB93_FXX_2026-01-01
5. Vous trouverez un fichier `iris.gpkg` dans 
6. Placer le fichier `iris.gpkg` dans le dossier nommé `data/` à la racine du projet.
7. Le script filtrera automatiquement les données pour ne garder que Paris.

---

## Contenu du projet

```
.
├── /data              # Fichier iris à placer dans ce dossier
├── 01_exploration_donnees.ipynb              # Fichier notebook à exécuter
├── 02_visualisation.ipynb              # Fichier notebook à exécuter
├── 03_modelisation.ipynb              # Fichier notebook à exécuter
├── requirements.txt        # Dépendances Python
├── README.md               # Présentation du projet
├── .gitignore              # Fichier à ignorer pour Github
```

---

## Données

Les données sur les arbres sont issues de data.gouv.fr et sont chargées directement dans le notebook via une URL publique. 

---
