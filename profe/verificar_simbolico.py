# -*- coding: utf-8 -*-
"""
=========================================================================
 VERIFICACION DE LAS ECUACIONES  (antes de publicar cualquier ejercicio)
=========================================================================
 Comprueba que las matematicas de cada ejercicio son coherentes. Pensado
 para correrse ANTES de escribir/dar por bueno un enunciado nuevo:

   PARTE 1 - todas las variantes del motor (precision ~1e-6):
     · f(raiz) = 0          la raiz reportada anula de verdad la funcion
     · g(raiz) = raiz       el despeje ES un despeje de f (no otra ecuacion)
     · f', f'' y g' declaradas coinciden con la derivada numerica
       (asi se detectan derivadas mal escritas)

   PARTE 2 - sympy, familias con forma analitica cerrada:
     · se resuelven las raices de f SIMBOLICAMENTE
     · se evalua (g(x) - x) en cada raiz: debe dar EXACTAMENTE 0
       (si ninguna raiz lo cumple, el "despeje" no corresponde a f)
     · se informa si (g(x) - x) / f(x) es constante (equivalencia global)

 Uso:   python profe/verificar_simbolico.py
=========================================================================
"""
import builtins
import importlib.util
import os
import sys

import numpy as np
import sympy as sp

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOL_F = 1e-6        # tolerancia relativa cuando la raiz es la TEORICA (exacta)
TOL_ITER = 3e-3     # tolerancia relativa cuando la raiz sale del criterio de paro
                    # (la iteracion para con ea <= 0.01 %, o sea que la raiz
                    #  reportada solo trae ~4 cifras: hay que dar holgura)
TOL_D = 1e-4        # tolerancia relativa para las derivadas (diferencias finitas)

fallos = []
avisos = []


def fallo(msg):
    fallos.append(msg)
    print("   FALLO: %s" % msg)


def aviso(msg):
    avisos.append(msg)
    print("   aviso: %s" % msg)


