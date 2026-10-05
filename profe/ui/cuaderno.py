# -*- coding: utf-8 -*-
"""
profe/ui/cuaderno.py — API que usa el cuaderno del alumno.

El cuaderno NO habla con los módulos internos: llama a estas funciones, que
son las mismas del motor original, así que las celdas y las explicaciones no
cambian cuando se reordena el código por dentro.

    generar_tarea(alumno_id)      crea MI_TAREA y muestra el encabezado
    pregunta(n)                   muestra la pregunta n y su widget resp_n
    mano_enunciado(metodo)        enunciado + tabla en blanco de la actividad
    mano_ecuacion(metodo, ...)    revisa las lambdas que escribió el alumno
    mano_comprueba(metodo, lista) realimentación de la tabla a mano
    mano_solucion(metodo)         valor de la 3ª iteración (referencia)
    hoja_manual()                 resumen para calificar las 6 rúbricas
    hoja_manual / calificar / enviar

Los mensajes al alumno se imprimen aquí (es la capa de presentación); el
motor de `profe.core` solo devuelve datos.
"""
import builtins
import inspect
import json

import numpy as np

from profe.config import buscar, obtener_configuracion
from profe.core import METODOS_MANO, NOMBRE_FUNCION, NOMBRE_METODO, elegir_mano
from profe.core.evaluator import Tarea
from profe.core.seed import extraer_nc, generar_semilla, obtener_rng
from profe.core.solvers import ES_DEFECTO, MAX_ITER, iteraciones

# ---------------------------------------------------------------------
#  Estado del cuaderno
# ---------------------------------------------------------------------
_EXAMEN = None             # la tarea que se está resolviendo
_MANO = {}                 # metodo -> valores que reportó el alumno
_MANO_EJ = {}              # metodo -> ejercicio de la actividad a mano
_MANO_RES = {}             # metodo -> True si acertó la 3ª iteración
_MANO_EC = {}              # metodo -> True si SUS lambdas coinciden
_ULTIMO_ENVIO = None       # resultado del último enviar() (lo ve ultimo_envio())

ORDEN_COLUMNAS = {
    'PF':  ['i', 'x_i', 'g(x_i)', 'x', 'ea'],
    'PFM': ['i', 'x_i', 'g(x_i)', 'x', 'ea'],
    'NR':  ['i', 'x_i', 'f(x_i)', "f'(x_i)", 'x', 'ea'],
    'NRM': ['i', 'x_i', 'f(x_i)', "f'(x_i)", "f''(x_i)", 'x', 'ea'],
    'SEC': ['i', 'x_{i-1}', 'x_i', 'f(x_{i-1})', 'f(x_i)', 'x', 'ea'],
    'SM':  ['i', 'x_i', 'x_i+dx', 'f(x_i)', 'f(x_i+dx)', 'x', 'ea'],
}

# Parámetros de arranque y su nombre en LaTeX (el orden importa: es el que
# se ve en la línea de datos). `_PARAMS_METODO` dice cuáles usa cada método:
# el ejercicio puede traer `lam` o `delta` sin que el método los necesite.
_PARAMS_TEXTO = (('x0', 'x_0'), ('x1', 'x_1'), ('lam', r'\lambda'), ('delta', r'\delta'))
_PARAMS_METODO = {
    'PF':  ('x0',),
    'PFM': ('x0', 'lam'),
    'NR':  ('x0',),
    'NRM': ('x0',),
    'SEC': ('x0', 'x1'),
    'SM':  ('x0', 'delta'),
}

# Encabezados "bonitos" para la impresión en texto plano.
ENCABEZADOS = {'x': 'x_{i+1}', 'ea': 'ea (%)'}

COLUMNAS_EXPL = {
    'PF': ('`x_i` = el valor con el que arranca la iteración (en la 1 es $x_0$)  ·  '
           '`g(x_i)` = evalúas el despeje  ·  `x_{i+1}` = tu nueva estimación, que es '
           '**el mismo** $g(x_i)$  ·  `ea (%)`.'),
    'PFM': ('`x_i` = valor de arranque  ·  `g(x_i)` = evalúas el despeje  ·  '
            '`x_{i+1}` = $\\lambda g(x_i)+(1-\\lambda)x_i$ (el punto medio entre '
            '$g(x_i)$ y $x_i$)  ·  `ea (%)`.'),
    'NR': ('`x_i` = valor de arranque  ·  `f(x_i)` y `f\'(x_i)` = evalúas la función y '
           'su derivada  ·  `x_{i+1}=x_i-\\frac{f(x_i)}{f\'(x_i)}$  ·  `ea (%)`.'),
    'NRM': ('`x_i` = valor de arranque  ·  `f`, `f\'` y `f\'\'` = función y sus dos '
            'primeras derivadas  ·  `x_{i+1}=x_i-\\frac{f f\'}{(f\')^2-ff\'\'}$  ·  '
            '`ea (%)`.'),
    'SEC': ('`x_{i-1}` y `x_i` = los DOS últimos valores  ·  `f(x_{i-1})` y `f(x_i)` = '
            'sus evaluaciones  ·  `x_{i+1}` = donde la recta que une esos dos puntos '
            'corta al eje $x$  ·  `ea (%)`.'),
    'SM': ('`x_i` = valor de arranque  ·  `x_i+dx` = ese valor más el incremento '
           'fijo $\\delta$ (no un porcentaje de $x_i$)  ·  `f(x_i)` y `f(x_i+dx)` = las '
           'dos evaluaciones  ·  `x_{i+1}` = el paso corregido con esa pendiente  ·  '
           '`ea (%)`.'),
}


