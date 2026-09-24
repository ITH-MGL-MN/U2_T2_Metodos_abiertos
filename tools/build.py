# -*- coding: utf-8 -*-
"""
tools/build.py — Script empaquetador y ofuscador del autograder para Colab.
"""
import os
import sys
import zlib
import base64
import yaml
import glob

RAIZ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def leer_archivo(ruta_relativa):
    ruta = os.path.join(RAIZ_DIR, ruta_relativa)
    with open(ruta, 'r', encoding='utf-8') as f:
        return f.read()

def construir_bundle():
    print("📦 Iniciando empaquetado del Autograder...")

    # 1. Cargar datos estáticos (YAML)
    cfg_yaml = leer_archivo('config/config.yaml')
    preguntas_yaml = leer_archivo('config/preguntas.yaml')

    # 2. Cargar todas las plantillas Markdown
    mda_dict = {}
    rutas_md = glob.glob(os.path.join(RAIZ_DIR, 'profe', 'ejercicios_md', '*.md'))
    for r in rutas_md:
        nombre = os.path.basename(r)
        with open(r, 'r', encoding='utf-8') as f:
            mda_dict[nombre] = f.read()

    # 3. Concatenar los módulos de código Python en orden estricto de dependencia
    modulos_py = [
        'profe/config.py',
        'profe/core/seed.py',
        'profe/core/helpers.py',
        'profe/core/markdown_loader.py',
        'profe/ejercicios/modelos.py',
        'profe/ejercicios/registry.py',
        'profe/core/solvers.py',
        'profe/core/evaluator.py',
        'profe/ui/widgets.py'
    ]

    codigo_unido = "# -*- coding: utf-8 -*-\n"
    codigo_unido += f"DATOS_CONFIG_YAML = {cfg_yaml!r}\n"
    codigo_unido += f"DATOS_PREGUNTAS_YAML = {preguntas_yaml!r}\n"
    codigo_unido += f"DATOS_MARKDOWN_DICT = {mda_dict!r}\n\n"

    for mod in modulos_py:
        print(f"  + Acoplando módulo: {mod}")
        contenido = leer_archivo(mod)
        # Filtrar importaciones relativas internas que ya estarán concatenadas
        lineas = [l for l in contenido.splitlines() if not l.startswith('from profe.') and not l.startswith('import profe.')]
        codigo_unido += "\n".join(lineas) + "\n\n"

    # Punto de entrada para el alumno en Colab
    codigo_unido += """
def iniciar_tarea(alumno_id, marco=None):
    import sys
    m = marco or sys._getframe(1)
    tarea = Tarea(alumno_id)
    ui = InterfazTarea(tarea, m)
    ui.mostrar()
"""

    # 4. Compresión y Ofuscación con Zlib + Base64
    bytes_codigo = codigo_unido.encode('utf-8')
    bytes_comprimidos = zlib.compress(bytes_codigo, level=9)
    b64_str = base64.b64encode(bytes_comprimidos).decode('ascii')

    script_ofuscado = f"""# -*- coding: utf-8 -*-
# Auto-generated Autograder Bundle — No modificar manualmente
import zlib, base64
_payload = "{b64_str}"
exec(zlib.decompress(base64.b64decode(_payload)).decode('utf-8'))
"""

    # 5. Guardar el resultado final
    ruta_salida = os.path.join(RAIZ_DIR, 'grader_U2_T2.txt')
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        f.write(script_ofuscado)

    tamano_kb = os.path.getsize(ruta_salida) / 1024.0
    print(f"\n✅ ¡Empaquetado exitoso! Archivo generado: grader_U2_T2.txt ({tamano_kb:.1f} KB)")

if __name__ == '__main__':
    construir_bundle()
