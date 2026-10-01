# -*- coding: utf-8 -*-
"""
profe/core/modelos.py — Modelos matemáticos de los ejercicios.

Cada fábrica sortea sus datos con el RNG del alumno (a través de los rangos
declarados en `profe/ejercicios/<nombre>.md`) y devuelve un diccionario con
`f`, `df`, `ddf`, `g`, `dg`, el punto de arranque `x0`/`x1`, `lam`, `delta`
y el texto del enunciado. La tabla de iteraciones y la raíz las añade
`profe.core.solvers.resolver()` al seleccionar el ejercicio.
"""
import math
import builtins
from profe.core.helpers import _fmt
from profe.core.markdown_loader import cargar_ejercicio_md, sustituir

def _paracaidista_modelo(m, t, v, grav=9.81):
    """
    Modelo del paracaidista para UN juego de datos (m, t, v).

    Devuelve `(f, df, ddf, g, dg)`:
      * `f(c) = (grav*m/c)*(1 - e^{-c t/m}) - v`  -> la ley fisica igualada a 0
      * `g(c) = (grav*m/v)*(1 - e^{-c t/m})`      -> el despeje, con g(c) - c = (c/v)*f(c)
      * `df`, `ddf` son las derivadas DE `f` (Newton / Newton modificado)
      * `dg` es la derivada DE `g` (solo para el criterio |g'| < 1)

    Lo comparten `_ej_paracaidista` y `_ej_paracaidista_relax` para que el
    texto del enunciado y las funciones usen SIEMPRE los mismos numeros.
    """
    def f(c): return (grav * m / c) * (1.0 - math.exp(-c * t / m)) - v
    def df(c): return (grav * m / (c**2)) * (math.exp(-c * t / m) * (1.0 + c * t / m) - 1.0)
    def ddf(c): return (df(c + 1e-5) - df(c - 1e-5)) / 2e-5
    def gfun(c): return (grav * m / v) * (1.0 - math.exp(-c * t / m))
    def dgfun(c): return (grav * t / v) * math.exp(-c * t / m)
    return f, df, ddf, gfun, dgfun

def _ej_paracaidista(rng):
    meta, ctx, d = cargar_ejercicio_md('paracaidista.md', rng)
    m, t, v, x0 = d['m'], d['t'], d['v'], d['x0']
    f, df, ddf, gfun, dgfun = _paracaidista_modelo(m, t, v)

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': gfun, 'dg': dgfun,
            'x0': x0, 'x1': x0 + 2.0, 'lam': None, 'delta': 0.01,
            'datos': [('m', m, 'kg'), ('t', t, 's'), ('v', v, 'm/s')]}

def _ej_colebrook(rng):
    meta, ctx, d = cargar_ejercicio_md('colebrook.md', rng)
    D, Re, eps, x0 = 0.05, d['Re'], d['eps'], d['x0']
    a = eps / (3.7 * D)

    def f(fr): return float('nan') if fr <= 0 else 1.0 / math.sqrt(fr) + 2.0 * math.log10(a + 2.51 / (Re * math.sqrt(fr)))
    def gfun(fr): return (-2.0 * math.log10(a + 2.51 / (Re * math.sqrt(fr)))) ** (-2.0)
    def df(fr): return (f(fr + 1e-7) - f(fr - 1e-7)) / 2e-7
    def ddf(fr): return (df(fr + 1e-5) - df(fr - 1e-5)) / 2e-5
    def dgfun(fr): return (gfun(fr + 1e-7) - gfun(fr - 1e-7)) / 2e-7

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': gfun, 'dg': dgfun,
            'x0': x0, 'x1': x0 * 1.5, 'lam': None, 'delta': 1e-5,
            'datos': [('D', D, 'm'), ('eps', eps, 'm'), ('Re', Re, '-')]}

def _ej_maldespeje(rng):
    meta, ctx, d = cargar_ejercicio_md('maldespeje.md', rng)
    x0 = d['x0']

    def f(x): return x**2 - 2.0 * x - 3.0
    def df(x): return 2.0 * x - 2.0
    def ddf(x): return 2.0
    def gfun(x): return (x**2 - 3.0) / 2.0
    def dgfun(x): return x

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': gfun, 'dg': dgfun,
            'x0': x0, 'x1': None, 'lam': None, 'delta': None, 'datos': [('ecuacion', 0, '-')],
            'diverge': True, 'par': ((x0 * x0 - 3.0) / 2.0, 3.0), 'raiz_teorica': 3.0}

def _ej_oscilatoria(rng):
    meta, ctx, d = cargar_ejercicio_md('oscilatoria.md', rng)
    x0, lam = d['x0'], d['lam']

    def f(x): return x**2 - x - 3.0
    def df(x): return 2.0 * x - 1.0
    def ddf(x): return 2.0
    def gfun(x): return 2.0 * x + 3.0 - x**2
    def dgfun(x): return 2.0 - 2.0 * x

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': gfun, 'dg': dgfun,
            'x0': x0, 'x1': None, 'lam': lam, 'delta': None,
            'datos': [('lam', lam, '-')], 'raiz_teorica': (1.0 + math.sqrt(13.0)) / 2.0}

def _ej_aurea(rng):
    meta, ctx, d = cargar_ejercicio_md('aurea.md', rng)
    x0, lam = d['x0'], d['lam']

    def f(x): return x**2 - x - 1.0
    def df(x): return 2.0 * x - 1.0
    def ddf(x): return 2.0
    def gfun(x): return math.sqrt(x + 1.0)
    def dgfun(x): return 1.0 / (2.0 * math.sqrt(x + 1.0))

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': gfun, 'dg': dgfun,
            'x0': x0, 'x1': None, 'lam': lam, 'delta': None, 'datos': [('lam', lam, '-')]}

