# -*- coding: utf-8 -*-
"""
profe/core/evaluator.py — Motor de generación, calificación y envío de la tarea.

Los slots (cuántas preguntas, de qué tipo y con qué peso) y las tolerancias
viven en `config/config.yaml`; los bancos teóricos en `config/preguntas.yaml`
y los TEXTOS de las preguntas de cada método en `profe/evaluador/<metodo>.md`
(con el mismo formato que los enunciados de `profe/ejercicios/`).
Todo lo que depende del alumno se sortea con una semilla derivada de su número
de control, así que su tarea es reproducible.
"""
import builtins
import json
import math
import urllib.request

import numpy as np

from profe.config import buscar, obtener_configuracion
from profe.core import NOMBRE_FUNCION, NOMBRE_METODO, elegir, elegir_mano
from profe.core.helpers import _fmt
from profe.core.markdown_loader import cargar_pregunta_md, sustituir
from profe.core.seed import extraer_nc, obtener_rng
from profe.core.solvers import iteracion_objetivo

# Valores por omisión si el config.yaml no los trae
TOLERANCIA_SIMPLE = 1e-6        # respuestas numéricas ('simple'), relativa
TOLERANCIA_FUNCION = 1e-4       # raíz de las preguntas de programación
MIN_APROBACION = 0.9
MAX_ITER_DEFECTO = 60
CRITERIOS_PARO = [0.01, 0.1, 0.001]
TOL_ITERACION = 0.5             # tolerancia de "¿en qué iteración...?"
CASOS_OCULTOS = 3
MAX_ITER_ALUMNO = 1000


