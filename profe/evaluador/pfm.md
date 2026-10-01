---
metodo: PFM
funcion: pfm
firma: "pfm(g, x0, lam, tol=1e-6, max_iter=100)"
ejemplo: "pfm(EJ_PFM['g'], EJ_PFM['x0'], EJ_PFM['lam'], tol={tol})"
concepto:
  correcta: 0
  opciones:
    - 'La sub-relajación ($0<\lambda<1$) puede estabilizar un despeje que oscila'
    - 'Siempre aumenta el número de iteraciones, nunca lo reduce'
    - '$\lambda$ debe ser mayor que 2 para que converja'
    - 'Cambia la raíz del problema: da otra solución'
---

Programa el **punto fijo con relajación** en `pfm`.

```python
def pfm(g, x0, lam, tol=1e-6, max_iter=100):
```
$$x_{i+1} = \lambda*g(x_i) + (1-\lambda)*x_i$$

Devuelve (`raiz`, `n_iter`).

Es decir $x_{i+1}=\lambda\,g(x_i)+(1-\lambda)x_i$. Con `lam=1` debe ser **idéntico** a `pf`. Criterio de paro igual que en `pf` (error relativo aproximado **en fracción**). Devuelve `(raiz, n_iteraciones)`.
