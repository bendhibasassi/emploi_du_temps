"""Référentiels métier partagés par l'application."""


SALLES_OFFICIELLES = {
    **{
        code: {'nom': f'Amphithéâtre {code}', 'type': 'AMPHI'}
        for code in ('A0', 'A1', 'A2', 'A3', 'BIO1', 'BIO2')
    },
    **{
        f'DSP{numero}': {
            'nom': f'DSP{numero}',
            'type': (
                'GRANDE_SALLE'
                if numero <= 7 or numero >= 22
                else 'PETITE_SALLE'
            ),
        }
        for numero in range(1, 25)
    },
}

TYPES_SALLE = tuple(dict.fromkeys(
    salle['type'] for salle in SALLES_OFFICIELLES.values()
))