class Tarea(object):
    def __init__(self, alumno_id, cfg=None, bancos=None):
        self.alumno_id = alumno_id
        self.nc = extraer_nc(alumno_id)
        if not self.nc:
            raise ValueError('No pude leer el Número de Control de %r' % (alumno_id,))

        cfg_disco, bancos_disco = obtener_configuracion()
        self.cfg = cfg_disco if cfg is None else cfg
        self.bancos_teoricos = bancos_disco if bancos is None else bancos

        self.id_tarea = buscar(self.cfg, 'tarea.id', 'U2_T2_Metodos_abiertos')
        self.nombre_tarea = buscar(self.cfg, 'tarea.nombre', self.id_tarea)
        self.tol_simple = float(buscar(self.cfg, 'evaluacion.tolerancia_simple',
                                       buscar(self.cfg, 'evaluacion.tolerancia_porcentual',
                                              TOLERANCIA_SIMPLE)))
        self.tol_funcion = float(buscar(self.cfg, 'evaluacion.tolerancia_funcion',
                                        TOLERANCIA_FUNCION))
        self.min_aprobacion = float(buscar(self.cfg, 'evaluacion.min_aprobacion',
                                           MIN_APROBACION))
        self.max_iter = int(buscar(self.cfg, 'evaluacion.max_iter', MAX_ITER_DEFECTO))
        self.criterios_paro = [float(v) for v in
                               buscar(self.cfg, 'evaluacion.criterios_paro', CRITERIOS_PARO)]
        self.url = buscar(self.cfg, 'evaluacion.apps_script_url', '')
        self.token = buscar(self.cfg, 'evaluacion.webhook_token', '')
        self.accion = buscar(self.cfg, 'evaluacion.accion', 'guardar')
        self.peso_auto = float(buscar(self.cfg, 'ponderacion.automatico', 0.70))
        self.peso_mano = float(buscar(self.cfg, 'ponderacion.manual', 0.30))

        self.slots = buscar(self.cfg, 'slots', []) or []
        self.rng = obtener_rng(self.nc, self.id_tarea)

        self.preguntas = []
        self.soluciones = []
        self.pesos = [float(sl.get('peso', 0)) for sl in self.slots]
        self.funciones = []

        self._generar()

    def _generar(self):
        """Genera las preguntas asignadas a los slots según la semilla del alumno."""
        for slot in self.slots:
            tipo = slot.get('tipo', 'teorica')
            metodo = slot.get('metodo')

            if tipo == 'teorica':
                p, s = self._generar_teorica(slot.get('banco'))
            elif tipo == 'ejercicio_num':
                p, s = self._generar_ejercicio_num(metodo)
            elif tipo == 'funcion':
                p, s = self._generar_funcion_oculta(metodo)
                self.funciones.append(p['funcion'])
            else:
                raise ValueError('Tipo de slot desconocido: %r' % (tipo,))

            self.preguntas.append(p)
            self.soluciones.append(s)

        self.maximo = builtins.sum(self.pesos)

    def _generar_teorica(self, banco_nom):
        """Pregunta de opción múltiple: elige del banco y baraja las opciones."""
        banco = (self.bancos_teoricos or {}).get(banco_nom) or []
        if not banco:
            raise ValueError('Banco teórico vacío o no encontrado: %r' % (banco_nom,))
        p_raw = banco[int(self.rng.integers(0, len(banco)))]

        # El orden de las opciones cambia, y con él la LETRA correcta: la
        # solución es la posición que quedó ocupando la opción buena.
        opciones = _reordenar(p_raw['opciones'], int(p_raw.get('correcta', 0)), self.rng)
        p = {
            'titulo': p_raw['titulo'],
            'tipo': 'opcion',
            'texto': p_raw['pregunta'],
            'opciones': [texto for texto, _ in opciones],
        }
        return p, float([i for i, (_, buena) in enumerate(opciones) if buena][0])

    def _generar_ejercicio_num(self, metodo):
        """
        Pregunta de iteraciones sobre EL MISMO ejercicio de la actividad a
        mano de esa sección. Tres variantes, como en el motor original:
          0,1) ¿en qué iteración εa cae por debajo de εs?
          2)   pregunta conceptual de opción múltiple
        Si con ese εs la iteración no converge (o no alcanza en max_iter), la
        pregunta es la conceptual: no habría ningún número que reportar.
        """
        variante = int(self.rng.integers(0, 3))
        es = self.criterios_paro[int(self.rng.integers(0, len(self.criterios_paro)))]

        # Misma semilla y mismo catálogo que `mano_enunciado`: el alumno ya
        # tiene delante ese enunciado (y su tabla en blanco). Además la tabla
        # se calcula CON el εs que se pregunta, así que la respuesta siempre
        # existe dentro de la tabla.
        rng_mano = obtener_rng(self.nc, self.id_tarea, 'mano', metodo)
        ej = elegir_mano(metodo, rng_mano, es=es)

        if not ej.get('_conv'):
            variante = 2

        if variante < 2:
            filas = ej.get('_filas') or []
            k = iteracion_objetivo(filas, es)
            if k is None:
                # Respaldo: con un ejercicio convergente no debería llegar aquí.
                k = builtins.min(builtins.len(filas), 3) or 3
            # εs viene en %; la función del alumno lo quiere en fracción.
            tol_txt = '%.0e' % (es / 100.0)
            meta, _ = _ficha(metodo)
            _, texto = cargar_pregunta_md(
                'iteraciones.md',
                es=_fmt(es, 4),
                tol=tol_txt,
                ejemplo=sustituir(meta.get('ejemplo', ''), tol=tol_txt))
            p = {
                'titulo': 'Iteraciones: %s' % NOMBRE_METODO.get(metodo, metodo),
                'tipo': 'simple',
                'texto': texto,
                'tol': TOL_ITERACION,
                '_ej': ej,
                '_es': es,
                '_mostrar_ejercicio': True,
            }
            return p, float(k)

        meta, _ = _ficha(metodo)
        concepto = meta.get('concepto') or {}
        opciones = _reordenar(list(concepto.get('opciones') or []),
                              int(concepto.get('correcta', 0)), self.rng)
        p = {
            'titulo': 'Concepto: %s' % NOMBRE_METODO.get(metodo, metodo),
            'tipo': 'opcion',
            'texto': 'Sobre **%s**, contesta lo siguiente.' % NOMBRE_METODO.get(metodo, metodo),
            'opciones': [texto for texto, _ in opciones],
            '_ej': ej,
        }
        return p, float([i for i, (_, buena) in enumerate(opciones) if buena][0])

    def _generar_funcion_oculta(self, metodo):
        """Pregunta de programación: la función se prueba con casos ocultos."""
        meta, texto = _ficha(metodo)
        casos = _casos_func(metodo, self.rng)
        p = {
            'titulo': 'Programa: %s' % NOMBRE_METODO.get(metodo, metodo),
            'tipo': 'funcion',
            'funcion': meta['funcion'],
            'texto': texto,
            'casos': casos,
            'firma': meta['firma'],
        }
        return p, None

    # -------------------------------------------------------------------------
    # CALIFICACIÓN
    # -------------------------------------------------------------------------
    @staticmethod
    def _num(valor):
        """Convierte a float lo que haya (número, widget, tupla, 'a)')."""
        if valor is None:
            return None
        try:
            if isinstance(valor, (tuple, list, np.ndarray)):
                return float(np.ravel(np.asarray(valor, dtype=float))[0])
            return float(valor)
        except (TypeError, ValueError):
            return None

    def _correcta(self, p, valor, sol):
        """Compara una respuesta numérica o de opción múltiple."""
        num = self._num(valor)
        if num is None or sol is None:
            return False
        tol = p.get('tol')
        if tol is None:
            return builtins.abs(num - sol) <= self.tol_simple * builtins.max(1.0, builtins.abs(sol))
        return builtins.abs(num - sol) <= tol

    def calificar(self, respuestas, marco=None):
        """Devuelve una fila de detalle por pregunta (puntos, estado, solución)."""
        filas_res = []

        for i, (p, sol) in enumerate(zip(self.preguntas, self.soluciones), 1):
            peso = self.pesos[i - 1]

            if p['tipo'] == 'funcion':
                filas_res.append(self._calificar_funcion(i, p, peso, marco))
                continue

            val_alumno = respuestas.get(i)
            if val_alumno is None:
                filas_res.append({
                    'i': i, 'estado': 'sin respuesta', 'puntos': 0.0,
                    'peso': peso, 'sol': sol, 'val': None
                })
                continue

            ok = self._correcta(p, val_alumno, sol)
            filas_res.append({
                'i': i, 'estado': 'correcta' if ok else 'incorrecta',
                'puntos': peso if ok else 0.0, 'peso': peso,
                'sol': sol, 'val': val_alumno
            })

        return filas_res

    def _calificar_funcion(self, i, p, peso, marco):
        """
        Prueba la función del alumno con los casos ocultos. Cada caso aporta
        la misma fracción del peso; solo cuenta como bien si la raíz coincide
        (tolerancia relativa) y el número de iteraciones es razonable.
        """
        fn_alumno = None
        if marco is not None:
            fn_alumno = marco.f_globals.get(p['funcion'])

        aciertos, total = 0, 0
        detalle = []

        for entrada, esperado in (p.get('casos') or []):
            total += 1
            res = None
            ok = False

            if callable(fn_alumno):
                try:
                    res = fn_alumno(*entrada)
                except Exception:                      # noqa: BLE001
                    res = None

            if res is not None:
                raiz, nit = None, None
                try:
                    if isinstance(res, (tuple, list, np.ndarray)) and len(res) >= 2:
                        raiz, nit = self._num(res[0]), self._num(res[1])
                    else:
                        raiz, nit = self._num(res), 999
                except Exception:                      # noqa: BLE001
                    raiz, nit = None, None
                if raiz is not None and nit is not None:
                    bien_raiz = (builtins.abs(raiz - esperado)
                                 <= self.tol_funcion * builtins.max(1.0, builtins.abs(esperado)))
                    ok = bool(bien_raiz and 1 <= nit <= MAX_ITER_ALUMNO)

            aciertos += 1 if ok else 0
            detalle.append((p['funcion'], esperado, res, ok))

        if total == 0:
            return {'i': i, 'estado': 'sin respuesta', 'puntos': 0.0, 'peso': peso,
                    'sol': None, 'val': None}

        puntos = peso * aciertos / float(total)
        estado = 'correcta' if aciertos == total else ('parcial' if aciertos else 'incorrecta')
        return {'i': i, 'estado': estado, 'puntos': puntos, 'peso': peso,
                'sol': p, 'val': detalle}

    # -------------------------------------------------------------------------
    # ENVÍO A GOOGLE APPS SCRIPT
    # -------------------------------------------------------------------------
    def enviar(self, respuestas, marco=None, debug=False, correo=None):
        """
        Califica y envía el resultado automático al Apps Script.

        Devuelve un diccionario con el resultado (no imprime nada: de la
        realimentación al alumno se encarga `profe.ui.cuaderno`).
        """
        filas = self.calificar(respuestas, marco)
        puntos = builtins.sum(f['puntos'] for f in filas)
        maximo = builtins.sum(f['peso'] for f in filas)
        calif = 100.0 * (puntos / maximo) if maximo > 0 else 0.0

        resultado = {
            'enviado': False,
            'calificacion': calif,
            'puntos': puntos,
            'maximo': maximo,
            'minimo': self.min_aprobacion * 100.0,
            'filas': filas,
        }

        if calif < self.min_aprobacion * 100.0:
            resultado['motivo'] = 'minimo'
            return resultado

        # El Apps Script (doPost.gs -> procesarTarea) no se fía del resumen:
        # exige `respuestas` (el PUNTAJE de cada pregunta), `pesos` y
        # `maxPuntos`, y con eso reconstruye las columnas R1..Rn y el total
        # escalado a 100. Sin `respuestas` responde
        #   {"status":"error","message":"Las respuestas deben ser un arreglo..."}
        # y NO guarda nada en la hoja.
        cuerpo = {
            'token': self.token,
            'accion': self.accion,
            'tarea': self.id_tarea,
            'NC': self.nc,
            'correo': correo or self.alumno_id,
            'calificacion': builtins.round(calif, 1),
            'automatico': builtins.round(puntos, 2),
            'maximo': maximo,
            'respuestas': [builtins.round(f['puntos'], 4) for f in filas],
            'pesos': list(self.pesos),
            'maxPuntos': builtins.max(self.pesos) if self.pesos else 2,
        }
        resultado['cuerpo'] = cuerpo

        if debug:
            return resultado

        datos = json.dumps(cuerpo).encode('utf-8')
        pet = urllib.request.Request(
            self.url, data=datos,
            headers={'Content-Type': 'text/plain;charset=utf-8'})
        try:
            with urllib.request.urlopen(pet, timeout=30) as resp:
                texto = resp.read().decode('utf-8', 'replace')
            resultado['respuesta'] = texto
            # El Apps Script contesta 200 aunque RECHAZE el envío, así que hay
            # que mirar el cuerpo: si trae status=error, no se guardó nada.
            try:
                aviso = json.loads(texto)
            except ValueError:
                aviso = None
            resultado['aviso'] = aviso
            if isinstance(aviso, dict) and str(aviso.get('status', '')).lower() == 'error':
                resultado['enviado'] = False
                resultado['motivo'] = 'servidor'
                resultado['error'] = aviso.get('message', texto)
            else:
                resultado['enviado'] = True
        except Exception as exc:                            # noqa: BLE001
            resultado['motivo'] = 'red'
            resultado['error'] = str(exc)
        return resultado


