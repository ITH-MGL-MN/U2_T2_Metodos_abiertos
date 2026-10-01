# -*- coding: utf-8 -*-
"""
Verificacion de la tarea U2_T2_Metodos_abiertos.

Comprueba, sobre 40 numeros de control:
  1. El examen se genera sin excepciones (14 reactivos, 20 puntos).
  2. Cada ejercicio sorteado cumple sus garantias matematicas
     (raiz real, f(raiz)=0, |g'|<1 cuando se afirma convergencia,
      divergencia real cuando se afirma lo contrario).
  3. Las respuestas de las preguntas 'simple' son consistentes con la tabla.
  4. Los casos ocultos de las preguntas 'funcion' los resuelve una
     implementacion de referencia correcta.
  5. Las actividades a mano (mano_*) no fallan.
  6. Los valores no se repiten de forma masiva entre los 40 alumnos.

Uso:  python profe/verificar_tarea.py
"""
import builtins
import math
import os
import sys
import traceback

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

FALLOS = []
AVISOS = []


def fallo(msg):
    FALLOS.append(msg)
    print('   [FALLA] %s' % msg)


def aviso(msg):
    AVISOS.append(msg)
    print('   [aviso] %s' % msg)


# ---------------------------------------------------------------------
# Carga del grader como modulo
# ---------------------------------------------------------------------
def cargar():
    """
    Importa la fachada del motor (`profe/grader.py`) como módulo. La raíz del
    proyecto tiene que estar en sys.path: la fachada importa `profe.core`.
    """
    if RAIZ not in sys.path:
        sys.path.insert(0, RAIZ)
    import profe.grader
    return profe.grader


# ---------------------------------------------------------------------
# Implementaciones de referencia (lo que debe entregar un alumno correcto)
# ---------------------------------------------------------------------
def pf(g, x0, tol=1e-6, max_iter=100):
    x = x0
    for i in range(1, max_iter + 1):
        xn = g(x)
        if xn != 0 and abs((xn - x) / xn) <= tol:
            return xn, i
        x = xn
    return x, max_iter


def pfm(g, x0, lam, tol=1e-6, max_iter=100):
    x = x0
    for i in range(1, max_iter + 1):
        xn = lam * g(x) + (1 - lam) * x
        if xn != 0 and abs((xn - x) / xn) <= tol:
            return xn, i
        x = xn
    return x, max_iter


def nr(f, df, x0, tol=1e-6, max_iter=100):
    x = x0
    for i in range(1, max_iter + 1):
        d = df(x)
        if d == 0:
            break
        xn = x - f(x) / d
        if xn != 0 and abs((xn - x) / xn) <= tol:
            return xn, i
        x = xn
    return x, max_iter


def nrm(f, df, ddf, x0, tol=1e-6, max_iter=100):
    x = x0
    for i in range(1, max_iter + 1):
        fx, d1, d2 = f(x), df(x), ddf(x)
        den = d1 * d1 - fx * d2
        if den == 0:
            break
        xn = x - fx * d1 / den
        if xn != 0 and abs((xn - x) / xn) <= tol:
            return xn, i
        x = xn
    return x, max_iter


def secante(f, x0, x1, tol=1e-6, max_iter=100):
    xa, xb = x0, x1
    for i in range(1, max_iter + 1):
        fa, fb = f(xa), f(xb)
        if fb == fa:
            break
        xn = xb - fb * (xb - xa) / (fb - fa)
        if xn != 0 and abs((xn - xb) / xn) <= tol:
            return xn, i
        xa, xb = xb, xn
    return xb, max_iter


def secmod(f, x0, delta=0.01, tol=1e-6, max_iter=100):
    x = x0
    for i in range(1, max_iter + 1):
        fx, fxd = f(x), f(x + delta)
        if fxd == fx:
            break
        xn = x - delta * fx / (fxd - fx)
        if xn != 0 and abs((xn - x) / xn) <= tol:
            return xn, i
        x = xn
    return x, max_iter


