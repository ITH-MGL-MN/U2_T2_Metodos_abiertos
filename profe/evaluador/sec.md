---
metodo: SEC
funcion: secante
firma: "secante(f, x0, x1, tol=1e-6, max_iter=100)"
ejemplo: "secante(EJ_SEC['f'], EJ_SEC['x0'], EJ_SEC['x1'], tol={tol})"
concepto:
  correcta: 0
  opciones:
    - 'Orden de convergencia $\approx1.618$ (superlineal) y no usa la derivada'
    - 'Conserva el cambio de signo, igual que la falsa posición'
    - 'Convergencia cuadrática, exactamente igual que Newton'
    - 'Necesita que $f(x_{i-1})=f(x_i)$ para arrancar'
---

Programa el método de la **secante** en `secante`.

```python
def secante(f, x0, x1, tol=1e-6, max_iter=100):
```

$$x_{i+1} = x_i - \frac{f(x_i)(x_{i-1}-x_i)}{f(x_{i-1})-f(x_i)}$$

Parte de **dos** valores iniciales `x0`, `x1`. Criterio de paro: error relativo aproximado **en fracción**. Devuelve `(raiz, n_iteraciones)`. Si `f(x0) == f(x1)` debes evitar la división entre cero.
