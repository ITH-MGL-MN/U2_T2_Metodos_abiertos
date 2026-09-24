# -*- coding: utf-8 -*-
"""
probador.py — Herramienta local para inspeccionar y probar ejercicios por NC.
"""
import math
from profe.core.seed import obtener_rng
from profe.core.registry import elegir, NOMBRE_METODO

def probar_ejercicio(nc="16330887", metodo="NR"):
    print(f"=" * 60)
    print(f" PROBANDO EJERCICIO | NC: {nc} | Método: {NOMBRE_METODO[metodo]}")
    print(f"=" * 60)

    # 1. Obtener generador sembrado
    rng = obtener_rng(nc, "U2_T2", metodo)

    # 2. Generar ejercicio aleatorio
    ej = elegir(metodo, rng)

    print(f"\n📌 TÍTULO: {ej['titulo']}")
    print(f"🎯 INCÓGNITA: {ej['incognita']} [{ej['unidad']}]")
    print(f"🚀 VALOR INICIAL (x0): {ej['x0']}")
    print("\n--- TEXTO QUE VERÁ EL ALUMNO (MARKDOWN) ---")
    print(ej['contexto'])
    print("-------------------------------------------\n")

    # 3. Validar evaluación matemática
    x0 = ej['x0']
    f_val = ej['f'](x0)
    print(f"🧪 PRUEBA MATEMÁTICA: f({x0}) = {f_val:.6f}")
    if abs(f_val) > 1e10 or math.isnan(f_val):
        print("⚠️ ADVERTENCIA: La función evaluó un valor numérico inestable.")
    else:
        print("✅ Evaluación matemática correcta.")

if __name__ == '__main__':
    # Puedes cambiar el NC para simular diferentes alumnos
    probar_ejercicio(nc="16330887", metodo="NR")
    #probar_ejercicio(nc="20330123", metodo="PF")