def _display(*objetos):
    """`display` de IPython, importado solo cuando se usa."""
    from IPython.display import display
    return display(*objetos)


def _markdown(texto):
    from IPython.display import Markdown
    return Markdown(texto)


def _obtener_examen(nc=None, marco=None):
    """
    La tarea del alumno. Si todavía no existe, la crea usando el `alumno_id`
    que esté en el cuaderno; si no hay ninguno, avisa.
    """
    global _EXAMEN
    if _EXAMEN is None:
        if marco is None:
            marco = inspect.currentframe().f_back
        glob = getattr(marco, 'f_globals', {}) or {}
        alumno = nc
        for clave in ('alumno_id', 'ALUMNO_ID', 'MI_CORREO', 'correo'):
            if alumno:
                break
            alumno = glob.get(clave)
        if alumno is None:
            raise RuntimeError('Primero ejecuta generar_tarea(alumno_id).')
        _EXAMEN = Tarea(alumno)
    return _EXAMEN


# =====================================================================
#  TABLAS DE ITERACIONES
# =====================================================================
def _filas_tabla(metodo, ej, filas_n=None):
    filas = ej.get('_filas')
    if not filas:
        filas = iteraciones(metodo, ej)[1]
    return filas if filas_n is None else filas[:filas_n]


def _texto_tabla(filas, orden):
    """Impresión en texto plano (sin pandas)."""
    if not filas:
        return '(tabla vacía)'
    cols = [c for c in orden if c in filas[0]]
    enc = [ENCABEZADOS.get(c, c)[:13] for c in cols]
    lineas = ['  '.join('%-13s' % c for c in enc), '-' * (15 * len(cols))]
    for fila in filas:
        celdas = []
        for c in cols:
            v = fila.get(c)
            if isinstance(v, float):
                celdas.append('%-13.8g' % v)
            elif isinstance(v, (int, np.integer)):
                celdas.append('%-13s' % v)
            else:
                celdas.append('%-13s' % ('' if v is None else v))
        lineas.append('  '.join(celdas))
    return '\n'.join(lineas)


def tabla_en_blanco(metodo, ej, n=3):
    """
    Tabla con los resultados OCULTOS, para que el alumno la llene a mano:
    solo se muestra el valor inicial y el número de iteración.
    """
    orden = ORDEN_COLUMNAS[metodo]
    filas = _filas_tabla(metodo, ej)[:n]
    salida = []
    for k, fila in enumerate(filas):
        nueva = {}
        for c in orden:
            if c == 'i':
                nueva[c] = fila['i']
            elif c in ('x_i', 'x_{i-1}') and k == 0:
                nueva[c] = fila[c]
            else:
                nueva[c] = ''
        salida.append(nueva)
    return salida


def tabla_df(metodo, ej, filas_n=None):
    """
    Tabla de iteraciones de referencia como DataFrame de pandas.
    Si pandas no está disponible, devuelve una lista de diccionarios.
    """
    datos = _filas_tabla(metodo, ej, filas_n)
    orden = ORDEN_COLUMNAS[metodo]
    try:
        import pandas as pd
    except ImportError:
        return [{k: fila.get(k) for k in orden} for fila in datos]
    df = pd.DataFrame(datos)
    df = df[[c for c in orden if c in df.columns]]
    return df.rename(columns=ENCABEZADOS)


def tabla(metodo, ej, filas_n=None):
    """Muestra la tabla de iteraciones de referencia."""
    datos = _filas_tabla(metodo, ej, filas_n)
    df = tabla_df(metodo, ej, filas_n)
    if df is not None and not isinstance(df, list):
        _display(_markdown('**Tabla de iteraciones (referencia)**'))
        _display(df)
    else:
        print('Tabla de iteraciones (referencia)')
        print(_texto_tabla(datos, ORDEN_COLUMNAS[metodo]))
    return df


