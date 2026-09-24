# -*- coding: utf-8 -*-
"""
profe/ui/widgets.py — Interfaz visual gráfica e interactiva para Google Colab.
"""
import sys
from IPython.display import display, HTML, Markdown
import ipywidgets as widgets

class InterfazTarea(object):
    """
    Despliega la tarea interactiva en el Notebook de Google Colab.
    """
    def __init__(self, tarea, marco_evaluacion=None):
        self.tarea = tarea
        self.marco = marco_evaluacion or sys._getframe(1)
        self.controles = {}
        self.out_feedback = widgets.Output()
        
    def mostrar(self):
        """Renderiza todas las preguntas y el botón de envío en Colab."""
        print("=" * 70)
        print(f" 📝 {self.tarea.cfg['tarea']['nombre']}")
        print(f" 👤 Alumno: {self.tarea.alumno_id} | NC: {self.tarea.nc}")
        print("=" * 70 + "\n")

        componentes = []

        for idx, p in enumerate(self.tarea.preguntas, 1):
            box_p = self._crear_pregunta_widget(idx, p)
            componentes.append(box_p)

        # Botón de Calificación y Envío
        btn_enviar = widgets.Button(
            description="🚀 Calificar y Enviar Tarea",
            button_style="success",
            icon="paper-plane",
            layout=widgets.Layout(width="280px", height="45px", margin="20px 0px 10px 0px")
        )
        btn_enviar.on_click(self._on_click_enviar)

        display(widgets.VBox(componentes))
        display(btn_enviar)
        display(self.out_feedback)

    def _crear_pregunta_widget(self, idx, p):
        """Construye la tarjeta visual para una pregunta específica."""
        tipo = p['tipo']
        html_titulo = f"<b>Pregunta {idx}: {p['titulo']}</b>"
        lbl_titulo = widgets.HTML(value=html_titulo)
        lbl_texto = widgets.Output()

        with lbl_texto:
            display(Markdown(p['texto']))

        if tipo == 'opcion':
            control = widgets.RadioButtons(
                options=p['opciones'],
                index=None,
                layout=widgets.Layout(width="100%")
            )
        elif tipo == 'simple':
            control = widgets.Text(
                placeholder="Escribe tu respuesta numérica aquí...",
                layout=widgets.Layout(width="300px")
            )
        elif tipo == 'funcion':
            control = widgets.HTML(
                value=f"<i>💡 Esta pregunta evalúa la función <code>{p['funcion']}</code> que programaste en tu código.</i>"
            )
        else:
            control = widgets.Label(value="Tipo de pregunta no soportado.")

        self.controles[idx] = (tipo, control)

        tarjeta = widgets.VBox(
            [lbl_titulo, lbl_texto, control],
            layout=widgets.Layout(
                border="1px solid #d0d0d0",
                padding="12px",
                margin="0px 0px 15px 0px",
                border_radius="8px",
                background_color="#fdfdfd"
            )
        )
        return tarjeta

    def _recopilar_respuestas(self):
        """Extrae los valores ingresados por el alumno en la interfaz."""
        respuestas = {}
        for idx, (tipo, ctrl) in self.controles.items():
            if tipo == 'opcion':
                val = ctrl.value
                if val is not None:
                    # 'a) ...' -> 0, 'b) ...' -> 1, ... (o el índice, si ya es número)
                    if isinstance(val, (int, float)):
                        respuestas[idx] = float(val)
                    else:
                        respuestas[idx] = float(ord(str(val).strip().lower()[0]) - 97)
            elif tipo == 'simple':
                val = ctrl.value.strip()
                if val:
                    try:
                        respuestas[idx] = float(val)
                    except ValueError:
                        respuestas[idx] = val
            elif tipo == 'funcion':
                respuestas[idx] = "EVALUAR_CODIGO"
        return respuestas

    def _on_click_enviar(self, b):
        """Manejador de evento al presionar el botón de Calificar."""
        self.out_feedback.clear_output()

        with self.out_feedback:
            respuestas = self._recopilar_respuestas()
            filas_res = self.tarea.calificar(respuestas, self.marco)

            puntos_obtenidos = sum(f['puntos'] for f in filas_res)
            puntos_maximos = sum(f['peso'] for f in filas_res)
            calif = (puntos_obtenidos / puntos_maximos * 100.0) if puntos_maximos > 0 else 0.0

            # Renderizar tabla de resultados en HTML
            html_tabla = """
            <table style="width:100%; border-collapse: collapse; margin-top: 15px;">
              <thead>
                <tr style="background-color: #f2f2f2; text-align: left;">
                  <th style="padding: 8px; border: 1px solid #ddd;">#</th>
                  <th style="padding: 8px; border: 1px solid #ddd;">Estado</th>
                  <th style="padding: 8px; border: 1px solid #ddd;">Puntos</th>
                  <th style="padding: 8px; border: 1px solid #ddd;">Detalle</th>
                </tr>
              </thead>
              <tbody>
            """

            for f in filas_res:
                est = f['estado']
                color = "#28a745" if est == 'correcta' else ("#ffc107" if est == 'parcial' else "#dc3545")
                badge = f"<span style='color: white; background-color: {color}; padding: 3px 8px; border-radius: 4px; font-weight: bold;'>{est.upper()}</span>"
                
                html_tabla += f"""
                <tr>
                  <td style="padding: 8px; border: 1px solid #ddd;"><b>{f['i']}</b></td>
                  <td style="padding: 8px; border: 1px solid #ddd;">{badge}</td>
                  <td style="padding: 8px; border: 1px solid #ddd;">{f['puntos']:.1f} / {f['peso']:.1f}</td>
                  <td style="padding: 8px; border: 1px solid #ddd;">Respuesta: {f['val']}</td>
                </tr>
                """

            html_tabla += f"""
              </tbody>
            </table>
            <h3 style="margin-top: 15px;">Calificación Final: <span style="color: #0056b3;">{calif:.1f} / 100</span></h3>
            """

            display(HTML(html_tabla))

            # Intentar envío a Google Sheets por Apps Script
            print("\nEnviando calificación a la hoja de registro oficial...")
            res = self.tarea.enviar(respuestas, self.marco)
            if res.get('motivo') == 'minimo':
                print('\u26d4 A\u00fan no puedes enviar: necesitas al menos %g %% (%g puntos).'
                      % (res['minimo'], self.tarea.min_aprobacion * res['maximo']))
            elif res['enviado']:
                print('\u2705 Enviado. Respuesta del servidor: %s' % res['respuesta'][:300])
            else:
                print('\u26a0\ufe0f No se pudo enviar: %s' % res.get('error'))
