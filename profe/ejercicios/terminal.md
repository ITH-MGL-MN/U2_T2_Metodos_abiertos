---
id: terminal
titulo: "Velocidad terminal de una esfera"
incognita: "v"
unidad: "m/s"
mano: true
rangos:
  m: [70.0, 90.0, 1]
---

Una esfera de masa **$m = {m}\text{ kg}$**, diámetro $D = 0.6\text{ m}$ y área frontal $A = 0.55\text{ m}^2$ cae en aire ($\rho = 1.2\text{ kg/m}^3$, $\mu = 1.8\times 10^{-5}\text{ Pa·s}$, $g = 9.81\text{ m/s}^2$). 

Su velocidad terminal satisface $v = \sqrt{\dfrac{2 m g}{\rho A C_d}}$, donde $C_d$ depende del número de Reynolds:

$$C_d = \frac{24}{Re} + \frac{6}{1 + \sqrt{Re}} + 0.4, \qquad Re = \frac{\rho v D}{\mu}.$$

Llevando todo a un lado queda $f(v) = \sqrt{\dfrac{2 m g}{\rho A C_d(v)}} - v = 0$, que no conviene derivar analíticamente: usa un método abierto **sin derivada** desde $v_0 = 40.0\text{ m/s}$.