# =====================================================================
#  TAREA Y PREGUNTAS
# =====================================================================
def generar_tarea(alumno_id):
    """Crea la tarea del alumno y muestra el encabezado."""
    global _EXAMEN
    _EXAMEN = Tarea(alumno_id)
    _display(_markdown('# Tarea · %s' % _EXAMEN.nombre_tarea))
    _display(_markdown('**Alumno:** `%s`  ·  **NC:** `%s`  ·  **Puntos automáticos:** %g'
                       % (_EXAMEN.alumno_id, _EXAMEN.nc, _EXAMEN.maximo)))
    _display(_markdown('Esta tarea tiene **%d** preguntas automáticas (%g puntos) y **6** '
                       'actividades a mano que revisa tu profesor (%g%% de la calificación).'
                       % (len(_EXAMEN.preguntas), _EXAMEN.maximo,
                          100.0 * _EXAMEN.peso_mano)))
    return _EXAMEN


# Compatibilidad: la función se llamaba `generar_examen` antes de renombrarla.
def generar_examen(alumno_id):
    return generar_tarea(alumno_id)


def _render_pregunta(i, p, peso=None, total=None):
    _display(_markdown('#### Pregunta %d: %s' % (i, p['titulo'])))
    if peso is not None and total:
        _display(_markdown('**Valor:** $\\frac{%g}{%g}$ puntos' % (peso, total)))
    # Las preguntas de iteraciones se refieren al ejercicio de la sección, que
    # el alumno ya tiene delante: se recuerda el TÍTULO nada más, sin repetir
    # entero el enunciado (es el mismo de su actividad a mano).
    if p.get('_mostrar_ejercicio') and p.get('_ej'):
        _display(_markdown('**Ejercicio:** %s' % p['_ej']['titulo']))
    _display(_markdown(p['texto']))
    if p['tipo'] == 'funcion':
        _display(_markdown(
            'Define la función con **exactamente** la firma `%s` en una celda aparte '
            'y ejecútala (no la definas dentro de esta celda).' % p.get('firma', '?')))


def _crear_widget_respuesta(i, p, marco):
    """
    Crea y muestra el widget de la pregunta y lo guarda como `resp_i` en el
    cuaderno. En las de tipo `opcion` el valor es el ÍNDICE de la opción.
    """
    import ipywidgets as widgets
    from ipywidgets import Layout

    t = p['tipo']
    if t == 'opcion':
        for op in p['opciones']:
            _display(_markdown(op))
        letras = [chr(97 + j) + ')' for j in range(len(p['opciones']))]
        w = widgets.RadioButtons(
            options=[(letra, j) for j, letra in enumerate(letras)],
            value=None, disabled=False, layout=Layout(width='170px'))
        _display(w)
        marco.f_globals['resp_%d' % i] = w
        return w
    if t == 'simple':
        w = widgets.FloatText(value=0.0, description='Respuesta:',
                              layout=Layout(width='260px'))
        _display(w)
        marco.f_globals['resp_%d' % i] = w
        return w
    # tipo 'funcion': no hay widget, la función se lee del cuaderno
    marco.f_globals['resp_%d' % i] = None
    return None


def pregunta(numero):
    """Muestra la pregunta `numero` (1..14) y su widget."""
    marco = inspect.currentframe().f_back
    ex = _obtener_examen(marco=marco)
    i = int(numero)
    if not 1 <= i <= len(ex.preguntas):
        raise ValueError('Esta tarea tiene %d preguntas.' % len(ex.preguntas))
    p = ex.preguntas[i - 1]
    _render_pregunta(i, p, peso=ex.pesos[i - 1], total=ex.maximo)
    _crear_widget_respuesta(i, p, marco)
    # Devuelve None a propósito: si regresara el diccionario, Jupyter lo
    # imprimiría debajo del widget. Para inspeccionarlo usa
    # MI_TAREA.preguntas[i-1] o MI_TAREA.soluciones[i-1].
    return None


def _leer_valor(marco, i):
    for clave in ('resp_%d' % i, 'r%d' % i):
        w = marco.f_globals.get(clave)
        if w is None:
            continue
        try:
            return w.value
        except AttributeError:
            return w
    return None


def _respuestas_del_cuaderno(marco):
    ex = _EXAMEN
    res = {}
    for i in range(1, len(ex.preguntas) + 1):
        if ex.preguntas[i - 1]['tipo'] == 'funcion':
            continue
        res[i] = _leer_valor(marco, i)
    return res


# Casos de prueba con solución conocida: sirven para comprobar la función del
# alumno cuando SU ejercicio es de los que no convergen (los "trampa" de PF).
CASOS_PRUEBA = {
    'PF': ('pf(lambda x: (2*x + 3)**0.5, 1.25)', 'x* = 3'),
    'PFM': ('pfm(lambda x: (2*x + 3)**0.5, 1.25, 0.5)', 'x* = 3'),
    'NR': ('nr(lambda x: x**3 - 2*x - 5, lambda x: 3*x**2 - 2, 2.0)', 'x* = 2.094551'),
    'NRM': ('nrm(lambda x: x**3 - 2*x - 5, lambda x: 3*x**2 - 2, lambda x: 6*x, 2.0)',
            'x* = 2.094551'),
    'SEC': ('secante(lambda x: x**3 - 2*x - 5, 1.0, 3.0)', 'x* = 2.094551'),
    'SM': ('secmod(lambda x: x**3 - 2*x - 5, 2.0, 0.01)', 'x* = 2.094551'),
}


