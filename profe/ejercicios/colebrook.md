---
id: colebrook
titulo: "Tubería: factor de fricción de Colebrook"
incognita: "f"
unidad: "(adimensional)"
mano: true
rangos:
  Re: [40000.0, 90000.0, 0]
  eps: [0.00003, 0.00012, 6]
  x0: [0.015, 0.03, 3]
---

Agua circula por una tubería de diámetro **$D = 0.05\text{ m}$** con rugosidad **$\varepsilon = {eps}\text{ m}$** y número de Reynolds **$Re = {Re}$**. 

El factor de fricción **$f$** satisface la ecuación implícita de Colebrook:

$$\frac{1}{\sqrt{f}} = -2 \log_{10}\left(\frac{\varepsilon}{3.7 D} + \frac{2.51}{Re \sqrt{f}}\right)$$

Pasando todo a un lado, se resuelve $f(x) = 0$ con $x$ el factor de fricción:

$$f(x) = \frac{1}{\sqrt{x}} + 2 \log_{10}\left(\frac{\varepsilon}{3.7 D} + \frac{2.51}{Re \sqrt{x}}\right) = 0.$$

Obtén el valor de $f$.
