#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de vérification des URLs
-------------------------------

Ce module est responsable de la vérification de l'état des URLs des bookmarks.
"""

import logging
import asyncio
import aiohttp
import time
import ssl
import certifi
import json
from datetime import datetime
from urllib.parse import urlparse
from tqdm import tqdm

logger = logging.getLogger("bookmark_analyzer.url_checker")

async def check_url(session, bookmark, config):
    """
    Vérifie l'état d'une URL de manière asynchrone.
    
    Args:
        session (aiohttp.ClientSession): Session HTTP pour les requêtes.
        bookmark (dict): Dictionnaire contenant les informations du bookmark.
        config (dict): Configuration pour la vérification.
        
    Returns:
        dict: Bookmark mis à jour avec les informations d'état.
    """
    url = bookmark['url']
    timeout = aiohttp.ClientTimeout(total=config.get('timeout', 10))
    
    start_time = time.time()
    redirect_url = None
    status_code = None
    ssl_valid = None
    
    try:
        # Effectuer la requête HEAD d'abord (plus légère)
        async with session.head(url, allow_redirects=False, timeout=timeout) as response:
            status_code = response.status
            
            # Vérifier si c'est une redirection
            if 300 <= status_code < 400:
                redirect_url = response.headers.get('Location', None)
                
                # Si la redirection est relative, la rendre absolue
                if redirect_url and not redirect_url.startswith(('http://', 'https://')):
                    parsed_url = urlparse(url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    if redirect_url.startswith('/'):
                        redirect_url = base_url + redirect_url
                    else:
                        path = parsed_url.path
                        if path.endswith('/'):
                            redirect_url = base_url + path + redirect_url
                        else:
                            # Enlever le dernier segment du chemin
                            path = '/'.join(path.split('/')[:-1]) + '/'
                            redirect_url = base_url + path + redirect_url
            
            # Pour les 4xx et 5xx, faire une requête GET pour confirmer
            if status_code >= 400:
                try:
                    async with session.get(url, timeout=timeout, allow_redirects=True) as get_response:
                        status_code = get_response.status
                        if 300 <= status_code < 400:
                            redirect_url = get_response.headers.get('Location', None)
                except Exception:
                    # En cas d'erreur sur la requête GET, conserver le code d'état original
                    pass
        
        # Vérifier la validité du certificat SSL
        if url.startswith('https://'):
            try:
                # Créer un contexte SSL avec les certificats de confiance
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                parsed_url = urlparse(url)
                
                # Vérifier manuellement le certificat
                conn = ssl_context.wrap_socket(
                    ssl.socket(),
                    server_hostname=parsed_url.netloc
                )
                conn.connect((parsed_url.netloc, 443))
                ssl_valid = True
                conn.close()
            except Exception:
                ssl_valid = False
                logger.debug(f"Certificat SSL invalide pour: {url}")
        else:
            ssl_valid = None  # Non applicable pour HTTP
        
    except aiohttp.ClientError as e:
        logger.debug(f"Erreur lors de la vérification de {url}: {str(e)}")
        if isinstance(e, aiohttp.ClientConnectorError):
            status_code = 0  # Indique une erreur de connexion
        elif isinstance(e, aiohttp.ClientResponseError):
            status_code = e.status
        else:
            status_code = -1  # Erreur générique
    except asyncio.TimeoutError:
        logger.debug(f"Timeout lors de la vérification de {url}")
        status_code = 408  # Request Timeout
    except Exception as e:
        logger.debug(f"Exception inattendue pour {url}: {str(e)}")
        status_code = -2  # Erreur inconnue
    
    response_time = time.time() - start_time
    
    # Mettre à jour les informations d'état du bookmark
    bookmark['status'] = {
        'code': status_code,
        'accessible': 200 <= (status_code or 0) < 400,
        'redirect': 300 <= (status_code or 0) < 400,
        'redirect_url': redirect_url,
        'response_time': response_time,
        'ssl_valid': ssl_valid,
        'last_checked': datetime.now().isoformat()
    }
    
    return bookmark

async def check_urls_async(bookmarks, config):
    """
    Vérifie l'état de plusieurs URLs de manière asynchrone.
    
    Args:
        bookmarks (list): Liste des bookmarks à vérifier.
        config (dict): Configuration pour la vérification.
        
    Returns:
        list: Liste des bookmarks mis à jour avec les informations d'état.
    """
    delay = config.get('delay', 1)
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
            domain = bookmark['domain']
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(bookmark)
        
        # Créer les tâches avec des délais adaptés
        for domain, domain_bookmarks in domains.items():
            for i, bookmark in enumerate(domain_bookmarks):
                # Ajouter un délai supplémentaire pour les bookmarks du même domaine
                domain_delay = i * delay / 2
                
                # Créer une tâche avec un délai
                task = asyncio.create_task(
                    check_url_with_delay(session, bookmark, config, domain_delay)
                )
                tasks.append(task)
        
        # Utiliser tqdm pour afficher une barre de progression
        updated_bookmarks = []
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Vérification des URLs"):
            bookmark = await f
            updated_bookmarks.append(bookmark)
        
        # Trier les bookmarks par ID pour maintenir l'ordre original
        updated_bookmarks.sort(key=lambda b: b['id'])
        
        return updated_bookmarks

async def check_url_with_delay(session, bookmark, config, additional_delay=0):
    """
    Vérifie l'état d'une URL avec un délai.
    
    Args:
        session (aiohttp.ClientSession): Session HTTP pour les requêtes.
        bookmark (dict): Dictionnaire contenant les informations du bookmark.
        config (dict): Configuration pour la vérification.
        additional_delay (float): Délai supplémentaire avant d'effectuer la requête.
        
    Returns:
        dict: Bookmark mis à jour avec les informations d'état.
    """
    if additional_delay > 0:
        await asyncio.sleep(additional_delay)
    
    return await check_url(session, bookmark, config)

def check_urls(bookmarks, **config):
    """
    Fonction principale pour vérifier l'état des URLs des bookmarks.
    
    Args:
        bookmarks (list): Liste des bookmarks à vérifier.
        **config: Configuration pour la vérification.
        
    Returns:
        list: Liste des bookmarks mis à jour avec les informations d'état.
    """
    logger.info(f"Vérification de {len(bookmarks)} URLs")
    
    try:
        # Exécuter la vérification asynchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        updated_bookmarks = loop.run_until_complete(check_urls_async(bookmarks, config))
        loop.close()
        
        # Compter les résultats
        accessible = sum(1 for b in updated_bookmarks if b['status']['accessible'])
        redirected = sum(1 for b in updated_bookmarks if b['status']['redirect'])
        
        logger.info(f"Vérification terminée: {accessible} accessibles, {redirected} redirigés, {len(bookmarks) - accessible} inaccessibles")
        
        return updated_bookmarks
    
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des URLs: {e}")
        return bookmarks

if __name__ == "__main__":
    # Test du module
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python url_checker.py <bookmarks.json>")
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
    
    # Limiter à 10 bookmarks pour les tests
    test_bookmarks = bookmarks[:10]
    
    # Configuration de test
    config = {
        'timeout': 10,
        'delay': 1,
        'user_agent': 'BookmarkAnalyzer-Test/1.0'
    }
    
    # Vérifier les URLs
    updated_bookmarks = check_urls(test_bookmarks, **config)
    
    # Afficher les résultats
    for bookmark in updated_bookmarks:
        status = bookmark['status']
        print(f"URL: {bookmark['url']}")
        print(f"  Code: {status['code']}")
        print(f"  Accessible: {status['accessible']}")
        print(f"  Redirection: {status['redirect']} -> {status['redirect_url']}")
        print(f"  Temps de réponse: {status['response_time']:.2f}s")
        print(f"  SSL valide: {status['ssl_valid']}")
        print()
