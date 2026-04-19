# Analyse des arbres à Paris

Ce dépôt contient le projet final de Python pour la Datascience de Raphaël CARRERE, Camille SIMONNOT et Maxine VOINSON.
Lisez ce Readme avant de lancer le projet. 

## Objectif

Ce projet a pour objectif d'analyser les populations d'arbres à Paris en fonction des IRIS (géographie parisienne). 

---

## Installation des données

Le chargement des données et le nettoyage des bases se fait directement dans notre fichier main 'Les_arbres_de_Paris.ipynb'. 

---

## Contenu du projet

```

├── les_arbres
    ├── notebook   
        ├── Les_arbres_de_Paris.ipynb           # Fichier notebook à exécuter
    ├── src
        ├── utils.py                    # Fichier contenant les fonctions nécessaires au code   
    ├── requirements.txt        # Dépendances Python
    ├── README.md               # Présentation du projet
    ├── .gitignore              # Fichier à ignorer pour Github
```

---

## Données

Les données sur les arbres sont issues de data.gouv.fr et sont chargées directement dans le notebook via une URL publique. Les données IRIS proviennent aussi de bases de données publiques et ont été chargées sur le cluster. 

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/RaphaelCarrere/les_arbres.git
cd les_arbres
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

---

## 3. Exécution

Ouvrir :

```
Les_arbres_de_Paris.ipynb
```

Exécuter toutes les cellules (`Run All`) pour reproduire les résultats.