def comparar_practica(metodo, ej, resultado):
    """
    Compara lo que devolvió la función del alumno con la referencia del
    ejercicio y le dice con claridad si el problema es su código o el
    despeje.

    `resultado` = lo que devolvió su función: (raiz, n_iteraciones).
    """
    nombre = NOMBRE_FUNCION.get(metodo, metodo)
    try:
        raiz, n = float(resultado[0]), int(resultado[1])
    except (TypeError, IndexError, ValueError):
        print('\u26a0\ufe0f Tu %s no devolvió una tupla (raiz, n_iteraciones): %r'
              % (nombre, resultado))
        return

    print('tu %-8s: raiz = %.8f   iteraciones = %d' % (nombre, raiz, n))

    # `raiz` del ejercicio es la raíz que se busca: la de la tabla cuando la
    # iteración converge, o la analítica cuando el despeje se la pierde.
    ref = ej.get('raiz')
    coincide = (ref is not None and
                builtins.abs(raiz - ref) <= 1e-4 * builtins.max(1.0, builtins.abs(ref)))

    if ej.get('_conv'):
        print('referencia : raiz = %.8f   iteraciones = %d' % (ref, len(ej['_filas'])))
        if coincide:
            print('   \u2705 coincide con la referencia. Las iteraciones pueden diferir:')
            print('      la tabla para con \u03b5s = %g %% y tu función usa tol = 1e-6'
                  % ej.get('_es', 0.01))
        else:
            print('   \u274c NO coincide con la referencia: revisa tu función antes de seguir')
        return

    # La tabla no resolvió el ejercicio: puede ser DIVERGENCIA de verdad
    # (|g'| >= 1) o simplemente LENTITUD (|g'| < 1 pero sin alcanzar εs en
    # MAX_ITER pasos). Son cosas distintas y no conviene confundirlas.
    lento = False
    if ej.get('dg') is not None and ref is not None:
        try:
            lento = builtins.abs(ej['dg'](ref)) < 1.0
        except (TypeError, ValueError, ZeroDivisionError):
            lento = False

    es = ej.get('_es', ES_DEFECTO)
    if lento:
        print('referencia : el despeje SÍ converge (|g\'(x*)| < 1), pero en %d '
              'iteraciones' % MAX_ITER)
        print('             no alcanza εs = %g %%: es lentitud, no divergencia.' % es)
    else:
        print('referencia : con el despeje del enunciado la iteración NO converge')
    if ref is not None:
        if lento:
            print('             (la raíz que se busca es x* = %.8f)' % ref)
        else:
            print('             (la raíz que se busca es x* = %.8f: hay que cambiar '
                  'de despeje)' % ref)
    if coincide:
        print('   \u2705 Tu función SÍ llegó a la raíz: la probaste con otro despeje, no')
        print('      con el del enunciado. Lo que falla es la iteración del enunciado.')
    else:
        print('\u26a0\ufe0f Tu función no está mal:')
        if lento:
            print('   el despeje del enunciado converge, pero demasiado lento: en %d'
                  % MAX_ITER)
            print('   iteraciones no llega a εs = %g %% (mira el laboratorio de la λ).' % es)
        else:
            print("   es el despeje del enunciado el que no converge (mira |g'(x*)|")
            print('   en el laboratorio de arriba).')
        cmd, valor = CASOS_PRUEBA.get(metodo, ('', ''))
        if cmd:
            print('   Compruébala con un caso que sí converge:')
            print('       %s   ->   %s' % (cmd, valor))


def _mostrar_resultados(filas):
    """Tabla de resultados de la calificación (la usa `calificar`)."""
    iconos = {'correcta': '\u2705', 'parcial': '\U0001f7e1',
              'incorrecta': '\u274c', 'sin respuesta': '\u26a0\ufe0f'}
    print('%-4s %-12s %-8s %s' % ('#', 'estado', 'puntos', 'respuesta'))
    print('-' * 62)
    for fila in filas:
        val = fila['val']
        if isinstance(val, (tuple, list)) and val and isinstance(val[0], tuple):
            val = 'programa (%d casos)' % len(val)
        print('%-4d %-12s %-8s %s' % (fila['i'], iconos[fila['estado']],
                                      '%g/%g' % (fila['puntos'], fila['peso']), val))
    print('-' * 62)