def cargar():
    ruta = os.path.join(RAIZ, 'profe', 'grader.py')
    spec = importlib.util.spec_from_file_location('grader_u2t2', ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def d1(fn, x, h=1e-6):
    return (fn(x + h) - fn(x - h)) / (2.0 * h)


def d2(fn, x, h=1e-4):
    return (fn(x + h) - 2.0 * fn(x) + fn(x - h)) / (h * h)


def rel(a, b):
    return builtins.abs(a - b) / builtins.max(1.0, builtins.abs(b))


# ---------------------------------------------------------------------
#  PARTE 1 - todas las variantes del motor
# ---------------------------------------------------------------------
def parte1(g, rng_semilla=20260918):
    print("\n[1] Coherencia numerica de TODAS las variantes del motor")
    print("    (f, f', f'', g, g' y la raiz reportada)\n")
    total = 0
    for etiqueta, fabricas in (('PREGUNTA', g.EJERCICIOS), ('MANO', g.MANO_FABRICA)):
        for metodo in sorted(fabricas):
            for k, fab in enumerate(fabricas[metodo]):
                rng = np.random.default_rng(rng_semilla + 7 * k)
                try:
                    ej = g._con_raiz(metodo, fab(rng))
                except Exception as exc:            # noqa: BLE001
                    fallo('%s/%s#%d: la fabrica lanzo %r' % (etiqueta, metodo, k, exc))
                    continue
                total += 1
                nom = '%s %s#%d [%s]' % (etiqueta, metodo, k, ej.get('titulo', '?'))
                r = ej.get('raiz_teorica')
                if r is None:
                    r = ej.get('raiz')
                f, df, ddf = ej.get('f'), ej.get('df'), ej.get('ddf')
                gg, dg = ej.get('g'), ej.get('dg')

                if r is None:
                    aviso('%s: sin raiz reportada (revisar a mano)' % nom)
                else:
                    exacta = ej.get('raiz_teorica') is not None
                    tol = (TOL_F if exacta else TOL_ITER) * builtins.max(1.0, builtins.abs(r))
                    oks = []
                    if f is not None:
                        if builtins.abs(f(r)) > tol:
                            fallo('%s: f(raiz=%.8g) = %.4g  (deberia ser 0; tol=%.3g)'
                                  % (nom, r, f(r), tol))
                        else:
                            oks.append('f')
                    if f is not None and df is not None:
                        if rel(d1(f, r), df(r)) > TOL_D:
                            fallo("%s: f'(%.6g): lambda=%.6g vs numerica=%.6g"
                                  % (nom, r, df(r), d1(f, r)))
                        else:
                            oks.append("f'")
                    if df is not None and ddf is not None:
                        if rel(d1(df, r), ddf(r)) > TOL_D:
                            fallo("%s: f''(%.6g): lambda=%.6g vs numerica=%.6g"
                                  % (nom, r, ddf(r), d1(df, r)))
                        else:
                            oks.append("f''")
                    # --- el despeje: en la raiz de f debe cumplirse g(r) = r ---
                    if gg is not None:
                        if builtins.abs(gg(r) - r) > tol:
                            fallo('%s: g(raiz=%.8g) = %.8g  -> NO es despeje de f'
                                  % (nom, r, gg(r)))
                        else:
                            oks.append('g')
                        if dg is not None:
                            if rel(d1(gg, r), dg(r)) > TOL_D:
                                fallo("%s: g'(%.6g): lambda=%.6g vs numerica=%.6g"
                                      % (nom, r, dg(r), d1(gg, r)))
                            else:
                                oks.append("g'")
                    if gg is None and ej.get('despeje_latex'):
                        aviso('%s: declara despeje_latex pero no tiene funcion g' % nom)
                    print('   %-56s raiz=%-14.8g ok: %s'
                          % (nom, r, ','.join(oks) if oks else '-'))
    print("\n    variantes revisadas: %d" % total)


# ---------------------------------------------------------------------
#  PARTE 2 - sympy: el despeje contra la ecuacion
# ---------------------------------------------------------------------
X = sp.symbols('x', real=True)


def familias():
    """
    (nombre, f(x), g(x) candidato).

    Solo familias con forma analitica cerrada. Si se agrega un ejercicio
    nuevo con despeje, agregar aqui su fila: es la red de seguridad.
    """
    return [
        ('mal despeje (el que NO converge)', X ** 2 - 2 * X - 3, (X ** 2 - 3) / 2),
        ('mal despeje (el despeje bueno)', X ** 2 - 2 * X - 3, sp.sqrt(2 * X + 3)),
        ('oscilatoria', X ** 2 - X - 3, 2 * X + 3 - X ** 2),
        ('proporcion aurea', X ** 2 - X - 1, sp.sqrt(X + 1)),
        ('ejemplo guiado PF/PFM', sp.cos(X) - X, sp.cos(X)),
    ]


def parte2():
    print("\n[2] Verificacion SIMBOLICA de los despejes (sympy)")
    print("     g(x) = x  debe cumplirse EXACTAMENTE en las raices de f(x) = 0\n")
    for nom, f, gg in familias():
        nota = ''
        try:
            raices = [r for r in sp.solve(sp.Eq(f, 0), X) if sp.im(r) == 0]
        except NotImplementedError:
            raices = []                  # sin forma cerrada (p. ej. cos(x) = x)
        if not raices:
            try:
                raices = [sp.nsolve(sp.Eq(f, 0), X, 0.5)]
                nota = '  (raiz numerica: no hay forma cerrada)'
            except Exception:                        # noqa: BLE001
                aviso('%s: no se pudieron hallar raices' % nom)
                continue
        buenas, malas = [], []
        for r in raices:
            delta = sp.simplify(gg.subs(X, r) - r)
            vale = False
            try:
                vale = (delta == 0)
            except Exception:                        # noqa: BLE001
                vale = False
            if not vale:
                try:
                    vale = builtins.abs(complex(sp.N(delta))) < 1e-9
                except Exception:                    # noqa: BLE001
                    vale = False
            (buenas if vale else malas).append((r, delta))
        detalle = ', '.join('x*=%.6g -> g(x*)-x* = %s'
                            % (float(r), sp.nsimplify(d)) for r, d in buenas)
        print('   %-34s raices: %s%s' % (nom, [float(r) for r in raices], nota))
        print('   %-34s cumple : %s' % ('', detalle if detalle else 'NINGUNA'))
        if malas:
            print('   %-34s no cumple (rama/otra raiz): %s'
                  % ('', ', '.join('x*=%.6g -> %s' % (float(r), d) for r, d in malas)))
        if not buenas:
            fallo('%s: ninguna raiz de f es punto fijo de g -> el despeje NO '
                  'corresponde a la ecuacion' % nom)
        # equivalencia global (solo si el cociente no depende de x)
        try:
            coc = sp.simplify(sp.together((gg - X) / f))
            if X not in coc.free_symbols:
                print('   %-34s      (g(x)-x) = %s * f(x): equivalente en TODO el dominio'
                      % ('', sp.simplify(coc)))
            else:
                print('   %-34s      cociente (g-x)/f no constante: el despeje vale '
                      'solo en las raices de arriba' % '')
        except Exception:                        # noqa: BLE001
            pass
        print('')


def main():
    print('=' * 73)
    print(' VERIFICACION DE ECUACIONES · U2_T2_Metodos_abiertos')
    print('=' * 73)
    g = cargar()
    parte1(g)
    parte2()
    print('=' * 73)
    if fallos:
        print(' RESULTADO: %d FALLO(S) - NO publicar hasta corregir' % len(fallos))
        for m in fallos:
            print('   · %s' % m)
        return 1
    print(' RESULTADO: TODO OK  (%d avisos)' % len(avisos))
    return 0


if __name__ == '__main__':
    sys.exit(main())
