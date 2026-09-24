# -*- coding: utf-8 -*-
"""
probador.py — Herramienta local para inspeccionar un ejercicio por NC.

    python probador.py                       # NC y método por omisión
    python probador.py 16330887 PF           # número de control y método
    python probador.py 16330887 PF mano      # el ejercicio de la actividad a mano

Muestra el enunciado tal como lo ve el alumno y la tabla de iteraciones de
referencia que usa el motor para calificar.
"""
import builtins
import sys

from profe.config import buscar, obtener_configuracion
from profe.core import METODOS_MANO, NOMBRE_METODO, elegir, elegir_mano, obtener_rng
from profe.ui.cuaderno import ORDEN_COLUMNAS, _texto_tabla

NC_POR_OMISION = '16330887'
METODO_POR_OMISION = 'NR'


def id_tarea():
    """Nombre de la hoja / parte de la semilla, tal como está en config.yaml."""
    cfg, _ = obtener_configuracion()
    return buscar(cfg, 'tarea.id', 'U2_T2_Metodos_abiertos')


def probar_ejercicio(nc=NC_POR_OMISION, metodo=METODO_POR_OMISION, mano=False):
    if metodo not in METODOS_MANO:
        print('Método desconocido: %r (usa uno de %s)'
              % (metodo, ', '.join(METODOS_MANO)))
        return 1

    tarea = id_tarea()
    partes = (nc, tarea, 'mano', metodo) if mano else (nc, tarea, metodo)
    rng = obtener_rng(*partes)
    ej = elegir_mano(metodo, rng) if mano else elegir(metodo, rng)

    print('=' * 68)
    print(' %s | NC: %s | %s' % (NOMBRE_METODO[metodo], nc,
                                 'actividad a mano' if mano else 'preguntas automáticas'))
    print('=' * 68)
    print('\nTÍTULO   : %s' % ej['titulo'])
    print('INCÓGNITA: %s [%s]' % (ej.get('incognita', '-'), ej.get('unidad', '-')))
    arranques = ['x0 = %g' % ej['x0']]
    if ej.get('x1') is not None:
        arranques.append('x1 = %g' % ej['x1'])
    if ej.get('lam') is not None:
        arranques.append('lambda = %s' % ej['lam'])
    if ej.get('delta') is not None:
        arranques.append('delta = %s' % ej['delta'])
    print('ARRANQUE : %s' % ', '.join(arranques))

    print('\n--- ENUNCIADO QUE VE EL ALUMNO ---')
    print(ej['contexto'].strip())
    print('----------------------------------')

    f = ej['f']
    print('\nf(x0) = %.6g' % f(ej['x0']))
    print('raíz  = %s   (%s, %d iteraciones con εs = %g %%)'
          % (('%.8g' % ej['raiz']) if ej['raiz'] is not None else 'None',
             'converge' if ej['_conv'] else 'NO converge',
             builtins.len(ej['_filas']), ej['_es']))
    print('\nTabla de referencia (primeras 5 iteraciones):')
    print(_texto_tabla(ej['_filas'][:5], ORDEN_COLUMNAS[metodo]))
    return 0


if __name__ == '__main__':
    args = [a for a in sys.argv[1:]]
    nc = args[0] if args else NC_POR_OMISION
    metodo = args[1].upper() if builtins.len(args) > 1 else METODO_POR_OMISION
    mano = builtins.len(args) > 2 and args[2].lower().startswith('mano')
    sys.exit(probar_ejercicio(nc, metodo, mano))
