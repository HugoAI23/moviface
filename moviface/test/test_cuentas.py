"""Pruebas de specs/002-login/spec.md (RF-1 a RF-5, RF-13).

Usan el doble en memoria `conexion_fake` (ver conftest.py) en vez de
una conexión real a PostgreSQL (specs/002-login/plan.md, D6).
"""

import pytest

import cuentas

_CONTRASENA_VALIDA = "Abcdef1!"


def test_rf1_y_rf5_crea_cuenta_correctamente(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")

    assert cuentas.identificador_en_uso(conexion_fake, "usuario@correo.com")


def test_rf2_rechaza_identificador_sin_formato_de_correo(conexion_fake):
    with pytest.raises(cuentas.IdentificadorInvalido):
        cuentas.crear_cuenta(conexion_fake, "no-es-un-correo", _CONTRASENA_VALIDA, tipo="pasajero")


def test_rf3_rechaza_identificador_duplicado(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")

    with pytest.raises(cuentas.IdentificadorEnUso):
        cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", "OtraClave2#", tipo="pasajero")


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
        cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", contrasena_invalida, tipo="pasajero")


def test_rf13_nunca_guarda_la_contrasena_en_texto_plano(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")

    cuenta = cuentas.buscar_cuenta(conexion_fake, "usuario@correo.com")
    assert cuenta["contrasena_hash"] != _CONTRASENA_VALIDA
    assert _CONTRASENA_VALIDA not in cuenta["contrasena_hash"]


def test_verificar_contrasena_correcta_e_incorrecta(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")

    assert cuentas.verificar_contrasena(conexion_fake, "usuario@correo.com", _CONTRASENA_VALIDA)
    assert not cuentas.verificar_contrasena(conexion_fake, "usuario@correo.com", "Incorrecta1!")
    assert not cuentas.verificar_contrasena(conexion_fake, "inexistente@correo.com", _CONTRASENA_VALIDA)


def test_identificador_sensible_a_mayusculas_y_espacios(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "Usuario@Correo.com", _CONTRASENA_VALIDA, tipo="pasajero")

    assert not cuentas.identificador_en_uso(conexion_fake, "usuario@correo.com")


# --- Spec 004: tipo de cuenta y saldo (RF-1 a RF-10) ---


def test_spec004_rf1_rf2_crea_cuenta_de_pasajero_y_de_chofer(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "pasajero@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")
    cuentas.crear_cuenta(conexion_fake, "chofer@correo.com", _CONTRASENA_VALIDA, tipo="chofer")

    assert cuentas.obtener_tipo(conexion_fake, "pasajero@correo.com") == "pasajero"
    assert cuentas.obtener_tipo(conexion_fake, "chofer@correo.com") == "chofer"


def test_spec004_rf1_identificador_unico_sin_importar_el_tipo(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")

    with pytest.raises(cuentas.IdentificadorEnUso):
        cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA_VALIDA, tipo="chofer")


@pytest.mark.parametrize("tipo_invalido", ["administrador", "", "Pasajero", None])
def test_spec004_rf3_rechaza_tipo_invalido_sin_crear_nada(conexion_fake, tipo_invalido):
    with pytest.raises(cuentas.TipoInvalido):
        cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA_VALIDA, tipo=tipo_invalido)

    assert not cuentas.identificador_en_uso(conexion_fake, "ana@correo.com")
    assert cuentas.obtener_tipo(conexion_fake, "ana@correo.com") is None


def test_spec004_rf5_pasajero_inicia_con_saldo_cero(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")

    assert cuentas.obtener_saldo(conexion_fake, "ana@correo.com") == 0


def test_spec004_rf6_chofer_no_tiene_saldo(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "chofer@correo.com", _CONTRASENA_VALIDA, tipo="chofer")

    with pytest.raises(cuentas.CuentaNoEsPasajero):
        cuentas.obtener_saldo(conexion_fake, "chofer@correo.com")


def test_spec004_rf7_rf8_recarga_suma_el_monto_entero(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")

    cuentas.recargar_saldo(conexion_fake, "ana@correo.com", 20)
    cuentas.recargar_saldo(conexion_fake, "ana@correo.com", 5)

    assert cuentas.obtener_saldo(conexion_fake, "ana@correo.com") == 25


@pytest.mark.parametrize("monto_invalido", [0, -10, 5.5, "10", True, None])
def test_spec004_rf8_rechaza_monto_invalido_sin_modificar_saldo(conexion_fake, monto_invalido):
    cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")
    cuentas.recargar_saldo(conexion_fake, "ana@correo.com", 10)

    with pytest.raises(cuentas.MontoInvalido):
        cuentas.recargar_saldo(conexion_fake, "ana@correo.com", monto_invalido)

    assert cuentas.obtener_saldo(conexion_fake, "ana@correo.com") == 10


def test_spec004_rf9_cuenta_de_chofer_no_puede_recargar(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "chofer@correo.com", _CONTRASENA_VALIDA, tipo="chofer")

    with pytest.raises(cuentas.CuentaNoEsPasajero):
        cuentas.recargar_saldo(conexion_fake, "chofer@correo.com", 10)


def test_spec004_rf10_recarga_sin_tope_maximo(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")

    cuentas.recargar_saldo(conexion_fake, "ana@correo.com", 1_000_000)

    assert cuentas.obtener_saldo(conexion_fake, "ana@correo.com") == 1_000_000


def test_spec004_rf24_rf28_descontar_rechaza_si_no_alcanza(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")
    cuentas.recargar_saldo(conexion_fake, "ana@correo.com", 4)

    with pytest.raises(cuentas.SaldoInsuficiente):
        cuentas.descontar_saldo(conexion_fake, "ana@correo.com", 5)

    assert cuentas.obtener_saldo(conexion_fake, "ana@correo.com") == 4


def test_spec004_saldo_exactamente_igual_a_la_tarifa_queda_en_cero(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")
    cuentas.recargar_saldo(conexion_fake, "ana@correo.com", 5)

    cuentas.descontar_saldo(conexion_fake, "ana@correo.com", 5)

    assert cuentas.obtener_saldo(conexion_fake, "ana@correo.com") == 0


# --- Spec 004, ampliación: borrado en PostgreSQL (RF-34, plan.md D9) ---


def test_spec004_rf34_eliminar_borra_cuenta_tipo_e_historial_sin_tocar_otras(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")
    cuentas.crear_cuenta(conexion_fake, "beto@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")
    conexion_fake.tabla_transacciones.extend(
        [
            {"identificador": "ana@correo.com", "modalidad": "metro", "monto": 5},
            {"identificador": "beto@correo.com", "modalidad": "bici", "monto": 10},
        ]
    )

    cuentas.eliminar_cuenta(conexion_fake, "ana@correo.com")

    assert not cuentas.identificador_en_uso(conexion_fake, "ana@correo.com")
    assert cuentas.obtener_tipo(conexion_fake, "ana@correo.com") is None
    assert conexion_fake.tabla_transacciones == [
        {"identificador": "beto@correo.com", "modalidad": "bici", "monto": 10}
    ]
    assert cuentas.obtener_tipo(conexion_fake, "beto@correo.com") == "pasajero"


def test_spec004_rf34_eliminar_cuenta_de_chofer(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "chofer@correo.com", _CONTRASENA_VALIDA, tipo="chofer")

    cuentas.eliminar_cuenta(conexion_fake, "chofer@correo.com")

    assert not cuentas.identificador_en_uso(conexion_fake, "chofer@correo.com")
    assert cuentas.obtener_tipo(conexion_fake, "chofer@correo.com") is None


def test_spec004_d9_si_falla_postgresql_no_borra_nada(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA_VALIDA, tipo="pasajero")
    conexion_fake.tabla_transacciones.append(
        {"identificador": "ana@correo.com", "modalidad": "metro", "monto": 5}
    )
    conexion_fake.commit()
    # Falla en el último DELETE, cuando los anteriores ya se aplicaron.
    conexion_fake.fallar_en = "DELETE FROM cuentas"

    with pytest.raises(RuntimeError):
        cuentas.eliminar_cuenta(conexion_fake, "ana@correo.com")

    assert cuentas.identificador_en_uso(conexion_fake, "ana@correo.com")
    assert cuentas.obtener_tipo(conexion_fake, "ana@correo.com") == "pasajero"
    assert len(conexion_fake.tabla_transacciones) == 1
