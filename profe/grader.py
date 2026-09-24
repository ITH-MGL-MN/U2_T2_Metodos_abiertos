# -*- coding: utf-8 -*-
"""
profe/grader.py — Fachada del motor de la tarea de Métodos Abiertos.

Es el ÚNICO punto de entrada que conoce el cuaderno del alumno. Por dentro
llama a los módulos pequeños:

    profe/config.py          pesos, tolerancias y URL del webhook
    profe/core/seed.py       semilla reproducible a partir del NC
    profe/core/modelos.py    las familias de ejercicios
    profe/core/registry.py   qué variante puede recibir cada método
    profe/core/solvers.py    las iteraciones de referencia
    profe/core/evaluator.py  generar, calificar y enviar
    profe/ui/cuaderno.py     la API que usa el cuaderno (widgets, mano, tablas)

Así el cuaderno puede seguir llamando a `generar_tarea`, `pregunta`,
`mano_*`, `hoja_manual` y `enviar` aunque el código se reordene por dentro.
"""
from profe.config import buscar, cargar_yaml, obtener_configuracion
from profe.core import (
    EJERCICIOS,
    ES_DEFECTO,
    MANO_FABRICA,
    MAX_ITER,
    METODOS_MANO,
    NOMBRE_FUNCION,
    NOMBRE_METODO,
    elegir,
    elegir_mano,
    extraer_nc,
    generar_semilla,
    iteracion_objetivo,
    iteraciones,
    obtener_rng,
    resolver,
)
from profe.core.evaluator import Tarea
from profe.ui.cuaderno import (
    CASOS_PRUEBA,
    COLUMNAS_EXPL,
    ENCABEZADOS,
    ORDEN_COLUMNAS,
    calificar,
    comparar_practica,
    enviar,
    generar_examen,
    generar_tarea,
    hoja_manual,
    mano_comprueba,
    mano_ecuacion,
    mano_enunciado,
    mano_referencia,
    mano_solucion,
    pregunta,
    semilla_de,
    tabla,
    tabla_df,
    tabla_en_blanco,
)

# Compatibilidad: la clase se llamaba `Examen` antes de renombrarla.
Examen = Tarea

# Compatibilidad: la función se llamaba `semilla` antes de renombrarla.
semilla = generar_semilla

# ---------------------------------------------------------------------
#  Constantes del curso (leen el config.yaml; nada escrito a mano)
# ---------------------------------------------------------------------
_CFG, _PREGUNTAS = obtener_configuracion()

TIPOS = buscar(_CFG, 'slots', []) or []
TAREA = buscar(_CFG, 'tarea.id', 'U2_T2_Metodos_abiertos')
NOMBRE_TAREA = buscar(_CFG, 'tarea.nombre', TAREA)
APPS_SCRIPT_URL = buscar(_CFG, 'evaluacion.apps_script_url', '')
WEBHOOK_TOKEN = buscar(_CFG, 'evaluacion.webhook_token', '')
MIN_APROBACION = float(buscar(_CFG, 'evaluacion.min_aprobacion', 0.90))
TOLERANCIA = float(buscar(_CFG, 'evaluacion.tolerancia_simple', 1e-6))
PESO_AUTO = float(buscar(_CFG, 'ponderacion.automatico', 0.70))
PESO_MANO = float(buscar(_CFG, 'ponderacion.manual', 0.30))

BANCO_INTRO = (_PREGUNTAS or {}).get('INTRO', [])
BANCO_CONCL = (_PREGUNTAS or {}).get('CONCL', [])

__all__ = [
    'APPS_SCRIPT_URL', 'BANCO_CONCL', 'BANCO_INTRO', 'CASOS_PRUEBA',
    'COLUMNAS_EXPL', 'EJERCICIOS', 'ENCABEZADOS', 'ES_DEFECTO', 'Examen',
    'MANO_FABRICA', 'MAX_ITER', 'METODOS_MANO', 'MIN_APROBACION',
    'NOMBRE_FUNCION', 'NOMBRE_METODO', 'NOMBRE_TAREA', 'ORDEN_COLUMNAS',
    'PESO_AUTO', 'PESO_MANO', 'TAREA', 'TIPOS', 'TOLERANCIA', 'Tarea',
    'WEBHOOK_TOKEN', 'buscar', 'cargar_yaml', 'calificar', 'comparar_practica',
    'elegir', 'elegir_mano', 'enviar', 'extraer_nc', 'generar_examen',
    'generar_semilla', 'generar_tarea', 'hoja_manual', 'iteracion_objetivo',
    'iteraciones', 'mano_comprueba', 'mano_ecuacion', 'mano_enunciado',
    'mano_referencia', 'mano_solucion', 'obtener_configuracion', 'obtener_rng',
    'pregunta', 'resolver', 'semilla', 'semilla_de', 'tabla', 'tabla_df',
    'tabla_en_blanco',
]
