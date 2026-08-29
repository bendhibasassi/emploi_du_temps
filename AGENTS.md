# Projet Emploi du Temps Universitaire

## Objectif
Application Flask de gestion et de génération d'emplois du temps universitaires.

## Stack
Python, Flask, SQLAlchemy, SQLite, Bootstrap et Alembic.

## Sources de vérité
- `app/models.py` est la définition officielle des modèles.
- `emploi_du_temps.db` à la racine est la base locale principale.
- Ne pas utiliser `instance/emploi_du_temps.db` comme base principale.
- Préserver toutes les données existantes.

## Architecture métier
Niveau -> Section -> Groupe

Professeur + Matière + Section/Groupe -> Affectation -> Séance

Une Affectation définit QUI enseigne QUOI et À QUI.
Une Séance définit QUAND et OÙ.

## Règles pédagogiques
- CM : concerne toute la section.
- TD/TP : concerne un groupe.
- Un conflit CM doit être vérifié au niveau de la section.
- Un conflit TD/TP doit être vérifié au niveau du groupe.
- Capacité CM : utiliser `Section.effectif`.
- Capacité TD/TP : utiliser `Groupe.effectif`.

## Affectations
Les affectations existantes sont des données pédagogiques officielles.
Ne pas créer automatiquement une affectation depuis une séance sauf demande explicite.

## Sécurité des données
Sans autorisation explicite :
- ne pas supprimer ou recréer la base ;
- ne pas réinitialiser les migrations ;
- ne pas exécuter de migration destructive ;
- ne pas faire `git reset --hard` ;
- ne pas faire `git push`.

## Méthode de travail
Pour chaque tâche :
1. Lire seulement les fichiers nécessaires.
2. Modifier seulement ce qui est demandé.
3. Ne pas refactoriser d'autres parties sans demande.
4. Exécuter les contrôles/tests nécessaires.
5. Ne pas lancer une analyse complète du projet sauf demande explicite.

## Compte-rendu
À la fin d'une tâche, répondre brièvement avec :
- fichiers modifiés ;
- changements réalisés ;
- tests exécutés ;
- résultat ;
- blocage éventuel.