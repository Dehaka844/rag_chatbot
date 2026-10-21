"""Motor principal del chatbot de RRHH."""

from __future__ import annotations

import logging
import unicodedata

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import MODEL_CONFIG, RAG_CONFIG, SYSTEM_PROMPT
from app.memory.conversation import MemoriaConversacion

logger = logging.getLogger(__name__)

RESPUESTA_SENSIBLE = (
    "Tu consulta requiere atención personalizada. Por favor, contacta con el "
    "equipo de Recursos Humanos o con el canal interno adecuado."
)
RESPUESTA_FUERA_DE_AMBITO = (
    "Solo puedo ayudar con consultas relacionadas con Recursos Humanos y el "
    "ámbito laboral de TechVentures Inc."
)
RESPUESTA_ERROR = (
    "No he podido procesar tu consulta en este momento. Inténtalo de nuevo más tarde."
)

# Expresiones que suelen indicar situaciones que requieren atención humana.
# Se comparan después de quitar acentos y convertir el texto a minúsculas.
_TEMAS_SENSIBLES = (
    "acoso",
    "hostigamiento",
    "discriminacion",
    "violencia",
    "abuso",
    "amenaza",
    "autolesion",
    "suicidio",
    "quitarme la vida",
    "salud mental",
    "diagnostico medico",
    "historial medico",
    "embarazo",
    "orientacion sexual",
    "religion",
    "numero de seguridad social",
    "datos bancarios",
    "salario de mi companero",
    "salario de mi compañero",
)


def _normalizar(texto: str) -> str:
    """Pasa el texto a minúsculas y elimina marcas diacríticas."""
    descompuesto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(caracter for caracter in descompuesto if not unicodedata.combining(caracter))


class ChatbotRRHH:
    """Coordina RAG, memoria, reglas de seguridad y el LLM."""

    def __init__(self, pipeline_rag, config: dict):
        """Inicializa el chatbot con un pipeline RAG y configuración opcional.

        ``config`` puede sobrescribir ``model``, ``temperature`` y ``max_tokens``
        del modelo, e incluir ``conversation_id`` y ``max_mensajes`` para la
        memoria conversacional.
        """
        if pipeline_rag is None:
            raise ValueError("pipeline_rag es obligatorio")
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise TypeError("config debe ser un diccionario")

        self.pipeline_rag = pipeline_rag
        self.config = config.copy()
        memoria_config = {
            clave: self.config[clave]
            for clave in ("max_mensajes", "conversation_id")
            if clave in self.config
        }
        self.memoria = MemoriaConversacion(**memoria_config)

        parametros_modelo = MODEL_CONFIG.copy()
        parametros_modelo.update(
            {
                clave: self.config[clave]
                for clave in ("model", "temperature", "max_tokens", "api_key", "base_url")
                if clave in self.config
            }
        )
        self.llm = ChatOpenAI(**parametros_modelo)

    def es_tema_sensible(self, mensaje: str) -> bool:
        """Detecta menciones sensibles que requieren intervención humana."""
        if not isinstance(mensaje, str) or not mensaje.strip():
            return False
        mensaje_normalizado = _normalizar(mensaje)
        return any(tema in mensaje_normalizado for tema in _TEMAS_SENSIBLES)

    def _es_consulta_rrhh(self, mensaje: str) -> bool:
        """Clasifica la consulta antes de recuperar documentos internos."""
        prompt_clasificacion = (
            "Clasifica el mensaje del usuario según su ámbito. Considera RRHH las "
            "consultas sobre empleo, políticas laborales, nómina, beneficios, "
            "onboarding, vacaciones, permisos, formación y procesos de personal. "
            "Responde únicamente RRHH o FUERA. Si hay duda razonable sobre una "
            "relación con el trabajo, responde RRHH.\n\n"
            f"Mensaje: {mensaje}"
        )
        resultado = self.llm.invoke([HumanMessage(content=prompt_clasificacion)])
        etiqueta = _normalizar(str(resultado.content)).strip().rstrip(".")
        return etiqueta == "rrhh" or etiqueta.startswith("rrhh\n")

    def _persistir_respuesta(self, respuesta: str) -> None:
        """Guarda la respuesta del asistente mediante la capa de memoria."""
        self.memoria.agregar_mensaje("assistant", respuesta)

    def generar_respuesta(self, mensaje_usuario: str) -> str:
        """Genera una respuesta combinando RAG, memoria y LLM."""
        if not isinstance(mensaje_usuario, str) or not mensaje_usuario.strip():
            return "Escribe una consulta para que pueda ayudarte."

        mensaje = mensaje_usuario.strip()
        if len(mensaje) < 3:
            respuesta = "Tu consulta es demasiado corta. Añade algo más de contexto, por favor."
            try:
                self.memoria.agregar_mensaje("user", mensaje)
                self._persistir_respuesta(respuesta)
            except Exception:
                logger.exception("No se pudo guardar la consulta demasiado corta")
                return RESPUESTA_ERROR
            return respuesta

        try:
            # Se guarda antes de procesar para conservar también consultas que
            # terminen en una ruta de rechazo o en un error del modelo.
            self.memoria.agregar_mensaje("user", mensaje)
            if self.es_tema_sensible(mensaje):
                respuesta = RESPUESTA_SENSIBLE
                self._persistir_respuesta(respuesta)
                return respuesta

            if not self._es_consulta_rrhh(mensaje):
                respuesta = RESPUESTA_FUERA_DE_AMBITO
                self._persistir_respuesta(respuesta)
                return respuesta

            contexto = self.pipeline_rag.buscar_contexto(
                mensaje,
                k=RAG_CONFIG["k"],
            )
            historial = self.memoria.obtener_ventana_contexto()
            mensajes = [SystemMessage(content=SYSTEM_PROMPT)]
            mensajes.append(
                SystemMessage(
                    content=(
                        "Responde de forma segura y precisa. Usa el contexto documental "
                        "para las políticas de la empresa. Si el contexto no contiene "
                        "la respuesta, dilo claramente y no inventes políticas."
                    )
                )
            )
            if contexto:
                mensajes.append(
                    SystemMessage(content=f"Contexto recuperado del repositorio:\n{contexto}")
                )
            for entrada in historial:
                if entrada["rol"] == "user":
                    mensajes.append(HumanMessage(content=entrada["contenido"]))
                else:
                    mensajes.append(AIMessage(content=entrada["contenido"]))

            resultado = self.llm.invoke(mensajes)
            respuesta = str(resultado.content).strip()
            if not respuesta:
                raise ValueError("El modelo devolvió una respuesta vacía")

            self._persistir_respuesta(respuesta)
            return respuesta
        except Exception:
            logger.exception("Error al generar o persistir la respuesta del chatbot")
            try:
                self._persistir_respuesta(RESPUESTA_ERROR)
            except Exception:
                logger.exception("No se pudo guardar el mensaje de error")
            return RESPUESTA_ERROR

    def reset_conversacion(self):
        """Elimina el historial actual conservando el identificador."""
        self.memoria.limpiar()
