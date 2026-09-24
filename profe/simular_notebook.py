# -*- coding: utf-8 -*-
"""
Compila y EJECUTA el cuaderno U2_T2_Metodos_abiertos.ipynb tal como lo
haria el alumno, para detectar errores antes de publicarlo.

    python profe/simular_notebook.py                 # ejecuta todo
    python profe/simular_notebook.py --experto       # ademas inyecta las
                                                     # funciones correctas
                                                     # y comprueba que un
                                                     # alumno perfecto saca
                                                     # 20/20

Reglas del simulador
--------------------
  · Ejecuta las celdas EN ORDEN (como el alumno con "Ejecutar todo").
  · Replica el entorno: matplotlib en modo Agg, display() capturado.
  · Las celdas que se detienen con NotImplementedError se reportan como
    "pendiente" (es lo esperado: son los esqueletos de programacion).
  · No hay acceso a internet: el envio se prueba con --experto en modo
    `debug`.
"""
import builtins
import io
import json
import os
import re
import sys
import traceback
from contextlib import redirect_stdout

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
CUADERNO = os.path.join(RAIZ, 'U2_T2_Metodos_abiertos.ipynb')

ESPERADAS = {'NotImplementedError'}


def _sin_magics(src):
    """
    Quita lineas de magia de IPython (%matplotlib, %time, !pip ...).

    CUIDADO: solo son magias las que empiezan con '%' o '!' seguidos de
    una LETRA. Una linea de continuacion como
        % (len(a), len(b)))
    empieza con '%' pero NO es una magia: si la comentaramos, la llamada
    de la linea anterior quedaria sin cerrar.
    """
    salida = []
    for linea in src.split('\n'):
        if re.match(r'^\s*%[A-Za-z]', linea) or re.match(r'^\s*![A-Za-z]', linea):
            salida.append('# ' + linea)
        else:
            salida.append(linea)
    return '\n'.join(salida)


class Salida:
    """Sustituto de display(): imprime de forma resumida."""

    def __init__(self, activo=True):
        self.activo = activo
        self.items = []

    def __call__(self, *objs, **kw):
        for o in objs:
            texto = getattr(o, 'data', None) or str(o)
            texto = str(texto).replace('\n', ' ')[:120]
            self.items.append(texto)
            if self.activo:
                print('   [display] %s' % texto)


def _tipo(celda):
    """nbformat usa 'cell_type'; algunas herramientas escriben 'type'."""
    return celda.get('cell_type') or celda.get('type')


def cargar():
    with open(CUADERNO, encoding='utf-8') as f:
        return json.load(f)


