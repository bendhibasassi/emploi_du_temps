"""Injection contrôlée. --dry-run explicite : simulation en mémoire.

N'importe pas Flask (évite les effets de bord d'initialisation).
Les collisions ou métadonnées insuffisantes provoquent un arrêt, jamais une fusion.
"""
import argparse
import csv
import hashlib
import json
import sqlite3
import sys
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'emploi_du_temps.db'
DRY_DB = ROOT / 'backups/PROD_REAL_008/emploi_du_temps_AVANT_PROD_REAL_008_20260912_013224.db'
PLAN = ROOT / 'donnees/injection_2026_2027/PLAN_PROD_REAL_007_20260912_012353'
REF = ROOT / 'donnees/referentiels_2026_2027/valides'
TIMES = [('08:00', '09:30'), ('09:40', '11:10'), ('11:20', '12:50'),
         ('13:00', '14:30'), ('14:40', '16:10'), ('16:20', '17:50')]

# Décisions métier confirmées le 12/09/2026.
MASTER_U_TO_A = {
    'M1-AFF', 'M1-CONT', 'M1-GOUV', 'M1-IMMO', 'M1-INT', 'M1-PEN',
    'M2-AFF', 'M2-CONT', 'M2-GOUV', 'M2-IMMO', 'M2-INT', 'M2-PEN',
}
L3_LEGACY_GROUP_LEVELS = {'L3-PRIV', 'L3-PUB'}
MASTER_LEGACY_GROUP_LEVELS = {
    'M1-AFF', 'M1-CONT', 'M1-GOUV', 'M1-IMMO', 'M1-INT', 'M1-PEN',
    'M2-AFF', 'M2-CONT', 'M2-GOUV', 'M2-IMMO', 'M2-INT', 'M2-PEN',
}
LEGACY_GROUP_LEVELS = L3_LEGACY_GROUP_LEVELS | MASTER_LEGACY_GROUP_LEVELS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter=';'))


def load_inputs():
    files = {
        'levels': REF / 'NIVEAUX_2026_2027.csv',
        'subjects_source': REF / 'MATIERES_2026_2027.csv',
        'teachers': REF / 'PROFESSEURS_PERMANENTS_2026_2027.csv',
        'rooms': REF / 'SALLES_EXISTENCE_2026_2027.csv',
        'sections': REF / 'SECTIONS_GROUPES_2026_2027.csv',
        'slots': REF / 'CRENEAUX_PRESENTIEL_2026_2027.csv',
        'level_plan': PLAN / '01_PLAN_NIVEAUX.csv',
        'teacher_plan': PLAN / '04_PLAN_PROFESSEURS.csv',
        'room_plan': PLAN / '03_PLAN_SALLES.csv',
        'subjects': PLAN / '06_MATIERES_CODIFIEES_PRE_IMPORT.csv',
    }
    data = {k: read_csv(p) for k, p in files.items()}
    data['hashes'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in files.values()}
    require(len(data['teachers']) == 101, 'Il faut 101 permanents.')
    require(all(r['categorie'] == 'PERMANENT' and r['statut_2026_2027'] == 'VALIDE_2026_2027'
                for r in data['teachers']), 'Personnel non permanent/non validé.')
    require(len({r['nom_complet'] for r in data['teachers']}) == 101, 'Noms permanents dupliqués.')
    require(len(data['sections']) == 17, 'Il faut 17 sections.')
    require(sum(int(r['nombre_groupes']) for r in data['sections']) == 54, 'Il faut 54 groupes.')
    require(len({(r['niveau_code'], r['section_code']) for r in data['sections']}) == 17,
            'Sections dupliquées dans le CSV.')
    for r in data['sections']:
        codes = r['codes_groupes'].split('|')
        require(len(codes) == len(set(codes)) == int(r['nombre_groupes']), 'Groupes incohérents.')
        require(r['annee_universitaire'] == '2026-2027' and r['ouverture'] == 'OUI', 'Année/ouverture incorrecte.')
    require(len(data['subjects']) == len(data['subjects_source']) == 82, 'Il faut 82 matières.')
    require(len({r['code_matiere'] for r in data['subjects']}) == 82, 'Codes matière dupliqués.')
    for p, s in zip(data['subjects'], data['subjects_source']):
        for field in ['semestre', 'ordre', 'matiere_ar', 'matiere_fr_source', 'cm', 'td', 'tp']:
            require(p[field] == s[field], f'Plan/source matière divergent : {field}')
        require(p['code_matiere'] and p['matiere_ar'] and p['statut_2026_2027'] == 'VALIDE_2026_2027',
                'Matière non validée ou vide.')
    require([(r['heure_debut'], r['heure_fin']) for r in data['slots']] == TIMES, 'Grille divergente.')
    require([r['code_creneau'] for r in data['slots']] == [f'PRES{i:02}' for i in range(1, 7)], 'Codes créneaux incorrects.')
    require(len({r['niveau_code'] for r in data['levels']}) == len(data['levels']), 'Niveaux dupliqués.')
    return data