# =====================================================================
#  BANCOS AUXILIARES: opciones, conceptos y textos de las preguntas
# =====================================================================
def _reordenar(opciones, idx_correcta, rng):
    """
    Reetiqueta las opciones a) b) c) d) y mueve la correcta a una posición al
    azar. Las opciones del banco vienen como 'a) texto' y la correcta la
    indica el campo `correcta` del YAML.

    Devuelve una lista de pares (texto_con_letra, es_la_correcta).
    """
    cuerpos = []
    for op in opciones:
        op = str(op).strip()
        cuerpos.append(op[2:].strip() if len(op) > 2 and op[1] == ')' else op)

    if not (0 <= idx_correcta < len(cuerpos)):
        idx_correcta = 0

    correcta = cuerpos.pop(idx_correcta)
    posicion = int(rng.integers(0, len(cuerpos) + 1))
    cuerpos.insert(posicion, correcta)

    return [('%s) %s' % (chr(97 + j), texto), j == posicion)
            for j, texto in enumerate(cuerpos)]


# =====================================================================
#  FICHAS DE LOS MÉTODOS (profe/evaluador/<metodo>.md)
#
#  Cada método tiene su archivo con el MISMO formato que los enunciados de
#  profe/ejercicios/: frontmatter (nombre de la función, firma exacta,
#  llamada de ejemplo y las opciones del concepto) y cuerpo con el texto que
#  lee el alumno. Así el profesor edita las preguntas sin tocar Python.
#
#  El ejemplo de llamada se usa en la pregunta de iteraciones: la tabla para
#  con εs **en por ciento**, pero las funciones del alumno reciben `tol` **en
#  fracción** (`tol = εs / 100`), y ese valor reproduce EXACTAMENTE la misma
#  iteración que la tabla (verificado con los 40 NC, los 6 métodos y los 3
#  criterios de paro). El nombre de la variable (`EJ_PF`, `EJ_PFM`, ...) es el
#  que usa el cuaderno en la sección de cada método.
# =====================================================================
ARCHIVO_FICHA = {
    'PF':  'pf.md',
    'PFM': 'pfm.md',
    'NR':  'nr.md',
    'NRM': 'nrm.md',
    'SEC': 'sec.md',
    'SM':  'sm.md',
}