def main():
    experto = '--experto' in sys.argv
    verboso = '--verboso' in sys.argv
    # --ofuscado: fuerza la ruta OFUSCADA (grad
    #             como la ve el alumno) aunque estemos en local.
    forzar_ofuscado = '--ofuscado' in sys.argv
    print('=' * 78)
    print(' SIMULACION DEL CUADERNO · U2_T2_Metodos_abiertos')
    print('=' * 78)

    nb = cargar()
    celdas = nb['cells']
    print('Celdas: %d  (%d de codigo)' % (len(celdas),
                                          builtins.sum(1 for c in celdas if _tipo(c) == 'code')))

    # ---- 1) compilacion de todas las celdas de codigo ----
    fallos_comp = []
    for k, c in enumerate(celdas):
        if _tipo(c) != 'code':
            continue
        try:
            compile(_sin_magics(''.join(c['source'])), '<celda %d>' % k, 'exec')
        except SyntaxError as exc:
            fallos_comp.append((k, exc))
            print('   [FALLA] celda %d no compila: %s (linea %s)'
                  % (k, exc.msg, exc.lineno))
    if fallos_comp:
        print('\nRESULTADO: %d celdas con error de sintaxis' % len(fallos_comp))
        return 1
    print('Compilacion de todas las celdas de codigo: OK')

    # ---- 2) ejecucion en orden ----
    os.chdir(RAIZ)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.show = lambda *a, **k: None

    from IPython.display import Markdown  # noqa: F401  (lo usa el cuaderno)

    ns = {'__name__': '__main__'}
    captura = Salida(activo=False)
    errores, pendientes, ejecutadas = [], [], 0

    for k, c in enumerate(celdas):
        if _tipo(c) != 'code':
            continue
        fuente = _sin_magics(''.join(c['source']))
        if not fuente.strip():
            continue
        if forzar_ofuscado and 'DEBUG_SIN_OFUSCAR = True' in fuente:
            # Ejercita la MISMA ruta que usara el alumno en Colab:
            # grader_ofuscado.txt descomprimido, no el fuente.
            fuente = fuente.replace('DEBUG_SIN_OFUSCAR = True',
                                    'DEBUG_SIN_OFUSCAR = False')
            print('   (celda %d: forzando el motor OFUSCADO)' % (k + 1))
        ns['display'] = captura          # el cuaderno lo re-importa: reponemos
        ns['get_ipython'] = lambda: None
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                exec(compile(fuente, '<celda %d>' % k, 'exec'), ns)
            ejecutadas += 1
            if verboso:
                salida = buf.getvalue().strip()
                print('\n--- celda %d ---\n%s' % (k + 1, salida[:2500]))
        except Exception as exc:
            nombre = type(exc).__name__
            if nombre in ESPERADAS:
                pendientes.append((k, str(exc)[:60]))
            else:
                errores.append((k, exc, buf.getvalue()))
                print('   [FALLA] celda %d: %s: %s' % (k, nombre, exc))
                traceback.print_exc()

    print('\nCeldas ejecutadas sin error : %d' % ejecutadas)
    print('Celdas "pendiente" (esqueleto sin completar): %d' % len(pendientes))
    for k, msg in pendientes:
        print('   - celda %d: %s' % (k, msg))
    print('Errores inesperados        : %d' % len(errores))

    # ---- 3) examen del alumno perfecto ----
    if experto:
        print('\n[experto] Inyectando las implementaciones correctas...')
        import importlib.util
        # Las implementaciones de referencia viven en el propio verificador,
        # asi no dependemos de ningun archivo que reciba el alumno.
        spec = importlib.util.spec_from_file_location(
            'ref_t2', os.path.join(AQUI, 'verificar_tarea.py'))
        ref = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ref)
        ns['pf'] = ref.pf
        ns['pfm'] = ref.pfm
        ns['nr'] = ref.nr
        ns['nrm'] = ref.nrm
        ns['secante'] = ref.secante
        ns['secmod'] = ref.secmod

        class Marco(object):
            def __init__(self, g):
                self.f_globals = g

        # El alumno perfecto tambien contesta bien los reactivos de opcion
        # y los numericos: llenamos los widgets con la solucion correcta.
        _ex = ns.get('_EXAMEN')
        if _ex is not None:
            for j, (p, sol) in enumerate(zip(_ex.preguntas, _ex.soluciones), 1):
                w = ns.get('resp_%d' % j)
                if w is not None and sol is not None:
                    try:
                        w.value = sol
                    except (TypeError, ValueError):
                        pass

        buf = io.StringIO()
        with redirect_stdout(buf):
            puntos, maximo = ns['calificar'](Marco(ns))
        print('   Puntos del alumno perfecto: %g / %g' % (puntos, maximo))
        if abs(puntos - maximo) > 1e-9:
            print('   [FALLA] un alumno perfecto NO saca el total.')
            errores.append((-1, Exception('experto < total'), ''))
        else:
            print('   OK: el examen se puede responder al 100%% con el temario.')
        if not ns.get('_MANO'):
            print('   [aviso] la hoja manual quedo vacia (revisa mano_comprueba).')
        nb2 = {'pf': 0, 'pfm': 0, 'nr': 0, 'nrm': 0, 'secante': 0, 'secmod': 0}
        _ex = ns.get('_EXAMEN')
        if _ex is not None:
            for p in _ex.preguntas:
                if p['tipo'] == 'funcion':
                    nb2[p['funcion']] = nb2.get(p['funcion'], 0) + 1
            print('   Funciones evaluadas por el examen: %s'
                  % ', '.join(sorted(k for k, v in nb2.items() if v)))

    # ---- resultado ----
    print('\n' + '=' * 78)
    if errores:
        print(' RESULTADO: %d ERRORES' % len(errores))
        for k, exc, _ in errores:
            print('   - celda %d: %s' % (k, exc))
    else:
        print(' RESULTADO: TODO OK')
    print('=' * 78)
    return 1 if errores else 0


if __name__ == '__main__':
    sys.exit(main())
