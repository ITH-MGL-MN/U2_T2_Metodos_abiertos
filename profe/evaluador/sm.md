---
metodo: SM
funcion: secmod
firma: "secmod(f, x0, delta=0.01, tol=1e-6, max_iter=100)"
ejemplo: "secmod(EJ_SM['f'], EJ_SM['x0'], EJ_SM['delta'], tol={tol})"
concepto:
  correcta: 0
  opciones:
    - 'Si $\delta$ es demasiado pequeño, el cociente sufre error de cancelación'
    - '$\delta$ debe ser exactamente el valor de la derivada en $x_i$'
    - 'El método necesita dos puntos iniciales separados'
    - '$\delta$ no influye en el resultado: da igual su valor'
---

Programa la **secante modificada** en `secmod`.

```python
def secmod(f, x0, delta=0.01, tol=1e-6, max_iter=100):
    """x_{i+1} = x_i - delta*f(x_i)/(f(x_i+delta)-f(x_i))."""
```

Usa un **solo** valor inicial y aproxima la derivada con el incremento `delta` (un incremento **fijo**, no un porcentaje de $x_i$). Criterio de paro: error relativo aproximado **en fracción**. Devuelve `(raiz, n_iteraciones)`. Evita dividir entre cero.
