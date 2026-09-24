# -*- coding: utf-8 -*-
"""
profe/core/evaluator.py — Motor de generación, calificación y envío de la tarea.

Los slots (cuántas preguntas, de qué tipo y con qué peso) y las tolerancias
viven en `config/config.yaml`; los bancos teóricos en `config/preguntas.yaml`.
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
            texto = (
                'Con el criterio de paro $\\varepsilon_s=%s\\%%$, revisa la tabla de '
                'iteraciones del ejercicio de arriba (el mismo de **tu actividad a '
                'mano**) y contesta: **¿en qué iteración el error aproximado '
                '$\\varepsilon_a$ queda por primera vez por debajo de '
                '$\\varepsilon_s$?**\n\n'
                'Escribe solo el número entero de la iteración (por ejemplo `4`).'
                % _fmt(es, 4)
            )
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

        opciones, correcta = _concepto_metodo(metodo)
        opciones = _reordenar(opciones, correcta, self.rng)
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
        casos = _casos_func(metodo, self.rng)
        firma, texto = _texto_func(metodo)
        p = {
            'titulo': 'Programa: %s' % NOMBRE_METODO.get(metodo, metodo),
            'tipo': 'funcion',
            'funcion': NOMBRE_FUNCION[metodo],
            'texto': texto,
            'casos': casos,
            'firma': firma,
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

        # El Apps Script espera el nombre de la HOJA en `tarea` y el token
        # compartido; el resto son los puntos y la identificación del alumno.
        cuerpo = {
            'token': self.token,
            'accion': self.accion,
            'tarea': self.id_tarea,
            'NC': self.nc,
            'correo': correo or self.alumno_id,
            'calificacion': builtins.round(calif, 1),
            'automatico': builtins.round(puntos, 2),
            'maximo': maximo,
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
                resultado['respuesta'] = resp.read().decode('utf-8', 'replace')
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


def _concepto_metodo(metodo):
    """(opciones, índice de la correcta) — la correcta siempre va primero."""
    if metodo == 'PF':
        return (['a) La iteracion $x_{i+1}=g(x_i)$ converge si $|g\'(x)|<1$ en la raiz',
                 'b) Converge siempre, sin importar la forma del despeje $g$',
                 'c) Converge solo si $f(a)f(b)<0$',
                 'd) Requiere dos puntos iniciales'], 0)
    if metodo == 'PFM':
        return (['a) La sub-relajacion ($0<\\lambda<1$) puede estabilizar un despeje que oscila',
                 'b) Siempre aumenta el numero de iteraciones',
                 'c) $\\lambda$ debe ser mayor que 2 para converger',
                 'd) Cambia la raiz del problema'], 0)
    if metodo == 'NR':
        return (['a) Convergencia cuadratica: el numero de digitos correctos se duplica cada iteracion',
                 'b) Convergencia lineal, del mismo orden que biseccion',
                 'c) No necesita la derivada $f\'$',
                 'd) Nunca falla, sin importar $f\'$'], 0)
    if metodo == 'NRM':
        return (['a) En una raiz multiple $f\'(x^*)=0$ y Newton-Raphson se vuelve lento (lineal)',
                 'b) Newton-Raphson es mas rapido en raices multiples',
                 'c) La raiz multiple no existe',
                 'd) El metodo modificado solo sirve para polinomios de grado 2'], 0)
    if metodo == 'SEC':
        return (['a) Orden de convergencia $\\approx1.618$ (superlineal) y no usa la derivada',
                 'b) Conserva el cambio de signo como la falsa posicion',
                 'c) Convergencia cuadratica, igual que Newton',
                 'd) Necesita que $f(x_{i-1})=f(x_i)$'], 0)
    if metodo == 'SM':
        return (['a) Si $\\delta$ es demasiado pequeno el cociente sufre error de cancelacion',
                 'b) $\\delta$ debe ser exactamente la derivada',
                 'c) El metodo necesita dos puntos iniciales',
                 'd) $\\delta$ no influye en el resultado'], 0)
    raise ValueError('Método desconocido: %r' % (metodo,))


def _texto_func(metodo):
    """(firma exacta, enunciado) de la pregunta de programación."""
    if metodo == 'PF':
        return ('pf(g, x0, tol=1e-6, max_iter=100)', (
            'Programa la **iteracion de punto fijo** en una funcion llamada `pf`.\n\n'
            '**Firma exacta** (respeta el nombre y el orden de los argumentos):\n\n'
            '```python\n'
            'def pf(g, x0, tol=1e-6, max_iter=100):\n'
            '    """Devuelve (raiz, n_iteraciones)."""\n'
            '```\n\n'
            '`g` es una funcion de una variable, `x0` el valor inicial y `tol` el criterio '
            'de paro **sobre el error relativo aproximado** '
            '$\\varepsilon_a=\\left|\\frac{x_{i+1}-x_i}{x_{i+1}}\\right|$ (expresado en '
            '**fraccion**, no en porciento: `tol=1e-6` = 1e-4 %).\n\n'
            'Devuelve una **tupla** `(raiz, n_iteraciones)`. Se probara con funciones '
            'ocultas, asi que no sirve escribir un resultado fijo.'))
    if metodo == 'PFM':
        return ('pfm(g, x0, lam, tol=1e-6, max_iter=100)', (
            'Programa el **punto fijo con relajacion** en `pfm`.\n\n'
            '```python\n'
            'def pfm(g, x0, lam, tol=1e-6, max_iter=100):\n'
            '    """x_{i+1} = lam*g(x_i) + (1-lam)*x_i. Devuelve (raiz, n_iter)."""\n'
            '```\n\n'
            'Es decir $x_{i+1}=\\lambda\\,g(x_i)+(1-\\lambda)x_i$. Con `lam=1` debe ser '
            'identico a `pf`. Criterio de paro igual que en `pf` (error relativo '
            'aproximado en fraccion). Devuelve `(raiz, n_iteraciones)`.'))
    if metodo == 'NR':
        return ('nr(f, df, x0, tol=1e-6, max_iter=100)', (
            'Programa **Newton-Raphson** en `nr`.\n\n'
            '```python\n'
            'def nr(f, df, x0, tol=1e-6, max_iter=100):\n'
            '    """x_{i+1} = x_i - f(x_i)/f\'(x_i). Devuelve (raiz, n_iter)."""\n'
            '```\n\n'
            '`df` es la derivada de `f`. Criterio de paro: error relativo aproximado '
            'en fraccion. Devuelve `(raiz, n_iteraciones)`. Debe proteger el caso '
            '$f\'(x_i)=0$ (evita la division entre cero).'))
    if metodo == 'NRM':
        return ('nrm(f, df, ddf, x0, tol=1e-6, max_iter=100)', (
            'Programa **Newton-Raphson modificado** (formula de Ralston-Rabinowitz) '
            'para raices multiples en `nrm`.\n\n'
            '```python\n'
            'def nrm(f, df, ddf, x0, tol=1e-6, max_iter=100):\n'
            '    """x_{i+1} = x_i - f f\' / ( (f\')^2 - f f\'\' ). Devuelve (raiz, n_iter)."""\n'
            '```\n\n'
            '`df` y `ddf` son la primera y la segunda derivada de `f`. Criterio de paro: '
            'error relativo aproximado en fraccion. Devuelve `(raiz, n_iteraciones)`. '
            'Protege el denominador nulo.'))
    if metodo == 'SEC':
        return ('secante(f, x0, x1, tol=1e-6, max_iter=100)', (
            'Programa el metodo de la **secante** en `secante`.\n\n'
            '```python\n'
            'def secante(f, x0, x1, tol=1e-6, max_iter=100):\n'
            '    """x_{i+1} = x_i - f(x_i)(x_{i-1}-x_i)/(f(x_{i-1})-f(x_i))."""\n'
            '```\n\n'
            'Parte de **dos** valores iniciales `x0`, `x1`. Criterio de paro: error '
            'relativo aproximado en fraccion. Devuelve `(raiz, n_iteraciones)`. '
            'Si `f(x0) == f(x1)` debes evitar la division entre cero.'))
    if metodo == 'SM':
        return ('secmod(f, x0, delta=0.01, tol=1e-6, max_iter=100)', (
            'Programa la **secante modificada** en `secmod`.\n\n'
            '```python\n'
            'def secmod(f, x0, delta=0.01, tol=1e-6, max_iter=100):\n'
            '    """x_{i+1} = x_i - delta*f(x_i)/(f(x_i+delta)-f(x_i))."""\n'
            '```\n\n'
            'Usa un **solo** valor inicial y aproxima la derivada con el incremento '
            '`delta`. Criterio de paro: error relativo aproximado en fraccion. '
            'Devuelve `(raiz, n_iteraciones)`. Evita dividir entre cero.'))
    raise ValueError('Método desconocido: %r' % (metodo,))


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