REF = {'pf': pf, 'pfm': pfm, 'nr': nr, 'nrm': nrm, 'secante': secante, 'secmod': secmod}


class Marco(object):
    """Imita el cuaderno: expone f_globals con las funciones del alumno."""

    def __init__(self, funciones):
        self.f_globals = dict(funciones)


def _seguro(f, x):
    try:
        v = f(x)
        if isinstance(v, complex) or v != v or v in (float('inf'), float('-inf')):
            return None
        return float(v)
    except Exception:
        return None


def _raiz_fina(f, x0, df=None):
    """
    Raiz real cerca de x0. Primero Newton (funciona incluso con raices
    multiples, donde no hay cambio de signo); si no, biseccion LOCAL.
    """
    escala = max(1.0, abs(x0))
    if df is not None:
        x = x0
        for _ in range(400):
            d = _seguro(df, x)
            fx = _seguro(f, x)
            if d is None or fx is None or d == 0:
                break
            xn = x - fx / d
            if _seguro(f, xn) is None:
                break
            if abs(xn - x) <= 1e-14 * escala:
                x = xn
                break
            x = xn
        if _seguro(f, x) is not None and abs(f(x) or 0.0) < 1e-8 * escala:
            return x
    for h0 in (1e-9, 1e-7, 1e-5, 1e-3, 1e-2, 1e-1):
        h = h0 * escala
        a, b = x0 - h, x0 + h
        fa, fb = _seguro(f, a), _seguro(f, b)
        if fa is None or fb is None:
            continue
        if fa == 0.0:
            return a
        if fb == 0.0:
            return b
        if fa * fb < 0:
            for _ in range(400):
                m = 0.5 * (a + b)
                fm = _seguro(f, m)
                if fm is None:
                    return None
                if fm == 0.0:
                    return m
                if fa * fm < 0:
                    b, fb = m, fm
                else:
                    a, fa = m, fm
                if abs(b - a) <= 1e-15 * escala:
                    break
            return 0.5 * (a + b)
    return None


