---
# Ficha del método: lo que la pregunta NECESITA va en el frontmatter y el
# texto que lee el alumno va en el cuerpo (igual que en profe/ejercicios/).
metodo: PF
funcion: pf
firma: "pf(g, x0, tol=1e-6, max_iter=100)"
ejemplo: "pf(EJ_PF['g'], EJ_PF['x0'], tol={tol})"
concepto:
  correcta: 0
  opciones:
    - 'La iteración $x_{i+1}=g(x_i)$ converge si $|g^{\prime}(x)|<1$ en la raíz'
    - 'Converge siempre, sin importar la forma del despeje $g$'
    - 'Converge solo si $f(a)f(b)<0$'
    - 'Requiere dos puntos iniciales'
---

Programa la **iteración de punto fijo** en una función llamada `pf`.

**Firma exacta** (respeta el nombre y el orden de los argumentos):

```python
def pf(g, x0, tol=1e-6, max_iter=100):
    """Devuelve (raiz, n_iteraciones)."""
```

`g` es una función de una variable, `x0` el valor inicial y `tol` el criterio de paro **sobre el error relativo aproximado** $\varepsilon_a=\left|\frac{x_{i+1}-x_i}{x_{i+1}}\right|$, expresado **en fracción** y no en por ciento: `tol=1e-6` equivale a $10^{-4}\,\%$.

Devuelve una **tupla** `(raiz, n_iteraciones)`. Se probará con funciones ocultas, así que no sirve escribir un resultado fijo.
