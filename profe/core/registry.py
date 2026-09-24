# -*- coding: utf-8 -*-
"""
profe/core/registry.py — Catálogo de ejercicios y selección sembrada.

Cada método recibe SOLO las variantes que puede resolver: PFM necesita un
`lam`, SEC dos puntos iniciales, SM un `delta`, NRM la segunda derivada y
PF/PFM un despeje `g`. La selección usa el RNG del alumno, así que el
ejercicio es reproducible.
"""
from .modelos import (
    _ej_paracaidista,
    _ej_colebrook,
    _ej_maldespeje,
    _ej_oscilatoria,
    _ej_aurea,
    _ej_paracaidista_relax,
    _ej_cubica,
    _ej_vdw,
    _ej_doble,
    _ej_diodo,
    _ej_terminal,
    _ej_polinomio,
)
from .solvers import resolver

# Mapeo de ejercicios disponibles por cada método abierto
EJERCICIOS = {
    'PF':  [_ej_paracaidista, _ej_colebrook, _ej_maldespeje, _ej_oscilatoria,
            _ej_aurea, _ej_cubica],
    'PFM': [_ej_oscilatoria, _ej_aurea, _ej_paracaidista_relax],
    'NR':  [_ej_paracaidista, _ej_colebrook, _ej_vdw, _ej_polinomio, _ej_diodo],
    'NRM': [_ej_doble, _ej_doble, _ej_polinomio],
    'SEC': [_ej_colebrook, _ej_diodo, _ej_terminal, _ej_polinomio],
    'SM':  [_ej_colebrook, _ej_paracaidista, _ej_polinomio],
}

# Mapeo de ejercicios específicos para la actividad realizada a mano
MANO_FABRICA = {
    'PF':  [_ej_paracaidista, _ej_colebrook, _ej_maldespeje],
    'PFM': [_ej_oscilatoria, _ej_paracaidista_relax],
    'NR':  [_ej_polinomio, _ej_paracaidista, _ej_vdw],
    'NRM': [_ej_doble],
    'SEC': [_ej_colebrook, _ej_diodo, _ej_polinomio],
    'SM':  [_ej_paracaidista, _ej_polinomio, _ej_diodo],
}

NOMBRE_METODO = {
    'PF': 'Punto fijo',
    'PFM': 'Punto fijo con relajación',
    'NR': 'Newton-Raphson',
    'NRM': 'Newton-Raphson modificado (raíces múltiples)',
    'SEC': 'Secante',
    'SM': 'Secante modificada',
}

# Nombre EXACTO de la función que debe programar el alumno. Tiene que
# coincidir con la firma que anuncia _texto_func(), porque el cuaderno
# declara esa función y la tarea la busca por nombre.
NOMBRE_FUNCION = {
    'PF': 'pf',
    'PFM': 'pfm',
    'NR': 'nr',
    'NRM': 'nrm',
    'SEC': 'secante',
    'SM': 'secmod',
}

METODOS_MANO = ('PF', 'PFM', 'NR', 'NRM', 'SEC', 'SM')


def _sortear(fabricas, metodo, rng, es=None):
    """Sortea una variante con el RNG del alumno y la deja resuelta."""
    idx = int(rng.integers(0, len(fabricas)))
    return resolver(metodo, fabricas[idx](rng), es=es)


def elegir(metodo: str, rng, es=None):
    """Selecciona un ejercicio aleatorio del catálogo según el método y el RNG del alumno."""
    return _sortear(EJERCICIOS[metodo], metodo, rng, es=es)


def elegir_mano(metodo: str, rng, es=None):
    """Selecciona un ejercicio para la actividad manual según el método y el RNG del alumno."""
    return _sortear(MANO_FABRICA[metodo], metodo, rng, es=es)