_FICHAS = {}


def _ficha(metodo):
    """`(meta, texto)` de la pregunta de programación del método."""
    if metodo not in _FICHAS:
        archivo = ARCHIVO_FICHA.get(metodo)
        if archivo is None:
            raise ValueError('Método desconocido: %r' % (metodo,))
        meta, texto = cargar_pregunta_md(archivo)
        # El nombre de la función es el que declara el cuaderno: si el .md y el
        # registro no coinciden, la pregunta se calificaría sola en el vacío.
        esperado = NOMBRE_FUNCION.get(metodo)
        if meta.get('funcion') != esperado:
            raise ValueError('profe/evaluador/%s declara la funcion %r pero '
                             'NOMBRE_FUNCION dice %r'
                             % (archivo, meta.get('funcion'), esperado))
        _FICHAS[metodo] = (meta, texto)
    return _FICHAS[metodo]


def _concepto_metodo(metodo):
    """(opciones, índice de la correcta) — la correcta siempre va primero."""
    meta, _ = _ficha(metodo)
    concepto = meta.get('concepto') or {}
    return (list(concepto.get('opciones') or []), int(concepto.get('correcta', 0)))


def _texto_func(metodo):
    """(firma exacta, enunciado) de la pregunta de programación."""
    meta, texto = _ficha(metodo)
    return meta['firma'], texto


