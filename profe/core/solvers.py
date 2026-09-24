# -*- coding: utf-8 -*-
"""
profe/core/solvers.py — Algoritmos de referencia de alta precisión.
"""
import builtins
import math
import numpy as np

MAX_ITER = 60
ES_DEFECTO = 0.01  # %

def _ea_pct(x_nuevo, x_previo):
    if x_nuevo == 0:
        return float('inf')
    return builtins.abs((x_nuevo - x_previo) / x_nuevo) * 100.0

def iteraciones(metodo, ej, es=None, max_iter=MAX_ITER):
    """
    Genera la tabla de iteraciones de referencia.
    Devuelve (convergio: bool, filas: list[dict]).
    """
    es = ES_DEFECTO if es is None else es
    filas = []
    f, df, ddf = ej.get('f'), ej.get('df'), ej.get('ddf')
    g, dg = ej.get('g'), ej.get('dg')

    if metodo == 'PFM' and ej.get('lam') is None:
        return False, filas
    if metodo == 'SM' and ej.get('delta') is None:
        return False, filas

    try:
        if metodo in ('PF', 'PFM'):
            lam = 1.0 if metodo == 'PF' else ej['lam']
            x = ej['x0']
            for i in range(1, max_iter + 1):
                gx = g(x)
                xn = lam * gx + (1.0 - lam) * x
                ea = _ea_pct(xn, x)
                filas.append({'i': i, 'x_i': x, 'g(x_i)': gx, 'x': xn, 'ea': ea})
                if not builtins.all(np.isfinite([xn, ea])):
                    return False, filas
                if ea <= es and i >= 2:
                    return True, filas
                x = xn
            return False, filas

        if metodo == 'NR':
            x = ej['x0']
            for i in range(1, max_iter + 1):
                fx, dfx = f(x), df(x)
                if dfx == 0 or not np.isfinite(fx / dfx):
                    return False, filas
                xn = x - fx / dfx
                ea = _ea_pct(xn, x)
                filas.append({'i': i, 'x_i': x, "f(x_i)": fx, "f'(x_i)": dfx, 'x': xn, 'ea': ea})
                if not builtins.all(np.isfinite([xn, ea])):
                    return False, filas
                if ea <= es and i >= 2:
                    return True, filas
                x = xn
            return False, filas

        if metodo == 'NRM':
            x = ej['x0']
            for i in range(1, max_iter + 1):
                fx, dfx, ddfx = f(x), df(x), ddf(x)
                den = dfx * dfx - fx * ddfx
                if den == 0 or not np.isfinite(fx / den):
                    return False, filas
                xn = x - fx * dfx / den
                ea = _ea_pct(xn, x)
                filas.append({'i': i, 'x_i': x, "f(x_i)": fx, "f'(x_i)": dfx, "f''(x_i)": ddfx, 'x': xn, 'ea': ea})
                if not builtins.all(np.isfinite([xn, ea])):
                    return False, filas
                if ea <= es and i >= 3:
                    return True, filas
                x = xn
            return False, filas

        if metodo == 'SEC':
            xa, xb = ej['x0'], ej['x1']
            for i in range(1, max_iter + 1):
                fa, fb = f(xa), f(xb)
                if fb == fa or not np.isfinite(fb - fa):
                    return False, filas
                xn = xb - fb * (xb - xa) / (fb - fa)
                ea = _ea_pct(xn, xb)
                filas.append({'i': i, 'x_{i-1}': xa, 'x_i': xb, 'f(x_{i-1})': fa, 'f(x_i)': fb, 'x': xn, 'ea': ea})
                if not builtins.all(np.isfinite([xn, ea])):
                    return False, filas
                if ea <= es and i >= 2:
                    return True, filas
                xa, xb = xb, xn
            return False, filas

        if metodo == 'SM':
            x = ej['x0']
            delta = ej['delta']
            for i in range(1, max_iter + 1):
                dx = delta if (delta and delta != 0) else 0.01 * builtins.max(1.0, builtins.abs(x))
                fx = f(x)
                fxd = f(x + dx)
                if fxd == fx or not np.isfinite(fxd - fx):
                    return False, filas
                xn = x - dx * fx / (fxd - fx)
                ea = _ea_pct(xn, x)
                filas.append({'i': i, 'x_i': x, 'x_i+dx': x + dx, 'f(x_i)': fx, 'f(x_i+dx)': fxd, 'x': xn, 'ea': ea})
                if not builtins.all(np.isfinite([xn, ea])):
                    return False, filas
                if ea <= es and i >= 2:
                    return True, filas
                x = xn
            return False, filas
    except (ZeroDivisionError, OverflowError, ValueError, TypeError):
        return False, filas

    raise ValueError(f'Método desconocido: {metodo}')

def iteracion_objetivo(filas, es):
    """Encuentra la primera iteración donde ea <= es."""
    for fila in filas:
        if fila['ea'] <= es:
            return fila['i']
    return None


def resolver(metodo, ej, es=None):
    """
    Calcula la tabla de referencia del ejercicio y deja el RESULTADO dentro
    del propio diccionario:

        ej['_conv']  -> True si la iteración llegó al criterio de paro
        ej['_filas'] -> la tabla de iteraciones
        ej['raiz']   -> la raíz de referencia
        ej['_es']    -> el criterio de paro usado (en %)

    Si la iteración se desboca, el último valor NO es la raíz: cuando el
    ejercicio conoce su raíz analítica (`raiz_teorica`) se reporta esa.
    """
    conv, filas = iteraciones(metodo, ej, es=es)
    raiz = filas[-1]['x'] if filas else None
    if not conv and ej.get('raiz_teorica') is not None:
        raiz = ej['raiz_teorica']
    ej['_conv'] = conv
    ej['_filas'] = filas
    ej['raiz'] = raiz
    ej['_es'] = ES_DEFECTO if es is None else es
    return ej
