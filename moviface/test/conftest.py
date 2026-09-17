"""Permite importar los módulos del proyecto (en la raíz de /moviface)
desde las pruebas ubicadas en /moviface/test.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import cobro
import sesion


class _CursorFalso:
    """Doble en memoria de un cursor de PostgreSQL (specs/002-login/plan.md, D6).

    Solo reconoce las consultas exactas que emiten cuentas.py y cobro.py:
    es un doble hecho a medida, no un motor SQL real.
    """

    def __init__(self, conexion: "ConexionFalsa"):
        self._conexion = conexion
        self._tabla = conexion.tabla_cuentas
        self._resultado = None

    def __enter__(self):
        return self

    def __exit__(self, *_excepcion):
        return False

    def execute(self, sql: str, parametros: tuple = ()) -> None:
        sql_normalizado = " ".join(sql.split())

        if self._conexion.fallar_en and sql_normalizado.startswith(self._conexion.fallar_en):
            raise RuntimeError(f"fallo simulado de PostgreSQL en: {self._conexion.fallar_en}")

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
        # --- Spec 004: pasajeros, choferes y transacciones ---
        elif sql_normalizado.startswith("INSERT INTO pasajeros"):
            (identificador,) = parametros
            self._conexion.tabla_pasajeros[identificador] = 0
        elif sql_normalizado.startswith("INSERT INTO choferes"):
            (identificador,) = parametros
            self._conexion.tabla_choferes.add(identificador)
        elif sql_normalizado.startswith("SELECT 1 FROM pasajeros"):
            (identificador,) = parametros
            self._resultado = (1,) if identificador in self._conexion.tabla_pasajeros else None
        elif sql_normalizado.startswith("SELECT 1 FROM choferes"):
            (identificador,) = parametros
            self._resultado = (1,) if identificador in self._conexion.tabla_choferes else None
        elif sql_normalizado.startswith("SELECT saldo FROM pasajeros"):
            (identificador,) = parametros
            saldo = self._conexion.tabla_pasajeros.get(identificador)
            self._resultado = None if saldo is None else (saldo,)
        elif sql_normalizado.startswith("UPDATE pasajeros SET saldo = saldo +"):
            monto, identificador = parametros
            self._conexion.tabla_pasajeros[identificador] += monto
        elif sql_normalizado.startswith("UPDATE pasajeros SET saldo = saldo -"):
            monto, identificador = parametros
            nuevo_saldo = self._conexion.tabla_pasajeros[identificador] - monto
            # Imita el CHECK (saldo >= 0) de la tabla real.
            if nuevo_saldo < 0:
                raise ValueError("violación de CHECK (saldo >= 0)")
            self._conexion.tabla_pasajeros[identificador] = nuevo_saldo
        elif sql_normalizado.startswith("INSERT INTO transacciones"):
            identificador, modalidad, monto = parametros
            self._conexion.tabla_transacciones.append(
                {"identificador": identificador, "modalidad": modalidad, "monto": monto}
            )
        # --- Spec 004, ampliación: eliminación de cuenta ---
        elif sql_normalizado.startswith("DELETE FROM transacciones"):
            (identificador,) = parametros
            self._conexion.tabla_transacciones[:] = [
                fila
                for fila in self._conexion.tabla_transacciones
                if fila["identificador"] != identificador
            ]
        elif sql_normalizado.startswith("DELETE FROM pasajeros"):
            (identificador,) = parametros
            self._conexion.tabla_pasajeros.pop(identificador, None)
        elif sql_normalizado.startswith("DELETE FROM choferes"):
            (identificador,) = parametros
            self._conexion.tabla_choferes.discard(identificador)
        elif sql_normalizado.startswith("DELETE FROM cuentas"):
            (identificador,) = parametros
            self._tabla.pop(identificador, None)
        else:
            raise NotImplementedError(f"Consulta no soportada por el doble: {sql!r}")

    def fetchone(self):
        return self._resultado


class ConexionFalsa:
    """Doble en memoria de una conexión de PostgreSQL (specs/002-login/plan.md, D6).

    Las escrituras se aplican al momento; commit() toma una foto del
    estado y rollback() vuelve a la última foto, para poder probar que un
    cobro fallido no deja cambios a medias (spec 004).
    """

    def __init__(self):
        self.tabla_cuentas: dict = {}
        self.tabla_pasajeros: dict = {}
        self.tabla_choferes: set = set()
        self.tabla_transacciones: list = []
        self.confirmaciones = 0
        # Prefijo de SQL con el que el doble simula una falla de PostgreSQL.
        self.fallar_en: str | None = None
        self._foto = self._tomar_foto()

    def _tomar_foto(self):
        return (
            dict(self.tabla_cuentas),
            dict(self.tabla_pasajeros),
            set(self.tabla_choferes),
            list(self.tabla_transacciones),
        )

    def cursor(self) -> _CursorFalso:
        return _CursorFalso(self)

    def commit(self) -> None:
        self.confirmaciones += 1
        self._foto = self._tomar_foto()

    def rollback(self) -> None:
        cuentas_, pasajeros, choferes, transacciones = self._foto
        # Se muta en sitio: los cursores guardan referencia a estos objetos.
        self.tabla_cuentas.clear()
        self.tabla_cuentas.update(cuentas_)
        self.tabla_pasajeros.clear()
        self.tabla_pasajeros.update(pasajeros)
        self.tabla_choferes.clear()
        self.tabla_choferes.update(choferes)
        self.tabla_transacciones[:] = transacciones


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


@pytest.fixture(autouse=True)
def _reiniciar_cobro():
    """Aísla cada prueba del estado de turno/modalidad en memoria (cobro.py)."""
    cobro.reiniciar_estado()
    yield
    cobro.reiniciar_estado()
