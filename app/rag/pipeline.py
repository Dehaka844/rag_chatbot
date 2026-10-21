"""Pipeline RAG basado en documentos locales y Qdrant."""

from __future__ import annotations

from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient

from app.core.config import QDRANT_URL, RAG_CONFIG


class PipelineRAG:
    """Carga, divide, indexa y recupera documentos de RRHH."""

    def __init__(self, directorio_docs: str):
        """Prepara los clientes y la configuración del pipeline.

        ``OPENAI_API_KEY`` debe estar disponible en el entorno. El nombre de
        cada archivo (sin extensión) se usa como categoría del documento.
        """
        self.directorio_docs = Path(directorio_docs).expanduser().resolve()
        self.collection_name = RAG_CONFIG["collection_name"]
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=RAG_CONFIG["chunk_size"],
            chunk_overlap=RAG_CONFIG["chunk_overlap"],
        )
        self._client = QdrantClient(url=QDRANT_URL)
        self._vectorstore: QdrantVectorStore | None = None

        if self._client.collection_exists(self.collection_name):
            self._vectorstore = QdrantVectorStore(
                client=self._client,
                collection_name=self.collection_name,
                embedding=self.embeddings,
            )

    def _cargar_documentos(self) -> list[Document]:
        """Lee los .txt y adjunta metadata de archivo, categoría y origen."""
        if not self.directorio_docs.is_dir():
            raise FileNotFoundError(
                f"No existe el directorio de documentos: {self.directorio_docs}"
            )

        documentos = []
        for ruta in sorted(self.directorio_docs.glob("*.txt")):
            texto = ruta.read_text(encoding="utf-8").strip()
            if not texto:
                continue
            documentos.append(
                Document(
                    page_content=texto,
                    metadata={
                        "filename": ruta.name,
                        "category": ruta.stem,
                        "source": str(ruta.resolve()),
                    },
                )
            )
        return documentos

    @staticmethod
    def _id_chunk(documento: Document, indice: int) -> str:
        """Crea un ID estable para actualizar chunks sin duplicarlos."""
        clave = f"{documento.metadata['source']}:{indice}"
        return str(uuid5(NAMESPACE_URL, clave))

    def indexar_documentos(self) -> int:
        """Indexa los documentos locales y devuelve la cantidad de chunks."""
        documentos = self._cargar_documentos()
        chunks = self.splitter.split_documents(documentos)
        if not chunks:
            return 0

        ids = []
        indices_por_origen: dict[str, int] = {}
        for chunk in chunks:
            origen = chunk.metadata["source"]
            indice = indices_por_origen.get(origen, 0)
            indices_por_origen[origen] = indice + 1
            ids.append(self._id_chunk(chunk, indice))

        if self._vectorstore is None:
            self._vectorstore = QdrantVectorStore.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                url=QDRANT_URL,
                collection_name=self.collection_name,
                ids=ids,
            )
        else:
            self._vectorstore.add_documents(documents=chunks, ids=ids)

        return len(chunks)

    def buscar_contexto(self, query: str, k: int = 3) -> str:
        """Devuelve los fragmentos más relevantes como contexto legible."""
        if k < 1:
            raise ValueError("k debe ser un entero mayor que cero")
        if not query or not query.strip() or self._vectorstore is None:
            return ""

        resultados = self._vectorstore.similarity_search(query.strip(), k=k)
        partes = []
        for numero, documento in enumerate(resultados, start=1):
            metadata = documento.metadata
            partes.append(
                f"[Fragmento {numero} | Archivo: {metadata.get('filename', 'desconocido')}"
                f" | Categoría: {metadata.get('category', 'sin categoría')}"
                f" | Origen: {metadata.get('source', 'desconocido')}]\n"
                f"{documento.page_content}"
            )
        return "\n\n".join(partes)
