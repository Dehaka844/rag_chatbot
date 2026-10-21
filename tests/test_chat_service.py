from unittest.mock import Mock, patch

import pytest

from app.chat.service import (
    RESPUESTA_FUERA_DE_AMBITO,
    RESPUESTA_SENSIBLE,
    ChatbotRRHH,
)


class FakeMemory:
    def __init__(self, **kwargs):
        self.messages = []

    def agregar_mensaje(self, rol, contenido):
        self.messages.append({"rol": rol, "contenido": contenido})

    def obtener_ventana_contexto(self):
        return self.messages[-10:]

    def limpiar(self):
        self.messages.clear()


class FakeResponse:
    def __init__(self, content):
        self.content = content


def crear_chatbot_de_prueba(respuestas):
    pipeline = Mock()
    llm = Mock()
    llm.invoke.side_effect = [FakeResponse(respuesta) for respuesta in respuestas]
    with (
        patch("app.chat.service.MemoriaConversacion", FakeMemory),
        patch("app.chat.service.ChatOpenAI", return_value=llm),
    ):
        chatbot = ChatbotRRHH(pipeline, {"model": "modelo-test"})
    return chatbot, pipeline, llm


def test_tema_sensible_se_escala_y_no_consulta_rag():
    chatbot, pipeline, llm = crear_chatbot_de_prueba([])

    respuesta = chatbot.generar_respuesta("Quiero reportar acoso de mi jefe")

    assert respuesta == RESPUESTA_SENSIBLE
    pipeline.buscar_contexto.assert_not_called()
    llm.invoke.assert_not_called()


def test_consulta_fuera_de_ambito_se_rechaza_amablemente():
    chatbot, pipeline, llm = crear_chatbot_de_prueba(["FUERA"])

    respuesta = chatbot.generar_respuesta("¿Cuál es la mejor pizzería?")

    assert respuesta == RESPUESTA_FUERA_DE_AMBITO
    pipeline.buscar_contexto.assert_not_called()
    assert llm.invoke.call_count == 1


def test_consulta_rrhh_combina_clasificacion_contexto_y_respuesta():
    chatbot, pipeline, llm = crear_chatbot_de_prueba(["RRHH", "Tienes 15 días de vacaciones."])
    pipeline.buscar_contexto.return_value = "0-2 años: 15 días al año"

    respuesta = chatbot.generar_respuesta("¿Cuántos días de vacaciones tengo?")

    assert respuesta == "Tienes 15 días de vacaciones."
    pipeline.buscar_contexto.assert_called_once()
    assert llm.invoke.call_count == 2
    assert chatbot.memoria.messages[-1]["rol"] == "assistant"


@pytest.mark.parametrize("mensaje", ["", " ", "??"])
def test_mensajes_vacios_o_muy_cortos_no_llaman_al_modelo(mensaje):
    chatbot, pipeline, llm = crear_chatbot_de_prueba([])

    respuesta = chatbot.generar_respuesta(mensaje)

    assert respuesta
    pipeline.buscar_contexto.assert_not_called()
    llm.invoke.assert_not_called()
