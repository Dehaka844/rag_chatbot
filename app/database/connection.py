"""Creacion de conexiones PostgreSQL."""

import psycopg

from app.core.config import POSTGRES_CONFIG


def crear_conexion() -> psycopg.Connection:
    """Crea y devuelve una conexion usando ``POSTGRES_CONFIG``.

    El llamador es responsable de cerrarla. Se puede usar como gestor de
    contexto (``with crear_conexion() as conexion``) para que psycopg gestione
    el cierre y la transaccion al salir del bloque.
    """
    return psycopg.connect(**POSTGRES_CONFIG)