def one(c, table, where, params):
    rows = c.execute(f'SELECT * FROM {table} WHERE {where}', params).fetchall()
    require(len(rows) <= 1, f'Correspondance ambiguë dans {table}: {params}')
    return rows[0] if rows else None


def insert(c, table, values):
    cols = ','.join(values)
    marks = ','.join('?' for _ in values)
    return c.execute(f'INSERT INTO {table} ({cols}) VALUES ({marks})', tuple(values.values())).lastrowid


def checks(c):
    require(not c.execute('PRAGMA foreign_key_check').fetchall(), 'foreign_key_check en échec.')
    require([r[0] for r in c.execute('PRAGMA integrity_check')] == ['ok'], 'integrity_check en échec.')


def snapshot(c, table):
    return [tuple(r) for r in c.execute(f'SELECT * FROM {table} ORDER BY 1')]


def inject(c, data, report):
    """Appelant responsable de BEGIN/COMMIT. N'effectue aucun commit implicite."""
    require(c.in_transaction, 'Transaction obligatoire.')
    checks(c)
    historical = {t: snapshot(c, t) for t in ['tbl_affectations', 'tbl_seances', 'tbl_indisponibilites']}
    old_times = {r['id_creneau']: (r['heure_debut'], r['heure_fin']) for r in c.execute('SELECT * FROM tbl_creneaux')}
    year = one(c, 'tbl_annees_univ', 'libelle=?', ('2026-2027',))
    old = one(c, 'tbl_annees_univ', 'libelle=?', ('2025-2026',))
    require(year and old, 'Les deux années doivent déjà exister ; dates non inventées.')
    yid = year['id_annee']
    historical_sections = [tuple(r) for r in c.execute('SELECT * FROM tbl_sections WHERE id_annee IS NOT ? ORDER BY 1', (yid,))]
    historical_groups = [tuple(r) for r in c.execute('SELECT g.* FROM tbl_groupes g JOIN tbl_sections s USING(id_section) WHERE s.id_annee IS NOT ? ORDER BY g.id_groupe', (yid,))]
    report.update({
        'modifications': Counter(),
        'matieres': {},
        'professeurs': {},
        'creneaux': {},
        'salles_exclues': [],
        'decisions_metier': {
            'DL-L3': {
                'cycle': 'Licence',
                'specialite': 'Licence double',
                'annee_etude': 'L3',
                'libelle': 'Licence double — troisième année',
                'id_formation': None,
                'id_specialite': None,
            },
            'sections_master': 'U -> A en conservant id_section',
            'groupes_legacy': 'L3 G1/G2 et Masters G1 conservés par FK, désactivés pour nouvelle planification; groupes numériques créés séparément',
        },
    })
    changes = report['modifications']
    lp = {r['code_niveau']: r for r in data['level_plan']}
    for r in data['levels']:
        code = r['niveau_code']
        require(r['statut_2026_2027'] == 'VALIDE_2026_2027', f'Niveau non validé: {code}')
        existing = one(c, 'tbl_niveaux', 'code_niveau=?', (code,))
        label = r['niveau_libelle']
        if code in ('M1-GOUV', 'M2-GOUV'):
            label = code[:2] + ' Gouvernance et lutte contre la corruption'
        if not existing:
            p = lp[code]
            if code == 'DL-L3':
                # Décision métier humaine confirmée :
                # DL-L3 = Licence double — troisième année.
                # Les FK id_formation/id_specialite sont facultatives et restent NULL
                # tant qu'aucune correspondance officielle locale n'est démontrée.
                cycle = 'Licence'
                spec = 'Licence double'
                study = 'L3'
                label = 'Licence double — troisième année'
            else:
                cycle, spec, study = p['cycle'], p['specialite'], p['annee_etude']
            require(all([cycle, spec, study, label]), f'Métadonnées niveau incomplètes: {code}')
            values = dict(code_niveau=code, cycle=cycle, specialite=spec, annee_etude=study, libelle=label, actif=1)
            if code == 'M2-ADMIN':
                parent = one(c, 'tbl_niveaux', 'code_niveau=?', ('M1-ADMIN',))
                require(parent is not None, 'M1-ADMIN absent.')
                values.update(id_formation=parent['id_formation'], id_specialite=parent['id_specialite'])
            insert(c, 'tbl_niveaux', values)
            changes['niveaux_ajoutes'] += 1
        elif code in ('M1-GOUV', 'M2-GOUV') and existing['libelle'] != label:
            c.execute('UPDATE tbl_niveaux SET libelle=? WHERE id_niveau=?', (label, existing['id_niveau']))
            changes['niveaux_harmonises'] += 1
    levels = {r['code_niveau']: r['id_niveau'] for r in c.execute('SELECT * FROM tbl_niveaux')}

    # Noms complets exacts ou ID explicitement validé par le plan ; aucune similarité floue.
    teacher_plan = {r['nom_officiel']: r for r in data['teacher_plan']}
    used = set()
    for r in data['teachers']:
        name = r['nom_complet']
        p = teacher_plan[name]
        matches = [t for t in c.execute('SELECT * FROM tbl_professeurs')
                   if ' '.join(filter(None, [t['nom'], t['prenom']])).strip() == name or t['nom'] == name]
        if p['id_professeur_existant']:
            t = one(c, 'tbl_professeurs', 'id_professeur=?', (int(p['id_professeur_existant']),))
            require(t is not None and any(m['id_professeur'] == t['id_professeur'] for m in matches),
                    f'Identité du plan non vérifiée: {name}')
        require(len(matches) <= 1, f'Homonymie/ambiguïté professeur: {name}')
        if matches:
            t = matches[0]; tid = t['id_professeur']
            require(t['statut'] == 'Permanent', f'Statut professeur divergent: {name}')
            if not t['actif']:
                c.execute('UPDATE tbl_professeurs SET actif=1 WHERE id_professeur=?', (tid,))
        else:
            tid = insert(c, 'tbl_professeurs', dict(nom=name, prenom=None, grade=r['grade_ou_type'] or None,
                         statut='Permanent', actif=1, peut_cm=1, peut_td=1, peut_tp=0))
            changes['professeurs_ajoutes'] += 1
        require(tid not in used, 'Deux permanents liés au même ID.'); used.add(tid)
        report['professeurs'][name] = tid

    expected_sections, expected_groups = set(), set()
    section_targets = {}
    for r in data['sections']:
        section_targets.setdefault(r['niveau_code'], set()).add(r['section_code'])
    for r in data['sections']:
        if r['niveau_code'] not in levels:
            report['blocages'].append({'objet': f"{r['niveau_code']}/{r['section_code']}", 'action': 'BLOQUE',
                                       'raison': 'Niveau absent ; section/groupes dépendants non simulés.'})
            continue
        nid = levels[r['niveau_code']]
        previous = c.execute(
            'SELECT * FROM tbl_sections WHERE id_annee=? AND id_niveau=?',
            (yid, nid)
        ).fetchall()
        unknown = [
            s['code_section']
            for s in previous
            if s['code_section'] not in section_targets[r['niveau_code']]
        ]

        # Décision métier confirmée : pour les 12 Masters concernés,
        # l'unique section historique U devient A en conservant id_section.
        if unknown:
            can_harmonize_u_to_a = (
                r['niveau_code'] in MASTER_U_TO_A
                and r['section_code'] == 'A'
                and set(unknown) == {'U'}
                and len(previous) == 1
                and previous[0]['code_section'] == 'U'
            )
            if can_harmonize_u_to_a:
                legacy = previous[0]
                c.execute(
                    'UPDATE tbl_sections SET code_section=?, libelle=?, actif=1 WHERE id_section=?',
                    ('A', 'A', legacy['id_section'])
                )
                changes['sections_harmonisees_U_A'] += 1
                previous = c.execute(
                    'SELECT * FROM tbl_sections WHERE id_annee=? AND id_niveau=?',
                    (yid, nid)
                ).fetchall()
                unknown = [
                    s['code_section']
                    for s in previous
                    if s['code_section'] not in section_targets[r['niveau_code']]
                ]

        if unknown:
            report['blocages'].append({
                'action': 'BLOQUE',
                'objet': f"section {r['niveau_code']}/{r['section_code']}",
                'raison': (
                    f'Sections existantes {unknown} hors codes cibles : '
                    'correspondance métier non couverte par les décisions validées.'
                ),
            })
            continue

        s = one(
            c,
            'tbl_sections',
            'id_annee=? AND id_niveau=? AND code_section=?',
            (yid, nid, r['section_code'])
        )
        if s:
            sid = s['id_section']
            old_groups = c.execute(
                'SELECT * FROM tbl_groupes WHERE id_section=?',
                (sid,)
            ).fetchall()
            target_group_codes = r['codes_groupes'].split('|')
            unknown_groups = [
                g['code_groupe']
                for g in old_groups
                if g['code_groupe'] not in target_group_codes
            ]

            # Décision métier confirmée pour L3 :
            # G1/G2 ne sont PAS remappés vers 01/02.
            # On conserve leurs IDs/FK pour les affectations existantes,
            # mais on les désactive pour la nouvelle planification.
            if unknown_groups:
                legacy_ok = (
                    r['niveau_code'] in LEGACY_GROUP_LEVELS
                    and set(unknown_groups).issubset({'G1', 'G2'})
                )
                if legacy_ok:
                    for g in old_groups:
                        if g['code_groupe'] in unknown_groups and g['actif']:
                            c.execute(
                                'UPDATE tbl_groupes SET actif=0 WHERE id_groupe=?',
                                (g['id_groupe'],)
                            )
                            changes['groupes_legacy_G1_G2_desactives'] += 1
                else:
                    report['blocages'].append({
                        'action': 'BLOQUE',
                        'objet': f"groupes {r['niveau_code']}/{r['section_code']}",
                        'raison': (
                            f'Codes existants {unknown_groups} et cibles '
                            f'{r["codes_groupes"]} : correspondance non validée.'
                        ),
                    })
                    continue

            if not s['actif']:
                c.execute(
                    'UPDATE tbl_sections SET actif=1 WHERE id_section=?',
                    (sid,)
                )
        else:
            sid = insert(
                c,
                'tbl_sections',
                dict(
                    id_annee=yid,
                    id_niveau=nid,
                    code_section=r['section_code'],
                    libelle=r['section_code'],
                    effectif=None,
                    actif=1,
                )
            )
            changes['sections_ajoutees'] += 1
        expected_sections.add(sid)
        for code in r['codes_groupes'].split('|'):
            g = one(c, 'tbl_groupes', 'id_section=? AND code_groupe=?', (sid, code))
            if g:
                gid = g['id_groupe']
                if not g['actif']: c.execute('UPDATE tbl_groupes SET actif=1 WHERE id_groupe=?', (gid,))
            else:
                gid = insert(c, 'tbl_groupes', dict(id_section=sid, code_groupe=code, nom_groupe=code, effectif=None, actif=1))
                changes['groupes_ajoutes'] += 1
            expected_groups.add(gid)
    # Aucun surplus n'est désactivé implicitement : il peut porter des affectations officielles.
    for s in c.execute('SELECT * FROM tbl_sections WHERE id_annee=? AND actif=1', (yid,)).fetchall():
        if s['id_niveau'] not in {levels[k] for k in section_targets if k in levels}:
            report['blocages'].append({'action': 'BLOQUE', 'objet': f"section id={s['id_section']}",
                'raison': 'Section active hors référentiel cible ; décision explicite de conservation/désactivation nécessaire.'})

    for p, s in zip(data['subjects'], data['subjects_source']):
        code, name, nid, semester = p['code_matiere'], p['matiere_ar'], levels[p['niveau_code']], p['semestre']
        mode = s['mode_pedagogique']
        flags = {'CM': (1, 0), 'CM + TD': (1, 1), 'TD': (0, 1), 'Mémoire': (0, 0), 'Séminaire': (0, 0)}.get(mode)
        if flags is None:
            # Inconnu conservé comme NULL : ne pas traduire une absence en absence de CM/TD.
            require(not mode and not any(p[k] for k in ['cm', 'td', 'tp']), f'Type non géré: {code}')
            flags = (None, None)
        by_code = one(c, 'tbl_matieres', 'code_matiere=?', (code,))
        matches = c.execute('SELECT * FROM tbl_matieres WHERE id_niveau=? AND semestre=? AND nom_matiere=?',
                            (nid, semester, name)).fetchall()
        require(len(matches) <= 1, f'Matière métier ambiguë: {code}')
        if by_code:
            require(by_code['id_niveau'] == nid and by_code['semestre'] == semester and by_code['nom_matiere'] == name,
                    f'Collision code matière: {code}')
            require(not matches or matches[0]['id_matiere'] == by_code['id_matiere'], f'Doublon matière: {code}')
        existing = by_code or (matches[0] if matches else None)
        if existing:
            mid = existing['id_matiere']
            # Pas de réécriture des codes/flags partagés avec l'historique : correspondance explicite dans le rapport.
            require(all(f is None or existing[k] == f for k, f in zip(['avec_cm', 'avec_td'], flags)),
                    f'Caractéristiques matière existante divergentes: {code}')
            if not existing['actif']: c.execute('UPDATE tbl_matieres SET actif=1 WHERE id_matiere=?', (mid,))
        else:
            mid = insert(c, 'tbl_matieres', dict(code_matiere=code, nom_matiere=name, id_niveau=nid,
                         semestre=semester, avec_cm=flags[0], avec_td=flags[1], actif=1))
            changes['matieres_ajoutees'] += 1
        report['matieres'][code] = {'id_matiere': mid, 'code_stocke': existing['code_matiere'] if existing else code}
    require(len({v['id_matiere'] for v in report['matieres'].values()}) == 82, 'Fusion matière interdite.')

    rp = {r['code_salle']: r for r in data['room_plan']}
    for r in data['rooms']:
        code = r['code_canonique']
        if code in {f'SP{i}' for i in range(1, 11)}:
            report['salles_exclues'].append(code); continue
        room = one(c, 'tbl_salles', 'code_salle=?', (code,))
        if not room:
            typ = rp[code]['type_salle_source']; require(typ, f'Type salle absent: {code}')
            insert(c, 'tbl_salles', dict(code_salle=code, nom_salle=code, type_salle=typ, capacite=None, actif=1))
            changes['salles_ajoutees'] += 1

    # ordre est globalement UNIQUE, pas annualisé. Déplacer les anciens ordres,
    # sans changer aucun ID ni horaire référencé, puis réserver 1..6 à la grille cible.
    slots = c.execute('SELECT * FROM tbl_creneaux ORDER BY id_creneau').fetchall()
    selected = []
    for start, end in TIMES:
        matches = [r for r in slots if r['heure_debut'][:5] == start and r['heure_fin'][:5] == end]
        require(len(matches) <= 1, f'Créneau horaire ambigu: {start}')
        selected.append(matches[0]['id_creneau'] if matches else None)
    offset = max([r['ordre'] for r in slots] + [6]) + 100
    for i, r in enumerate(slots):
        if r['id_creneau'] in selected or r['ordre'] in range(1, 7):
            c.execute('UPDATE tbl_creneaux SET ordre=?, actif=0 WHERE id_creneau=?', (offset+i, r['id_creneau']))
        elif r['actif']:
            c.execute('UPDATE tbl_creneaux SET actif=0 WHERE id_creneau=?', (r['id_creneau'],))
    for order, ((start, end), cid) in enumerate(zip(TIMES, selected), 1):
        if cid is None:
            cid = insert(c, 'tbl_creneaux', dict(heure_debut=start+':00.000000', heure_fin=end+':00.000000', ordre=order, actif=1))
        else:
            c.execute('UPDATE tbl_creneaux SET ordre=?, actif=1 WHERE id_creneau=?', (order, cid))
        report['creneaux'][f'PRES{order:02}'] = cid
    for r in c.execute('SELECT * FROM tbl_creneaux'):
        if r['id_creneau'] in old_times:
            require(old_times[r['id_creneau']] == (r['heure_debut'], r['heure_fin']), 'Horaire historique modifié.')
    for table, before in historical.items():
        require(snapshot(c, table) == before, f'Historique modifié: {table}')
    require(historical_sections == [tuple(r) for r in c.execute('SELECT * FROM tbl_sections WHERE id_annee IS NOT ? ORDER BY 1', (yid,))], 'Sections historiques modifiées.')
    require(historical_groups == [tuple(r) for r in c.execute('SELECT g.* FROM tbl_groupes g JOIN tbl_sections s USING(id_section) WHERE s.id_annee IS NOT ? ORDER BY g.id_groupe', (yid,))], 'Groupes historiques modifiés.')
    require(report['blocages'] or (len(expected_sections) == 17 and len(expected_groups) == 54), 'Volumes sections/groupes incorrects.')
    report['sections_cibles_resolues'] = len(expected_sections)
    report['groupes_cibles_resolus'] = len(expected_groups)
    report['controles'] = {'foreign_key_check': 0, 'integrity_check': 'ok',
                          'affectations_inchangees': len(historical['tbl_affectations']),
                          'seances_inchangees': len(historical['tbl_seances']),
                          'horaires_historiques_inchanges': len(old_times),
                          'permanents_resolus': len(used), 'matieres_resolues': len(report['matieres'])}
    checks(c)
    if report['blocages']:
        return report
    # Dernières écritures métier uniquement après tous les contrôles précédents.
    c.execute('UPDATE tbl_annees_univ SET active=0 WHERE active IS NOT 0 AND id_annee<>?', (yid,))
    c.execute('UPDATE tbl_annees_univ SET active=1 WHERE id_annee=?', (yid,))
    checks(c)
    return report


