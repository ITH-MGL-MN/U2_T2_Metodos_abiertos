# profe/core/markdown_loader.py
import os
import yaml
import re
from .helpers import _r, _fmt

def cargar_ejercicio_md(nombre_archivo, rng):
    ruta = os.path.join(os.path.dirname(__file__), '..', 'ejercicios', nombre_archivo)
    with open(ruta, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # Separar el Frontmatter YAML (entre --- y ---) del cuerpo Markdown
    partes = re.split(r'^---\s*$', contenido, flags=re.MULTILINE)
    meta = yaml.safe_load(partes)
    cuerpo_md = partes.strip()

    # Aleatorizar variables según los rangos definidos en el YAML
    datos = {}
    valores_fmt = {}
    for var, (lo, hi, dec) in meta.get('rangos', {}).items():
        val = _r(rng, lo, hi, dec)
        datos[var] = val
        valores_fmt[var] = _fmt(val, dec)

    # Inyectar los valores reales en la plantilla del texto Markdown
    contexto_formateado = cuerpo_md.format(**valores_fmt)
    
    return meta, contexto_formateado, datos