def _nota_ponderada(ex, porcentaje_auto):
    """
    Imprime la nota final del curso: 0.70 * automático + 0.30 * manual.

    `porcentaje_auto` es el % del automático (0-100). La parte manual todavía
    no existe en este punto (son las 6 rúbricas de la hoja de trabajo), así
    que solo se muestra lo que aporta el automático.
    """
    print('NOTA FINAL (ponderada): %.1f / 100  =  %.2f × %.1f %%  +  %.2f × manual'
          % (100.0 * ex.peso_auto * porcentaje_auto / 100.0, ex.peso_auto,
             porcentaje_auto, ex.peso_mano))
    print('   (falta el %.0f %% manual: las 6 rúbricas de la hoja de trabajo)'
          % (100.0 * ex.peso_mano))


def calificar(marco=None):
    """Califica las 14 preguntas automáticas y muestra el detalle."""
    ex = _EXAMEN
    if ex is None:
        raise RuntimeError('Primero ejecuta generar_tarea(alumno_id).')
    if marco is None:
        marco = inspect.currentframe().f_back

    respuestas = _respuestas_del_cuaderno(marco)
    filas = ex.calificar(respuestas, marco)

    puntos = 0.0
    maximo = 0.0
    for fila in filas:
        puntos += fila['puntos']
        maximo += fila['peso']
    _mostrar_resultados(filas)
    print('AUTOMÁTICO: %.1f / %g  =  %.1f %%' % (puntos, maximo, 100.0 * puntos / maximo))
    _nota_ponderada(ex, 100.0 * puntos / maximo)
    return puntos, maximo


def ultimo_envio(detalle=False):
    """
    Resumen del último `enviar()`. Con `detalle=True` devuelve además el
    diccionario completo (para depurar desde otra celda).

    `enviar()` devuelve None a propósito: es la última celda del cuaderno, y
    Jupyter imprime el valor de la última expresión de una celda, así que
    devolver el diccionario volcaría en la salida el POST completo (con el
    token del Apps Script) y los valores esperados de los casos ocultos.
    """
    if _ULTIMO_ENVIO is None:
        print('Todavía no has llamado a enviar().')
        return None
    res = _ULTIMO_ENVIO
    print('Último envío: %s  ·  %.1f %% (%g/%g puntos)'
          % ('enviado' if res.get('enviado') else 'NO enviado',
             res.get('calificacion', 0.0), res.get('puntos', 0.0),
             res.get('maximo', 0.0)))
    if res.get('motivo'):
        print('   motivo: %s' % res['motivo'])
    if res.get('error'):
        print('   error : %s' % res['error'])
    return res if detalle else None


def enviar(correo=None, marco=None, debug=False):
    """
    Envía el resultado automático al Apps Script (exige ≥ MIN_APROBACION).

    Devuelve None a propósito (el resultado queda en `_ULTIMO_ENVIO`, que
    muestra `ultimo_envio()`): si devolviera el diccionario, Jupyter lo
    imprimiría debajo de la celda. Con `debug=True` sí lo devuelve, porque
    lo consumen las herramientas del profesor.
    """
    global _ULTIMO_ENVIO
    ex = _EXAMEN
    if ex is None:
        raise RuntimeError('Primero ejecuta generar_tarea(alumno_id).')
    if marco is None:
        marco = inspect.currentframe().f_back

    puntos, maximo = calificar(marco)
    correo = correo or marco.f_globals.get('alumno_id', '') or ex.alumno_id
    res = ex.enviar(_respuestas_del_cuaderno(marco), marco, debug=debug, correo=correo)
    _ULTIMO_ENVIO = res

    if debug:
        print('POST', ex.url)
        print(json.dumps(res['cuerpo'], indent=2, ensure_ascii=False))
        return res

    if res.get('motivo') == 'minimo':
        print('⛔ Aún no puedes enviar: necesitas al menos %g %% (%g puntos). '
              'Corrige y vuelve a intentarlo.'
              % (res['minimo'], ex.min_aprobacion * res['maximo']))
        print('   (este intento NO se gastó: no se guardó nada en la hoja)')
        return None

    if res['enviado']:
        detalle = ''
        aviso = res.get('aviso')
        if isinstance(aviso, dict) and isinstance(aviso.get('data'), dict):
            d = aviso['data']
            detalle = ' Intento %s, total %.1f %%.' % (d.get('intento', '?'),
                                                       d.get('total', 0.0))
        print('\u2705 Enviado.%s Respuesta del servidor: %s'
              % (detalle, res['respuesta'][:300]))
    else:
        print('\u26a0\ufe0f No se pudo enviar a la hoja de cálculo: %s'
              % res.get('error'))
    return None


