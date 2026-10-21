from unittest.mock import patch

import pytest

from app.memory.conversation import MemoriaConversacion


class FakeConnection:
    """Conexion minima para probar la memoria sin PostgreSQL."""

    rows = []
    executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None):
        normalized = " ".join(query.split()).upper()
        self.executed.append((normalized, params))

        if normalized.startswith("INSERT INTO MENSAJES_CONVERSACION"):
            conversation_id, rol, contenido = params
            FakeConnection.rows.append((conversation_id, rol, contenido))
        elif normalized.startswith("DELETE FROM MENSAJES_CONVERSACION"):
            conversation_id = params[0]
            FakeConnection.rows = [
                row for row in FakeConnection.rows if row[0] != conversation_id
            ]
        return self

    def fetchall(self):
        conversation_id = self.executed[-1][1][0]
        return [
            (rol, contenido)
            for cid, rol, contenido in FakeConnection.rows
            if cid == conversation_id
        ]


@pytest.fixture
def fake_database():
    FakeConnection.rows = []
    FakeConnection.executed = []
    with patch("app.memory.conversation.crear_conexion", FakeConnection):
        yield


def test_memoria_persiste_historial_y_limita_ventana(fake_database):
    memoria = MemoriaConversacion(max_mensajes=2)
    memoria.agregar_mensaje("user", "Primero")
    memoria.agregar_mensaje("assistant", "Segundo")
    memoria.agregar_mensaje("user", "Tercero")

    assert [m["contenido"] for m in memoria.obtener_historial()] == [
        "Primero",
        "Segundo",
        "Tercero",
    ]
    assert [m["contenido"] for m in memoria.obtener_ventana_contexto()] == [
        "Segundo",
        "Tercero",
    ]
    assert "Usuario: Tercero" in memoria.formatear_para_prompt()


def test_memoria_limpia_solo_la_conversacion_actual(fake_database):
    memoria = MemoriaConversacion()
    memoria.agregar_mensaje("user", "Consulta")

    memoria.limpiar()

    assert memoria.obtener_historial() == []


@pytest.mark.parametrize("valor", [0, -1, True, "10"])
def test_memoria_rechaza_limites_invalidos(fake_database, valor):
    with pytest.raises(ValueError):
        MemoriaConversacion(max_mensajes=valor)


def test_memoria_rechaza_roles_y_contenido_invalidos(fake_database):
    memoria = MemoriaConversacion()

    with pytest.raises(ValueError):
        memoria.agregar_mensaje("system", "No permitido")
    with pytest.raises(ValueError):
        memoria.agregar_mensaje("user", "   ")
