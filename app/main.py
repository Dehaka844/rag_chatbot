"""Punto de entrada y composición de la aplicación."""

from __future__ import annotations

from pathlib import Path

from app.chat.service import ChatbotRRHH
from app.cli.interface import main as ejecutar_cli
from app.core.config import MODEL_CONFIG
from app.rag.pipeline import PipelineRAG


RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
DIRECTORIO_DOCUMENTOS = RAIZ_PROYECTO / "documentos"


def crear_chatbot(directorio_documentos: Path = DIRECTORIO_DOCUMENTOS) -> ChatbotRRHH:
    """Construye el pipeline RAG y el motor de chat de la aplicación.

    La indexación utiliza identificadores estables en ``PipelineRAG``, por lo
    que este paso puede ejecutarse al arrancar sin crear duplicados lógicos en
    Qdrant.
    """
    pipeline_rag = PipelineRAG(str(directorio_documentos))
    pipeline_rag.indexar_documentos()
    return ChatbotRRHH(pipeline_rag=pipeline_rag, config=MODEL_CONFIG.copy())


def main() -> None:
    """Construye las dependencias y arranca la interfaz CLI."""
    chatbot = crear_chatbot()
    ejecutar_cli(chatbot)


if __name__ == "__main__":
    main()