def consultar_calificacion():
    """
    Muestra lo que la hoja de cálculo tiene guardado para este alumno: los
    intentos usados y el último total. NO envía nada (la consulta es de solo
    lectura), así que no gasta intentos: se puede llamar las veces que sea.

    Devuelve None a propósito, para que Jupyter no imprima nada debajo.
    """
    marco = inspect.currentframe().f_back
    ex = _obtener_examen(marco=marco)
    res = ex.consultar()

    if not res.get('ok'):
        print('\u26a0\ufe0f No pude consultar la hoja de cálculo: %s'
              % res.get('error'))
        print('   (la consulta no gasta intentos; revisa tu conexión y reintenta)')
        return None

    usados = int(res.get('intento') or 0)
    total = res.get('total')
    restantes = builtins.max(0, ex.max_intentos - usados)
    print('NC %s  ·  %s' % (res.get('NC', ex.nc), res.get('tarea', ex.id_tarea)))
    print('   Intentos usados : %d de %d' % (usados, ex.max_intentos))
    print('   Te quedan       : %d' % restantes)
    print('   Último total    : %s'
          % ('%.1f %%' % float(total) if total is not None else '(todavía sin nota)'))
    print('   Estado          : %s' % res.get('estado', '?'))
    if total is not None:
        _nota_ponderada(ex, float(total))
    if total is not None and float(total) >= 100.0 * ex.min_aprobacion:
        print('\u2705 Ya tienes guardado un envío con nota suficiente.')
    elif restantes == 0:
        print('\u26d4 Ya no te quedan intentos; si necesitas otra oportunidad,')
        print('   habla con tu profesor.')
    else:
        print('   Todavía tienes %d intento%s: revisa con calificar() y luego envía.'
              % (restantes, '' if restantes == 1 else 's'))
    return None


# =====================================================================
#  ACTIVIDADES A MANO (con realimentación automática)
# =====================================================================
def _num_txt(valor):
    """Número corto para el enunciado: 69.0 -> 69, 1e-05 -> 1e-05."""
    try:
        return '%g' % float(valor)
    except (TypeError, ValueError):
        return str(valor)


def _datos_texto(metodo, ej):
    """
    Línea con los datos del ejercicio y los parámetros de arranque.

    El enunciado (.md) cuenta las constantes físicas en prosa, pero los
    parámetros del método (x0, x1, λ, δ) no siempre aparecen ahí: la secante
    modificada necesita un δ que hasta ahora no se mostraba en ningún lado,
    así que su tabla a mano era imposible de llenar.

    Devuelve el Markdown de la línea, o None si no hay nada que mostrar.
    """
    piezas = []
    for nombre, valor, unidad in (ej.get('datos') or []):
        if nombre in ('ecuacion', 'lam'):
            # 'ecuacion' no es un dato (es la ecuación del enunciado) y 'lam'
            # se imprime abajo, en LaTeX y solo si el método la usa.
            continue
        sufijo = '' if not unidad or unidad == '-' else ' %s' % unidad
        piezas.append('%s = %s%s' % (nombre, _num_txt(valor), sufijo))

    usados = _PARAMS_METODO.get(metodo, ('x0',))
    for clave, etiqueta in _PARAMS_TEXTO:
        if clave not in usados:
            continue
        valor = ej.get(clave)
        if valor is None:
            continue
        piezas.append('$%s = %s$' % (etiqueta, _num_txt(valor)))

    if not piezas:
        return None
    return '**Datos y arranque:** ' + '  ·  '.join(piezas)


def _marco_mano(metodo, ej):
    """
    Enunciado de la actividad a mano (sin revelar los resultados).

    El texto va con display(Markdown(...)) para que el LaTeX del enunciado
    se renderice; la tabla va con print() porque es texto monoespaciado y
    así las columnas quedan alineadas.
    """
    _display(_markdown('### ✏️ Actividad a mano: %s' % NOMBRE_METODO[metodo]))
    _display(_markdown('**%s**' % ej['titulo']))
    _display(_markdown(ej['contexto'].strip()))
    linea_datos = _datos_texto(metodo, ej)
    if linea_datos:
        _display(_markdown(linea_datos))
    filas = ej['_filas']
    n = builtins.min(3, builtins.len(filas))
    _display(_markdown('**Tu tabla para llenar a mano** (no redondees los pasos '
                       'intermedios):'))
    print(_texto_tabla(tabla_en_blanco(metodo, ej, n), ORDEN_COLUMNAS[metodo]))
    _display(_markdown('Reporta en la celda siguiente la lista `[x_1, x_2, x_3]` con al '
                       'menos 4 decimales. **Solo se comprueba el valor de la 3ª '
                       'iteración** para que verifiques tu resultado.'))
    return n


def mano_enunciado(metodo, nc=None):
    """
    Imprime el enunciado de la actividad a mano del método y guarda el
    ejercicio en `_MANO_EJ[metodo]` para la realimentación.

    El ejercicio se sortea con el número de control del alumno, así que no
    coincide con el de sus compañeros.
    """
    marco = inspect.currentframe().f_back
    ex = _obtener_examen(nc=nc, marco=marco)
    rng = obtener_rng(nc or ex.nc, ex.id_tarea, 'mano', metodo)
    ej = elegir_mano(metodo, rng)
    _MANO_EJ[metodo] = ej
    _marco_mano(metodo, ej)
    return ej


