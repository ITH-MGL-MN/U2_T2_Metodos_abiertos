# -*- coding: utf-8 -*-
"""
profe/core/evaluator.py — Motor de generación, calificación y envío de la tarea.
"""
import builtins
import json
import math
import urllib.request
import numpy as np

from profe.config import obtener_configuracion
from profe.core.seed import extraer_nc, obtener_rng
from profe.core.solvers import iteraciones, iteracion_objetivo
from profe.core import elegir, NOMBRE_METODO, NOMBRE_FUNCION

class Tarea(object):
    def __init__(self, alumno_id):
        self.alumno_id = alumno_id
        self.nc = extraer_nc(alumno_id)
        if not self.nc:
            raise ValueError(f"No pude leer el Número de Control de {alumno_id!r}")

        self.cfg, self.bancos_teoricos = obtener_configuracion()
        self.rng = obtener_rng(self.nc, self.cfg['tarea']['id'])

        self.preguntas = []
        self.soluciones = []
        self.slots = self.cfg['slots']
        self.pesos = [s['peso'] for s in self.slots]
        self.funciones = []

        self._generar()

    def _generar(self):
        """Genera las preguntas asignadas a los slots según la semilla del alumno."""
        orden = {}
        for slot in self.slots:
            tipo = slot.get('tipo', 'teorica')
            banco_nom = slot.get('banco')
            metodo = slot.get('metodo')

            if tipo == 'teorica':
                p, s = self._generar_teorica(banco_nom)
            elif tipo == 'ejercicio_num':
                p, s = self._generar_ejercicio_num(metodo, orden)
            elif tipo == 'funcion':
                p, s = self._generar_funcion_oculta(metodo)
                self.funciones.append(p['funcion'])
            else:
                raise ValueError(f"Tipo de slot desconocido: {tipo}")

            self.preguntas.append(p)
            self.soluciones.append(s)

    def _generar_teorica(self, banco_nom):
        banco = self.bancos_teoricos.get(banco_nom, [])
        if not banco:
            raise ValueError(f"Banco teórico vacío o no encontrado: {banco_nom}")
        idx_p = int(self.rng.integers(0, len(banco)))
        p_raw = banco[idx_p]

        # Reordenar opciones para que la opción correcta no siempre sea la primera
        opcs = list(p_raw['opciones'])
        idx_correcta = int(self.rng.integers(0, len(opcs)))

        # Swap
        correcta = opcs
        opcs = opcs[idx_correcta]
        opcs[idx_correcta] = correcta

        # Re-etiquetar a), b), c), d)
        opcs_fmt = []
        for j, op in enumerate(opcs):
            cuerpo = op[2:].strip() if len(op) > 2 and op == ')' else op.strip()
            opcs_fmt.append(f"{chr(97 + j)}) {cuerpo}")

        p = {
            'titulo': p_raw['titulo'],
            'tipo': 'opcion',
            'texto': p_raw['pregunta'],
            'opciones': opcs_fmt
        }
        return p, float(idx_correcta)

    def _generar_ejercicio_num(self, metodo, orden):
        ej = elegir(metodo, self.rng)
        filas = ej.get('_filas', [])
        es = 0.01  # % por omisión

        k = iteracion_objetivo(filas, es)
        if k is None or not ej.get('_conv', True):
            k = 3

        texto = (
            f"**{ej['titulo']}** (Tabla de iteraciones).\n\n"
            f"Con el criterio de paro $\\varepsilon_s = {es}\\%$, revisa la tabla de "
            f"iteraciones de tu ejercicio y contesta: **¿en qué iteración el error "
            f"aproximado $\\varepsilon_a$ queda por primera vez por debajo de $\\varepsilon_s$?**\n\n"
            f"Escribe solo el número entero de la iteración (ejemplo: `3`)."
        )
        p = {
            'titulo': f"Iteraciones: {NOMBRE_METODO.get(metodo, metodo)}",
            'tipo': 'simple',
            'texto': texto,
            'tol': 0.5,
            '_ej': ej
        }
        return p, float(k)

    def _generar_funcion_oculta(self, metodo):
        nombre_fn = NOMBRE_FUNCION[metodo]
        casos = self._generar_casos_ocultos(metodo)
        firma = f"{nombre_fn}(...)"
        texto = f"Programa la función **{nombre_fn}** para resolver {NOMBRE_METODO[metodo]}."
        p = {
            'titulo': f"Programa: {NOMBRE_METODO.get(metodo, metodo)}",
            'tipo': 'funcion',
            'funcion': nombre_fn,
            'texto': texto,
            'casos': casos,
            'firma': firma
        }
        return p, None

    def _generar_casos_ocultos(self, metodo):
        casos = []
        for _ in range(3):
            a = builtins.round(float(self.rng.uniform(1.5, 5.0)), 3)
            f = lambda x, a=a: x * x - a
            df = lambda x: 2.0 * x
            ddf = lambda x: 2.0
            raiz_ref = math.sqrt(a)

            if metodo == 'PF':
                g = lambda x, a=a: math.sqrt(x + a)
                casos.append(((g, 1.0), raiz_ref))
            elif metodo == 'PFM':
                g = lambda x, a=a: math.sqrt(x + a)
                casos.append(((g, 1.0, 0.5), raiz_ref))
            elif metodo == 'NR':
                casos.append(((f, df, 1.0), raiz_ref))
            elif metodo == 'NRM':
                casos.append(((f, df, ddf, 1.0), raiz_ref))
            elif metodo == 'SEC':
                casos.append(((f, 1.0, 2.0), raiz_ref))
            elif metodo == 'SM':
                casos.append(((f, 1.0), raiz_ref))
        return casos

    # -------------------------------------------------------------------------
    # CALIFICACIÓN
    # -------------------------------------------------------------------------
    def calificar(self, respuestas, marco=None):
        filas_res = []
        tol_rel = self.cfg['evaluacion']['tolerancia_porcentual']

        for i, (p, sol) in enumerate(zip(self.preguntas, self.soluciones), 1):
            peso = self.pesos[i - 1]
            tipo = p['tipo']

            if tipo == 'funcion':
                res_fn = self._calificar_funcion(i, p, peso, marco)
                filas_res.append(res_fn)
                continue

            val_alumno = respuestas.get(i)
            if val_alumno is None:
                filas_res.append({
                    'i': i, 'estado': 'sin respuesta', 'puntos': 0.0,
                    'peso': peso, 'sol': sol, 'val': None
                })
                continue

            # Evaluación numérica o selección múltiple
            try:
                val_num = float(val_alumno)
                ok = abs(val_num - sol) <= (p.get('tol', tol_rel) if p.get('tol') else tol_rel * max(1.0, abs(sol)))
            except (ValueError, TypeError):
                ok = False

            filas_res.append({
                'i': i, 'estado': 'correcta' if ok else 'incorrecta',
                'puntos': peso if ok else 0.0, 'peso': peso,
                'sol': sol, 'val': val_alumno
            })

        return filas_res

    def _calificar_funcion(self, i, p, peso, marco):
        fn_alumno = None
        if marco is not None:
            fn_alumno = marco.f_globals.get(p['funcion'])

        aciertos, total = 0, 0
        detalle = []

        for entrada, esperado in (p.get('casos') or []):
            total += 1
            ok = False
            res = None

            if callable(fn_alumno):
                try:
                    res = fn_alumno(*entrada)
                    if isinstance(res, (tuple, list, np.ndarray)) and len(res) >= 2:
                        raiz, nit = float(res), int(res)
                        bien_raiz = abs(raiz - esperado) <= 1e-3 * max(1.0, abs(esperado))
                        bien_iter = (1 <= nit <= 1000)
                        ok = bien_raiz and bien_iter
                except Exception:
                    ok = False

            aciertos += 1 if ok else 0
            detalle.append((p['funcion'], esperado, res, ok))

        if total == 0:
            return {'i': i, 'estado': 'sin respuesta', 'puntos': 0.0, 'peso': peso, 'sol': None, 'val': None}

        puntos = peso * (aciertos / float(total))
        estado = 'correcta' if aciertos == total else ('parcial' if aciertos > 0 else 'incorrecta')
        return {'i': i, 'estado': estado, 'puntos': puntos, 'peso': peso, 'sol': p, 'val': detalle}

    # -------------------------------------------------------------------------
    # ENVÍO A GOOGLE APPS SCRIPT
    # -------------------------------------------------------------------------
    def enviar(self, respuestas, marco=None):
        filas = self.calificar(respuestas, marco)
        puntos = sum(f['puntos'] for f in filas)
        maximo = sum(f['peso'] for f in filas)
        calif = 100.0 * (puntos / maximo) if maximo > 0 else 0.0

        min_aprob = self.cfg['config'].get('min_aprobacion', 0.90) * 100.0
        if calif < min_aprob:
            print(f"⛔ Aún no puedes enviar: necesitas al menos {min_aprob:.1f}% ({min_aprob*maximo/100:.1f} pts).")
            print("Corrige tus respuestas e inténtalo de nuevo.")
            return False

        cuerpo = {
            'tarea': self.cfg['tarea']['id'],
            'NC': self.nc,
            'correo': self.alumno_id,
            'calificacion': round(calif, 1),
            'automatico': round(puntos, 2),
            'maximo': maximo
        }

        url = self.cfg['evaluacion']['apps_script_url']
        datos = json.dumps(cuerpo).encode('utf-8')
        pet = urllib.request.Request(url, data=datos, headers={'Content-Type': 'application/json'})

        try:
            with urllib.request.urlopen(pet, timeout=30) as resp:
                res_txt = resp.read().decode('utf-8', 'replace')
                print(f"✅ Enviado con éxito. Respuesta del servidor: {res_txt[:150]}")
                return True
        except Exception as exc:
            print(f"⚠️ No se pudo enviar a la hoja de cálculo: {exc}")
            return False
