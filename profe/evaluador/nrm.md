---
metodo: NRM
funcion: nrm
firma: "nrm(f, df, ddf, x0, tol=1e-6, max_iter=100)"
ejemplo: "nrm(EJ_NRM['f'], EJ_NRM['df'], EJ_NRM['ddf'], EJ_NRM['x0'], tol={tol})"
concepto:
  correcta: 0
  opciones:
    - 'En una raíz múltiple $f^{\prime}(x^*)=0$ y Newton-Raphson se vuelve lento (lineal)'
    - 'Newton-Raphson es más rápido precisamente en raíces múltiples'
    - 'La raíz múltiple no existe: $f$ tiene siempre raíces simples'
    - 'El método modificado solo sirve para polinomios de grado 2'
---

Programa **Newton-Raphson modificado** (fórmula de Ralston-Rabinowitz) para raíces múltiples en `nrm`.

```python
def nrm(f, df, ddf, x0, tol=1e-6, max_iter=100):
```
$$x_{i+1} = x_i - \frac{f f'}{(f')^2 - f f''}$$

Devuelve (`raiz`, `n_iter`).

`df` y `ddf` son la primera y la segunda derivada de `f`. Criterio de paro: error relativo aproximado **en fracción**. Devuelve `(raiz, n_iteraciones)`. Protege el denominador nulo.
