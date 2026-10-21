"""Memoria conversacional respaldada por PostgreSQL."""

from uuid import UUID, uuid4

from app.database.connection import crear_conexion


class MemoriaConversacion:
    """Persiste el historial completo y expone una ventana para el contexto."""

    def __init__(self, max_mensajes: int = 10, conversation_id: str | UUID | None = None):
        """Inicializa la memoria y carga el historial de la conversación indicada.

        Si no se proporciona ``conversation_id``, se crea una conversación nueva.
        El identificador puede conservarse para reanudarla en otra instancia.
        """
        if not isinstance(max_mensajes, int) or isinstance(max_mensajes, bool) or max_mensajes <= 0:
            raise ValueError("max_mensajes debe ser un entero mayor que cero")

        self.max_mensajes = max_mensajes
        self.conversation_id = UUID(str(conversation_id)) if conversation_id else uuid4()
        self._crear_estructura()

    def _crear_estructura(self) -> None:
        """Crea la tabla de mensajes si todavía no existe."""
        with crear_conexion() as conexion:
            conexion.execute(
                """
                CREATE TABLE IF NOT EXISTS mensajes_conversacion (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    conversation_id UUID NOT NULL,
                    rol TEXT NOT NULL CHECK (rol IN ('user', 'assistant')),
                    contenido TEXT NOT NULL,
                    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conexion.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mensajes_conversacion_fecha
                ON mensajes_conversacion (conversation_id, creado_en, id)
                """
            )

    def agregar_mensaje(self, rol: str, contenido: str) -> None:
        """Guarda un mensaje de usuario o asistente en esta conversación."""
        if rol not in ("user", "assistant"):
            raise ValueError("rol debe ser 'user' o 'assistant'")
        if not isinstance(contenido, str) or not contenido.strip():
            raise ValueError("contenido debe ser un texto no vacío")

        with crear_conexion() as conexion:
            conexion.execute(
                """
                INSERT INTO mensajes_conversacion (conversation_id, rol, contenido)
                VALUES (%s, %s, %s)
                """,
                (self.conversation_id, rol, contenido),
            )

    def obtener_historial(self) -> list[dict[str, str]]:
        """Devuelve todos los mensajes persistidos en orden cronológico."""
        with crear_conexion() as conexion:
            filas = conexion.execute(
                """
                SELECT rol, contenido
                FROM mensajes_conversacion
                WHERE conversation_id = %s
                ORDER BY creado_en ASC, id ASC
                """,
                (self.conversation_id,),
            ).fetchall()
        return [{"rol": rol, "contenido": contenido} for rol, contenido in filas]

    def obtener_ventana_contexto(self) -> list[dict[str, str]]:
        """Devuelve únicamente los últimos mensajes configurados para el modelo."""
        return self.obtener_historial()[-self.max_mensajes :]

    def formatear_para_prompt(self) -> str:
        """Formatea la ventana reciente como texto para incorporarla al prompt."""
        etiquetas = {"user": "Usuario", "assistant": "Asistente"}
        return "\n".join(
            f"{etiquetas[mensaje['rol']]}: {mensaje['contenido']}"
            for mensaje in self.obtener_ventana_contexto()
        )

    def limpiar(self) -> None:
        """Elimina los mensajes de esta conversación y conserva su identificador."""
        with crear_conexion() as conexion:
            conexion.execute(
                "DELETE FROM mensajes_conversacion WHERE conversation_id = %s",
                (self.conversation_id,),
            )
