"""Pruebas de specs/002-login/spec.md (RF-1 a RF-5, RF-13).

Usan el doble en memoria `conexion_fake` (ver conftest.py) en vez de
una conexión real a PostgreSQL (specs/002-login/plan.md, D6).
"""

import pytest

import cuentas

_CONTRASENA_VALIDA = "Abcdef1!"


def test_rf1_y_rf5_crea_cuenta_correctamente(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", _CONTRASENA_VALIDA)

    assert cuentas.identificador_en_uso(conexion_fake, "usuario@correo.com")


def test_rf2_rechaza_identificador_sin_formato_de_correo(conexion_fake):
    with pytest.raises(cuentas.IdentificadorInvalido):
        cuentas.crear_cuenta(conexion_fake, "no-es-un-correo", _CONTRASENA_VALIDA)


def test_rf3_rechaza_identificador_duplicado(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", _CONTRASENA_VALIDA)

    with pytest.raises(cuentas.IdentificadorEnUso):
        cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", "OtraClave2#")


@pytest.mark.parametrize(
    "contrasena_invalida",
    [
        "Corta1!",  # menos de 8 caracteres
        "abcdefg1!",  # sin mayúscula
        "ABCDEFG1!",  # sin minúscula
        "Abcdefgh!",  # sin número
        "Abcdefg1",  # sin carácter especial
        "Abcdef 1!",  # con espacio
    ],
)
def test_rf4_rechaza_contrasena_sin_requisitos(conexion_fake, contrasena_invalida):
    with pytest.raises(cuentas.ContrasenaInvalida):
        cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", contrasena_invalida)


def test_rf13_nunca_guarda_la_contrasena_en_texto_plano(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", _CONTRASENA_VALIDA)

    cuenta = cuentas.buscar_cuenta(conexion_fake, "usuario@correo.com")
    assert cuenta["contrasena_hash"] != _CONTRASENA_VALIDA
    assert _CONTRASENA_VALIDA not in cuenta["contrasena_hash"]


def test_verificar_contrasena_correcta_e_incorrecta(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", _CONTRASENA_VALIDA)

    assert cuentas.verificar_contrasena(conexion_fake, "usuario@correo.com", _CONTRASENA_VALIDA)
    assert not cuentas.verificar_contrasena(conexion_fake, "usuario@correo.com", "Incorrecta1!")
    assert not cuentas.verificar_contrasena(conexion_fake, "inexistente@correo.com", _CONTRASENA_VALIDA)


def test_identificador_sensible_a_mayusculas_y_espacios(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "Usuario@Correo.com", _CONTRASENA_VALIDA)

    assert not cuentas.identificador_en_uso(conexion_fake, "usuario@correo.com")
