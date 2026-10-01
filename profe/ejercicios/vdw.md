---
id: vdw
titulo: "Dióxido de carbono: volumen molar (van der Waals)"
incognita: "v"
unidad: "L/mol"
mano: true
rangos:
  T: [300.0, 330.0, 1]
  p: [80.0, 120.0, 0]
---

Se almacena $\text{CO}_2$ a **$T = {T}\text{ K}$** y **$p = {p}\text{ atm}$**. La ecuación de van der Waals es:

$$\left(p + \frac{a}{v^2}\right)(v - b) = R T$$

con $a = 3.592$, $b = 0.04267$ y $R = 0.08206$. Pasando todo a un lado, se resuelve

$$f(v) = \left(p + \frac{a}{v^2}\right)(v - b) - R T = 0.$$

Obtén el volumen molar $v$ partiendo del valor ideal $v_0 = R T / p$.
