---
metodo: NR
funcion: nr
firma: "nr(f, df, x0, tol=1e-6, max_iter=100)"
ejemplo: "nr(EJ_NR['f'], EJ_NR['df'], EJ_NR['x0'], tol={tol})"
concepto:
  correcta: 0
  opciones:
    - 'Convergencia cuadrática: los dígitos correctos se duplican en cada iteración'
    - 'Convergencia lineal, del mismo orden que la bisección'
    - 'No necesita la derivada $f^{\prime}$: la aproxima sola'
    - 'Nunca falla, sin importar cómo sea $f^{\prime}$'
---

Programa **Newton-Raphson** en `nr`.

```python
def nr(f, df, x0, tol=1e-6, max_iter=100):
```
$$x_{i+1} = x_i - \frac{f(x_i)}{f'(x_i)}$$

Devuelve (`raiz`, `n_iter`).

`df` es la derivada de `f`. Criterio de paro: error relativo aproximado **en fracción**. Devuelve `(raiz, n_iteraciones)`. Debe proteger el caso $f^{\prime}(x_i)=0$ (evita la división entre cero).