def _ej_paracaidista_relax(rng):
    # UN SOLO sorteo, desde paracaidista_relax.md: el texto, `x0`, `lam` y las
    # funciones f/g salen todos de los mismos numeros. Antes se sorteaba dos
    # veces (paracaidista.md + paracaidista_relax.md) y el enunciado mostraba
    # datos distintos a los que usaban f, g y la tabla de referencia.
    meta, ctx, d = cargar_ejercicio_md('paracaidista_relax.md', rng)
    m, t, v, x0, lam = d['m'], d['t'], d['v'], d['x0'], d['lam']
    f, df, ddf, gfun, dgfun = _paracaidista_modelo(m, t, v)

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': gfun, 'dg': dgfun,
            'x0': x0, 'x1': x0 + 2.0, 'lam': lam, 'delta': 0.01,
            'datos': [('m', m, 'kg'), ('t', t, 's'), ('v', v, 'm/s'), ('lam', lam, '-')]}

def _ej_cubica(rng):
    meta, ctx, d = cargar_ejercicio_md('cubica.md', rng)
    x0 = d['x0']

    def f(x): return x**3 - x - 1.0
    def df(x): return 3.0 * x**2 - 1.0
    def ddf(x): return 6.0 * x
    def gfun(x): return (x + 1.0) ** (1.0 / 3.0)
    def dgfun(x): return (1.0 / 3.0) * (x + 1.0) ** (-2.0 / 3.0)

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': gfun, 'dg': dgfun,
            'x0': x0, 'x1': x0 + 1.0, 'lam': None, 'delta': 0.01, 'datos': []}

def _ej_vdw(rng):
    meta, ctx, d = cargar_ejercicio_md('vdw.md', rng)
    T, p, R, a, b = d['T'], d['p'], 0.08206, 3.592, 0.04267
    x0 = R * T / p

    def f(v): return (p + a / (v**2)) * (v - b) - R * T
    def df(v): return p + a / (v**2) - 2.0 * a * (v - b) / (v**3)
    def ddf(v): return (df(v + 1e-6 * v) - df(v - 1e-6 * v)) / (2e-6 * v)

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': None, 'dg': None,
            'x0': x0, 'x1': None, 'lam': None, 'delta': 1e-4,
            'datos': [('T', T, 'K'), ('p', p, 'atm')]}

def _ej_doble(rng):
    meta, ctx, d = cargar_ejercicio_md('doble.md', rng)
    s = d['s']
    r = s + d['r_off']
    x0 = r + d['x0_off']
    # `r` y `x0` no se sortean: se calculan aquí, así que los completamos ahora.
    ctx = sustituir(ctx, r=_fmt(r, 1), x0=_fmt(x0, 2))

    def f(x): return (x - r)**2 * (x - s)
    def df(x): return (x - r) * (3.0 * x - (2.0 * s + r))
    def ddf(x): return 6.0 * x - 2.0 * (2.0 * r + s)

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': None, 'dg': None,
            'x0': x0, 'x1': None, 'lam': None, 'delta': 0.01,
            'datos': [('raíz doble', r, 'mm'), ('raíz simple', s, 'mm')], 'raiz_doble': r}

def _ej_diodo(rng):
    meta, ctx, d = cargar_ejercicio_md('diodo.md', rng)
    Vcc, R, Is, nVT, x0 = d['Vcc'], d['R'], 1e-12, 0.05, 1.0

    def f(V): return Is * (math.exp(V / nVT) - 1.0) - (Vcc - V) / R
    def df(V): return (Is / nVT) * math.exp(V / nVT) + 1.0 / R
    def ddf(V): return (Is / (nVT**2)) * math.exp(V / nVT)

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': None, 'dg': None,
            'x0': x0, 'x1': 1.3, 'lam': None, 'delta': 0.001,
            'datos': [('Vcc', Vcc, 'V'), ('R', R, 'ohm'), ('nVT', nVT, 'V')]}

def _ej_terminal(rng):
    meta, ctx, d = cargar_ejercicio_md('terminal.md', rng)
    m, g, A, rho, v0 = d['m'], 9.81, 0.55, 1.2, 40.0

    def f(v):
        Re = rho * v * 0.6 / 1.8e-5
        Cd = 24.0 / Re + 6.0 / (1.0 + math.sqrt(Re)) + 0.4
        return math.sqrt(2.0 * m * g / (rho * A * Cd)) - v

    def df(v): return (f(v + 1e-5 * v) - f(v - 1e-5 * v)) / (2e-5 * v)
    def ddf(v): return (df(v + 1e-4 * v) - df(v - 1e-4 * v)) / (2e-4 * v)

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': None, 'dg': None,
            'x0': v0, 'x1': v0 + 3.0, 'lam': None, 'delta': 0.01,
            'datos': [('m', m, 'kg'), ('A', A, 'm2'), ('rho', rho, 'kg/m3')]}

def _ej_polinomio(rng):
    meta, ctx, d = cargar_ejercicio_md('polinomio.md', rng)
    a, b, x0 = d['a'], d['b'], d['x0']

    def f(x): return x**3 - a * x - b
    def df(x): return 3.0 * x**2 - a
    def ddf(x): return 6.0 * x

    return {**meta, 'contexto': ctx, 'f': f, 'df': df, 'ddf': ddf, 'g': None, 'dg': None,
            'x0': x0, 'x1': x0 + 1.0, 'lam': None, 'delta': 0.01, 'datos': []}
