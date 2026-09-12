# PROD-REAL-008-FIX — préparation, sans injection réelle

Le script temporaire original et son traceback n'ont pas été conservés. La cause
exacte ne peut donc pas être certifiée. Le plan comporte un défaut susceptible de
provoquer l'échec : DL-L3 a trois champs métier vides alors que le modèle les impose.
Une insertion de NULL violerait NOT NULL ; des chaînes vides, elles, seraient
acceptées par SQLite mais resteraient des données invalides. Aucune erreur précise
SQLite n'est attribuée à l'essai passé sans preuve.

## Périmètre et commandes

Depuis la racine du projet :

```powershell
python -X utf8 scripts/prod_real_008_fix.py --static-check
python -X utf8 scripts/prod_real_008_fix.py --dry-run --pause
python -X utf8 scripts/test_prod_real_008_fix.py
```

Le dry-run exige une sauvegarde et refuse la base principale. Par défaut il lit
`backups/PROD_REAL_008/emploi_du_temps_AVANT_PROD_REAL_008_20260912_013224.db`
en mode SQLite `ro&immutable=1`, puis utilise une copie en mémoire. Cette option est
réservée à une sauvegarde fermée, sans journal WAL à rejouer. Une autre sauvegarde
peut être donnée avec `--database CHEMIN`. La base principale n'a pas été ouverte
pendant cette préparation.

Commande future, **non exécutée, à utiliser seulement après résolution des blocages
et nouveau dry-run conforme** :

```powershell
python -X utf8 scripts/prod_real_008_fix.py --apply --pause
```

## Protections

- Modes explicites et exclusifs ; aucun import Flask, aucune création implicite de base.
- `BEGIN IMMEDIATE`, sauvegarde SQLite cohérente sous verrou avant les écritures,
  contrôle de cette sauvegarde, rollback sur erreur.
- Rapport JSON détaillé INSERT / UPDATE / INCHANGE / BLOQUE, anciennes et nouvelles
  valeurs, hashes des CSV, correspondances des 82 codes matière vers les IDs.
- Horaires et IDs de tous les créneaux préexistants conservés ; créneaux cibles
  réutilisés par paire horaire exacte ou ajoutés. Les anciens ordres hors grille
  sont déplacés et désactivés ; les ordres 1–6 restent uniques pour la grille active.
  Aucune FK de séance ou d'indisponibilité n'est déplacée.
- Aucune suppression ; toutes les affectations, séances, indisponibilités, sections
  et groupes historiques sont comparés avant/après.
- Capacités/effectifs absents restent NULL lors d'une création ; les valeurs
  préexistantes ne sont pas remplacées par des estimations.
- Correspondances professeurs exactes et vérification des IDs du plan ; pas de
  vacataire ajouté, pas de rapprochement flou.
- Matières réutilisées uniquement sur nom exact + niveau + semestre, sans modifier
  leur code historique ; le rapport expose les codes du plan et les codes stockés.
  Divergences de flags explicites et ambiguïtés bloquent. Type inconnu : flags NULL.
- SP1–SP10 exclus. Activation de 2026-2027 en dernières écritures métier,
  foreign_key_check et integrity_check avant commit.

## Résultat de la simulation sur la sauvegarde réelle

**BLOQUÉ, rollback intégral** :

1. DL-L3 : aucun DL-L1/DL-L2, aucune formation/spécialité Licence double exploitable
   dans les deux sauvegardes inspectées et les références textuelles consultées.
   Le libellé et la troisième année sont connus ; la spécialité et son rattachement
   ne le sont pas. Aucune valeur de remplacement n'est inventée.
2. Quatre sections Licence : groupes G1/G2 existants contre codes cibles numériques
   continus (01…12). Une correspondance métier explicite est nécessaire.
3. Douze sections Master : code existant U contre code cible A. Il faut valider les
   correspondances sections ET groupes avant synchronisation. Le script ne crée
   pas une seconde occurrence en supposant que ces objets sont distincts.

Les autres étapes sont simulées en mémoire, puis intégralement annulées.
101 permanents et 82 matières résolus ; 14 matières réutilisées, 68 insertions matière
simulées. 500 affectations et 9 séances inchangées ; les 5 horaires existants sont
identiques ; FK=0 et intégrité=ok. Les hashes avant/après de la sauvegarde sont identiques.

Trois tests passent : blocages réels avec rollback, réussite/idempotence avec des
références **synthétiques réservées aux tests**, erreur forcée après écritures avec
rollback. Le test de réussite n'est pas une validation métier de DL-L3.

## Limites avant production

- Le schéma n'annualise pas les créneaux. Les horaires historiques restent exacts,
  mais les écrans qui filtrent uniquement `actif=1` peuvent masquer les anciens
  créneaux ; aucune correction d'interface n'est incluse.
- Niveaux, professeurs et matières sont globaux. Les harmonisations autorisées
  sont visibles également lors de la consultation d'anciennes années.
- La simulation décrit la sauvegarde de 01:32:24, pas une lecture de la base actuelle.
- Le rapport APPLY écrit avant COMMIT porte `VALIDEE_AVANT_COMMIT` : seule la sortie
  `COMMIT réussi` confirme le commit. Un arrêt processus pendant le commit requiert
  un audit de l'état réel ; il ne faut pas interpréter le rapport préparatoire comme
  une attestation de commit.
