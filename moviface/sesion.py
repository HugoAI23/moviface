"""Stub de sesión: simula un usuario autenticado mientras no existe specs/002-login.

Este módulo es el único punto que se reemplazará cuando se redacte e
implemente specs/002-login; el resto del flujo de enrolamiento
(ver enrolamiento.py) solo debe depender de las funciones públicas
definidas aquí, nunca de cómo se determina la sesión internamente.
"""

# Cuenta demo fija usada como "sesión activa" hasta que exista un login
# real. No se valida contra PostgreSQL en esta spec (specs/001): esa
# verificación queda a cargo de specs/002-login.
_CUENTA_DEMO_ACTIVA = "demo"


def obtener_cuenta_activa() -> str | None:
    """Devuelve el id de la cuenta con sesión iniciada, o None si no hay sesión.

    Implementación actual (stub): siempre devuelve la cuenta demo fija.
    """
    return _CUENTA_DEMO_ACTIVA


def hay_sesion_activa() -> bool:
    """RF-1/RF-2: indica si existe una sesión iniciada."""
    return obtener_cuenta_activa() is not None