# =====================================================================
#  CASOS OCULTOS DE LAS PREGUNTAS DE PROGRAMACIÓN
#
#  Son problemas DISTINTOS a los del alumno (nunca los ve): si su función
#  conoce el método, los resuelve; si devuelve un número fijo, falla.
#  El valor esperado NO es una fórmula escrita a mano: lo calcula el solver
#  de referencia, así que la comparación siempre es consistente.
# =====================================================================
def _casos_func(metodo, rng):
    """Casos ocultos: lista de (entrada, esperado) con valores sembrados."""
    casos = []
    for _ in range(CASOS_OCULTOS):
        tipo = int(rng.integers(0, 3))
        if tipo == 0:
            a = builtins.round(float(rng.uniform(1.5, 5.0)), 3)
            x0 = a / 2.0
            f = (lambda a: (lambda x: x * x - a))(a)
            df = lambda x: 2.0 * x
            ddf = lambda x: 2.0
        elif tipo == 1:
            a = builtins.round(float(rng.uniform(1.2, 4.0)), 3)
            x0 = 1.0 + 0.3 * a
            f = (lambda a: (lambda x: x ** 3 - a))(a)
            df = lambda x: 3.0 * x * x
            ddf = lambda x: 6.0 * x
        else:
            a = builtins.round(float(rng.uniform(0.7, 1.6)), 3)
            x0 = 0.6
            f = (lambda a: (lambda x: math.exp(-a * x) - x))(a)
            df = (lambda a: (lambda x: -a * math.exp(-a * x) - 1.0))(a)
            ddf = (lambda a: (lambda x: a * a * math.exp(-a * x)))(a)

        if metodo in ('PF', 'PFM'):
            # g(x) = sqrt(x + k) tiene su punto fijo en x* = (1+sqrt(1+4k))/2:
            # es un despeje de verdad y ademas converge.
            k = builtins.round(float(rng.uniform(0.5, 2.0)), 3)
            g = (lambda k: (lambda x: math.sqrt(x + k)))(k)
            xinit = 1.0
            if metodo == 'PF':
                casos.append(((g, xinit), _ref_pf(g, xinit)))
            else:
                lam = builtins.round(float(rng.uniform(0.5, 1.2)), 2)
                casos.append(((g, xinit, lam), _ref_pf(g, xinit, lam)))
        elif metodo == 'NR':
            casos.append(((f, df, x0), _ref_nr(f, df, x0)))
        elif metodo == 'NRM':
            r = builtins.round(float(rng.uniform(1.5, 2.5)), 2)
            rr = (lambda r: (lambda x: (x - r) ** 2 * (x - (r + 1.0))))(r)
            d1 = (lambda r: (lambda x: (x - r) * (3.0 * x - (2.0 * (r + 1.0) + r))))(r)
            d2 = (lambda r: (lambda x: 6.0 * x - 2.0 * (2.0 * r + (r + 1.0))))(r)
            casos.append(((rr, d1, d2, r + 0.6), _ref_nrm(rr, d1, d2, r + 0.6)))
        elif metodo == 'SEC':
            x1 = x0 + builtins.round(float(rng.uniform(0.5, 1.5)), 2)
            casos.append(((f, x0, x1), _ref_sec(f, x0, x1)))
        elif metodo == 'SM':
            casos.append(((f, x0), _ref_sm(f, x0, 0.01)))
        else:
            raise ValueError('Método desconocido: %r' % (metodo,))
    return casos


