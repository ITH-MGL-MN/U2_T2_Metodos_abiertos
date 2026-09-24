---
id: oscilatoria
titulo: "Divergencia oscilatoria y sub-relajación"
incognita: "x"
unidad: "mol/L"
mano: true
diverge: true
rangos:
  x0: [1.3, 1.9, 2]
  lam: [0.25, 0.35, 2]
---

La ecuación **$x^2 - x - 3 = 0$** admite el despeje **$x = 2x + 3 - x^2 = g(x)$**. 

Partiendo de **$x_0 = {x0}$**, la iteración simple oscila y crece. Aplica **sub-relajación** con **$\lambda = {lam}$** para estabilizar la convergencia.
