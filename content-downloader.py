#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de téléchargement du contenu
-----------------------------------

Ce module est responsable du téléchargement et du stockage du contenu des pages web.
"""

import logging
import asyncio
import aiohttp
import os
import time
import json
import hashlib
from datetime import datetime
from urllib.parse import urlparse
from tqdm import tqdm

logger = logging.getLogger("bookmark_analyzer.content_downloader")

async def download_page_content(session, bookmark, config):
    """
    Télécharge le contenu d'une page web de manière asynchrone.
    
    Args:
        session (aiohttp.ClientSession): Session HTTP pour les requêtes.
        bookmark (dict): Dictionnaire contenant les informations du bookmark.
        config (dict): Configuration pour le téléchargement.
        
    Returns:
        dict: Bookmark mis à jour avec les informations de contenu.
    """
    # Ne pas télécharger si la page n'est pas accessible
    if not bookmark['status'].get('accessible', False):
        logger.debug(f"URL non accessible, téléchargement ignoré: {bookmark['url']}")
        return bookmark
    
    url = bookmark['url']
    # Si l'URL est redirigée, utiliser l'URL finale
    if bookmark['status'].get('redirect', False) and bookmark['status'].get('redirect_url'):
        url = bookmark['status']['redirect_url']
        logger.debug(f"Utilisation de l'URL de redirection: {url}")
    
    timeout = aiohttp.ClientTimeout(total=config.get('timeout', 30))  # Timeout plus long pour le téléchargement
    
    try:
        async with session.get(url, timeout=timeout) as response:
            # Vérifier le code de statut
            if response.status != 200:
                logger.debug(f"Statut de réponse inattendu: {response.status} pour {url}")
                bookmark['content'] = {
                    'downloaded': False,
                    'error': f'status_code: {response.status}',
                    'download_date': datetime.now().isoformat(),
                    'url_used': url
                }
                return bookmark
            
            # Déterminer le type MIME
            content_type = response.headers.get('Content-Type', 'text/html')
            
            # Générer un nom de fichier unique basé sur l'URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace(':', '_')  # Remplacer les caractères non valides
            path = parsed_url.path.strip('/')
            if not path:
                path = 'index'
            else:
                # Nettoyer le chemin pour un nom de fichier valide
                path = path.replace('/', '_')
                # Tronquer si trop long
                if len(path) > 100:
                    path = path[:100]
            
            # Utiliser un hash pour garantir l'unicité
            url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
            timestamp = datetime.now().strftime("%Y%m%d")
            
            # Créer le dossier pour le domaine
            content_dir = os.path.join(config['output_dir'], 'data/content', domain)
            os.makedirs(content_dir, exist_ok=True)
            
            # Déterminer l'extension de fichier en fonction du type MIME
            extension = '.html'
            if 'json' in content_type:
                extension = '.json'
            elif 'xml' in content_type:
                extension = '.xml'
            elif 'text/plain' in content_type:
                extension = '.txt'
            
            # Construire le chemin du fichier
            filename = f"{path}_{url_hash}_{timestamp}{extension}"
            file_path = os.path.join(content_dir, filename)
            
            # Télécharger le contenu
            content = await response.read()
            
            # Enregistrer le contenu
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Mettre à jour les informations de contenu du bookmark
            bookmark['content'] = {
                'downloaded': True,
                'path': file_path,
                'size': len(content),
                'mime_type': content_type,
                'download_date': datetime.now().isoformat(),
                'url_used': url  # Enregistrer l'URL utilisée (peut être différente de l'URL originale en cas de redirection)
            }
            
            logger.debug(f"Contenu téléchargé pour: {url}, taille: {len(content)} octets, chemin: {file_path}")
            
    except aiohttp.ClientError as e:
        logger.debug(f"Erreur lors du téléchargement de {url}: {str(e)}")
        bookmark['content'] = {
            'downloaded': False,
            'error': f'client_error: {str(e)}',
            'download_date': datetime.now().isoformat(),
            'url_used': url
        }
    except asyncio.TimeoutError:
        logger.debug(f"Timeout lors du téléchargement de {url}")
        bookmark['content'] = {
            'downloaded': False,
            'error': 'timeout',
            'download_date': datetime.now().isoformat(),
            'url_used': url
        }
    except Exception as e:
        logger.debug(f"Exception inattendue pour {url}: {str(e)}")
        bookmark['content'] = {
            'downloaded': False,
            'error': f'unexpected_error: {str(e)}',
            'download_date': datetime.now().isoformat(),
            'url_used': url
        }
    
    return bookmark

async def download_content_with_delay(session, bookmark, config, additional_delay=0):
    """
    Télécharge le contenu d'une page avec un délai.
    
    Args:
        session (aiohttp.ClientSession): Session HTTP pour les requêtes.
        bookmark (dict): Dictionnaire contenant les informations du bookmark.
        config (dict): Configuration pour le téléchargement.
        additional_delay (float): Délai supplémentaire avant d'effectuer la requête.
        
    Returns:
        dict: Bookmark mis à jour avec les informations de contenu.
    """
    if additional_delay > 0:
        await asyncio.sleep(additional_delay)
    
    return await download_page_content(session, bookmark, config)

async def download_content_async(bookmarks, config):
    """
    Télécharge le contenu de plusieurs pages de manière asynchrone.
    
    Args:
        bookmarks (list): Liste des bookmarks dont le contenu doit être téléchargé.
        config (dict): Configuration pour le téléchargement.
        
    Returns:
        list: Liste des bookmarks mis à jour avec les informations de contenu.
    """
    delay = config.get('delay', 2)  # Délai plus long pour le téléchargement
    user_agent = config.get('user_agent', 'BookmarkAnalyzer/1.0')
    connector = aiohttp.TCPConnector(ssl=False)  # Désactiver la vérification SSL par défaut
    
    headers = {
        'User-Agent': user_agent
    }
    
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        tasks = []
        
        # Regrouper les tâches par domaine pour éviter de surcharger un même serveur
        domains = {}
        for bookmark in bookmarks:
            # Ne considérer que les bookmarks accessibles
            if not bookmark['status'].get('accessible', False):
                continue
                
            domain = bookmark['domain']
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(bookmark)
        
        # Créer les tâches avec des délais adaptés
        for domain, domain_bookmarks in domains.items():
            for i, bookmark in enumerate(domain_bookmarks):
                # Ajouter un délai supplémentaire pour les bookmarks du même domaine
                domain_delay = i * delay
                
                # Créer une tâche avec un délai
                task = asyncio.create_task(
                    download_content_with_delay(session, bookmark, config, domain_delay)
                )
                tasks.append(task)
        
        # Utiliser tqdm pour afficher une barre de progression
        updated_bookmarks = []
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Téléchargement du contenu"):
            bookmark = await f
            updated_bookmarks.append(bookmark)
        
        # Ajouter les bookmarks non téléchargeables
        non_downloaded = []
        for bookmark in bookmarks:
            if not bookmark['status'].get('accessible', False):
                bookmark['content'] = {
                    'downloaded': False,
                    'error': 'inaccessible_url',
                    'download_date': datetime.now().isoformat()
                }
                non_downloaded.append(bookmark)
        
        updated_bookmarks.extend(non_downloaded)
        
        # Trier les bookmarks par ID pour maintenir l'ordre original
        updated_bookmarks.sort(key=lambda b: b['id'])
        
        return updated_bookmarks

def download_content(bookmarks, **config):
    """
    Fonction principale pour télécharger le contenu des pages web des bookmarks.
    
    Args:
        bookmarks (list): Liste des bookmarks dont le contenu doit être téléchargé.
        **config: Configuration pour le téléchargement.
        
    Returns:
        list: Liste des bookmarks mis à jour avec les informations de contenu.
    """
    logger.info(f"Téléchargement du contenu pour {len(bookmarks)} bookmarks")
    
    # Vérifier et compléter la configuration
    if 'output_dir' not in config:
        config['output_dir'] = 'output'
    
    # Créer le dossier de contenu s'il n'existe pas
    content_dir = os.path.join(config['output_dir'], 'data/content')
    os.makedirs(content_dir, exist_ok=True)
    
    try:
        # Exécuter le téléchargement asynchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        updated_bookmarks = loop.run_until_complete(download_content_async(bookmarks, config))
        loop.close()
        
        # Compter les résultats
        downloaded = sum(1 for b in updated_bookmarks if b.get('content', {}).get('downloaded', False))
        
        logger.info(f"Téléchargement terminé: {downloaded} pages téléchargées sur {len(bookmarks)} bookmarks")
        
        return updated_bookmarks
    
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement du contenu: {e}")
        return bookmarks

if __name__ == "__main__":
    # Test du module
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python content_downloader.py <bookmarks.json>")
        sys.exit(1)
    
    # Configuration du logging pour les tests
    logging.basicConfig(level=logging.INFO)
    
    # Charger les bookmarks
    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            bookmarks = json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement du fichier JSON: {e}")
        sys.exit(1)
    
    # Limiter à 5 bookmarks pour les tests
    test_bookmarks = bookmarks[:5]
    
    # Configuration de test
    config = {
        'timeout': 30,
        'delay': 2,
        'user_agent': 'BookmarkAnalyzer-Test/1.0',
        'output_dir': 'output'
    }
    
    # Créer le dossier de sortie
    os.makedirs(os.path.join(config['output_dir'], 'data/content'), exist_ok=True)
    
    # Télécharger le contenu
    updated_bookmarks = download_content(test_bookmarks, **config)
    
    # Afficher les résultats
    for bookmark in updated_bookmarks:
        content = bookmark.get('content', {})
        if content.get('downloaded', False):
            print(f"URL: {bookmark['url']}")
            print(f"  Téléchargé: {content['downloaded']}")
            print(f"  Chemin: {content['path']}")
            print(f"  Taille: {content['size']} octets")
            print(f"  Type MIME: {content['mime_type']}")
            print()
        else:
            print(f"URL: {bookmark['url']}")
            print(f"  Non téléchargé: {content.get('error', 'inconnu')}")
            print()