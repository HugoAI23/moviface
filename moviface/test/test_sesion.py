"""Pruebas de specs/002-login/spec.md (RF-6 a RF-12).

Usan `conexion_fake` (ver conftest.py) y cuentas reales creadas sobre
ese doble en memoria, sin necesitar PostgreSQL real (D6). El estado de
sesión se reinicia entre pruebas mediante el fixture autouse
`_reiniciar_sesion` (conftest.py).
"""

import time

import pytest

import cuentas
import sesion

_IDENTIFICADOR = "usuario@correo.com"
_CONTRASENA = "Abcdef1!"


@pytest.fixture
def cuenta_creada(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, _IDENTIFICADOR, _CONTRASENA)
    return conexion_fake


def test_rf6_inicia_sesion_con_credenciales_correctas(cuenta_creada):
    sesion.iniciar_sesion(cuenta_creada, _IDENTIFICADOR, _CONTRASENA)

    assert sesion.hay_sesion_activa()
    assert sesion.obtener_cuenta_activa() == _IDENTIFICADOR


def test_rf7_rechaza_contrasena_incorrecta_con_mensaje_generico(cuenta_creada):
    with pytest.raises(sesion.CredencialesInvalidas):
        sesion.iniciar_sesion(cuenta_creada, _IDENTIFICADOR, "Incorrecta1!")

    assert not sesion.hay_sesion_activa()


def test_rf7_rechaza_identificador_inexistente(cuenta_creada):
    with pytest.raises(sesion.CredencialesInvalidas):
        sesion.iniciar_sesion(cuenta_creada, "inexistente@correo.com", _CONTRASENA)

    assert not sesion.hay_sesion_activa()


def test_rf8_rechaza_nuevo_login_si_ya_hay_sesion_activa(cuenta_creada):
    sesion.iniciar_sesion(cuenta_creada, _IDENTIFICADOR, _CONTRASENA)

    with pytest.raises(sesion.SesionYaActiva):
        sesion.iniciar_sesion(cuenta_creada, _IDENTIFICADOR, _CONTRASENA)


def test_rf9_cierra_sesion_manualmente(cuenta_creada):
    sesion.iniciar_sesion(cuenta_creada, _IDENTIFICADOR, _CONTRASENA)

    sesion.cerrar_sesion()

    assert not sesion.hay_sesion_activa()
    assert sesion.obtener_cuenta_activa() is None


def test_rf10_cerrar_sesion_sin_sesion_activa_informa_error():
    with pytest.raises(sesion.SinSesionActiva):
        sesion.cerrar_sesion()


def test_rf11_no_expira_antes_de_tiempo(cuenta_creada):
    sesion.iniciar_sesion(cuenta_creada, _IDENTIFICADOR, _CONTRASENA)

    assert sesion.verificar_expiracion() is False
    assert sesion.hay_sesion_activa()


def test_rf11_y_rf12_expira_por_inactividad_y_descarta_el_estado(cuenta_creada, monkeypatch):
    sesion.iniciar_sesion(cuenta_creada, _IDENTIFICADOR, _CONTRASENA)

    monkeypatch.setattr(sesion, "_ultima_actividad", time.monotonic() - 31 * 60)

    assert sesion.verificar_expiracion() is True
    assert not sesion.hay_sesion_activa()
    assert sesion.obtener_cuenta_activa() is None


def test_registrar_actividad_reinicia_el_contador(cuenta_creada, monkeypatch):
    sesion.iniciar_sesion(cuenta_creada, _IDENTIFICADOR, _CONTRASENA)

    monkeypatch.setattr(sesion, "_ultima_actividad", time.monotonic() - 31 * 60)
    sesion.registrar_actividad()

    assert sesion.verificar_expiracion() is False
    assert sesion.hay_sesion_activa()


def test_rf12_cerrar_sesion_manual_descarta_el_estado(cuenta_creada):
    sesion.iniciar_sesion(cuenta_creada, _IDENTIFICADOR, _CONTRASENA)

    sesion.cerrar_sesion()

    assert sesion._cuenta_activa is None
    assert sesion._ultima_actividad is None