# =====================================================================
def main():
    print('=' * 74)
    print(' VERIFICACION U2_T2_Metodos_abiertos')
    print('=' * 74)
    g = cargar()

    NCs = ['m{%d}@hermosillo.tecnm.mx' % (16330000 + 7 * k) for k in range(40)]

    # ---------------- 1 y 4: examenes completos ----------------
    print('\n[1] Generacion de examenes (40 NC) y casos ocultos...')
    raices = {m: [] for m in ('PF', 'PFM', 'NR', 'NRM', 'SEC', 'SM')}
    simples = {m: [] for m in ('PF', 'PFM', 'NR', 'NRM', 'SEC', 'SM')}
    titulos = {}
    variantes_func = set()
    for nc in NCs:
        try:
            ex = g.Examen(nc)
        except Exception as exc:
            fallo('Examen(%s) lanza %r' % (nc, exc))
            traceback.print_exc()
            continue
        if len(ex.preguntas) != 14:
            fallo('%s: %d reactivos (esperaba 14)' % (nc, len(ex.preguntas)))
        total = builtins.sum(ex.pesos)
        if total != 20:
            fallo('%s: pesos suman %g (esperaba 20)' % (nc, total))
        # tipo admitido por slot. Se deduce de la config en vez de escribir el
        # orden a mano: así, si se reordenan los slots (por ejemplo para pedir
        # el código antes que las iteraciones), el verificador sigue al día.
        #   teorica       -> opcion
        #   ejercicio_num -> simple, o 'opcion' si la pregunta sale conceptual
        #   funcion       -> funcion
        _ADMITIDOS = {'teorica': ['opcion'],
                      'ejercicio_num': ['simple', 'opcion'],
                      'funcion': ['funcion']}
        admitidos = [_ADMITIDOS.get(sl.get('tipo', 'teorica'), ['simple', 'opcion'])
                     for sl in ex.slots]
        for i, p in enumerate(ex.preguntas, 1):
            if p['tipo'] not in admitidos[i - 1]:
                fallo('%s: reactivo %d es %s (esperaba %s)'
                      % (nc, i, p['tipo'], '/'.join(admitidos[i - 1])))
            if p['tipo'] == 'opcion':
                if len(p['opciones']) != 4:
                    fallo('%s: reactivo %d con %d opciones' % (nc, i, len(p['opciones'])))
                if not (0 <= ex.soluciones[i - 1] <= 3):
                    fallo('%s: reactivo %d con solucion %r' % (nc, i, ex.soluciones[i - 1]))
            if p['tipo'] == 'funcion':
                variantes_func.add((p['funcion'], len(p['casos'])))
                if not p['casos']:
                    fallo('%s: reactivo %d sin casos ocultos' % (nc, i))
        # metodo por slot (posicion fija)
        etiquetas = ['INTRO', 'PF', 'PF', 'PFM', 'PFM', 'NR', 'NR', 'NRM', 'NRM',
                     'SEC', 'SEC', 'SM', 'SM', 'CONCL']
        for i, etq in enumerate(etiquetas, 1):
            if etq in raices:
                p = ex.preguntas[i - 1]
                ej = p.get('_ej')
                if ej is not None:
                    raices[etq].append(ej.get('raiz'))
                    titulos.setdefault((etq, ej['titulo']), 0)
                    titulos[(etq, ej['titulo'])] += 1
                if p['tipo'] == 'simple':
                    simples[etq].append(ex.soluciones[i - 1])
        # calificacion con un alumno perfecto: responde bien los 14 reactivos
        marco = Marco({})
        for nombre, fn in REF.items():
            marco.f_globals[nombre] = fn

        class _W(object):
            def __init__(self, v):
                self.value = v

        respuestas = {}
        for j, (p, sol) in enumerate(zip(ex.preguntas, ex.soluciones), 1):
            if p['tipo'] == 'funcion':
                continue
            marco.f_globals['resp_%d' % j] = _W(sol)
            respuestas[j] = sol
        filas = ex.calificar(respuestas, marco)
        puntos = builtins.sum(f['puntos'] for f in filas)
        maximo = builtins.sum(f['peso'] for f in filas)
        if abs(puntos - maximo) > 1e-9:
            malas = [f for f in filas if f['puntos'] < f['peso'] - 1e-9]
            fallo('%s: un alumno PERFECTO saca %.2f/%g (fallan: %s)'
                  % (nc, puntos, maximo,
                     ', '.join('#%d' % f['i'] for f in malas)))
    print('   examenes generados: %d' % len(NCs))

    # ---------------- 4b: respuestas correctas de las 'opcion' ----------------
    print('\n[2] Respuestas de opcion verificables (1, 14)...')
    for nc in NCs[:10]:
        ex = g.Examen(nc)
        for i in (1, 14):
            p = ex.preguntas[i - 1]
            sol = ex.soluciones[i - 1]
            if p['tipo'] != 'opcion':
                continue
            # la opcion marcada como correcta debe empezar con la letra esperada
            letra = chr(97 + int(sol))
            if not p['opciones'][int(sol)].startswith(letra):
                fallo('%s reactivo %d: la opcion correcta no esta en la posicion %s'
                      % (nc, i, letra))
    print('   ok')

    # ---------------- 2: garantias de los ejercicios ----------------
    print('\n[3] Garantias matematicas de cada ejercicio sorteado...')
    vistos = {}
    for nc in NCs:
        try:
            ex = g.Examen(nc)
        except Exception:
            continue
        # posición del reactivo de iteraciones de cada método, leída de la
        # config (no fija): así sigue valiendo si se reordenan los slots.
        idx_iter = {}
        for k, sl in enumerate(ex.slots):
            if sl.get('tipo') == 'ejercicio_num':
                idx_iter[sl.get('metodo')] = k
        for etq in ('PF', 'PFM', 'NR', 'NRM', 'SEC', 'SM'):
            idx = idx_iter.get(etq)
            if idx is None:
                continue
            ej = ex.preguntas[idx].get('_ej')
            if ej is None:
                continue
            vistos[(etq, id(ej))] = (etq, ej)
    print('   ejercicios distintos: %d' % len(vistos))
    for (etq, ej) in vistos.values():
        raiz = ej.get('raiz')
        if raiz is None:
            fallo('%s/%s: raiz None' % (etq, ej['titulo']))
            continue
        f = ej['f']
        conv = ej.get('_conv')
        if ej.get('diverge'):
            # un ejercicio divergente: el valor final no es raiz; lo unico
            # exigible es que la iteracion simple NO converja
            if etq != 'PFM' and conv:
                fallo('%s/%s: marcado divergente pero la iteracion simple convergio'
                      % (etq, ej['titulo']))
            if etq == 'PF' and ej.get('raiz_teorica'):
                gp = ej['dg'](ej['raiz_teorica'])
                if not (abs(gp) > 1.0):
                    fallo('%s/%s: se afirma divergencia pero |g\'(x*)|=%.4f <= 1'
                          % (etq, ej['titulo'], gp))
        else:
            if not conv:
                fallo('%s/%s: NO convergio y no esta marcado divergente'
                      % (etq, ej['titulo']))
                continue
            # la raiz tabulada debe ser la raiz real, hasta el criterio de paro
            try:
                fina = _raiz_fina(f, raiz, ej.get('df'))
            except Exception as exc:
                fallo('%s/%s: no pude refinar la raiz (%r)' % (etq, ej['titulo'], exc))
                continue
            if fina is None:
                fallo('%s/%s: la funcion no se anula cerca de %.6g'
                      % (etq, ej['titulo'], raiz))
                continue
            err = abs(raiz - fina) / max(1.0, abs(fina))
            if err > 1e-3:
                fallo('%s/%s: la raiz de la tabla dista %.3e de la raiz real (%.8g vs %.8g)'
                      % (etq, ej['titulo'], err, raiz, fina))
            if abs(f(fina)) > 1e-6 * max(1.0, abs(fina)):
                fallo('%s/%s: f(raiz)=%.3e no es ~0' % (etq, ej['titulo'], f(fina)))
        # derivadas del iterador
        if etq == 'PF' and ej.get('dg') and not ej.get('diverge'):
            gp = ej['dg'](raiz)
            if not (abs(gp) < 1.0):
                fallo('%s/%s: |g\'(x*)|=%.4f >= 1 y no esta marcado divergente'
                      % (etq, ej['titulo'], gp))
        if etq == 'PFM':
            gp = ej['dg'](raiz)
            lam = ej['lam']
            factor = abs(1.0 + lam * (gp - 1.0))
            if not (factor < 1.0):
                fallo('%s/%s: |1+lam(g\'-1)|=%.4f >= 1 (lam=%s, g\'=%.4f)'
                      % (etq, ej['titulo'], factor, lam, gp))
        if etq in ('SEC',) and ej.get('x1') is None:
            fallo('%s/%s: secante sin x1' % (etq, ej['titulo']))
        if etq in ('SEC',) and builtins.abs(f(ej['x0']) - f(ej['x1'])) < 1e-14:
            fallo('%s/%s: f(x0)==f(x1) en la secante' % (etq, ej['titulo']))
        # la respuesta 'simple' debe ser alcanzable
        if etq in ('PF', 'PFM', 'NR', 'NRM', 'SEC', 'SM'):
            p = None
            for (e, ejj) in vistos.values():
                pass
    print('   garantias revisadas')

    # ---------------- 3: respuestas 'simple' consistentes ----------------
    print('\n[4] Respuestas de iteraciones alcanzables...')
    for nc in NCs:
        try:
            ex = g.Examen(nc)
        except Exception:
            continue
        for i in range(1, 15):
            p = ex.preguntas[i - 1]
            if p['tipo'] != 'simple':
                continue
            ej, es, sol = p.get('_ej'), p.get('_es'), ex.soluciones[i - 1]
            if ej is None or es is None:
                continue
            filas = ej['_filas']
            if not (1 <= sol <= len(filas)):
                fallo('%s reactivo %d: solucion %g fuera de la tabla (%d filas)'
                      % (nc, i, sol, len(filas)))
                continue
            fila = filas[int(sol) - 1]
            if not (fila['ea'] <= es * (1 + 1e-9)):
                fallo('%s reactivo %d: ea(%.1f)=%.3e > es=%s' % (nc, i, sol, fila['ea'], es))
            if int(sol) > 1 and filas[int(sol) - 2]['ea'] <= es:
                aviso('%s reactivo %d: no es la PRIMERA iteracion bajo es' % (nc, i))
    print('   ok')

    # ---------------- 5: actividades a mano ----------------
    print('\n[5] Actividades a mano...')
    import io
    from contextlib import redirect_stdout
    for etq in ('PF', 'PFM', 'NR', 'NRM', 'SEC', 'SM'):
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                ej = g.mano_enunciado(etq, nc='16330000')
                if ej['_filas']:
                    vals = [fila['x'] for fila in ej['_filas'][:3]]
                else:
                    vals = [1.0, 1.0, 1.0]
                g.mano_comprueba(etq, vals)
                g.mano_solucion(etq)
            txt = buf.getvalue()
            if 'Traceback' in txt:
                fallo('mano %s: excepcion' % etq)
        except Exception as exc:
            fallo('mano %s lanza %r' % (etq, exc))
            traceback.print_exc()
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            g.hoja_manual()
        assert 'HOJA DE TRABAJO' in buf.getvalue()
    except Exception as exc:
        fallo('hoja_manual lanza %r' % (exc))
    print('   ok')

    # ---------------- 6: diversidad ----------------
    print('\n[6] Diversidad entre los 40 alumnos...')
    for etq in ('PF', 'PFM', 'NR', 'NRM', 'SEC', 'SM'):
        vals = [v for v in raices[etq] if v is not None]
        uniq = len(set(round(v, 6) for v in vals))
        print('   %-4s raices distintas: %d de %d' % (etq, uniq, len(vals)))
        if vals and uniq < builtins.max(3, len(vals) // 4):
            fallo('%s: poca variedad de raices (%d/%d)' % (etq, uniq, len(vals)))
        if etq in ('PF', 'PFM', 'NR', 'NRM', 'SEC', 'SM'):
            s = [int(x) for x in simples[etq]]
            if s and len(set(s)) < 2:
                aviso('%s: todas las respuestas de iteraciones son %s' % (etq, set(s)))
    print('\n   Variantes usadas:')
    for (etq, tit), n in sorted(titulos.items()):
        print('     %-4s %-52s %d' % (etq, tit[:52], n))

    # ---------------- resultado ----------------
    print('\n' + '=' * 74)
    if FALLOS:
        print(' RESULTADO: %d FALLAS, %d avisos' % (len(FALLOS), len(AVISOS)))
        grupos = {}
        for m in FALLOS:
            clave = m.split(': ', 1)[1] if ': ' in m else m
            clave = ''.join('#' if c.isdigit() else c for c in clave)
            grupos.setdefault(clave, []).append(m)
        for clave, ms in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
            print('   x%-4d %s' % (len(ms), clave[:100]))
            print('         ej: %s' % ms[0][:110])
        print('\n   Avisos:')
        for a in AVISOS[:10]:
            print('   - %s' % a[:110])
    else:
        print(' RESULTADO: TODO OK  (%d avisos)' % len(AVISOS))
    print('=' * 74)
    return 1 if FALLOS else 0


if __name__ == '__main__':
    sys.exit(main())
