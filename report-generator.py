#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de génération de rapport
-------------------------------

Ce module est responsable de la génération d'un rapport détaillé sur l'analyse des bookmarks.
"""

import logging
import json
import os
import time
from datetime import datetime
from collections import Counter
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger("bookmark_analyzer.report_generator")

def generate_charts(bookmarks, output_dir):
    """
    Génère des graphiques d'analyse pour le rapport.
    
    Args:
        bookmarks (list): Liste des bookmarks analysés.
        output_dir (str): Dossier de sortie pour les graphiques.
        
    Returns:
        dict: Chemins vers les graphiques générés.
    """
    charts_dir = os.path.join(output_dir, 'reports', 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    charts = {}
    
    try:
        # 1. Distribution des catégories
        categories = Counter(b.get('categorization', {}).get('primary_category', 'Non classé') for b in bookmarks)
        top_categories = dict(categories.most_common(10))  # Top 10 catégories
        
        plt.figure(figsize=(10, 6))
        plt.bar(top_categories.keys(), top_categories.values(), color='skyblue')
        plt.xticks(rotation=45, ha='right')
        plt.title('Top 10 des Catégories')
        plt.tight_layout()
        category_chart = os.path.join(charts_dir, 'category_distribution.png')
        plt.savefig(category_chart)
        plt.close()
        
        charts['categories'] = category_chart
        
        # 2. Distribution des recommandations
        actions = Counter(b.get('recommendation', {}).get('action', 'keep') for b in bookmarks)
        
        plt.figure(figsize=(8, 8))
        plt.pie(actions.values(), labels=actions.keys(), autopct='%1.1f%%', 
                shadow=True, startangle=90)
        plt.axis('equal')
        plt.title('Distribution des Recommandations')
        action_chart = os.path.join(charts_dir, 'recommendation_distribution.png')
        plt.savefig(action_chart)
        plt.close()
        
        charts['actions'] = action_chart
        
        # 3. Distribution de la qualité
        quality_scores = [b.get('analysis', {}).get('quality_score', 0) for b in bookmarks 
                          if b.get('analysis', {}).get('quality_score') is not None]
        
        plt.figure(figsize=(8, 6))
        plt.hist(quality_scores, bins=20, color='green', alpha=0.7)
        plt.title('Distribution des Scores de Qualité')
        plt.xlabel('Score de Qualité')
        plt.ylabel('Nombre de Bookmarks')
        quality_chart = os.path.join(charts_dir, 'quality_distribution.png')
        plt.savefig(quality_chart)
        plt.close()
        
        charts['quality'] = quality_chart
        
        # 4. État des URLs
        status_counts = Counter()
        for b in bookmarks:
            if b.get('status', {}).get('accessible', False):
                if b.get('status', {}).get('redirect', False):
                    status_counts['Redirigé'] += 1
                else:
                    status_counts['Accessible'] += 1
            else:
                status_counts['Inaccessible'] += 1
        
        plt.figure(figsize=(8, 6))
        plt.bar(status_counts.keys(), status_counts.values(), color=['green', 'orange', 'red'])
        plt.title('État des URLs')
        plt.ylabel('Nombre de Bookmarks')
        status_chart = os.path.join(charts_dir, 'status_distribution.png')
        plt.savefig(status_chart)
        plt.close()
        
        charts['status'] = status_chart
        
        # 5. Distribution des types de contenu
        content_types = Counter(b.get('analysis', {}).get('content_type', 'unknown') for b in bookmarks)
        
        plt.figure(figsize=(10, 6))
        plt.bar(content_types.keys(), content_types.values(), color='purple')
        plt.xticks(rotation=45, ha='right')
        plt.title('Types de Contenu')
        plt.tight_layout()
        content_chart = os.path.join(charts_dir, 'content_distribution.png')
        plt.savefig(content_chart)
        plt.close()
        
        charts['content_types'] = content_chart
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération des graphiques: {e}")
    
    return charts

def create_domain_summary(bookmarks):
    """
    Crée un résumé des domaines les plus fréquents.
    
    Args:
        bookmarks (list): Liste des bookmarks analysés.
        
    Returns:
        list: Résumé des domaines.
    """
    domains = Counter(b.get('domain', '') for b in bookmarks if b.get('domain'))
    top_domains = domains.most_common(20)  # Top 20 domaines
    
    domain_summary = []
    for domain, count in top_domains:
        # Filtrer les bookmarks pour ce domaine
        domain_bookmarks = [b for b in bookmarks if b.get('domain') == domain]
        
        # Calculer des statistiques
        accessible = sum(1 for b in domain_bookmarks if b.get('status', {}).get('accessible', False))
        avg_quality = sum(b.get('analysis', {}).get('quality_score', 0) for b in domain_bookmarks) / max(1, len(domain_bookmarks))
        
        # Compter les recommandations
        actions = Counter(b.get('recommendation', {}).get('action', 'keep') for b in domain_bookmarks)
        primary_action = actions.most_common(1)[0][0] if actions else 'keep'
        
        domain_summary.append({
            'domain': domain,
            'count': count,
            'accessible_percent': round(accessible / count * 100, 1),
            'avg_quality': round(avg_quality, 1),
            'primary_action': primary_action
        })
    
    return domain_summary

def create_category_summary(bookmarks):
    """
    Crée un résumé des catégories.
    
    Args:
        bookmarks (list): Liste des bookmarks analysés.
        
    Returns:
        list: Résumé des catégories.
    """
    categories = Counter(b.get('categorization', {}).get('primary_category', 'Non classé') for b in bookmarks)
    
    category_summary = []
    for category, count in categories.most_common():
        # Filtrer les bookmarks pour cette catégorie
        category_bookmarks = [b for b in bookmarks 
                              if b.get('categorization', {}).get('primary_category') == category]
        
        # Calculer des statistiques
        accessible = sum(1 for b in category_bookmarks if b.get('status', {}).get('accessible', False))
        avg_quality = sum(b.get('analysis', {}).get('quality_score', 0) for b in category_bookmarks) / max(1, len(category_bookmarks))
        
        # Compter les recommandations
        actions = Counter(b.get('recommendation', {}).get('action', 'keep') for b in category_bookmarks)
        
        category_summary.append({
            'category': category,
            'count': count,
            'accessible_percent': round(accessible / count * 100, 1),
            'avg_quality': round(avg_quality, 1),
            'actions': dict(actions.most_common())
        })
    
    return category_summary

def create_action_details(bookmarks):
    """
    Crée un résumé détaillé des actions recommandées.
    
    Args:
        bookmarks (list): Liste des bookmarks analysés.
        
    Returns:
        dict: Détails des actions recommandées.
    """
    action_details = {}
    
    # Regrouper les bookmarks par action recommandée
    for action in ['keep', 'update', 'archive', 'delete', 'replace', 'review']:
        action_bookmarks = [b for b in bookmarks 
                            if b.get('recommendation', {}).get('action') == action]
        
        if not action_bookmarks:
            continue
        
        # Calculer des statistiques
        avg_quality = sum(b.get('analysis', {}).get('quality_score', 0) for b in action_bookmarks) / max(1, len(action_bookmarks))
        top_categories = Counter(b.get('categorization', {}).get('primary_category', 'Non classé') 
                                 for b in action_bookmarks).most_common(3)
        top_domains = Counter(b.get('domain', '') for b in action_bookmarks if b.get('domain')).most_common(3)
        
        # Extraire quelques exemples représentatifs
        examples = []
        for bookmark in sorted(action_bookmarks, 
                               key=lambda b: b.get('recommendation', {}).get('confidence', 0), 
                               reverse=True)[:5]:
            examples.append({
                'id': bookmark.get('id'),
                'title': bookmark.get('title', ''),
                'url': bookmark.get('url', ''),
                'reason': bookmark.get('recommendation', {}).get('reason', ''),
                'confidence': bookmark.get('recommendation', {}).get('confidence', 0)
            })
        
        action_details[action] = {
            'count': len(action_bookmarks),
            'avg_quality': round(avg_quality, 1),
            'top_categories': top_categories,
            'top_domains': top_domains,
            'examples': examples
        }
    
    return action_details

def create_duplicates_summary(bookmarks):
    """
    Crée un résumé des groupes de doublons.
    
    Args:
        bookmarks (list): Liste des bookmarks analysés.
        
    Returns:
        list: Résumé des groupes de doublons.
    """
    # Identifier tous les groupes de doublons
    duplicate_groups = {}
    
    for bookmark in bookmarks:
        if 'duplicates' in bookmark and bookmark['duplicates']:
            for dup_info in bookmark['duplicates']:
                group_name = dup_info.get('group')
                if group_name:
                    if group_name not in duplicate_groups:
                        duplicate_groups[group_name] = {
                            'type': dup_info.get('type', 'unknown'),
                            'bookmarks': []
                        }
                    duplicate_groups[group_name]['bookmarks'].append(bookmark)
    
    # Créer le résumé
    duplicates_summary = []
    
    for group_name, group_info in duplicate_groups.items():
        group_bookmarks = group_info['bookmarks']
        
        # Trier les bookmarks par qualité
        sorted_bookmarks = sorted(group_bookmarks, 
                                 key=lambda b: b.get('analysis', {}).get('quality_score', 0), 
                                 reverse=True)
        
        # Déterminer le meilleur bookmark
        best_bookmark = sorted_bookmarks[0] if sorted_bookmarks else None
        
        # Créer le résumé du groupe
        duplicates_summary.append({
            'group': group_name,
            'type': group_info['type'],
            'count': len(group_bookmarks),
            'best_bookmark': {
                'id': best_bookmark.get('id'),
                'title': best_bookmark.get('title', ''),
                'url': best_bookmark.get('url', ''),
                'quality': best_bookmark.get('analysis', {}).get('quality_score', 0)
            } if best_bookmark else None,
            'bookmarks': [
                {
                    'id': b.get('id'),
                    'title': b.get('title', ''),
                    'url': b.get('url', ''),
                    'accessible': b.get('status', {}).get('accessible', False),
                    'quality': b.get('analysis', {}).get('quality_score', 0)
                }
                for b in group_bookmarks
            ]
        })
    
    return duplicates_summary

def generate_bookmarks_table(bookmarks):
    """
    Génère un tableau des bookmarks analysés.
    
    Args:
        bookmarks (list): Liste des bookmarks analysés.
        
    Returns:
        list: Tableau des bookmarks.
    """
    table = []
    
    for bookmark in bookmarks:
        table.append({
            'id': bookmark.get('id'),
            'title': bookmark.get('title', ''),
            'url': bookmark.get('url', ''),
            'domain': bookmark.get('domain', ''),
            'folder': bookmark.get('folder', ''),
            'accessible': bookmark.get('status', {}).get('accessible', False),
            'category': bookmark.get('categorization', {}).get('primary_category', 'Non classé'),
            'quality': bookmark.get('analysis', {}).get('quality_score', 0),
            'content_type': bookmark.get('analysis', {}).get('content_type', ''),
            'action': bookmark.get('recommendation', {}).get('action', 'keep'),
            'confidence': bookmark.get('recommendation', {}).get('confidence', 0)
        })
    
    return table

def generate_html_report(data, charts, output_dir):
    """
    Génère un rapport HTML.
    
    Args:
        data (dict): Données du rapport.
        charts (dict): Chemins vers les graphiques générés.
        output_dir (str): Dossier de sortie.
        
    Returns:
        str: Chemin vers le rapport HTML.
    """
    html_path = os.path.join(output_dir, 'reports', 'bookmark_analysis_report.html')
    
    # Charger les templates
    try:
        # Charger les templates (version simplifiée)
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Rapport d'Analyse des Bookmarks</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
                h1, h2, h3 { color: #2c3e50; }
                .container { max-width: 1200px; margin: 0 auto; }
                .summary { background-color: #f8f9fa; border-radius: 5px; padding: 15px; margin-bottom: 20px; }
                .section { margin-bottom: 30px; }
                table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                .chart-container { margin: 20px 0; text-align: center; }
                .chart { max-width: 100%; height: auto; }
                .success { color: green; }
                .warning { color: orange; }
                .danger { color: red; }
                .badge { display: inline-block; padding: 3px 7px; border-radius: 3px; font-size: 12px; }
                .badge-primary { background-color: #007bff; color: white; }
                .badge-success { background-color: #28a745; color: white; }
                .badge-warning { background-color: #ffc107; color: black; }
                .badge-danger { background-color: #dc3545; color: white; }
                .badge-info { background-color: #17a2b8; color: white; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Rapport d'Analyse des Bookmarks</h1>
                <p>Rapport généré le: {date}</p>
                
                <div class="summary">
                    <h2>Résumé</h2>
                    <table>
                        <tr>
                            <td>Nombre total de bookmarks</td>
                            <td>{total_bookmarks}</td>
                        </tr>
                        <tr>
                            <td>Bookmarks accessibles</td>
                            <td>{accessible_bookmarks} ({accessible_percent}%)</td>
                        </tr>
                        <tr>
                            <td>Bookmarks redirigés</td>
                            <td>{redirected_bookmarks} ({redirected_percent}%)</td>
                        </tr>
                        <tr>
                            <td>Bookmarks inaccessibles</td>
                            <td>{inaccessible_bookmarks} ({inaccessible_percent}%)</td>
                        </tr>
                        <tr>
                            <td>Score de qualité moyen</td>
                            <td>{avg_quality}</td>
                        </tr>
                        <tr>
                            <td>Nombre de catégories</td>
                            <td>{category_count}</td>
                        </tr>
                        <tr>
                            <td>Groupes de doublons</td>
                            <td>{duplicate_groups}</td>
                        </tr>
                    </table>
                </div>
                
                <div class="section">
                    <h2>Graphiques</h2>
                    <div class="chart-container">
                        <h3>Distribution des Catégories</h3>
                        <img src="{categories_chart}" alt="Distribution des Catégories" class="chart">
                    </div>
                    <div class="chart-container">
                        <h3>Distribution des Recommandations</h3>
                        <img src="{actions_chart}" alt="Distribution des Recommandations" class="chart">
                    </div>
                    <div class="chart-container">
                        <h3>Distribution des Scores de Qualité</h3>
                        <img src="{quality_chart}" alt="Distribution des Scores de Qualité" class="chart">
                    </div>
                    <div class="chart-container">
                        <h3>État des URLs</h3>
                        <img src="{status_chart}" alt="État des URLs" class="chart">
                    </div>
                    <div class="chart-container">
                        <h3>Types de Contenu</h3>
                        <img src="{content_types_chart}" alt="Types de Contenu" class="chart">
                    </div>
                </div>
                
                <div class="section">
                    <h2>Recommandations</h2>
                    <table>
                        <tr>
                            <th>Action</th>
                            <th>Nombre</th>
                            <th>Description</th>
                        </tr>
                        {action_rows}
                    </table>
                </div>
                
                <div class="section">
                    <h2>Top Domaines</h2>
                    <table>
                        <tr>
                            <th>Domaine</th>
                            <th>Nombre</th>
                            <th>% Accessibles</th>
                            <th>Qualité Moyenne</th>
                            <th>Action Principale</th>
                        </tr>
                        {domain_rows}
                    </table>
                </div>
                
                <div class="section">
                    <h2>Catégories</h2>
                    <table>
                        <tr>
                            <th>Catégorie</th>
                            <th>Nombre</th>
                            <th>% Accessibles</th>
                            <th>Qualité Moyenne</th>
                            <th>Actions</th>
                        </tr>
                        {category_rows}
                    </table>
                </div>
                
                <div class="section">
                    <h2>Doublons</h2>
                    {duplicates_content}
                </div>
                
                <div class="section">
                    <h2>Tableau Complet des Bookmarks</h2>
                    <p>Les 100 premiers bookmarks sont affichés ci-dessous. Pour la liste complète, consultez le fichier CSV.</p>
                    <table>
                        <tr>
                            <th>ID</th>
                            <th>Titre</th>
                            <th>Domaine</th>
                            <th>Accessible</th>
                            <th>Catégorie</th>
                            <th>Qualité</th>
                            <th>Action</th>
                        </tr>
                        {bookmark_rows}
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Formater les lignes pour les actions
        action_rows = ""
        action_descriptions = {
            'keep': "Conserver ce bookmark tel quel",
            'update': "Mettre à jour ce bookmark (généralement en raison d'une redirection)",
            'archive': "Archiver ce bookmark (potentiellement obsolète ou rarement utilisé)",
            'delete': "Supprimer ce bookmark (inaccessible ou de très mauvaise qualité)",
            'replace': "Remplacer ce bookmark par une alternative de meilleure qualité",
            'review': "Vérifier manuellement ce bookmark"
        }
        
        for action, details in data['action_details'].items():
            badge_class = {
                'keep': 'badge-success',
                'update': 'badge-primary',
                'archive': 'badge-info',
                'delete': 'badge-danger',
                'replace': 'badge-warning',
                'review': 'badge-primary'
            }.get(action, 'badge-primary')
            
            action_rows += f"""
            <tr>
                <td><span class="badge {badge_class}">{action}</span></td>
                <td>{details['count']}</td>
                <td>{action_descriptions.get(action, "")}</td>
            </tr>
            """
        
        # Formater les lignes pour les domaines
        domain_rows = ""
        for domain in data['domain_summary'][:10]:  # Top 10
            badge_class = {
                'keep': 'badge-success',
                'update': 'badge-primary',
                'archive': 'badge-info',
                'delete': 'badge-danger',
                'replace': 'badge-warning',
                'review': 'badge-primary'
            }.get(domain['primary_action'], 'badge-primary')
            
            domain_rows += f"""
            <tr>
                <td>{domain['domain']}</td>
                <td>{domain['count']}</td>
                <td>{domain['accessible_percent']}%</td>
                <td>{domain['avg_quality']}</td>
                <td><span class="badge {badge_class}">{domain['primary_action']}</span></td>
            </tr>
            """
        
        # Formater les lignes pour les catégories
        category_rows = ""
        for category in data['category_summary']:
            actions_html = ""
            for action, count in category['actions'].items():
                badge_class = {
                    'keep': 'badge-success',
                    'update': 'badge-primary',
                    'archive': 'badge-info',
                    'delete': 'badge-danger',
                    'replace': 'badge-warning',
                    'review': 'badge-primary'
                }.get(action, 'badge-primary')
                
                actions_html += f'<span class="badge {badge_class}">{action}: {count}</span> '
            
            category_rows += f"""
            <tr>
                <td>{category['category']}</td>
                <td>{category['count']}</td>
                <td>{category['accessible_percent']}%</td>
                <td>{category['avg_quality']}</td>
                <td>{actions_html}</td>
            </tr>
            """
        
        # Formater le contenu des doublons
        duplicates_content = ""
        for i, group in enumerate(data['duplicates_summary'][:10]):  # Top 10
            duplicates_content += f"""
            <h3>Groupe {i+1}: {group['type']} ({group['count']} bookmarks)</h3>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Titre</th>
                    <th>URL</th>
                    <th>Accessible</th>
                    <th>Qualité</th>
                    <th>Recommandation</th>
                </tr>
            """
            
            for bookmark in group['bookmarks']:
                status_class = "success" if bookmark['accessible'] else "danger"
                duplicates_content += f"""
                <tr>
                    <td>{bookmark['id']}</td>
                    <td>{bookmark['title']}</td>
                    <td>{bookmark['url']}</td>
                    <td class="{status_class}">{bookmark['accessible']}</td>
                    <td>{bookmark['quality']}</td>
                    <td>{"Conserver" if bookmark['id'] == group['best_bookmark']['id'] else "Supprimer ou Archiver"}</td>
                </tr>
                """
            
            duplicates_content += "</table>"
        
        # Formater les lignes pour les bookmarks
        bookmark_rows = ""
        for bookmark in data['bookmarks_table'][:100]:  # Limiter à 100
            status_class = "success" if bookmark['accessible'] else "danger"
            badge_class = {
                'keep': 'badge-success',
                'update': 'badge-primary',
                'archive': 'badge-info',
                'delete': 'badge-danger',
                'replace': 'badge-warning',
                'review': 'badge-primary'
            }.get(bookmark['action'], 'badge-primary')
            
            bookmark_rows += f"""
            <tr>
                <td>{bookmark['id']}</td>
                <td title="{bookmark['url']}">{bookmark['title'][:40]}</td>
                <td>{bookmark['domain']}</td>
                <td class="{status_class}">{bookmark['accessible']}</td>
                <td>{bookmark['category']}</td>
                <td>{bookmark['quality']}</td>
                <td><span class="badge {badge_class}">{bookmark['action']}</span></td>
            </tr>
            """
        
        # Remplacer les variables dans le template
        html = html.format(
            date=data['date'],
            total_bookmarks=data['total_bookmarks'],
            accessible_bookmarks=data['accessible_bookmarks'],
            accessible_percent=data['accessible_percent'],
            redirected_bookmarks=data['redirected_bookmarks'],
            redirected_percent=data['redirected_percent'],
            inaccessible_bookmarks=data['inaccessible_bookmarks'],
            inaccessible_percent=data['inaccessible_percent'],
            avg_quality=data['avg_quality'],
            category_count=data['category_count'],
            duplicate_groups=data['duplicate_groups'],
            categories_chart=os.path.relpath(charts.get('categories', ''), os.path.dirname(html_path)),
            actions_chart=os.path.relpath(charts.get('actions', ''), os.path.dirname(html_path)),
            quality_chart=os.path.relpath(charts.get('quality', ''), os.path.dirname(html_path)),
            status_chart=os.path.relpath(charts.get('status', ''), os.path.dirname(html_path)),
            content_types_chart=os.path.relpath(charts.get('content_types', ''), os.path.dirname(html_path)),
            action_rows=action_rows,
            domain_rows=domain_rows,
            category_rows=category_rows,
            duplicates_content=duplicates_content,
            bookmark_rows=bookmark_rows
        )
        
        # Écrire le fichier HTML
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Rapport HTML généré: {html_path}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport HTML: {e}")
    
    return html_path

def generate_csv_reports(data, output_dir):
    """
    Génère des rapports CSV.
    
    Args:
        data (dict): Données du rapport.
        output_dir (str): Dossier de sortie.
        
    Returns:
        dict: Chemins vers les fichiers CSV générés.
    """
    csv_dir = os.path.join(output_dir, 'reports', 'csv')
    os.makedirs(csv_dir, exist_ok=True)
    
    csv_files = {}
    
    try:
        # 1. Tableau complet des bookmarks
        bookmarks_csv = os.path.join(csv_dir, 'bookmarks.csv')
        pd.DataFrame(data['bookmarks_table']).to_csv(bookmarks_csv, index=False, encoding='utf-8')
        csv_files['bookmarks'] = bookmarks_csv
        
        # 2. Résumé des domaines
        domains_csv = os.path.join(csv_dir, 'domains.csv')
        pd.DataFrame(data['domain_summary']).to_csv(domains_csv, index=False, encoding='utf-8')
        csv_files['domains'] = domains_csv
        
        # 3. Résumé des catégories
        categories_csv = os.path.join(csv_dir, 'categories.csv')
        # Transformer les dictionnaires d'actions en chaînes pour le CSV
        category_data = []
        for category in data['category_summary']:
            category_copy = category.copy()
            category_copy['actions'] = ', '.join([f"{action}: {count}" for action, count in category['actions'].items()])
            category_data.append(category_copy)
        
        pd.DataFrame(category_data).to_csv(categories_csv, index=False, encoding='utf-8')
        csv_files['categories'] = categories_csv
        
        # 4. Doublons
        duplicates_csv = os.path.join(csv_dir, 'duplicates.csv')
        # Transformer les données de doublons pour un format plat
        duplicate_data = []
        for group in data['duplicates_summary']:
            for bookmark in group['bookmarks']:
                duplicate_data.append({
                    'group': group['group'],
                    'type': group['type'],
                    'is_best': bookmark['id'] == group['best_bookmark']['id'] if group['best_bookmark'] else False,
                    **bookmark
                })
        
        pd.DataFrame(duplicate_data).to_csv(duplicates_csv, index=False, encoding='utf-8')
        csv_files['duplicates'] = duplicates_csv
        
        logger.info(f"Rapports CSV générés dans: {csv_dir}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération des rapports CSV: {e}")
    
    return csv_files

def generate_report(bookmarks, output_dir):
    """
    Fonction principale pour générer le rapport d'analyse.
    
    Args:
        bookmarks (list): Liste des bookmarks analysés.
        output_dir (str): Dossier de sortie.
        
    Returns:
        str: Chemin vers le rapport principal.
    """
    logger.info(f"Génération du rapport pour {len(bookmarks)} bookmarks")
    
    # Calculer les statistiques générales
    total_bookmarks = len(bookmarks)
    accessible = sum(1 for b in bookmarks if b.get('status', {}).get('accessible', False))
    redirected = sum(1 for b in bookmarks if b.get('status', {}).get('redirect', False))
    inaccessible = total_bookmarks - accessible
    
    quality_scores = [b.get('analysis', {}).get('quality_score', 0) for b in bookmarks 
                      if b.get('analysis', {}).get('quality_score') is not None]
    avg_quality = round(sum(quality_scores) / max(1, len(quality_scores)), 1)
    
    categories = set(b.get('categorization', {}).get('primary_category', 'Non classé') for b in bookmarks)
    category_count = len(categories)
    
    # Compter les groupes de doublons uniques
    duplicate_groups = set()
    for bookmark in bookmarks:
        if 'duplicates' in bookmark and bookmark['duplicates']:
            for dup_info in bookmark['duplicates']:
                duplicate_groups.add(dup_info.get('group', ''))
    
    duplicate_groups_count = len(duplicate_groups)
    
    # Générer les graphiques
    charts = generate_charts(bookmarks, output_dir)
    
    # Créer les résumés
    domain_summary = create_domain_summary(bookmarks)
    category_summary = create_category_summary(bookmarks)
    action_details = create_action_details(bookmarks)
    duplicates_summary = create_duplicates_summary(bookmarks)
    bookmarks_table = generate_bookmarks_table(bookmarks)
    
    # Préparer les données du rapport
    report_data = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_bookmarks': total_bookmarks,
        'accessible_bookmarks': accessible,
        'accessible_percent': round(accessible / total_bookmarks * 100, 1) if total_bookmarks > 0 else 0,
        'redirected_bookmarks': redirected,
        'redirected_percent': round(redirected / total_bookmarks * 100, 1) if total_bookmarks > 0 else 0,
        'inaccessible_bookmarks': inaccessible,
        'inaccessible_percent': round(inaccessible / total_bookmarks * 100, 1) if total_bookmarks > 0 else 0,
        'avg_quality': avg_quality,
        'category_count': category_count,
        'duplicate_groups': duplicate_groups_count,
        'domain_summary': domain_summary,
        'category_summary': category_summary,
        'action_details': action_details,
        'duplicates_summary': duplicates_summary,
        'bookmarks_table': bookmarks_table
    }
    
    # Générer les rapports
    html_path = generate_html_report(report_data, charts, output_dir)
    csv_files = generate_csv_reports(report_data, output_dir)
    
    # Enregistrer une copie des données complètes en JSON
    try:
        json_path = os.path.join(output_dir, 'reports', 'report_data.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            # Nettoyer les données pour la sérialisation JSON
            clean_data = report_data.copy()
            # Supprimer les éléments non sérialisables ou trop volumineux
            clean_data.pop('bookmarks_table', None)
            json.dump(clean_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Données du rapport enregistrées: {json_path}")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement des données JSON: {e}")
    
    logger.info(f"Génération du rapport terminée: {html_path}")
    return html_path

if __name__ == "__main__":
    # Test du module
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python report_generator.py <bookmarks.json>")
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
    
    # Définir le dossier de sortie
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    
    # Générer le rapport
    report_path = generate_report(bookmarks, output_dir)
    
    print(f"Rapport généré: {report_path}")
    print(f"Consultez le dossier {os.path.join(output_dir, 'reports')} pour tous les rapports.")
