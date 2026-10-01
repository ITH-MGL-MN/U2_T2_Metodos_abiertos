---
# Texto de la pregunta de ITERACIONES (la segunda de cada método).
# Marcadores que rellena profe/core/evaluator.py:
#   {es}      criterio de paro en por ciento, ya formateado (p. ej. 0.0100)
#   {tol}     ese mismo criterio en fracción, para el `tol` de la función
#   {ejemplo} la llamada de ejemplo a la función del alumno, con `tol` puesto
---

Con el criterio de paro $\varepsilon_s = {es}\,\%$, contesta: **¿en qué iteración el error aproximado $\varepsilon_a$ queda por primera vez por debajo de $\varepsilon_s$?**

No lo cuentes a mano: pásale a **tu función** esa misma tolerancia **en fracción** (sin usar porcentaje) y el número de iteraciones que te devuelva es la respuesta.

```python
{ejemplo}
```

Escribe solo el número entero de la iteración (por ejemplo `4`).
