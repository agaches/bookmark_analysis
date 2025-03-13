#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'analyse du contenu
---------------------------

Ce module est responsable de l'analyse du contenu des pages web téléchargées.
"""

import logging
import os
import json
import re
import time
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
from bs4 import BeautifulSoup
from langdetect import detect, LangDetectException
import trafilatura
from trafilatura.settings import use_config
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from collections import Counter

logger = logging.getLogger("bookmark_analyzer.content_analyzer")

# Initialiser NLTK (télécharger les ressources nécessaires)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

def extract_main_content(html_content, url):
    """
    Extrait le contenu principal d'une page HTML en utilisant trafilatura.
    
    Args:
        html_content (bytes): Contenu HTML brut.
        url (str): URL de la page.
        
    Returns:
        tuple: (texte extrait, métadonnées)
    """
    try:
        # Configurer trafilatura
        config = use_config()
        config.set("DEFAULT", "MIN_OUTPUT_SIZE", "100")
        config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "100")
        
        # Extraire le contenu
        extracted = trafilatura.extract(
            html_content,
            url=url,
            output_format='xml',
            include_comments=False,
            include_tables=True,
            config=config
        )
        
        if not extracted:
            # Si trafilatura échoue, utiliser BeautifulSoup comme fallback
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Supprimer les scripts, styles et balises de navigation
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # Extraire le texte
            text = soup.get_text(separator=' ', strip=True)
            return text, {}
        
        # Analyser le XML retourné
        soup = BeautifulSoup(extracted, 'lxml-xml')
        
        # Extraire les métadonnées
        meta = {}
        
        # Titre
        title_elem = soup.find('title')
        if title_elem:
            meta['title'] = title_elem.get_text(strip=True)
        
        # Auteur
        author_elem = soup.find('author')
        if author_elem:
            meta['author'] = author_elem.get_text(strip=True)
        
        # Date
        date_elem = soup.find('date')
        if date_elem:
            meta['date'] = date_elem.get_text(strip=True)
        
        # Extraire le texte principal
        text = ''
        for p in soup.find_all(['p', 'head', 'list', 'quote', 'item']):
            text += p.get_text(strip=True) + '\n\n'
        
        return text.strip(), meta
    
    except Exception as e:
        logger.debug(f"Erreur lors de l'extraction du contenu pour {url}: {e}")
        return "", {}

def detect_language(text):
    """
    Détecte la langue du texte.
    
    Args:
        text (str): Texte à analyser.
        
    Returns:
        str: Code de langue (iso639-1) ou None en cas d'échec.
    """
    if not text or len(text.strip()) < 50:
        return None
    
    try:
        return detect(text)
    except LangDetectException:
        return None

def extract_keywords(text, lang='en', max_keywords=10):
    """
    Extrait les mots-clés principaux du texte.
    
    Args:
        text (str): Texte à analyser.
        lang (str): Code de langue.
        max_keywords (int): Nombre maximum de mots-clés à extraire.
        
    Returns:
        list: Liste des mots-clés avec leur score.
    """
    if not text:
        return []
    
    # Obtenir la liste des stopwords pour la langue
    try:
        stop_words = set(stopwords.words(lang if lang in stopwords.fileids() else 'english'))
    except:
        stop_words = set()
    
    # Tokeniser le texte
    words = word_tokenize(text.lower())
    
    # Filtrer les mots (longueur, stopwords, chiffres, etc.)
    words = [word for word in words if word.isalpha() and len(word) > 2 and word not in stop_words]
    
    # Calculer la fréquence des mots
    freq_dist = FreqDist(words)
    
    # Extraire les N mots les plus fréquents
    keywords = []
    for word, count in freq_dist.most_common(max_keywords * 2):
        # Éviter les mots trop courts ou trop longs
        if 3 <= len(word) <= 20:
            keywords.append((word, count))
        
        if len(keywords) >= max_keywords:
            break
    
    return keywords

def generate_summary(text, max_sentences=3):
    """
    Génère un résumé automatique du texte en extrayant les phrases les plus importantes.
    
    Args:
        text (str): Texte à résumer.
        max_sentences (int): Nombre maximum de phrases à inclure.
        
    Returns:
        str: Résumé du texte.
    """
    if not text:
        return ""
    
    # Diviser le texte en phrases
    sentences = sent_tokenize(text)
    
    # Si le texte est déjà court, le retourner tel quel
    if len(sentences) <= max_sentences:
        return text
    
    # Calculer la fréquence des mots
    words = word_tokenize(text.lower())
    word_freq = Counter(word for word in words if word.isalpha())
    
    # Calculer le score de chaque phrase
    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        score = 0
        for word in word_tokenize(sentence.lower()):
            if word.isalpha():
                score += word_freq[word]
        sentence_scores[i] = score / max(1, len(word_tokenize(sentence)))
    
    # Sélectionner les phrases les plus importantes
    best_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:max_sentences]
    best_sentences = sorted(best_sentences, key=lambda x: x[0])  # Trier par position originale
    
    # Générer le résumé
    summary = ' '.join(sentences[i] for i, _ in best_sentences)
    
    return summary

def detect_content_type(text, meta):
    """
    Détecte le type de contenu (article, documentation, commercial, etc.).
    
    Args:
        text (str): Texte à analyser.
        meta (dict): Métadonnées extraites.
        
    Returns:
        str: Type de contenu détecté.
    """
    if not text:
        return "unknown"
    
    # Calculer les caractéristiques du texte
    word_count = len(word_tokenize(text))
    sentence_count = len(sent_tokenize(text))
    avg_sentence_length = word_count / max(1, sentence_count)
    
    # Rechercher des motifs spécifiques
    patterns = {
        'documentation': [r'documentation', r'guide', r'tutorial', r'how[\s-]to', r'reference', r'manual', r'api'],
        'article': [r'article', r'blog', r'post', r'news'],
        'commercial': [r'buy', r'price', r'offer', r'discount', r'sale', r'shop', r'product'],
        'academic': [r'research', r'study', r'journal', r'paper', r'conference', r'abstract'],
        'forum': [r'forum', r'thread', r'comment', r'discussion', r'reply', r'post'],
    }
    
    scores = {content_type: 0 for content_type in patterns}
    
    # Calculer les scores pour chaque type de contenu
    for content_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            regex = re.compile(pattern, re.IGNORECASE)
            matches = regex.findall(text)
            scores[content_type] += len(matches)
    
    # Ajouter des heuristiques supplémentaires
    if avg_sentence_length > 25:
        scores['academic'] += 2
    elif avg_sentence_length < 15:
        scores['forum'] += 2
    
    if word_count > 1000:
        scores['article'] += 2
        scores['documentation'] += 1
    elif word_count < 300:
        scores['commercial'] += 1
    
    # Déterminer le type dominant
    max_score = 0
    content_type = "article"  # Type par défaut
    
    for ctype, score in scores.items():
        if score > max_score:
            max_score = score
            content_type = ctype
    
    return content_type

def calculate_reading_time(text, words_per_minute=200):
    """
    Calcule le temps de lecture estimé du texte.
    
    Args:
        text (str): Texte à analyser.
        words_per_minute (int): Vitesse de lecture moyenne.
        
    Returns:
        float: Temps de lecture estimé en minutes.
    """
    if not text:
        return 0
    
    word_count = len(word_tokenize(text))
    reading_time = word_count / words_per_minute
    
    return round(reading_time, 2)

def calculate_quality_score(bookmark, text, meta):
    """
    Calcule un score de qualité pour le contenu.
    
    Args:
        bookmark (dict): Bookmark avec ses métadonnées.
        text (str): Texte extrait.
        meta (dict): Métadonnées extraites.
        
    Returns:
        float: Score de qualité (0-100).
    """
    if not text:
        return 0
    
    score = 50  # Score de base
    
    # Longueur du texte (jusqu'à +20 points)
    text_length = len(text)
    if text_length > 10000:
        score += 20
    elif text_length > 5000:
        score += 15
    elif text_length > 2000:
        score += 10
    elif text_length > 1000:
        score += 5
    
    # Diversité du vocabulaire (jusqu'à +10 points)
    words = word_tokenize(text.lower())
    unique_words = set(word for word in words if word.isalpha())
    if len(words) > 0:
        vocabulary_ratio = len(unique_words) / len(words)
        score += int(vocabulary_ratio * 10)
    
    # Pénalité pour les temps de réponse lents (jusqu'à -5 points)
    response_time = bookmark['status'].get('response_time', 0)
    if response_time > 5:
        score -= 5
    elif response_time > 3:
        score -= 3
    elif response_time > 1:
        score -= 1
    
    # Bonus pour SSL valide (+5 points)
    if bookmark['status'].get('ssl_valid', False):
        score += 5
    
    # Pénalité pour redirection (-5 points)
    if bookmark['status'].get('redirect', False):
        score -= 5
    
    # Ajustement final
    score = max(0, min(100, score))
    
    return score

def analyze_bookmark_content(bookmark, config):
    """
    Analyse le contenu d'un bookmark.
    
    Args:
        bookmark (dict): Dictionnaire contenant les informations du bookmark.
        config (dict): Configuration pour l'analyse.
        
    Returns:
        dict: Bookmark mis à jour avec les informations d'analyse.
    """
    # Vérifier si le contenu a été téléchargé
    if not bookmark.get('content', {}).get('downloaded', False):
        return bookmark
    
    file_path = bookmark['content']['path']
    url = bookmark['url']
    
    try:
        # Charger le contenu du fichier
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Extraire le contenu principal
        text, meta = extract_main_content(content, url)
        
        if not text:
            logger.debug(f"Aucun contenu textuel extrait pour: {url}")
            return bookmark
        
        # Détecter la langue
        lang = detect_language(text)
        
        # Extraire les mots-clés
        keywords = extract_keywords(text, lang or 'en')
        
        # Générer un résumé
        summary = generate_summary(text)
        
        # Détecter le type de contenu
        content_type = detect_content_type(text, meta)
        
        # Calculer le temps de lecture
        reading_time = calculate_reading_time(text)
        
        # Calculer le score de qualité
        quality_score = calculate_quality_score(bookmark, text, meta)
        
        # Mettre à jour les informations d'analyse du bookmark
        bookmark['analysis'] = {
            'language': lang,
            'keywords': keywords,
            'summary': summary,
            'content_type': content_type,
            'text_length': len(text),
            'reading_time': reading_time,
            'quality_score': quality_score,
            'metadata': meta
        }
        
        logger.debug(f"Analyse terminée pour: {url}")
        
    except Exception as e:
        logger.debug(f"Erreur lors de l'analyse pour {url}: {str(e)}")
    
    return bookmark

def analyze_content(bookmarks, **config):
    """
    Fonction principale pour analyser le contenu des bookmarks.
    
    Args:
        bookmarks (list): Liste des bookmarks à analyser.
        **config: Configuration pour l'analyse.
        
    Returns:
        list: Liste des bookmarks mis à jour avec les informations d'analyse.
    """
    logger.info(f"Analyse du contenu pour {len(bookmarks)} bookmarks")
    
    # Compter les bookmarks avec contenu téléchargé
    with_content = sum(1 for b in bookmarks if b.get('content', {}).get('downloaded', False))
    logger.info(f"{with_content} bookmarks avec contenu téléchargé à analyser")
    
    try:
        # Utiliser ProcessPoolExecutor pour paralléliser l'analyse
        max_workers = config.get('max_workers', os.cpu_count() or 4)
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Créer les tâches
            futures = [executor.submit(analyze_bookmark_content, bookmark, config) 
                      for bookmark in bookmarks if bookmark.get('content', {}).get('downloaded', False)]
            
            # Utiliser tqdm pour afficher une barre de progression
            results = []
            for f in tqdm(futures, total=len(futures), desc="Analyse du contenu"):
                results.append(f.result())
        
        # Ajouter les bookmarks sans contenu
        for bookmark in bookmarks:
            if not bookmark.get('content', {}).get('downloaded', False):
                results.append(bookmark)
        
        # Trier les bookmarks par ID pour maintenir l'ordre original
        results.sort(key=lambda b: b['id'])
        
        # Compter les résultats
        analyzed = sum(1 for b in results if 'analysis' in b and b['analysis'].get('text_length') is not None)
        
        logger.info(f"Analyse terminée: {analyzed} bookmarks analysés sur {len(bookmarks)}")
        
        return results
    
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du contenu: {e}")
        return bookmarks

if __name__ == "__main__":
    # Test du module
    import sys
    from urllib.parse import urlparse
    
    if len(sys.argv) != 2:
        print("Usage: python content_analyzer.py <bookmarks.json>")
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
    
    # Filtrer pour ne garder que les bookmarks avec contenu téléchargé
    test_bookmarks = [b for b in bookmarks if b.get('content', {}).get('downloaded', False)][:3]
    
    if not test_bookmarks:
        print("Aucun bookmark avec contenu téléchargé trouvé. Veuillez d'abord exécuter content_downloader.py.")
        sys.exit(1)
    
    # Configuration de test
    config = {
        'max_workers': 2
    }
    
    # Analyser le contenu
    updated_bookmarks = analyze_content(test_bookmarks, **config)
    
    # Afficher les résultats
    for bookmark in updated_bookmarks:
        analysis = bookmark.get('analysis', {})
        print(f"URL: {bookmark['url']}")
        print(f"  Langue: {analysis.get('language')}")
        print(f"  Type de contenu: {analysis.get('content_type')}")
        print(f"  Longueur du texte: {analysis.get('text_length')} caractères")
        print(f"  Temps de lecture: {analysis.get('reading_time')} minutes")
        print(f"  Score de qualité: {analysis.get('quality_score')}")
        
        keywords = analysis.get('keywords', [])
        if keywords:
            print(f"  Mots-clés: {', '.join(word for word, _ in keywords[:5])}")
        
        print(f"  Résumé: {analysis.get('summary')[:100]}...")
        print()
