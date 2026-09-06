"""Validation pure des lignes d'import d'affectations.

Ce module ne modifie jamais la session ni les objets ORM fournis.
"""

from app.models import Affectation, AnneeUniversitaire, Groupe, Matiere, Professeur, Section
from app.services.affectation_rules import valider_semestre_import


COLONNES_ATTENDUES = {
    'Professeur', 'Matiere', 'Section', 'Groupe', 'Type_enseignement',
    'Semestre', 'Nb_seances_semaine', 'Duree_seance_minutes',
    'Volume_total_minutes', 'Priorite', 'Actif',
}
TYPES = {'CM', 'TD', 'TP'}


def _texte(value):
    return '' if value is None else str(value).strip()


def _entier(value, nom, positif=False, vide=False):
    if value is None or _texte(value) == '':
        return (None, None) if vide else (None, f'{nom} est obligatoire.')
    try:
        resultat = int(value)
    except (TypeError, ValueError):
        return None, f'{nom} doit être un entier.'
    if positif and resultat <= 0:
        return None, f'{nom} doit être positif.'
    if not positif and resultat < 0:
        return None, f'{nom} ne peut pas être négatif.'
    return resultat, None


def _booleen(value):
    texte = _texte(value).lower()
    if texte in {'1', 'true', 'vrai', 'yes', 'oui', 'o'}:
        return True
    if texte in {'0', 'false', 'faux', 'no', 'non', 'n'}:
        return False
    return None


def _unique(query, champ, valeur):
    objets = query.filter_by(**{champ: valeur}).all()
    if len(objets) != 1:
        return None, ('introuvable' if not objets else 'ambigu')
    return objets[0], None


def valider_lignes_import(
        session, lignes, annee, verifier_doublons_base=True):
    """Retourne un rapport structuré sans add/delete/flush/commit."""
    rapport = {'statut_global': 'PRETE_A_IMPORTER', 'resultats': [],
               'colonnes_attendues': sorted(COLONNES_ATTENDUES)}
    if annee is None or getattr(annee, 'id_annee', None) is None:
        rapport['statut_global'] = 'ERREUR_BLOQUANTE'
        rapport['erreur'] = "L'année universitaire est introuvable."
        return rapport
    deja = set()
    existants = (
        session.query(Affectation).filter_by(id_annee=annee.id_annee).all()
        if verifier_doublons_base else []
    )
    for numero, ligne in enumerate(lignes, 2):
        erreurs, avertissements, resolues = [], [], {}
        if set(ligne) != COLONNES_ATTENDUES:
            erreurs.append('Colonnes absentes ou inattendues.')
        professeur, err = _unique(session.query(Professeur), 'nom', _texte(ligne.get('Professeur')))
        if err: erreurs.append(f'Professeur {err}.')
        else:
            resolues['professeur'] = professeur
            if not professeur.actif: erreurs.append('Professeur inactif.')
        matiere, err = _unique(session.query(Matiere), 'nom_matiere', _texte(ligne.get('Matiere')))
        if err: erreurs.append(f'Matiere {err}.')
        else:
            resolues['matiere'] = matiere
            if not matiere.actif: erreurs.append('Matiere inactive.')
            elif matiere.niveau is None: erreurs.append('Niveau de matiere inexistant.')
            elif not matiere.niveau.actif: erreurs.append('Niveau de matiere inactif.')
        section, err = _unique(session.query(Section), 'libelle', _texte(ligne.get('Section')))
        if err: erreurs.append(f'Section {err}.')
        else:
            resolues['section'] = section
            if not section.actif: erreurs.append('Section inactive.')
            elif section.niveau is None: erreurs.append('Niveau de section inexistant.')
            elif not section.niveau.actif: erreurs.append('Niveau de section inactif.')
        if (matiere is not None and section is not None and
                matiere.id_niveau != section.id_niveau):
            erreurs.append('Incoherence matiere/section.')
        groupe = None
        if _texte(ligne.get('Groupe')):
            if section is None:
                erreurs.append('Groupe non resolu sans section valide.')
            else:
                groupes_section = session.query(Groupe).filter_by(
                    id_section=section.id_section
                )
                groupe, err = _unique(
                    groupes_section, 'code_groupe', _texte(ligne.get('Groupe'))
                )
                if err: erreurs.append(f'Groupe {err}.')
                else:
                    resolues['groupe'] = groupe
                    if not groupe.actif: erreurs.append('Groupe inactif.')
                    elif groupe.section is None: erreurs.append('Section du groupe inexistante.')
                    elif not groupe.section.actif: erreurs.append('Section du groupe inactive.')
                    elif groupe.section.niveau is None: erreurs.append('Niveau du groupe inexistant.')
                    elif not groupe.section.niveau.actif: erreurs.append('Niveau du groupe inactif.')
                    elif groupe.id_section != section.id_section:
                        erreurs.append('Le groupe n’appartient pas à la section.')
        type_enseignement = _texte(ligne.get('Type_enseignement')).upper()
        if type_enseignement not in TYPES: erreurs.append('Type_enseignement invalide.')
        elif type_enseignement == 'CM' and groupe is not None:
            erreurs.append('Une affectation CM ne peut pas avoir de groupe.')
        elif type_enseignement in {'TD', 'TP'} and groupe is None:
            erreurs.append('Une affectation TD ou TP doit cibler un groupe.')
        semestre, err = valider_semestre_import(resolues.get('matiere'), ligne.get('Semestre')) if resolues.get('matiere') else (None, 'Matiere introuvable.')
        if err: erreurs.append(err)
        valeurs = {
            'semestre': semestre,
            'type_enseignement': type_enseignement,
        }
        for cle, lib, positif, vide in [('Nb_seances_semaine','Nb_seances_semaine',True,False),('Duree_seance_minutes','Duree_seance_minutes',True,False),('Volume_total_minutes','Volume_total_minutes',True,True),('Priorite','Priorite',False,False)]:
            valeurs[cle], err = _entier(ligne.get(cle), lib, positif, vide)
            if err: erreurs.append(err)
        actif = _booleen(ligne.get('Actif'))
        if actif is None: erreurs.append('Actif doit être un booléen reconnu.')
        if not erreurs:
            cle = (annee.id_annee, resolues['professeur'].id_professeur, resolues['matiere'].id_matiere, resolues['section'].id_section, getattr(groupe, 'id_groupe', None), type_enseignement, semestre)
            if any((x.id_professeur, x.id_matiere, x.id_section, x.id_groupe, x.type_enseignement, x.semestre) == cle[1:] for x in existants):
                avertissements.append('Doublon déjà présent en base.')
                statut = 'DOUBLON_IGNORE'
            elif cle in deja:
                avertissements.append('Doublon dans le fichier.')
                statut = 'DOUBLON_IGNORE'
            else:
                deja |= {cle}; statut = 'PRETE_A_IMPORTER'
            resolues['groupe'] = groupe
        else:
            statut = 'ERREUR_BLOQUANTE'
        rapport['resultats'].append({'ligne': numero, 'statut': statut, 'erreurs': erreurs, 'avertissements': avertissements, 'references': resolues, 'valeurs': valeurs, 'actif': actif})
        if statut == 'ERREUR_BLOQUANTE': rapport['statut_global'] = 'ERREUR_BLOQUANTE'
    return rapport
