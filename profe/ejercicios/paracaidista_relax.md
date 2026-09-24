---
id: paracaidista_relax
titulo: "Paracaidista: sobre-relajación para acelerar"
incognita: "c"
unidad: "kg/s"
mano: true
rangos:
  m: [60.0, 82.0, 1]
  t: [8.0, 12.0, 1]
  v: [36.0, 44.0, 1]
  x0: [5.0, 7.0, 1]
  lam: [1.1, 1.3, 2]
---

El coeficiente de arrastre $c$ del paracaidista ($m = {m}\text{ kg}$, $t = {t}\text{ s}$, $v = {v}\text{ m/s}$) se obtiene del despeje:

$$c = \frac{g m}{v}\left(1 - e^{-c t / m}\right)$$

Dado que este despeje es lento, aplica **sobre-relajación** con **$\lambda = {lam}$** partiendo de **$c_0 = {x0}$**.