def _ref_pf(g, x0, lam=None, tol=1e-12, max_iter=400):
    """Punto fijo (o con relajación) de alta precisión."""
    x = x0
    for _ in range(max_iter):
        gx = g(x)
        xn = gx if lam is None else lam * gx + (1.0 - lam) * x
        if builtins.abs(xn - x) <= tol * builtins.max(1.0, builtins.abs(xn)):
            return xn
        x = xn
    return x


def _ref_nr(f, df, x0, tol=1e-13, max_iter=200):
    """Newton-Raphson de alta precisión."""
    x = x0
    for _ in range(max_iter):
        d = df(x)
        if d == 0:
            break
        xn = x - f(x) / d
        if builtins.abs(xn - x) <= tol * builtins.max(1.0, builtins.abs(xn)):
            return xn
        x = xn
    return x


def _ref_nrm(f, df, ddf, x0, tol=1e-13, max_iter=300):
    """Newton-Raphson modificado (raíces múltiples) de alta precisión."""
    x = x0
    for _ in range(max_iter):
        fx, d1, d2 = f(x), df(x), ddf(x)
        den = d1 * d1 - fx * d2
        if den == 0:
            break
        xn = x - fx * d1 / den
        if builtins.abs(xn - x) <= tol * builtins.max(1.0, builtins.abs(xn)):
            return xn
        x = xn
    return x


def _ref_sec(f, xa, xb, tol=1e-13, max_iter=200):
    """Secante de alta precisión."""
    for _ in range(max_iter):
        fa, fb = f(xa), f(xb)
        if fb == fa:
            break
        xn = xb - fb * (xb - xa) / (fb - fa)
        if builtins.abs(xn - xb) <= tol * builtins.max(1.0, builtins.abs(xn)):
            return xn
        xa, xb = xb, xn
    return xb


def _ref_sm(f, x0, dx, tol=1e-13, max_iter=200):
    """Secante modificada de alta precisión."""
    x = x0
    for _ in range(max_iter):
        fx, fxd = f(x), f(x + dx)
        if fxd == fx:
            break
        xn = x - dx * fx / (fxd - fx)
        if builtins.abs(xn - x) <= tol * builtins.max(1.0, builtins.abs(xn)):
            return xn
        x = xn
    return x
