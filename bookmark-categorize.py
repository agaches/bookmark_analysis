#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de catégorisation des bookmarks
--------------------------------------

Ce module est responsable de la catégorisation et de l'organisation des bookmarks
basées sur leur contenu et leurs métadonnées.
"""

import logging
import json
import numpy as np
from collections import Counter, defaultdict
import re
from urllib.parse import urlparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

logger = logging.getLogger("bookmark_analyzer.categorizer")

# Catégories prédéfinies et mots-clés associés
PREDEFINED_CATEGORIES = {
    'Technologie et Développement': [
        'programming', 'code', 'developer', 'software', 'github', 'stack overflow', 'api',
        'python', 'javascript', 'java', 'c++', 'framework', 'web', 'database', 'sql',
        'cloud', 'aws', 'azure', 'devops', 'docker', 'kubernetes', 'linux', 'windows',
        'server', 'network', 'security', 'algorithm', 'data structure', 'machine learning'
    ],
    'Actualités et Médias': [
        'news', 'article', 'blog', 'magazine', 'journal', 'media', 'press', 'reporter',
        'cnn', 'bbc', 'nytimes', 'guardian', 'reuters', 'bloomberg', 'huffpost', 'fox',
        'breaking', 'headline', 'politics', 'world', 'economy', 'report', 'analysis'
    ],
    'Sciences et Recherche': [
        'science', 'research', 'study', 'paper', 'journal', 'academic', 'scientific',
        'physics', 'chemistry', 'biology', 'mathematics', 'astronomy', 'nature', 'theory',
        'experiment', 'laboratory', 'professor', 'university', 'scholar', 'publication',
        'conference', 'thesis', 'hypothesis', 'data', 'statistics'
    ],
    'Arts et Culture': [
        'art', 'culture', 'museum', 'gallery', 'exhibition', 'painting', 'sculpture',
        'artist', 'literature', 'poetry', 'novel', 'book', 'writer', 'author', 'music',
        'film', 'movie', 'cinema', 'theatre', 'theater', 'dance', 'performance', 'heritage',
        'history', 'design', 'creative'
    ],
    'Commerce et Shopping': [
        'shop', 'store', 'shopping', 'product', 'price', 'discount', 'sale', 'offer',
        'buy', 'purchase', 'market', 'amazon', 'ebay', 'etsy', 'walmart', 'ecommerce',
        'retail', 'brand', 'fashion', 'clothing', 'electronics', 'furniture', 'deal',
        'order', 'shipping', 'customer', 'review'
    ],
    'Réseaux sociaux': [
        'social', 'media', 'facebook', 'twitter', 'instagram', 'tiktok', 'linkedin',
        'pinterest', 'reddit', 'youtube', 'snapchat', 'whatsapp', 'telegram', 'discord',
        'post', 'share', 'like', 'follow', 'friend', 'connection', 'profile', 'message',
        'community', 'viral', 'trend'
    ],
    'Éducation et Formation': [
        'education', 'learning', 'course', 'tutorial', 'lesson', 'school', 'college',
        'university', 'student', 'teacher', 'professor', 'class', 'lecture', 'curriculum',
        'study', 'exam', 'quiz', 'test', 'assignment', 'homework', 'mooc', 'udemy',
        'coursera', 'edx', 'khan academy', 'educational'
    ],
    'Santé et Bien-être': [
        'health', 'wellness', 'medical', 'doctor', 'hospital', 'clinic', 'medicine',
        'fitness', 'exercise', 'yoga', 'diet', 'nutrition', 'healthy', 'disease', 'symptom',
        'therapy', 'mental health', 'psychology', 'meditation', 'mindfulness', 'workout',
        'weight loss', 'vitamin', 'supplement', 'organic', 'natural'
    ],
    'Voyage et Tourisme': [
        'travel', 'tourism', 'vacation', 'holiday', 'trip', 'tour', 'flight', 'hotel',
        'resort', 'booking', 'accommodation', 'destination', 'adventure', 'guide', 'map',
        'tourist', 'beach', 'mountain', 'city', 'country', 'abroad', 'passport', 'visa',
        'backpacking', 'sightseeing', 'landmark', 'attraction'
    ],
    'Cuisine et Gastronomie': [
        'food', 'recipe', 'cooking', 'cuisine', 'chef', 'restaurant', 'ingredient',
        'meal', 'dinner', 'lunch', 'breakfast', 'dessert', 'baking', 'kitchen', 'gourmet',
        'vegetarian', 'vegan', 'organic', 'tasty', 'delicious', 'flavor', 'menu',
        'dish', 'culinary', 'diet', 'nutrition'
    ],
    'Divertissement et Loisirs': [
        'entertainment', 'game', 'gaming', 'play', 'fun', 'hobby', 'sport', 'outdoor',
        'movie', 'film', 'tv', 'television', 'series', 'show', 'stream', 'netflix',
        'disney', 'amazon prime', 'hulu', 'spotify', 'music', 'podcast', 'party',
        'festival', 'concert', 'event', 'leisure'
    ],
    'Finance et Économie': [
        'finance', 'economy', 'money', 'investment', 'stock', 'market', 'trading', 'bank',
        'banking', 'loan', 'mortgage', 'credit', 'debt', 'tax', 'income', 'expense',
        'budget', 'saving', 'retirement', 'insurance', 'wealth', 'financial', 'economic',
        'business', 'entrepreneur', 'startup', 'company'
    ],
    'Outils et Utilitaires': [
        'tool', 'utility', 'app', 'application', 'software', 'calculator', 'converter',
        'translator', 'dictionary', 'note', 'calendar', 'reminder', 'organizer', 'task',
        'productivity', 'efficiency', 'management', 'planning', 'to-do', 'checklist',
        'download', 'generator', 'analyzer', 'scanner', 'monitor'
    ]


def prepare_bookmark_text(bookmark):
    """
    Prépare le texte du bookmark pour la catégorisation.
    
    Args:
        bookmark (dict): Dictionnaire contenant les informations du bookmark.
        
    Returns:
        str: Texte préparé pour l'analyse.
    """
    text_parts = []
    
    # Ajouter le titre (avec plus de poids)
    title = bookmark.get('title', '')
    if title:
        text_parts.append(title + ' ' + title)  # Doubler pour plus de poids
    
    # Ajouter le nom de domaine
    domain = bookmark.get('domain', '')
    if domain:
        text_parts.append(domain.replace('.', ' '))
    
    # Ajouter le chemin de l'URL
    parsed_url = urlparse(bookmark.get('url', ''))
    path = parsed_url.path
    if path:
        # Nettoyer et séparer les segments du chemin
        path_parts = re.sub(r'[^a-zA-Z0-9\s]', ' ', path).split()
        text_parts.extend(path_parts)
    
    # Ajouter les mots-clés d'analyse si disponibles
    analysis = bookmark.get('analysis', {})
    keywords = analysis.get('keywords', [])
    if keywords:
        # Ajouter les mots-clés avec leur fréquence comme poids
        for word, count in keywords:
            text_parts.extend([word] * min(count, 5))  # Limiter la répétition
    
    # Ajouter le résumé si disponible
    summary = analysis.get('summary', '')
    if summary:
        text_parts.append(summary)
    
    # Ajouter le type de contenu
    content_type = analysis.get('content_type', '')
    if content_type:
        text_parts.append(content_type)
    
    # Ajouter la langue
    language = analysis.get('language', '')
    if language:
        text_parts.append(language)
    
    # Joindre toutes les parties et normaliser
    return ' '.join(text_parts).lower()

def assign_predefined_category(bookmark_text):
    """
    Assigne une catégorie prédéfinie basée sur le texte du bookmark.
    
    Args:
        bookmark_text (str): Texte préparé du bookmark.
        
    Returns:
        tuple: (catégorie principale, score, catégories secondaires)
    """
    scores = {}
    
    # Calculer un score pour chaque catégorie
    for category, keywords in PREDEFINED_CATEGORIES.items():
        score = 0
        for keyword in keywords:
            # Rechercher le mot-clé dans le texte (mot complet ou sous-chaîne)
            if re.search(r'\b' + re.escape(keyword) + r'\b', bookmark_text, re.IGNORECASE):
                score += 2  # Match exact
            elif keyword.lower() in bookmark_text.lower():
                score += 1  # Match partiel
        
        scores[category] = score
    
    # Trier les catégories par score
    sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Déterminer la catégorie principale et les catégories secondaires
    primary_category = "Non classé"
    primary_score = 0
    secondary_categories = []
    
    if sorted_categories:
        if sorted_categories[0][1] > 0:
            primary_category = sorted_categories[0][0]
            primary_score = sorted_categories[0][1]
        
        # Ajouter jusqu'à 3 catégories secondaires significatives
        for category, score in sorted_categories[1:4]:
            if score > 0:
                secondary_categories.append(category)
    
    return primary_category, primary_score, secondary_categories

def cluster_bookmarks(bookmarks):
    """
    Regroupe les bookmarks similaires en clusters.
    
    Args:
        bookmarks (list): Liste des bookmarks à regrouper.
        
    Returns:
        dict: Dictionnaire avec les bookmarks mis à jour avec leur cluster.
    """
    # Filtrer les bookmarks avec du texte
    valid_bookmarks = [b for b in bookmarks if 'analysis' in b and b['analysis'].get('text_length', 0) > 0]
    
    if len(valid_bookmarks) < 3:
        logger.warning("Pas assez de bookmarks avec contenu pour le clustering")
        return bookmarks
    
    # Préparer les textes pour le clustering
    texts = []
    valid_indices = []
    
    for i, bookmark in enumerate(bookmarks):
        if 'analysis' in bookmark and bookmark['analysis'].get('text_length', 0) > 0:
            text = prepare_bookmark_text(bookmark)
            if text:
                texts.append(text)
                valid_indices.append(i)
    
    try:
        # Vectoriser les textes
        vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        X = vectorizer.fit_transform(texts)
        
        # Calculer la matrice de similarité
        similarity_matrix = cosine_similarity(X)
        
        # Appliquer DBSCAN pour le clustering
        clustering = DBSCAN(eps=0.6, min_samples=2, metric='precomputed')
        similarity_distance_matrix = 1 - similarity_matrix  # Convertir similarité en distance
        cluster_labels = clustering.fit_predict(similarity_distance_matrix)
        
        # Assigner les clusters aux bookmarks
        for idx, label in enumerate(cluster_labels):
            bookmark_idx = valid_indices[idx]
            if label != -1:  # -1 signifie pas de cluster
                cluster_name = f"Cluster_{label + 1}"
            else:
                cluster_name = None
            
            if 'categorization' not in bookmarks[bookmark_idx]:
                bookmarks[bookmark_idx]['categorization'] = {}
            
            bookmarks[bookmark_idx]['categorization']['similarity_cluster'] = cluster_name
        
        # Compter les clusters
        cluster_counts = Counter(label for label in cluster_labels if label != -1)
        logger.info(f"Clustering terminé: {len(cluster_counts)} clusters trouvés, {sum(1 for label in cluster_labels if label == -1)} bookmarks isolés")
        
    except Exception as e:
        logger.error(f"Erreur lors du clustering: {e}")
    
    return bookmarks

def detect_duplicates(bookmarks):
    """
    Détecte les doublons potentiels parmi les bookmarks.
    
    Args:
        bookmarks (list): Liste des bookmarks à analyser.
        
    Returns:
        dict: Dictionnaire des groupes de doublons.
    """
    # Regrouper par URL normalisée
    normalized_urls = defaultdict(list)
    for i, bookmark in enumerate(bookmarks):
        url = bookmark.get('url', '').lower()
        
        # Normaliser l'URL (supprimer protocole, www, paramètres, etc.)
        parsed = urlparse(url)
        normalized = parsed.netloc.replace('www.', '') + parsed.path.rstrip('/')
        
        normalized_urls[normalized].append(i)
    
    # Regrouper par titre similaire
    title_groups = defaultdict(list)
    for i, bookmark in enumerate(bookmarks):
        title = bookmark.get('title', '').lower()
        if title and len(title) > 10:  # Ignorer les titres trop courts
            # Simplifier le titre pour la comparaison
            simplified = re.sub(r'[^\w\s]', '', title)
            simplified = re.sub(r'\s+', ' ', simplified).strip()
            
            if simplified:
                title_groups[simplified].append(i)
    
    # Trouver les groupes de doublons
    duplicate_groups = {}
    group_id = 1
    
    # Doublons par URL
    for url, indices in normalized_urls.items():
        if len(indices) > 1:
            duplicate_groups[f"DuplicateURL_{group_id}"] = {
                'indices': indices,
                'type': 'url',
                'value': url
            }
            group_id += 1
    
    # Doublons par titre
    for title, indices in title_groups.items():
        if len(indices) > 1:
            duplicate_groups[f"DuplicateTitle_{group_id}"] = {
                'indices': indices,
                'type': 'title',
                'value': title
            }
            group_id += 1
    
    logger.info(f"Détection de doublons terminée: {len(duplicate_groups)} groupes trouvés")
    
    return duplicate_groups

def categorize_bookmarks(bookmarks, **config):
    """
    Fonction principale pour catégoriser et organiser les bookmarks.
    
    Args:
        bookmarks (list): Liste des bookmarks à catégoriser.
        **config: Configuration pour la catégorisation.
        
    Returns:
        list: Liste des bookmarks mis à jour avec les informations de catégorisation.
    """
    logger.info(f"Catégorisation de {len(bookmarks)} bookmarks")
    
    # Catégoriser chaque bookmark
    for bookmark in tqdm(bookmarks, desc="Attribution des catégories"):
        # Préparer le texte
        bookmark_text = prepare_bookmark_text(bookmark)
        
        # Assigner une catégorie prédéfinie
        primary_category, score, secondary_categories = assign_predefined_category(bookmark_text)
        
        # Mettre à jour les informations de catégorisation
        bookmark['categorization'] = {
            'primary_category': primary_category,
            'primary_score': score,
            'secondary_categories': secondary_categories,
            'similarity_cluster': None  # Sera mis à jour par clustering
        }
    
    # Regrouper les bookmarks similaires
    bookmarks = cluster_bookmarks(bookmarks)
    
    # Détecter les doublons
    duplicate_groups = detect_duplicates(bookmarks)
    
    # Ajouter les informations de doublons
    for group_name, group_info in duplicate_groups.items():
        for idx in group_info['indices']:
            if idx < len(bookmarks):
                if 'duplicates' not in bookmarks[idx]:
                    bookmarks[idx]['duplicates'] = []
                bookmarks[idx]['duplicates'].append({
                    'group': group_name,
                    'type': group_info['type'],
                    'count': len(group_info['indices'])
                })
    
    # Compter les résultats
    categories = Counter(b.get('categorization', {}).get('primary_category', 'Non classé') for b in bookmarks)
    
    logger.info(f"Catégorisation terminée: {len(categories)} catégories distinctes")
    for category, count in categories.most_common():
        logger.info(f"  {category}: {count} bookmarks")
    
    return bookmarks

if __name__ == "__main__":
    # Test du module
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python bookmark_categorizer.py <bookmarks.json>")
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
    
    # Configuration de test
    config = {}
    
    # Catégoriser les bookmarks
    updated_bookmarks = categorize_bookmarks(bookmarks, **config)
    
    # Afficher les résultats
    categories = Counter(b.get('categorization', {}).get('primary_category', 'Non classé') for b in updated_bookmarks)
    print("Distribution des catégories:")
    for category, count in categories.most_common():
        print(f"  {category}: {count} bookmarks")
    
    # Afficher quelques exemples
    print("\nExemples de catégorisation:")
    for i, bookmark in enumerate(updated_bookmarks[:5]):
        cat = bookmark.get('categorization', {})
        print(f"URL: {bookmark['url']}")
        print(f"  Titre: {bookmark.get('title', '')}")
        print(f"  Catégorie: {cat.get('primary_category', 'Non classé')} (score: {cat.get('primary_score', 0)})")
        print(f"  Secondaires: {', '.join(cat.get('secondary_categories', []))}")
        print(f"  Cluster: {cat.get('similarity_cluster')}")
        if 'duplicates' in bookmark:
            print(f"  Doublons: {bookmark['duplicates']}")
        print()