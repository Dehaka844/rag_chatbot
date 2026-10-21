from unittest.mock import Mock, patch

from app.chat.service import ChatbotRRHH
from app.cli.interface import main


def test_cli_procesa_comandos_y_consultas(capsys):
    chatbot = ChatbotRRHH.__new__(ChatbotRRHH)
    chatbot.generar_respuesta = Mock(return_value="Respuesta de prueba")
    chatbot.reset_conversacion = Mock()

    with patch("builtins.input", side_effect=["/ayuda", "/reset", "Hola", "/salir"]):
        main(chatbot)

    chatbot.reset_conversacion.assert_called_once_with()
    chatbot.generar_respuesta.assert_called_once_with("Hola")
    salida = capsys.readouterr().out
    assert "Comandos disponibles" in salida
    assert "Respuesta de prueba" in salida
    assert "Hasta luego" in salida
