#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de génération des recommandations
----------------------------------------

Ce module est responsable de la génération de recommandations pour chaque bookmark
(conserver, archiver, supprimer).
"""

import logging
import json
from datetime import datetime, timedelta
from tqdm import tqdm

logger = logging.getLogger("bookmark_analyzer.recommendation_engine")

# Seuils de décision
THRESHOLDS = {
    'quality_score': {
        'high': 75,  # Au-dessus: haute qualité
        'medium': 50,  # Entre medium et high: qualité moyenne
        'low': 25  # En dessous: basse qualité
    },
    'age': {
        'recent': 365,  # Moins d'un an: récent
        'old': 1095  # Plus de 3 ans: ancien
    }
}

def calculate_age_score(bookmark):
    """
    Calcule un score basé sur l'âge du bookmark.
    
    Args:
        bookmark (dict): Dictionnaire contenant les informations du bookmark.
        
    Returns:
        float: Score d'âge (0-100, plus élevé = plus récent).
    """
    # Extraire la date d'ajout
    add_date = bookmark.get('add_date', None)
    
    if not add_date:
        return 50  # Score par défaut si pas de date
    
    try:
        # Convertir en datetime
        if 'T' in add_date:  # Format ISO
            bookmark_date = datetime.fromisoformat(add_date)
        else:  # Autre format
            bookmark_date = datetime.strptime(add_date[:10], '%Y-%m-%d')
        
        # Calculer l'âge en jours
        now = datetime.now()
        age_days = (now - bookmark_date).days
        
        # Calculer le score (inversement proportionnel à l'âge)
        if age_days <= 0:
            return 100
        elif age_days >= 2190:  # 6 ans
            return 0
        else:
            return max(0, 100 - (age_days / 2190 * 100))
    
    except Exception:
        return 50  # Score par défaut en cas d'erreur

def calculate_usage_score(bookmark):
    """
    Estime un score d'utilisation basé sur les métadonnées disponibles.
    
    Args:
        bookmark (dict): Dictionnaire contenant les informations du bookmark.
        
    Returns:
        float: Score d'utilisation estimé (0-100).
    """
    # Pour l'instant, c'est une estimation simple basée sur les métriques disponibles
    # Dans un système plus avancé, on pourrait utiliser l'historique de navigation
    
    # Facteurs positifs
    factors = []
    
    # Si le bookmark est dans un dossier organisé (pas Root ou non classé)
    folder = bookmark.get('folder', 'Root')
    if folder not in ['Root', 'Non classé', 'Autres', 'Divers']:
        factors.append(10)
    
    # Si le bookmark a été modifié après sa création
    add_date = bookmark.get('add_date', '')
    last_modified = bookmark.get('last_modified', '')
    if add_date and last_modified and add_date != last_modified:
        factors.append(20)
    
    # Si le bookmark fait partie d'un cluster (indiquant une utilisation thématique)
    if bookmark.get('categorization', {}).get('similarity_cluster', None):
        factors.append(15)
    
    # Si le bookmark a un score de qualité élevé
    quality_score = bookmark.get('analysis', {}).get('quality_score', 0)
    if quality_score > THRESHOLDS['quality_score']['high']:
        factors.append(25)
    elif quality_score > THRESHOLDS['quality_score']['medium']:
        factors.append(15)
    
    # Score de base
    base_score = 30
    
    # Calculer le score final
    score = base_score + sum(factors)
    
    # Limiter entre 0 et 100
    return max(0, min(100, score))

def find_alternatives(bookmark, all_bookmarks):
    """
    Trouve des alternatives potentielles pour un bookmark.
    
    Args:
        bookmark (dict): Bookmark pour lequel trouver des alternatives.
        all_bookmarks (list): Liste complète des bookmarks.
        
    Returns:
        list: Liste des alternatives trouvées (IDs).
    """
    alternatives = []
    
    # Si le bookmark n'a pas de catégorie ou n'est pas accessible, retourner une liste vide
    if not bookmark.get('categorization', {}).get('primary_category') or not bookmark.get('status', {}).get('accessible', False):
        return alternatives
    
    # Catégorie et cluster du bookmark actuel
    category = bookmark.get('categorization', {}).get('primary_category')
    cluster = bookmark.get('categorization', {}).get('similarity_cluster')
    
    # Score de qualité du bookmark actuel
    quality = bookmark.get('analysis', {}).get('quality_score', 0)
    
    # Chercher des alternatives de meilleure qualité dans la même catégorie/cluster
    for other in all_bookmarks:
        # Ignorer le même bookmark
        if other['id'] == bookmark['id']:
            continue
        
        # Ignorer les bookmarks inaccessibles
        if not other.get('status', {}).get('accessible', False):
            continue
        
        other_category = other.get('categorization', {}).get('primary_category')
        other_cluster = other.get('categorization', {}).get('similarity_cluster')
        other_quality = other.get('analysis', {}).get('quality_score', 0)
        
        # Vérifier si c'est une alternative potentielle
        is_alternative = False
        
        # Même cluster (s'il existe)
        if cluster and other_cluster and cluster == other_cluster and other_quality > quality + 10:
            is_alternative = True
        
        # Même catégorie et qualité supérieure
        elif category == other_category and other_quality > quality + 20:
            is_alternative = True
        
        if is_alternative:
            alternatives.append(other['id'])
    
    # Limiter à 3 alternatives maximum
    return alternatives[:3]

def generate_recommendation(bookmark, all_bookmarks):
    """
    Génère une recommandation pour un bookmark spécifique.
    
    Args:
        bookmark (dict): Dictionnaire contenant les informations du bookmark.
        all_bookmarks (list): Liste complète des bookmarks pour la recherche d'alternatives.
        
    Returns:
        dict: Recommandation générée avec action, confiance et raison.
    """
    # Variables de décision
    is_accessible = bookmark.get('status', {}).get('accessible', False)
    is_redirect = bookmark.get('status', {}).get('redirect', False)
    quality_score = bookmark.get('analysis', {}).get('quality_score', 0)
    age_score = calculate_age_score(bookmark)
    usage_score = calculate_usage_score(bookmark)
    has_duplicates = 'duplicates' in bookmark and bookmark['duplicates']
    
    # Décision par défaut
    action = 'keep'
    confidence = 0.5
    reason = "Bookmark standard sans caractéristiques particulières."
    
    # Logique de décision
    
    # Cas 1: Lien mort
    if not is_accessible:
        action = 'delete'
        confidence = 0.9
        reason = "Le lien n'est plus accessible (erreur HTTP ou timeout)."
    
    # Cas 2: Redirection (potentiellement obsolète)
    elif is_redirect:
        target_url = bookmark.get('status', {}).get('redirect_url', '')
        if target_url:
            action = 'update'
            confidence = 0.8
            reason = f"Le lien redirige vers: {target_url}. Considérez mettre à jour le bookmark."
        else:
            action = 'keep'
            confidence = 0.6
            reason = "Le lien redirige, mais la cible est inconnue. Vérification manuelle recommandée."
    
    # Cas 3: Duplicata exact
    elif has_duplicates:
        dup_info = bookmark['duplicates'][0]
        action = 'review'
        confidence = 0.7
        reason = f"Ce bookmark fait partie d'un groupe de doublons ({dup_info['type']}). Conservez le meilleur et supprimez les autres."
    
    # Cas 4: Haute qualité récente
    elif quality_score > THRESHOLDS['quality_score']['high'] and age_score > 70:
        action = 'keep'
        confidence = 0.9
        reason = "Contenu de haute qualité et relativement récent. À conserver."
    
    # Cas 5: Basse qualité et ancien
    elif quality_score < THRESHOLDS['quality_score']['low'] and age_score < 30:
        # Chercher des alternatives
        alternatives = find_alternatives(bookmark, all_bookmarks)
        
        if alternatives:
            action = 'replace'
            confidence = 0.7
            alt_ids = ', '.join([str(alt_id) for alt_id in alternatives])
            reason = f"Contenu de basse qualité et ancien. Des alternatives de meilleure qualité existent (IDs: {alt_ids})."
        else:
            action = 'archive'
            confidence = 0.6
            reason = "Contenu de basse qualité et ancien. Considérez l'archiver ou le supprimer s'il n'est plus utile."
    
    # Cas 6: Usage estimé faible
    elif usage_score < 40:
        action = 'archive'
        confidence = 0.5
        reason = "Faible probabilité d'utilisation basée sur les métadonnées. Considérez l'archiver s'il n'est pas utilisé régulièrement."
    
    # Cas 7: Contenu très ancien
    elif age_score < 20:
        action = 'review'
        confidence = 0.6
        reason = "Bookmark très ancien. Vérifiez s'il est toujours pertinent pour vos besoins actuels."
    
    # Cas 8: Qualité moyenne à bonne
    elif THRESHOLDS['quality_score']['medium'] <= quality_score <= THRESHOLDS['quality_score']['high']:
        action = 'keep'
        confidence = 0.7
        reason = "Contenu de qualité correcte. Recommandé à conserver."
    
    # Finaliser la recommandation
    bookmark['recommendation'] = {
        'action': action,
        'confidence': round(confidence, 2),
        'reason': reason,
        'alternatives': find_alternatives(bookmark, all_bookmarks) if action in ['replace', 'archive'] else []
    }
    
    return bookmark

def generate_recommendations(bookmarks, **config):
    """
    Fonction principale pour générer des recommandations pour tous les bookmarks.
    
    Args:
        bookmarks (list): Liste des bookmarks à analyser.
        **config: Configuration pour la génération des recommandations.
        
    Returns:
        list: Liste des bookmarks mis à jour avec les recommandations.
    """
    logger.info(f"Génération des recommandations pour {len(bookmarks)} bookmarks")
    
    # Générer des recommandations
    for bookmark in tqdm(bookmarks, desc="Génération des recommandations"):
        generate_recommendation(bookmark, bookmarks)
    
    # Compter les résultats
    actions = {}
    for bookmark in bookmarks:
        action = bookmark.get('recommendation', {}).get('action', 'keep')
        if action not in actions:
            actions[action] = 0
        actions[action] += 1
    
    logger.info("Recommandations générées:")
    for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {action}: {count} bookmarks")
    
    return bookmarks

if __name__ == "__main__":
    # Test du module
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python recommendation_engine.py <bookmarks.json>")
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
    
    # Générer des recommandations
    updated_bookmarks = generate_recommendations(bookmarks, **config)
    
    # Afficher les résultats
    actions = {}
    for bookmark in updated_bookmarks:
        action = bookmark.get('recommendation', {}).get('action', 'keep')
        if action not in actions:
            actions[action] = 0
        actions[action] += 1
    
    print("Distribution des recommandations:")
    for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
        print(f"  {action}: {count} bookmarks")
    
    # Afficher quelques exemples
    print("\nExemples de recommandations:")
    for i, bookmark in enumerate(updated_bookmarks[:5]):
        rec = bookmark.get('recommendation', {})
        print(f"URL: {bookmark['url']}")
        print(f"  Titre: {bookmark.get('title', '')}")
        print(f"  Action: {rec.get('action', 'keep')} (confiance: {rec.get('confidence', 0)})")
        print(f"  Raison: {rec.get('reason', '')}")
        if rec.get('alternatives', []):
            print(f"  Alternatives: {rec.get('alternatives', [])}")
        print()