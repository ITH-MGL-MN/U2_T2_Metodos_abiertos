---
id: paracaidista
titulo: "Paracaidista: Coeficiente de arrastre"
incognita: "c"
unidad: "kg/s"
mano: true
rangos:
  m: [60.0, 82.0, 1]   # [mínimo, máximo, decimales]
  t: [8.0, 12.0, 1]
  v: [36.0, 44.0, 1]
  x0: [5.0, 7.0, 1]
---

Un paracaidista de masa **$m = {m}\text{ kg}$** salta desde el reposo. 
Tras **$t = {t}\text{ s}$** su velocidad es **$v = {v}\text{ m/s}$**.

El modelo físico de caída libre con resistencia del aire está dado por:

$$v = \frac{g m}{c}\left(1 - e^{-c\,t/m}\right)$$

donde $g = 9.81\text{ m/s}^2$. 

Pasando todo a un lado, la ecuación que se resuelve es $f(c) = \dfrac{g m}{c}\left(1 - e^{-c\,t/m}\right) - v = 0$.

Determina el **coeficiente de arrastre $c$** necesario para alcanzar dicha velocidad.