def mano_comprueba(metodo, valores):
    """
    Realimentación de la actividad a mano.
    `valores` = [x_1, x_2, x_3]; SOLO se compara la 3ª iteración contra la
    referencia (las dos primeras son trabajo del alumno).
    """
    ej = (_MANO_EJ or {}).get(metodo)
    if ej is None:
        print('Primero ejecuta mano_enunciado(%r).' % metodo)
        return None

    vals = list(builtins.map(float, valores))
    _MANO[metodo] = vals
    print('Tus valores reportados: %s'
          % ', '.join('x_%d = %.8g' % (k + 1, v) for k, v in enumerate(vals)))

    ref = [fila['x'] for fila in ej['_filas']]
    if not ref:
        _MANO_RES[metodo] = False
        print('⚠️ Con este método la iteración NO converge (se sale de rango): '
              'la tabla se desboca, eso es el resultado.')
        return None

    k = builtins.min(3, builtins.len(ref))
    r = ref[k - 1]
    v = vals[k - 1] if builtins.len(vals) >= k else float('nan')
    err = builtins.abs(v - r) / builtins.max(builtins.abs(r), 1e-12)
    bien = err <= 1e-3
    _MANO_RES[metodo] = bool(bien)
    print('')
    print('   Referencia de la 3ª iteración : x_%d = %.8f' % (k, r))
    print('   Tu valor                      : x_%d = %.8f' % (k, v))
    print('   Error relativo                : %.3e   %s'
          % (err, '✅ correcto' if bien else '❌ revisa tus cuentas'))
    if not bien:
        print('   Sugerencias: arrastra TODOS los decimales de la iteración anterior')
        print('   y evalúa siempre la misma fórmula (no redondees a la mitad).')
    if not ej.get('_conv'):
        print('💡 Ojo: con este despeje la iteración NO converge a la raíz')
        print('   del enunciado (oscila o se sale de rango). Eso es lo que')
        print('   tienes que reportar como conclusión.')
    # None a propósito: evita que Jupyter imprima el diccionario del ejercicio.
    return None


def mano_solucion(metodo):
    """
    Da SOLO el valor de la 3ª iteración (es la referencia de la actividad).
    La tabla completa queda para la revisión del profesor en hoja_manual().
    """
    ej = (_MANO_EJ or {}).get(metodo)
    if ej is None:
        print('Primero ejecuta mano_enunciado(%r).' % metodo)
        return None
    ref = [fila['x'] for fila in ej['_filas']]
    if not ref:
        print('Este ejercicio NO converge con %s: la iteración se sale de rango.'
              % NOMBRE_METODO[metodo])
        return None
    k = builtins.min(3, builtins.len(ref))
    fila = ej['_filas'][k - 1]
    print('Referencia de la 3ª iteración : x_%d = %.8f   (con ea = %.4f %%)'
          % (k, fila['x'], fila['ea']))
    print('(La tabla completa de las 3 iteraciones la revisa tu profesor en la')
    print(' HOJA DE TRABAJO MANUAL.)')
    # None a propósito: evita que Jupyter imprima el diccionario del ejercicio.
    return None


# Nombre alterno, más descriptivo que "solución".
def mano_referencia(metodo):
    return mano_solucion(metodo)


