"""Permite importar los módulos del proyecto (en la raíz de /moviface)
desde las pruebas ubicadas en /moviface/test.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import sesion


class _CursorFalso:
    """Doble en memoria de un cursor de PostgreSQL (specs/002-login/plan.md, D6).

    Solo reconoce las consultas exactas que emite cuentas.py: es un
    doble hecho a medida, no un motor SQL real.
    """

    def __init__(self, tabla_cuentas: dict):
        self._tabla = tabla_cuentas
        self._resultado = None

    def __enter__(self):
        return self

    def __exit__(self, *_excepcion):
        return False

    def execute(self, sql: str, parametros: tuple = ()) -> None:
        sql_normalizado = " ".join(sql.split())

        if sql_normalizado.startswith("SELECT 1 FROM cuentas WHERE identificador"):
            (identificador,) = parametros
            self._resultado = (1,) if identificador in self._tabla else None
        elif sql_normalizado.startswith("INSERT INTO cuentas"):
            identificador, contrasena_hash = parametros
            self._tabla[identificador] = contrasena_hash
            self._resultado = None
        elif sql_normalizado.startswith(
            "SELECT identificador, contrasena_hash FROM cuentas"
        ):
            (identificador,) = parametros
            if identificador in self._tabla:
                self._resultado = (identificador, self._tabla[identificador])
            else:
                self._resultado = None
        else:
            raise NotImplementedError(f"Consulta no soportada por el doble: {sql!r}")

    def fetchone(self):
        return self._resultado


class ConexionFalsa:
    """Doble en memoria de una conexión de PostgreSQL (specs/002-login/plan.md, D6)."""

    def __init__(self):
        self.tabla_cuentas: dict = {}

    def cursor(self) -> _CursorFalso:
        return _CursorFalso(self.tabla_cuentas)

    def commit(self) -> None:
        pass


@pytest.fixture
def conexion_fake() -> ConexionFalsa:
    return ConexionFalsa()


@pytest.fixture(autouse=True)
def _reiniciar_sesion():
    """Aísla cada prueba del estado de sesión en memoria (sesion.py)."""
    sesion._cuenta_activa = None
    sesion._ultima_actividad = None
    yield
    sesion._cuenta_activa = None
    sesion._ultima_actividad = None
