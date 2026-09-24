# -*- coding: utf-8 -*-
# profe/core/__init__.py
from .seed import (
    extraer_nc, 
    generar_semilla, 
    obtener_rng
)

from .registry import (
    EJERCICIOS,
    MANO_FABRICA,
    NOMBRE_METODO,
    NOMBRE_FUNCION,
    elegir,
    elegir_mano
)

__all__ = [
    'extraer_nc', 
    'generar_semilla', 
    'obtener_rng',
    'EJERCICIOS',
    'MANO_FABRICA',
    'NOMBRE_METODO',
    'NOMBRE_FUNCION',
    'elegir',
    'elegir_mano'
]
