# -*- coding: utf-8 -*-
# profe/core/__init__.py
from .seed import (
    extraer_nc,
    generar_semilla,
    obtener_rng
)

from .solvers import (
    ES_DEFECTO,
    MAX_ITER,
    iteracion_objetivo,
    iteraciones,
    resolver
)

from .registry import (
    EJERCICIOS,
    MANO_FABRICA,
    METODOS_MANO,
    NOMBRE_METODO,
    NOMBRE_FUNCION,
    elegir,
    elegir_mano
)

__all__ = [
    'extraer_nc',
    'generar_semilla',
    'obtener_rng',
    'ES_DEFECTO',
    'MAX_ITER',
    'iteracion_objetivo',
    'iteraciones',
    'resolver',
    'EJERCICIOS',
    'MANO_FABRICA',
    'METODOS_MANO',
    'NOMBRE_METODO',
    'NOMBRE_FUNCION',
    'elegir',
    'elegir_mano'
]