def mano_ecuacion(metodo, f=None, df=None, ddf=None, g=None):
    """
    Revisa la ECUACIÓN que escribió el alumno (como funciones lambda) contra
    la del enunciado, evaluándola en puntos OCULTOS.

    Cada método pide lo que usa:
        PF, PFM  ->  f y el despeje g
        NR       ->  f y f'
        NRM      ->  f, f' y f''
        SEC, SM  ->  f
    El resultado queda en `_MANO_EC[metodo]` y se imprime en hoja_manual().
    """
    ej = (_MANO_EJ or {}).get(metodo)
    if ej is None:
        print('Primero ejecuta mano_enunciado(%r).' % metodo)
        return None

    necesarias = {
        'PF':  (('f', f), ('g', g)),
        'PFM': (('f', f), ('g', g)),
        'NR':  (('f', f), ("f'", df)),
        'NRM': (('f', f), ("f'", df), ("f''", ddf)),
        'SEC': (('f', f),),
        'SM':  (('f', f),),
    }[metodo]
    referencia = {'f': ej.get('f'), "f'": ej.get('df'), "f''": ej.get('ddf'),
                  'g': ej.get('g')}

    # --- puntos ocultos: el inicio, la raíz y un valor intermedio ---------
    x0 = float(ej.get('x0'))
    r = ej.get('raiz')
    xs = []
    for cand in (x0, r, None if r is None else 0.5 * (x0 + r), x0 * 1.05 + 0.1):
        if cand is None:
            continue
        cand = float(cand)
        if not np.isfinite(cand):
            continue
        if builtins.all(builtins.abs(cand - v) > 1e-6 * builtins.max(1.0, builtins.abs(v))
                        for v in xs):
            xs.append(cand)
        if builtins.len(xs) == 3:
            break

    print('Revisión de TU ecuación (en %d valores que no ves):' % builtins.len(xs))
    todo_ok, faltan, malas = True, [], []
    for nombre, fn_alumno in necesarias:
        fn_ref = referencia.get(nombre)
        if fn_alumno is None:
            faltan.append(nombre)
            todo_ok = False
            print('   %-4s : todavía no la escribiste' % nombre)
            continue
        if fn_ref is None:
            print('   %-4s : (este enunciado no la pide)' % nombre)
            continue
        peor, falla = 0.0, None
        for x in xs:
            try:
                a, b = float(fn_alumno(x)), float(fn_ref(x))
            except Exception as exc:                       # noqa: BLE001
                falla = 'tu lambda falló en x=%.6g (%r)' % (x, exc)
                break
            if not (np.isfinite(a) and np.isfinite(b)):
                continue
            peor = builtins.max(peor, builtins.abs(a - b) /
                                builtins.max(1.0, builtins.abs(b)))
        if falla:
            todo_ok = False
            malas.append(nombre)
            print('   %-4s : NO  -> %s' % (nombre, falla))
        elif peor <= 1e-6:
            print('   %-4s : OK  (diferencia relativa máxima %.2e)' % (nombre, peor))
        else:
            todo_ok = False
            malas.append(nombre)
            print('   %-4s : NO coincide (diferencia relativa máxima %.2e)' % (nombre, peor))

    _MANO_EC[metodo] = bool(todo_ok)
    if todo_ok:
        print('✅ Tu ecuación coincide con la del enunciado.')
    elif faltan:
        print('⚠️ Falta escribir: %s' % ', '.join(faltan))
    else:
        print('❌ Revisa %s: compárala con la fórmula del enunciado (paréntesis, '
              'signos, unidades).' % ', '.join(malas))
    return None


def hoja_manual(metodo=None):
    """
    Resumen para calificar a mano (lo que ve el profesor).
    Con `metodo` muestra solo esa actividad; sin argumentos, las seis.
    """
    ex = _EXAMEN
    nombre = ex.id_tarea if ex is not None else 'U2_T2_Metodos_abiertos'
    metodos = (metodo,) if metodo else METODOS_MANO

    print('=' * 72)
    print('HOJA DE TRABAJO MANUAL · %s' % nombre)
    print('=' * 72)
    for met in metodos:
        ej = (_MANO_EJ or {}).get(met)
        if ej is None:
            continue
        ref = [fila['x'] for fila in ej['_filas']][:3]
        alumno = _MANO.get(met, [])
        print('\n%s · %s' % (NOMBRE_METODO[met], ej['titulo']))
        raiz = ej['raiz'] if ej['raiz'] is not None else float('nan')
        print('  raíz       = %.8g' % raiz)
        print('  referencia : %s' % ', '.join('%.6g' % v for v in ref))
        print('  alumno     : %s' % (', '.join('%.6g' % v for v in alumno)
                                     if alumno else '(sin reportar)'))
        _ec = _MANO_EC.get(met)
        print('  ecuación   : %s' % ('OK' if _ec else ('NO' if _ec is False
                                                      else '(sin escribir)')))
        print('  tabla      : %s' % ('acertada' if _MANO_RES.get(met)
                                     else ('revisar' if met in _MANO_RES
                                           else '(sin comprobar)')))
    if ex is not None:
        print('\nCalifica cada rúbrica de 0 a 10 en la hoja %s_Manual.' % nombre)
        print('Nota final = %.2f*automático + %.2f*manual'
              % (ex.peso_auto, ex.peso_mano))


# =====================================================================
#  Utilidades sueltas que el cuaderno (o el profesor) puede usar
# =====================================================================
def semilla_de(alumno_id):
    """Semilla entera del alumno (útil para reproducir su tarea)."""
    cfg, _ = obtener_configuracion()
    id_tarea = buscar(cfg, 'tarea.id', 'U2_T2_Metodos_abiertos')
    return generar_semilla(extraer_nc(alumno_id), id_tarea)


__all__ = [
    'CASOS_PRUEBA', 'COLUMNAS_EXPL', 'ENCABEZADOS', 'ORDEN_COLUMNAS',
    'calificar', 'comparar_practica', 'consultar_calificacion', 'enviar',
    'generar_examen', 'generar_tarea', 'hoja_manual', 'iteraciones',
    'mano_comprueba', 'mano_ecuacion', 'mano_enunciado', 'mano_referencia',
    'mano_solucion', 'pregunta', 'tabla', 'tabla_df', 'tabla_en_blanco',
    'ultimo_envio'
]
