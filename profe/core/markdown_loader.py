# -*- coding: utf-8 -*-
"""
profe/core/markdown_loader.py — Enunciados Markdown de los ejercicios.

Cada ejercicio vive en `profe/ejercicios/<nombre>.md`: un frontmatter YAML
(titulo, incognita, unidad, rangos aleatorios) y el cuerpo Markdown con los
valores entre llaves.

Los textos viajan EMBEBIDOS en el bundle (`DATOS_MARKDOWN_DICT`, lo pone
`tools/build.py`) para que el motor ofuscado no necesite el disco; al
importar el paquete en local se leen de `profe/ejercicios/`.
"""
import os
import re

import yaml

from .helpers import _r, _fmt

try:
    _AQUI = os.path.dirname(os.path.abspath(__file__))
except NameError:            # dentro del bundle (exec) no existe __file__
    _AQUI = os.getcwd()
DIR_EJERCICIOS = os.path.normpath(os.path.join(_AQUI, '..', 'ejercicios'))

_CACHE = {}

# Marcadores del enunciado: un nombre sencillo entre llaves, {x0}, {lam}, {m}.
# NO tocamos las llaves de LaTeX (\frac{x^2-3}{2}, e^{-ct/m}) porque no son
# identificadores sueltos: así el .md sigue siendo LaTeX legible.
_PLACEHOLDER = re.compile(r'\{([A-Za-z_][A-Za-z_0-9]*)\}')


def sustituir(texto, **valores):
    """
    Reemplaza los marcadores `{nombre}` por sus valores YA formateados.

    Los marcadores que no estén en `valores` se dejan tal cual, así que
    también sirve para completar valores que la fábrica calcula después
    de sortear (por ejemplo `r` y `x0` en el ejercicio de la raíz doble).
    """
    return _PLACEHOLDER.sub(
        lambda m: str(valores[m.group(1)]) if m.group(1) in valores else m.group(0),
        texto)


def _texto(nombre_archivo):
    """Markdown del ejercicio: primero el embebido (bundle), si no del disco."""
    try:
        embebido = DATOS_MARKDOWN_DICT  # noqa: F821  (lo define tools/build.py)
    except NameError:
        embebido = None
    if embebido and nombre_archivo in embebido:
        return embebido[nombre_archivo]

    if nombre_archivo not in _CACHE:
        with open(os.path.join(DIR_EJERCICIOS, nombre_archivo), 'r',
                  encoding='utf-8') as f:
            _CACHE[nombre_archivo] = f.read()
    return _CACHE[nombre_archivo]


def cargar_ejercicio_md(nombre_archivo, rng):
    """
    Devuelve `(meta, cuerpo_formateado, valores)` del ejercicio indicado.

    `meta`     : el frontmatter YAML (titulo, incognita, unidad, rangos, ...)
    `cuerpo`   : el Markdown con los valores sorteados ya sustituidos
    `valores`  : dict variable -> valor numerico sorteado
    """
    contenido = _texto(nombre_archivo)

    # Frontmatter:  ---  YAML  ---  cuerpo
    partes = re.split(r'^---\s*$', contenido, flags=re.MULTILINE)
    if len(partes) < 3:
        raise ValueError('%s no tiene frontmatter YAML (--- ... ---)' % nombre_archivo)
    meta = yaml.safe_load(partes[1]) or {}
    cuerpo_md = partes[2]

    # Aleatorizar variables según los rangos definidos en el YAML
    datos = {}
    valores_fmt = {}
    for var, (lo, hi, dec) in meta.get('rangos', {}).items():
        val = _r(rng, lo, hi, dec)
        datos[var] = val
        valores_fmt[var] = _fmt(val, dec)

    # Inyectar los valores reales en la plantilla del texto Markdown
    contexto_formateado = sustituir(cuerpo_md, **valores_fmt)

    return meta, contexto_formateado, datos