def collect_operations(c, before_tables, report):
    """Diff détaillé, y compris les lignes inchangées ; aucune écriture."""
    ops = []
    for table, before in before_tables.items():
        after = [dict(r) for r in c.execute(f'SELECT * FROM {table}')]
        pk = next(r['name'] for r in c.execute(f'PRAGMA table_info({table})') if r['pk'] == 1)
        old = {r[pk]: r for r in before}
        for row in after:
            prev = old.pop(row[pk], None)
            action = 'INSERT' if prev is None else ('INCHANGE' if prev == row else 'UPDATE')
            ops.append({'table': table, 'id': row[pk], 'action': action, 'avant': prev, 'apres': row})
        require(not old, f'Suppression interdite dans {table}.')
    report['operations'] = ops + report['blocages']
    report['totaux_actions'] = dict(Counter(r['action'] for r in report['operations']))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--apply', action='store_true', help='Écriture réelle et atomique dans la base principale.')
    mode.add_argument('--dry-run', action='store_true', help='Simulation en mémoire depuis une sauvegarde en lecture seule.')
    mode.add_argument('--static-check', action='store_true', help='CSV seulement ; aucune base ouverte.')
    parser.add_argument('--database', type=Path, help='Sauvegarde pour --dry-run ; --apply impose la base principale.')
    parser.add_argument('--pause', action='store_true', help='Attendre Entrée avant fermeture, succès ou erreur.')
    args = parser.parse_args(argv)
    c = None
    report = {'blocages': [], 'operations': []}
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    before_tables = {}
    path = None
    try:
        data = load_inputs()
        if args.static_check:
            print('Contrôles statiques CSV OK. Aucune base ouverte.')
            print('Décision métier intégrée: DL-L3 = Licence / Licence double / L3 ; FK formation/spécialité laissées NULL sans preuve locale.')
            print('Décision métier intégrée: sections Masters U -> A avec conservation de id_section.')
            print('Décision métier intégrée: groupes L3 G1/G2 non remappés, conservés par FK et désactivés pour la nouvelle planification.')
            return 0
        database = args.database or (DB if args.apply else DRY_DB)
        require(database.resolve().is_file(), 'Base inexistante ; création implicite interdite.')
        if args.apply:
            require(database.resolve() == DB.resolve(), '--apply autorisé uniquement sur la base principale racine.')
            c = sqlite3.connect(DB.resolve().as_uri()+'?mode=rw', uri=True, isolation_level=None, timeout=30)
        else:
            require(database.resolve() != DB.resolve(), '--dry-run : utiliser une sauvegarde, jamais la base principale.')
            c = sqlite3.connect(':memory:', isolation_level=None)
            reader = sqlite3.connect(database.resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
            try: reader.backup(c)
            finally: reader.close()
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        c.execute('BEGIN IMMEDIATE')
        report.update({'mode': 'APPLY' if args.apply else 'DRY_RUN', 'base_source': str(database.resolve()), 'sources_sha256': data['hashes']})
        if not args.apply:
            report['base_source_sha256_avant'] = hashlib.sha256(database.read_bytes()).hexdigest()
        for table in ['tbl_niveaux', 'tbl_professeurs', 'tbl_sections', 'tbl_groupes', 'tbl_matieres', 'tbl_salles', 'tbl_creneaux', 'tbl_annees_univ']:
            before_tables[table] = [dict(r) for r in c.execute(f'SELECT * FROM {table}')]
        if args.apply:
            folder = ROOT/'backups/PROD_REAL_008_FIX'; folder.mkdir(parents=True, exist_ok=True)
            backup = folder/f'emploi_du_temps_AVANT_FIX_{stamp}.db'
            # Le verrou réservé bloque les écrivains pendant la sauvegarde et la transaction.
            with sqlite3.connect(DB.resolve().as_uri()+'?mode=ro', uri=True) as reader:
                with sqlite3.connect(backup) as target:
                    reader.backup(target); checks(target)
            report['backup'] = str(backup)
            report['backup_sha256'] = hashlib.sha256(backup.read_bytes()).hexdigest()
            print('Sauvegarde cohérente:', backup)
        inject(c, data, report)
        collect_operations(c, before_tables, report)
        if not args.apply:
            report['base_source_sha256_apres'] = hashlib.sha256(database.read_bytes()).hexdigest()
            require(report['base_source_sha256_avant'] == report['base_source_sha256_apres'], 'Sauvegarde source modifiée.')
        # Rapport de correspondances persisté AVANT commit : échec disque => rollback.
        folder = ROOT/'donnees/injection_2026_2027/PROD_REAL_008_FIX'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder/f'{report["mode"]}_{stamp}.json'
        report['transaction'] = 'BLOQUE_ROLLBACK' if report['blocages'] else ('VALIDEE_AVANT_COMMIT' if args.apply else 'SIMULATION_SANS_ECRITURE_CIBLE')
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        if report['blocages']:
            c.rollback()
            print('BLOQUE — rollback intégral. Rapport:', path)
            for b in report['blocages']: print(b['objet'], ':', b['raison'])
            return 1
        if args.apply:
            checks(c); c.commit(); print('COMMIT réussi.')
        else:
            c.rollback(); print('Dry-run réussi en mémoire ; base source inchangée.')
        print('Rapport:', path)
        return 0
    except Exception as exc:
        report['blocages'].append({'action': 'BLOQUE', 'objet': 'transaction', 'raison': f'{type(exc).__name__}: {exc}'})
        if c is not None and before_tables:
            collect_operations(c, before_tables, report)
        if c is not None and c.in_transaction:
            c.rollback()
        report['transaction'] = 'BLOQUE_ROLLBACK'
        folder = ROOT/'donnees/injection_2026_2027/PROD_REAL_008_FIX'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder/f'BLOQUE_{stamp}.json'
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Rapport détaillé:', path)
        print(f'ERREUR — aucune transaction partielle conservée : {type(exc).__name__}: {exc}', file=sys.stderr)
        traceback.print_exc()
        return 1
    finally:
        if c is not None: c.close()
        if args.pause:
            try: input('Appuyez sur Entrée pour fermer...')
            except EOFError: pass


if __name__ == '__main__':
    sys.exit(main())