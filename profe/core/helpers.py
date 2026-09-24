# -*- coding: utf-8 -*-
"""
profe/core/helpers.py — Utilidades base de formateo y generación aleatoria.
"""
import builtins

def _r(rng, lo, hi, dec=4) -> float:
    """Genera un número flotante aleatorio entre [lo, hi] redondeado a 'dec' decimales."""
    return builtins.round(float(rng.uniform(lo, hi)), dec)

def _fmt(v, dec=4) -> str:
    """Convierte un número a un texto LaTeX compacto."""
    if v == int(v) and builtins.abs(v) < 1e6:
        return str(int(v))
    return ('%.' + str(dec) + 'f') % v
