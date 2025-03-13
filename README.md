# Système d'analyse de bookmarks

Un outil complet pour analyser, trier et évaluer vos bookmarks de navigateur.

## Description

Ce système automatisé analyse vos bookmarks exportés afin de vous aider à :
- Identifier les liens morts ou redirigés
- Évaluer la pertinence et la qualité du contenu
- Catégoriser automatiquement vos favoris
- Détecter les doublons
- Obtenir des recommandations (conserver, archiver, supprimer)
- Générer un rapport détaillé de l'analyse

## Installation

### Prérequis

- Python 3.7 ou supérieur
- pip (gestionnaire de paquets Python)

### Dépendances

Installez les dépendances requises :

```bash
pip install -r requirements.txt
```

Le fichier `requirements.txt` contient les bibliothèques suivantes :
```
requests>=2.28.1
beautifulsoup4>=4.11.1
aiohttp>=3.8.3
tqdm>=4.64.1
trafilatura>=1.4.0
langdetect>=1.0.9
nltk>=3.7
scikit-learn>=1.1.3
matplotlib>=3.6.2
pandas>=1.5.1
certifi>=2022.9.24
```

### Configuration initiale

Lors de la première exécution, certains modules comme NLTK peuvent nécessiter le téléchargement de données supplémentaires. Le système les téléchargera automatiquement si nécessaire.

## Comment utiliser le système

### Étape 1 : Exporter vos bookmarks

1. Depuis votre navigateur (Chrome, Firefox, etc.), exportez vos bookmarks au format HTML :
   - **Chrome** : Gestionnaire de favoris > ⋮ > Exporter les favoris
   - **Firefox** : Bibliothèque > Marque-pages > Afficher tous les marque-pages > Importation et sauvegarde > Exporter les marque-pages
   - **Edge** : Favoris > ⋯ > Gérer les favoris > ⋯ > Exporter les favoris

2. Sauvegardez le fichier HTML résultant dans un emplacement accessible.

### Étape 2 : Exécuter l'analyse

Utilisez le script principal pour analyser vos bookmarks :

```bash
python bookmark_analyzer.py chemin/vers/bookmarks.html --output-dir dossier/sortie
```

Options disponibles :
- `--output-dir` : Dossier où seront stockés les résultats (défaut : `output`)
- `--max-urls N` : Limite le nombre d'URLs à analyser (pratique pour tester)
- `--delay 2.0` : Définit le délai entre les requêtes en secondes (défaut : 1.0)
- `--timeout 20.0` : Définit le timeout des requêtes HTTP en secondes (défaut : 10.0)
- `--user-agent "Mon Agent"` : Définit le User-Agent à utiliser pour les requêtes

### Étape 3 : Consulter les résultats

Une fois l'analyse terminée, consultez les résultats :

1. Ouvrez le rapport HTML généré dans votre navigateur :
   ```
   dossier/sortie/reports/bookmark_analysis_report.html
   ```

2. Explorez les différentes sections du rapport :
   - Résumé global
   - Graphiques d'analyse
   - Distribution des catégories
   - Recommandations détaillées
   - Détection des doublons
   - Liste complète des bookmarks analysés

3. Consultez les fichiers CSV pour des analyses plus poussées :
   ```
   dossier/sortie/reports/csv/
   ```

### Reprise après interruption

Si l'analyse est interrompue, vous pouvez la reprendre à une étape spécifique :

```bash
python bookmark_analyzer.py chemin/vers/bookmarks.html --skip-to analyze --state-file chemin/vers/état.json
```

Options pour `--skip-to` :
- `extract` : Démarre depuis l'extraction (par défaut)
- `check` : Démarre depuis la vérification des URLs
- `download` : Démarre depuis le téléchargement du contenu
- `analyze` : Démarre depuis l'analyse du contenu
- `categorize` : Démarre depuis la catégorisation
- `recommend` : Démarre depuis la génération des recommandations
- `report` : Génère uniquement le rapport

## Exemple d'utilisation

```bash
# Analyse complète
python bookmark_analyzer.py mes_favoris.html --output-dir resultats

# Test rapide avec seulement 50 bookmarks
python bookmark_analyzer.py mes_favoris.html --max-urls 50

# Analyse avec délai plus long entre les requêtes (pour les serveurs sensibles)
python bookmark_analyzer.py mes_favoris.html --delay 3.0

# Reprise après interruption
python bookmark_analyzer.py mes_favoris.html --skip-to download --state-file resultats/data/processed/bookmarks_checked_20230215_143022.json
```

## Structure des résultats

```
output/
├── data/
│   ├── raw/              # Copies des données brutes
│   ├── processed/        # États intermédiaires du traitement
│   └── content/          # Contenu HTML téléchargé (par domaine)
└── reports/
    ├── charts/           # Graphiques générés
    ├── csv/              # Exports CSV des analyses
    ├── report_data.json  # Données d'analyse au format JSON
    └── bookmark_analysis_report.html  # Rapport principal
```

## Interprétation des recommandations

Le système fournit les recommandations suivantes :

- **keep** : Bookmark de bonne qualité à conserver
- **update** : Bookmark à mettre à jour (généralement en raison d'une redirection)
- **archive** : Bookmark potentiellement obsolète ou rarement utilisé
- **delete** : Bookmark inaccessible ou de très mauvaise qualité
- **replace** : Bookmark qui pourrait être remplacé par une alternative de meilleure qualité
- **review** : Bookmark nécessitant une vérification manuelle

## Licence

Ce projet est distribué sous licence MIT.