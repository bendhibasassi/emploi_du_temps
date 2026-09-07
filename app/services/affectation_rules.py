"""Règles métier partagées par les écritures d'affectations."""


SEMESTRES_MATIERE_VALIDES = {
    f'S{numero}': numero for numero in range(1, 7)
}


def semestre_matiere_entier(matiere):
    """Convertit S1 à S6 en entier, ou retourne None."""
    return SEMESTRES_MATIERE_VALIDES.get(
        (matiere.semestre or '').strip().upper()
    )


def erreur_semestre_affectation(
        matiere, semestre_affectation, exiger_semestre_matiere=False):
    """Valide le semestre d'une affectation depuis sa matière."""
    semestre_matiere = semestre_matiere_entier(matiere)
    if semestre_matiere is None:
        if exiger_semestre_matiere:
            return (
                "Le semestre de la matière est absent ou invalide ; "
                "la ligne ne peut pas être validée automatiquement."
            )
        return None
    if semestre_affectation != semestre_matiere:
        return (
            "Le semestre de l'affectation doit correspondre au semestre "
            "de la matière sélectionnée."
        )
    return None


def valider_semestre_import(matiere, valeur_importee):
    """Convertit et valide un semestre fourni par un import."""
    texte = str(valeur_importee).strip().upper()
    if texte.startswith('S'):
        texte = texte[1:]
    try:
        semestre = int(texte)
    except (TypeError, ValueError):
        return None, "Le semestre importé est invalide."
    if not 1 <= semestre <= 6:
        return None, "Le semestre importé est invalide."
    erreur = erreur_semestre_affectation(
        matiere, semestre, exiger_semestre_matiere=True
    )
    if erreur:
        return None, erreur
    return semestre, None
