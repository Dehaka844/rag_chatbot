"""Configuracion central de la aplicacion."""

import os

from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """
Eres el asistente virtual de Recursos Humanos de TechVentures Inc.
""".strip()

RAG_CONFIG = {
    "chunk_size": 1000,
    "chunk_overlap": 150,
    "k": 3,
    "collection_name": os.getenv("QDRANT_COLLECTION", "rrhh_documents"),
}

MODEL_CONFIG = {
    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "temperature": 0.2,
    "max_tokens": 700,
}

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "rrhh_chatbot"),
    "user": os.getenv("POSTGRES_USER", "rrhh_user"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}
