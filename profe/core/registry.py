# -*- coding: utf-8 -*-
"""
profe/ejercicios/registry.py — Registro central de ejercicios y funciones de selección.
"""
from .modelos import (
    _ej_paracaidista,
    _ej_colebrook,
    _ej_maldespeje,
    _ej_oscilatoria,
    _ej_diodo,
    _ej_doble
)

# Mapeo de ejercicios disponibles por cada método abierto
EJERCICIOS = {
    'PF':  [_ej_paracaidista, _ej_colebrook, _ej_maldespeje, _ej_oscilatoria],
    'PFM': [_ej_oscilatoria, _ej_paracaidista],
    'NR':  [_ej_paracaidista, _ej_colebrook, _ej_diodo],
    'NRM': [_ej_doble],
    'SEC': [_ej_colebrook, _ej_diodo],
    'SM':  [_ej_colebrook, _ej_paracaidista, _ej_diodo],
}

# Mapeo de ejercicios específicos para la actividad realizada a mano
MANO_FABRICA = {
    'PF':  [_ej_paracaidista, _ej_colebrook],
    'PFM': [_ej_oscilatoria],
    'NR':  [_ej_paracaidista, _ej_diodo],
    'NRM': [_ej_doble],
    'SEC': [_ej_colebrook, _ej_diodo],
    'SM':  [_ej_paracaidista, _ej_diodo],
}

NOMBRE_METODO = {
    'PF': 'Punto fijo',
    'PFM': 'Punto fijo con relajación',
    'NR': 'Newton-Raphson',
    'NRM': 'Newton-Raphson modificado (raíces múltiples)',
    'SEC': 'Secante',
    'SM': 'Secante modificada',
}

NOMBRE_FUNCION = {
    'PF': 'pf',
    'PFM': 'pfm',
    'NR': 'nr',
    'NRM': 'nrm',
    'SEC': 'secante',
    'SM': 'secmod',
}

def elegir(metodo: str, rng):
    """Selecciona un ejercicio aleatorio del catálogo según el método y el RNG del alumno."""
    fabricas = EJERCICIOS[metodo]
    idx = int(rng.integers(0, len(fabricas)))
    return fabricas[idx](rng)

def elegir_mano(metodo: str, rng):
    """Selecciona un ejercicio para la actividad manual según el método y el RNG del alumno."""
    fabricas = MANO_FABRICA[metodo]
    idx = int(rng.integers(0, len(fabricas)))
    return fabricas[idx](rng)
