"""Gestión de sesión de usuario.

Implementa specs/002-login/spec.md (RF-6 a RF-12). Reemplaza el stub
que simulaba una única cuenta demo siempre activa mientras esta spec
no existía.

El estado de sesión vive únicamente en memoria de este proceso
(specs/002-login/plan.md, D4): no se persiste en ninguna base de datos
ni sobrevive a un reinicio del programa (spec.md, NFR de persistencia
de sesión), y no se comparte entre procesos distintos (spec.md, RF-8
y "Fuera de alcance").

El resto del proyecto (enrolamiento.py) solo debe depender de las
funciones públicas `obtener_cuenta_activa` y `hay_sesion_activa`,
cuya firma no cambia respecto al stub original de specs/001.
"""

import time

import cuentas

MINUTOS_INACTIVIDAD = 30

_cuenta_activa: str | None = None
_ultima_actividad: float | None = None


class SesionYaActiva(Exception):
    """RF-8: ya hay una sesión iniciada en este mismo proceso."""


class CredencialesInvalidas(Exception):
    """RF-7: el identificador o la contraseña no coinciden con ninguna cuenta."""


class SinSesionActiva(Exception):
    """RF-10: se pidió cerrar sesión sin haber ninguna sesión iniciada."""


def iniciar_sesion(conexion, identificador: str, contrasena: str) -> None:
    """RF-6/RF-7/RF-8: inicia sesión si las credenciales son válidas y no
    hay ya una sesión activa en este proceso.
    """
    global _cuenta_activa, _ultima_actividad

    if _cuenta_activa is not None:
        raise SesionYaActiva(
            "Ya hay una sesión iniciada. Cierra sesión antes de continuar."
        )

    if not cuentas.verificar_contrasena(conexion, identificador, contrasena):
        raise CredencialesInvalidas("Identificador o contraseña inválidos.")

    _cuenta_activa = identificador
    _ultima_actividad = time.monotonic()


def cerrar_sesion() -> None:
    """RF-9/RF-10/RF-12: cierra la sesión manualmente y descarta su estado."""
    global _cuenta_activa, _ultima_actividad

    if _cuenta_activa is None:
        raise SinSesionActiva("No hay ninguna sesión activa.")

    _cuenta_activa = None
    _ultima_actividad = None


def registrar_actividad() -> None:
    """RF-11: cualquier acción del menú principal reinicia el contador
    de inactividad, mientras haya una sesión activa."""
    global _ultima_actividad

    if _cuenta_activa is not None:
        _ultima_actividad = time.monotonic()


def verificar_expiracion(minutos_inactividad: float = MINUTOS_INACTIVIDAD) -> bool:
    """RF-11/RF-12: verificación perezosa (plan.md, D4). Si ya pasó el
    tiempo de inactividad, cierra la sesión y descarta su estado.
    Devuelve True si la sesión expiró en esta llamada.
    """
    global _cuenta_activa, _ultima_actividad

    if _cuenta_activa is None:
        return False

    segundos_inactivo = time.monotonic() - _ultima_actividad
    if segundos_inactivo >= minutos_inactividad * 60:
        _cuenta_activa = None
        _ultima_actividad = None
        return True

    return False


def obtener_cuenta_activa() -> str | None:
    """Devuelve el identificador de la cuenta con sesión iniciada, o None."""
    return _cuenta_activa


def hay_sesion_activa() -> bool:
    """RF-1/RF-2 (specs/001): indica si existe una sesión iniciada."""
    return _cuenta_activa is not None
