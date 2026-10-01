---
id: diodo
titulo: "Diodo: tensión de operación"
incognita: "V"
unidad: "V"
mano: true
rangos:
  Vcc: [4.5, 6.0, 1]
  R: [900.0, 1200.0, 0]
---

En un circuito serie con **$V_{CC} = {Vcc}\text{ V}$** y **$R = {R}\ \Omega$** hay un diodo con $I_s = 10^{-12}\text{ A}$ y $n V_T = 0.05\text{ V}$. 

La corriente del diodo satisface $I = I_s\left(e^{V / n V_T} - 1\right)$ y, como la resistencia está en serie, también $I = (V_{CC} - V)/R$. Juntando ambas y pasando todo a un lado, se resuelve

$$f(V) = I_s\left(e^{V / n V_T} - 1\right) - \frac{V_{CC} - V}{R} = 0.$$

Partiendo de **$V_0 = 1.0\text{ V}$**, halla la tensión $V$ del diodo.
