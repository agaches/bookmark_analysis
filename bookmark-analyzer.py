#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Système d'analyse de bookmarks
------------------------------

Ce script principal coordonne l'ensemble du processus d'analyse des bookmarks.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Modules du projet - mise à jour des imports pour correspondre aux noms de fichiers
from bookmark_extractor import extract_bookmarks_from_html
from url_checker import check_urls
from content_downloader import download_content
from content_analyzer import analyze_content
from bookmark_categorizer import categorize_bookmarks
from recommendation_engine import generate_recommendations
from report_generator import generate_report

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bookmark_analyzer.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bookmark_analyzer")

def create_project_structure(output_dir):
    """Crée la structure de dossiers pour le projet."""
    directories = [
        "data",
        "data/raw",
        "data/processed",
        "data/content",
        "reports",
        "reports/charts",
        "reports/csv"
    ]
    
    for directory in directories:
        path = os.path.join(output_dir, directory)
        os.makedirs(path, exist_ok=True)
        logger.debug(f"Dossier créé: {path}")

def save_state(bookmarks, stage, output_dir):
    """Sauvegarde l'état du traitement à une étape donnée."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"data/processed/bookmarks_{stage}_{timestamp}.json")
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(bookmarks, f, ensure_ascii=False, indent=2)
    
    logger.info(f"État sauvegardé à l'étape: {stage}, fichier: {filename}")
    return filename

def main():
    parser = argparse.ArgumentParser(description="Système d'analyse et de tri de bookmarks")
    parser.add_argument("input_file", help="Fichier HTML de bookmarks exportés")
    parser.add_argument("--output-dir", default="output", help="Dossier de sortie pour les résultats")
    parser.add_argument("--skip-to", choices=["extract", "check", "download", "analyze", "categorize", "recommend", "report"], 
                        default="extract", help="Commencer à une étape spécifique (en chargeant les données de l'étape précédente)")
    parser.add_argument("--state-file", help="Fichier d'état à charger pour commencer à une étape spécifique")
    parser.add_argument("--max-urls", type=int, default=None, help="Nombre maximum d'URLs à traiter (pour les tests)")
    parser.add_argument("--delay", type=float, default=1.0, help="Délai entre les requêtes (en secondes)")
    parser.add_argument("--timeout", type=float, default=10.0, help="Timeout pour les requêtes HTTP (en secondes)")
    parser.add_argument("--user-agent", default="BookmarkAnalyzer/1.0", help="User-Agent à utiliser pour les requêtes")
    parser.add_argument("--no-download", action="store_true", help="Ignorer l'étape de téléchargement du contenu")
    args = parser.parse_args()

    # Créer la structure du projet
    create_project_structure(args.output_dir)
    
    start_time = time.time()
    logger.info(f"Démarrage de l'analyse des bookmarks: {args.input_file}")

    # Configuration des paramètres communs
    config = {
        "max_urls": args.max_urls,
        "delay": args.delay,
        "timeout": args.timeout,
        "user_agent": args.user_agent,
        "output_dir": args.output_dir
    }
    
    # Initialisation des bookmarks
    bookmarks = None
    
    # Charger depuis un fichier d'état si spécifié
    if args.state_file:
        try:
            with open(args.state_file, 'r', encoding='utf-8') as f:
                bookmarks = json.load(f)
            logger.info(f"État chargé depuis: {args.state_file}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'état: {e}")
            sys.exit(1)
    
    # Étape 1: Extraction des bookmarks
    if args.skip_to <= "extract" and not bookmarks:
        logger.info("Étape 1: Extraction des bookmarks")
        bookmarks = extract_bookmarks_from_html(args.input_file)
        
        # Sauvegarder une copie des données brutes
        raw_file = os.path.join(args.output_dir, "data/raw/bookmarks_raw.json")
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(bookmarks, f, ensure_ascii=False, indent=2)
        
        # Limiter le nombre d'URLs pour les tests si spécifié
        if config['max_urls']:
            bookmarks = bookmarks[:config['max_urls']]
            logger.info(f"Limité à {config['max_urls']} bookmarks pour les tests")
        
        logger.info(f"Nombre de bookmarks extraits: {len(bookmarks)}")
        save_state(bookmarks, "extracted", args.output_dir)
    
    # Étape 2: Vérification des URLs
    if args.skip_to <= "check":
        logger.info("Étape 2: Vérification de l'état des URLs")
        bookmarks = check_urls(bookmarks, **config)
        save_state(bookmarks, "checked", args.output_dir)
    
    # Étape 3: Téléchargement du contenu (peut être ignorée avec --no-download)
    if args.skip_to <= "download" and not args.no_download:
        logger.info("Étape 3: Téléchargement du contenu des pages")
        bookmarks = download_content(bookmarks, **config)
        save_state(bookmarks, "downloaded", args.output_dir)
    elif args.no_download:
        logger.info("Étape 3: Téléchargement du contenu ignoré (--no-download)")
    
    # Étape 4: Analyse du contenu
    if args.skip_to <= "analyze":
        logger.info("Étape 4: Analyse du contenu")
        bookmarks = analyze_content(bookmarks, **config)
        save_state(bookmarks, "analyzed", args.output_dir)
    
    # Étape 5: Catégorisation des bookmarks
    if args.skip_to <= "categorize":
        logger.info("Étape 5: Catégorisation des bookmarks")
        bookmarks = categorize_bookmarks(bookmarks, **config)
        save_state(bookmarks, "categorized", args.output_dir)
    
    # Étape 6: Génération des recommandations
    if args.skip_to <= "recommend":
        logger.info("Étape 6: Génération des recommandations")
        bookmarks = generate_recommendations(bookmarks, **config)
        save_state(bookmarks, "recommended", args.output_dir)
    
    # Génération du rapport final
    logger.info("Génération du rapport final")
    report_path = generate_report(bookmarks, args.output_dir)
    
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = elapsed_time % 60
    
    logger.info(f"Analyse terminée en {minutes}m {seconds:.2f}s")
    logger.info(f"Rapport généré: {report_path}")
    
    print(f"\nAnalyse terminée. Rapport disponible à: {report_path}")
    print(f"Durée totale: {minutes}m {seconds:.2f}s")
    print(f"Nombre de bookmarks analysés: {len(bookmarks)}")

if __name__ == "__main__":
    main()
