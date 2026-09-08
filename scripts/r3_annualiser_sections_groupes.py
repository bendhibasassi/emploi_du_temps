"""Rejoue R3K/R3M/R3N/R3O apres les migrations de schema R3J et R3L.

Usage : python scripts/r3_annualiser_sections_groupes.py --database CHEMIN [--apply]
Par defaut : connexion SQLite mode=ro, aucune ecriture. Aucun schema cree.
Les etats partiels/inattendus sont refuses ; ALREADY_APPLIED interdit de rejouer.
Les correspondances sources sont celles validees en R3F ; les nouveaux IDs
sont generes par SQLite. Aucune correction Matiere/Section n'est effectuee.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys


SOURCE_SECTIONS = set(range(6, 22))
SOURCE_GROUPS = set(range(8, 28))
EXCLUDED_SECTIONS = {1, 2, 3, 4, 5, 22}
EXCLUDED_GROUPS = {2, 3, 4, 6, 7, 28}
EXPECTED = {"sections": 38, "groupes": 46, "affectations": 500,
            "seances": 9, "sections_null": 6, "groupes_sections_null": 6,
            "references_croisees": 0, "violations_fk": 0}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def snapshot(conn):
    """Copie en memoire uniquement, y compris toutes les tables hors perimetre."""
    result = {}
    for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        quoted = '"' + name.replace('"', '""') + '"'
        result[name] = [dict(r) for r in conn.execute('SELECT * FROM ' + quoted)]
    return result


def canonical(rows):
    return sorted(json.dumps(r, sort_keys=True, ensure_ascii=True) for r in rows)


def schema(conn):
    return [tuple(r) for r in conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]


def check_schema(conn):
    columns = {r['name']: r for r in conn.execute('PRAGMA table_info(tbl_sections)')}
    require('id_annee' in columns and columns['id_annee']['notnull'] == 0,
            'Prerequis R3J absent : Section.id_annee doit etre nullable.')
    require(any(r['from'] == 'id_annee' and r['table'] == 'tbl_annees_univ'
                and r['to'] == 'id_annee'
                for r in conn.execute('PRAGMA foreign_key_list(tbl_sections)')),
            'FK Section/Annee absente.')
    for table, expected in [('tbl_sections', ['id_annee', 'id_niveau', 'code_section']),
                            ('tbl_groupes', ['id_section', 'code_groupe'])]:
        keys = []
        for idx in conn.execute('PRAGMA index_list(' + table + ')').fetchall():
            if idx['unique'] and not idx['partial']:
                name = idx['name'].replace('"', '""')
                keys.append([r['name'] for r in conn.execute('PRAGMA index_info("' + name + '")')])
        require(expected in keys, 'Unicite requise absente : ' + table)
        if table == 'tbl_sections':
            require(['id_niveau', 'code_section'] not in keys,
                    'Prerequis R3L absent : ancienne unicite toujours presente.')
    require(not conn.execute('PRAGMA foreign_key_check').fetchall(), 'Violation FK existante.')


def inspect_state(conn):
    check_schema(conn)
    data = snapshot(conn)
    years = data['tbl_annees_univ']
    def year(label):
        found = [r['id_annee'] for r in years if r['libelle'] == label]
        require(len(found) == 1, 'Annee absente ou ambigue : ' + label)
        return found[0]
    old_year, new_year = year('2025-2026'), year('2026-2027')
    require(len(years) == 2, 'Nombre d annees inattendu.')
    sections = {r['id_section']: r for r in data['tbl_sections']}
    groups = {r['id_groupe']: r for r in data['tbl_groupes']}
    affs = data['tbl_affectations']
    require(SOURCE_SECTIONS | EXCLUDED_SECTIONS <= sections.keys(), 'Sections historiques manquantes.')
    require(SOURCE_GROUPS | EXCLUDED_GROUPS <= groups.keys(), 'Groupes historiques manquants.')
    require(all(sections[i]['id_annee'] is None for i in EXCLUDED_SECTIONS),
            'Une Section exclue a ete annualisee.')
    require({i for i, g in groups.items() if g['id_section'] in EXCLUDED_SECTIONS}
            == EXCLUDED_GROUPS, 'Groupes exclus inattendus.')
    require(all(groups[i]['id_section'] in SOURCE_SECTIONS for i in SOURCE_GROUPS),
            'Rattachement historique Groupe/Section invalide.')
    require(len(affs) == 500 and Counter(a['id_annee'] for a in affs)
            == {old_year: 250, new_year: 250}, 'Volumetrie Affectations inattendue.')
    for y in (old_year, new_year):
        require(Counter(a['type_enseignement'] for a in affs if a['id_annee'] == y)
                == {'CM': 110, 'TD': 140}, 'Repartition CM/TD/TP inattendue.')
    for a in affs:
        sid, gid = a['id_section'], a['id_groupe']
        require(sid in sections and sid not in EXCLUDED_SECTIONS, 'Section Affectation invalide.')
        require((a['type_enseignement'] == 'CM' and gid is None) or
                (a['type_enseignement'] == 'TD' and gid in groups
                 and groups[gid]['id_section'] == sid),
                'Regle CM/TD ou coherence Groupe/Section invalide : ' + str(a['id_affectation']))
        if a['id_annee'] == old_year:
            require(sid in SOURCE_SECTIONS and (gid is None or gid in SOURCE_GROUPS),
                    'References historiques 2025-2026 inattendues.')
    seances = data['tbl_seances']
    by_aff = {a['id_affectation']: a for a in affs}
    require(len(seances) == 9, 'Nombre de Seances inattendu.')
    require(all(s['id_annee'] == old_year and s['id_affectation'] in by_aff
                and by_aff[s['id_affectation']]['id_annee'] == old_year for s in seances),
            'Seances hors annee historique ou references invalides.')
    for table, key in [('tbl_sections', ('id_annee', 'id_niveau', 'code_section')),
                       ('tbl_groupes', ('id_section', 'code_groupe'))]:
        counts = Counter(tuple(r[k] for k in key) for r in data[table])
        require(all(n == 1 for n in counts.values()), 'Doublon : ' + table)
    targets = {i: s for i, s in sections.items() if s['id_annee'] == new_year}
    if targets:
        require(len(sections) == 38 and len(groups) == 46 and len(targets) == 16,
                'Etat partiel : copies annuelles incompletes.')
        require(all(sections[i]['id_annee'] == old_year for i in SOURCE_SECTIONS),
                'Etat partiel : Sections historiques non rattachees.')
        sm, gm = {}, {}
        for i in sorted(SOURCE_SECTIONS):
            s = sections[i]
            matches = [j for j, t in targets.items()
                       if t['id_niveau'] == s['id_niveau'] and t['code_section'] == s['code_section']]
            require(len(matches) == 1, 'Correspondance annuelle Section absente/ambigue.')
            j = matches[0]
            require(all(s[k] == sections[j][k] for k in s if k not in ('id_section', 'id_annee')),
                    'Caracteristiques Section copiee differentes.')
            sm[i] = j
        require(set(sm.values()).isdisjoint(SOURCE_SECTIONS | EXCLUDED_SECTIONS),
                'IDs copies Section invalides.')
        for i in sorted(SOURCE_GROUPS):
            g = groups[i]
            matches = [j for j, t in groups.items() if t['id_section'] == sm[g['id_section']]
                       and t['code_groupe'] == g['code_groupe']]
            require(len(matches) == 1, 'Correspondance annuelle Groupe absente/ambigue.')
            j = matches[0]
            require(all(g[k] == groups[j][k] for k in g if k not in ('id_groupe', 'id_section')),
                    'Caracteristiques Groupe copie differentes.')
            gm[i] = j
        require(set(gm.values()).isdisjoint(SOURCE_GROUPS | EXCLUDED_GROUPS),
                'IDs copies Groupe invalides.')
        require(all(a['id_section'] in sm.values() and
                    (a['id_groupe'] is None or a['id_groupe'] in gm.values())
                    for a in affs if a['id_annee'] == new_year),
                'Etat partiel : Affectations non reorientees.')
        require(all(sections[a['id_section']]['id_annee'] == a['id_annee'] for a in affs),
                'Reference croisee entre annees.')
        return 'ALREADY_APPLIED', data, old_year, new_year
    require(len(sections) == 22 and len(groups) == 26, 'Etat initial inattendu.')
    source_years = {sections[i]['id_annee'] for i in SOURCE_SECTIONS}
    require(source_years in ({None}, {old_year}), 'Rattachement historique partiel/inattendu.')
    require(all(a['id_section'] in SOURCE_SECTIONS and
                (a['id_groupe'] is None or a['id_groupe'] in SOURCE_GROUPS) for a in affs),
            'References initiales hors correspondances validees.')
    require({a['id_section'] for a in affs if a['id_annee'] == old_year} == SOURCE_SECTIONS,
            'Sections candidates non confirmees par les Affectations historiques.')
    require({a['id_groupe'] for a in affs if a['id_groupe'] is not None} == SOURCE_GROUPS,
            'Groupes candidats non confirmes par les Affectations.')
    return 'READY', data, old_year, new_year


def run(path, apply=False):
    require(path.is_file(), 'Base inexistante : ' + str(path))
    conn = sqlite3.connect(path.as_uri() + ('?mode=rw' if apply else '?mode=ro'), uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        if not apply:
            conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
        state, before, old_year, new_year = inspect_state(conn)
        print(state)
        if state == 'ALREADY_APPLIED':
            print('Aucune ecriture ; deuxieme application refusee.')
            conn.rollback()
            return 2 if apply else 0
        report = {
            'sections_a_annualiser': [r['id_section'] for r in before['tbl_sections']
                                     if r['id_section'] in SOURCE_SECTIONS and r['id_annee'] is None],
            'sections_a_dupliquer': sorted(SOURCE_SECTIONS),
            'groupes_a_dupliquer': sorted(SOURCE_GROUPS),
            'affectations_a_reorienter': sorted(a['id_affectation'] for a in before['tbl_affectations']
                                              if a['id_annee'] == new_year),
            'sections_null_exclues': sorted(EXCLUDED_SECTIONS),
            'groupes_exclus': sorted(EXCLUDED_GROUPS), 'controles_attendus': EXPECTED,
        }
        print(json.dumps(report, ensure_ascii=True, indent=2))
        if not apply:
            print('DRY_RUN : aucune ecriture.')
            conn.rollback()
            return 0
        old_schema = schema(conn)
        expected = {t: [dict(r) for r in rows] for t, rows in before.items()}
        sm, gm = {}, {}
        for s in sorted(before['tbl_sections'], key=lambda r: r['id_section']):
            if s['id_section'] not in SOURCE_SECTIONS:
                continue
            conn.execute('UPDATE tbl_sections SET id_annee=? WHERE id_section=?',
                         (old_year, s['id_section']))
            cur = conn.execute('INSERT INTO tbl_sections '
                               '(id_niveau,code_section,libelle,effectif,actif,id_annee) VALUES (?,?,?,?,?,?)',
                               (s['id_niveau'], s['code_section'], s['libelle'], s['effectif'], s['actif'], new_year))
            sm[s['id_section']] = cur.lastrowid
            expected['tbl_sections'].append(dict(s, id_section=cur.lastrowid, id_annee=new_year))
        for s in expected['tbl_sections']:
            if s['id_section'] in SOURCE_SECTIONS:
                s['id_annee'] = old_year
        for g in sorted(before['tbl_groupes'], key=lambda r: r['id_groupe']):
            if g['id_groupe'] not in SOURCE_GROUPS:
                continue
            sid = sm[g['id_section']]
            cur = conn.execute('INSERT INTO tbl_groupes '
                               '(id_section,code_groupe,nom_groupe,effectif,actif) VALUES (?,?,?,?,?)',
                               (sid, g['code_groupe'], g['nom_groupe'], g['effectif'], g['actif']))
            gm[g['id_groupe']] = cur.lastrowid
            expected['tbl_groupes'].append(dict(g, id_groupe=cur.lastrowid, id_section=sid))
        for a in expected['tbl_affectations']:
            if a['id_annee'] != new_year:
                continue
            a['id_section'] = sm[a['id_section']]
            if a['type_enseignement'] == 'CM':
                cur = conn.execute('UPDATE tbl_affectations SET id_section=? WHERE id_affectation=? AND id_annee=?',
                                   (a['id_section'], a['id_affectation'], new_year))
            else:
                a['id_groupe'] = gm[a['id_groupe']]
                cur = conn.execute('UPDATE tbl_affectations SET id_section=?,id_groupe=? '
                                   'WHERE id_affectation=? AND id_annee=?',
                                   (a['id_section'], a['id_groupe'], a['id_affectation'], new_year))
            require(cur.rowcount == 1, 'Mise a jour Affectation inattendue.')
        final_state, after, _, _ = inspect_state(conn)
        require(final_state == 'ALREADY_APPLIED', 'Etat final invalide.')
        require(schema(conn) == old_schema, 'Schema modifie de maniere inattendue.')
        require(after.keys() == expected.keys() and all(canonical(after[t]) == canonical(expected[t])
                                                      for t in expected),
                'Donnees modifiees hors transformation autorisee.')
        conn.commit()
        print('APPLIED : controles conformes ; transaction unique validee.')
        print(json.dumps({'sections': sm, 'groupes': gm, 'controles': EXPECTED}, sort_keys=True))
        return 0
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path, help='Chemin explicite de la base SQLite')
    parser.add_argument('--apply', action='store_true', help='Autoriser explicitement la transaction d ecriture')
    args = parser.parse_args()
    try:
        return run(args.database.resolve(), args.apply)
    except (ValueError, sqlite3.Error) as exc:
        print('REFUSED : ' + str(exc) + ' ; aucune modification validee.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
