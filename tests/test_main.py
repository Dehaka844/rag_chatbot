from unittest.mock import Mock, patch

from app import main as modulo_main


def test_crear_chatbot_indexa_documentos_y_construye_motor(tmp_path):
    pipeline = Mock()
    chatbot = Mock()

    with (
        patch.object(modulo_main, "PipelineRAG", return_value=pipeline) as pipeline_cls,
        patch.object(modulo_main, "ChatbotRRHH", return_value=chatbot) as chatbot_cls,
    ):
        resultado = modulo_main.crear_chatbot(tmp_path)

    assert resultado is chatbot
    pipeline_cls.assert_called_once_with(str(tmp_path))
    pipeline.indexar_documentos.assert_called_once_with()
    chatbot_cls.assert_called_once()


def test_main_entrega_el_chatbot_a_la_cli():
    chatbot = Mock()

    with (
        patch.object(modulo_main, "crear_chatbot", return_value=chatbot) as crear,
        patch.object(modulo_main, "ejecutar_cli") as ejecutar_cli,
    ):
        modulo_main.main()

    crear.assert_called_once_with()
    ejecutar_cli.assert_called_once_with(chatbot)
