"""Interfaz interactiva de línea de comandos."""

from __future__ import annotations

import logging

from app.chat.service import ChatbotRRHH

logger = logging.getLogger(__name__)

_AYUDA = """Comandos disponibles:
  /ayuda  Muestra esta ayuda.
  /reset  Borra el historial de esta conversación.
  /salir  Cierra el asistente.

Escribe tu consulta de Recursos Humanos y pulsa Intro para enviarla."""


def main(chatbot: ChatbotRRHH) -> None:
    """Ejecuta el bucle de conversación usando el chatbot recibido."""
    if not isinstance(chatbot, ChatbotRRHH):
        raise TypeError("chatbot debe ser una instancia de ChatbotRRHH")

    print("¡Hola! Soy el asistente de Recursos Humanos de TechVentures Inc.")
    print("Escribe /ayuda para ver los comandos disponibles.")

    while True:
        try:
            mensaje = input("Tú> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            return

        if not mensaje:
            continue

        comando = mensaje.casefold()
        if comando == "/salir":
            print("Hasta luego.")
            return
        if comando == "/ayuda":
            print(_AYUDA)
            continue
        if comando == "/reset":
            try:
                chatbot.reset_conversacion()
                print("Asistente> He borrado el historial de esta conversación.")
            except Exception:
                logger.exception("No se pudo reiniciar la conversación")
                print("Asistente> No he podido reiniciar la conversación. Inténtalo de nuevo.")
            continue

        try:
            respuesta = chatbot.generar_respuesta(mensaje)
            print(f"Asistente> {respuesta}")
        except KeyboardInterrupt:
            print("\nHasta luego.")
            return
        except Exception:
            # Una consulta fallida no debe cerrar el bucle interactivo.
            logger.exception("Error puntual al procesar la consulta")
            print("Asistente> No he podido procesar tu consulta. Inténtalo de nuevo.")
