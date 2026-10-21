from pathlib import Path

from langchain_core.documents import Document

from app.rag.pipeline import PipelineRAG


def test_id_de_chunk_es_estable():
    documento = Document(
        page_content="Contenido",
        metadata={"source": str(Path("documentos/beneficios.txt"))},
    )

    primero = PipelineRAG._id_chunk(documento, 0)
    segundo = PipelineRAG._id_chunk(documento, 0)
    diferente = PipelineRAG._id_chunk(documento, 1)

    assert primero == segundo
    assert primero != diferente


def test_carga_documentos_asigna_metadata(tmp_path):
    ruta = tmp_path / "beneficios.txt"
    ruta.write_text("Seguro médico y vacaciones", encoding="utf-8")
    pipeline = PipelineRAG.__new__(PipelineRAG)
    pipeline.directorio_docs = tmp_path

    documentos = pipeline._cargar_documentos()

    assert len(documentos) == 1
    assert documentos[0].metadata["filename"] == "beneficios.txt"
    assert documentos[0].metadata["category"] == "beneficios"
    assert documentos[0].page_content == "Seguro médico y vacaciones"
