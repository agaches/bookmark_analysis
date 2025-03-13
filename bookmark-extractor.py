#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'extraction des bookmarks
---------------------------------

Ce module est responsable de l'extraction des bookmarks à partir d'un fichier HTML exporté.
"""

import logging
import os
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger("bookmark_analyzer.extractor")

def extract_bookmarks_from_html(html_file):
    """
    Extrait les bookmarks d'un fichier HTML exporté depuis un navigateur.
    
    Args:
        html_file (str): Chemin vers le fichier HTML contenant les bookmarks exportés.
        
    Returns:
        list: Liste de dictionnaires contenant les informations des bookmarks.
    """
    logger.info(f"Extraction des bookmarks depuis: {html_file}")
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
    except Exception as e:
        logger.error(f"Erreur lors de l'ouverture du fichier HTML: {e}")
        return []
    
    bookmarks = []
    
    # Les bookmarks sont généralement dans des balises <a> avec l'attribut href
    # et potentiellement dans des structures de dossiers avec des balises <h3> pour les noms de dossiers
    
    # On commence par trouver toutes les balises <a> avec un attribut href
    links = soup.find_all('a', href=True)
    
    # Pour chaque lien, on extrait les informations pertinentes
    for i, link in enumerate(links):
        # Extraire l'URL
        url = link.get('href', '')
        
        # Vérifier si c'est une URL valide
        if not url or not url.startswith(('http://', 'https://')):
            continue
        
        # Extraire le titre
        title = link.get_text(strip=True)
        if not title:
            title = url
        
        # Extraire les métadonnées supplémentaires
        add_date = link.get('add_date', '')
        if add_date:
            try:
                # Convertir le timestamp en datetime (format généralement utilisé par les navigateurs)
                add_date = datetime.fromtimestamp(int(add_date)).isoformat()
            except:
                pass
        
        last_modified = link.get('last_modified', '')
        if last_modified:
            try:
                last_modified = datetime.fromtimestamp(int(last_modified)).isoformat()
            except:
                pass
        
        # Determiner le dossier parent
        folder = "Root"
        parent = link.parent
        while parent and parent.name != 'html':
            if parent.name == 'dl':
                # Remonter pour trouver le h3 précédent qui contient le nom du dossier
                h3 = parent.find_previous_sibling('h3')
                if h3:
                    folder = h3.get_text(strip=True)
                    break
            parent = parent.parent
        
        # Analyser le domaine
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Créer l'entrée du bookmark
        bookmark = {
            'id': i + 1,
            'url': url,
            'title': title,
            'domain': domain,
            'folder': folder,
            'add_date': add_date,
            'last_modified': last_modified,
            'tags': [],  # Les tags seront ajoutés ultérieurement
            'status': {
                'code': None,
                'accessible': None,
                'redirect': None,
                'redirect_url': None,
                'response_time': None,
                'ssl_valid': None,
                'last_checked': None
            },
            'content': {
                'downloaded': False,
                'path': None,
                'size': None,
                'mime_type': None,
                'download_date': None
            },
            'analysis': {
                'language': None,
                'keywords': [],
                'summary': None,
                'content_type': None,
                'text_length': None,
                'reading_time': None,
                'quality_score': None
            },
            'categorization': {
                'primary_category': None,
                'secondary_categories': [],
                'similarity_cluster': None
            },
            'recommendation': {
                'action': None,  # 'keep', 'archive', 'delete'
                'confidence': None,
                'reason': None
            }
        }
        
        bookmarks.append(bookmark)
    
    logger.info(f"Extraction terminée: {len(bookmarks)} bookmarks trouvés")
    return bookmarks

if __name__ == "__main__":
    # Test du module
    import sys
    import json
    
    if len(sys.argv) != 2:
        print("Usage: python bookmark_extractor.py <bookmarks.html>")
        sys.exit(1)
    
    # Configuration du logging pour les tests
    logging.basicConfig(level=logging.INFO)
    
    html_file = sys.argv[1]
    bookmarks = extract_bookmarks_from_html(html_file)
    
    print(f"Nombre de bookmarks extraits: {len(bookmarks)}")
    print(json.dumps(bookmarks[:2], indent=2, ensure_ascii=False))
