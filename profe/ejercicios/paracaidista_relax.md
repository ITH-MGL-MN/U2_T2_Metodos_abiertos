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

Un paracaidista de masa $m = {m}\text{ kg}$ alcanza una velocidad $v = {v}\text{ m/s}$ tras
caer $t = {t}\text{ s}$ (usa $g = 9.81\text{ m/s}^2$). El modelo físico es

$$v = \frac{g m}{c}\left(1 - e^{-c t / m}\right),$$

que pasada toda a un lado queda

$$f(c) = \frac{g m}{c}\left(1 - e^{-c t / m}\right) - v = 0,$$

y su despeje equivalente es

$$c = g(c) = \frac{g m}{v}\left(1 - e^{-c t / m}\right).$$

Dado que este despeje converge lento, aplica **sobre-relajación** con
**$\lambda = {lam}$** partiendo de **$c_0 = {x0}$**.
