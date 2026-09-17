"""Pruebas de specs/004-sistema-cobro-transporte-interfaz-chofer-usuario/spec.md
(RF-11 a RF-28).

No dependen de cámara, DeepFace, ventana ni PostgreSQL reales: la
identificación y la ventana de resultado se inyectan como dobles, la
conexión es el doble en memoria de conftest.py, y la hora se simula
sustituyendo cobro._ahora.
"""

from datetime import datetime

import pytest

import cobro
import cuentas
import master
import sesion

_CONTRASENA = "Abcdef1!"
_CHOFER = "chofer@correo.com"
_PASAJERO = "pasajero@correo.com"


class _Reloj:
    def __init__(self):
        self.ahora = datetime(2026, 9, 16, 9, 0)

    def poner(self, hora: int, minuto: int = 0, dia: int = 16) -> None:
        self.ahora = datetime(2026, 9, dia, hora, minuto)


@pytest.fixture
def reloj(monkeypatch) -> _Reloj:
    reloj = _Reloj()
    monkeypatch.setattr(cobro, "_ahora", lambda: reloj.ahora)
    return reloj


@pytest.fixture
def conexion(conexion_fake):
    """Una cuenta de chofer con sesión iniciada y un pasajero con saldo 37."""
    cuentas.crear_cuenta(conexion_fake, _CHOFER, _CONTRASENA, tipo="chofer")
    cuentas.crear_cuenta(conexion_fake, _PASAJERO, _CONTRASENA, tipo="pasajero")
    cuentas.recargar_saldo(conexion_fake, _PASAJERO, 37)
    sesion.iniciar_sesion(conexion_fake, _CHOFER, _CONTRASENA)
    return conexion_fake


class _Identificacion:
    """Doble de identificacion.identificar(): registra cómo se llamó."""

    def __init__(self, resultado=_PASAJERO, al_identificar=None):
        self.resultado = resultado
        self.al_identificar = al_identificar
        self.llamadas = []

    def __call__(self, **kwargs):
        self.llamadas.append(kwargs)
        if self.al_identificar:
            self.al_identificar()
        return self.resultado


@pytest.fixture
def mensajes():
    return []


def _notificar(mensajes):
    return lambda mensaje, *, exito: mensajes.append((mensaje, exito))


def _cobrar(conexion, mensajes, identificar=None):
    identificar = identificar or _Identificacion()
    cobro.cobrar(conexion, identificar=identificar, notificar=_notificar(mensajes))
    return identificar


# --- RF-11: solo un chofer con sesión ---


def test_rf11_sin_sesion_no_puede_fijar_ni_cobrar(conexion_fake, reloj, mensajes):
    with pytest.raises(cobro.NoEsChofer) as error_fijar:
        cobro.fijar_modalidad(conexion_fake, "metro")
    with pytest.raises(cobro.NoEsChofer) as error_cobrar:
        _cobrar(conexion_fake, mensajes)

    assert str(error_fijar.value) == str(error_cobrar.value)


def test_rf11_pasajero_con_sesion_recibe_el_mismo_mensaje(conexion_fake, reloj, mensajes):
    cuentas.crear_cuenta(conexion_fake, _PASAJERO, _CONTRASENA, tipo="pasajero")
    sesion.iniciar_sesion(conexion_fake, _PASAJERO, _CONTRASENA)

    with pytest.raises(cobro.NoEsChofer) as error:
        cobro.fijar_modalidad(conexion_fake, "metro")

    assert str(error.value) == "Debes iniciar sesión como chofer para continuar."


# --- RF-12: turnos fijos ---


@pytest.mark.parametrize(
    "hora, minuto, esperado",
    [
        (5, 59, None),
        (6, 0, "matutino"),
        (13, 59, "matutino"),
        (14, 0, "vespertino"),
        (21, 59, "vespertino"),
        (22, 0, None),
        (0, 30, None),
    ],
)
def test_rf12_turno_vigente_segun_la_hora(hora, minuto, esperado):
    assert cobro._turno_vigente(datetime(2026, 9, 16, hora, minuto)) == esperado


# --- RF-13 a RF-19: modalidad por turno ---


def test_rf13_modalidad_invalida(conexion, reloj):
    with pytest.raises(cobro.ModalidadInvalida):
        cobro.fijar_modalidad(conexion, "taxi")


def test_rf14_modalidad_fijada_sin_turno_queda_en_espera_y_se_activa(conexion, reloj, mensajes):
    reloj.poner(5, 30)
    cobro.fijar_modalidad(conexion, "bici")
    assert cobro.modalidad_en_espera()

    reloj.poner(6, 5)
    _cobrar(conexion, mensajes)

    assert not cobro.modalidad_en_espera()
    assert cuentas.obtener_saldo(conexion, _PASAJERO) == 27  # 37 - bici $10


def test_rf15_fuera_de_horario_se_rechaza_sin_identificar(conexion, reloj, mensajes):
    reloj.poner(23, 0)
    identificar = _Identificacion()

    with pytest.raises(cobro.SinTurnoVigente):
        _cobrar(conexion, mensajes, identificar)

    assert identificar.llamadas == []


def test_rf16_sin_modalidad_fijada_se_rechaza_sin_identificar(conexion, reloj, mensajes):
    identificar = _Identificacion()

    with pytest.raises(cobro.ModalidadNoFijada):
        _cobrar(conexion, mensajes, identificar)

    assert identificar.llamadas == []


def test_rf17_la_modalidad_se_reutiliza_en_varios_cobros_del_turno(conexion, reloj, mensajes):
    cobro.fijar_modalidad(conexion, "metro")

    for _ in range(3):
        _cobrar(conexion, mensajes)

    assert cuentas.obtener_saldo(conexion, _PASAJERO) == 22  # 37 - 3 x $5
    assert all(exito for _, exito in mensajes)


def test_modalidad_no_se_cambia_dentro_del_mismo_turno(conexion, reloj):
    cobro.fijar_modalidad(conexion, "metro")

    with pytest.raises(cobro.ModalidadYaFijada):
        cobro.fijar_modalidad(conexion, "bici")


@pytest.mark.parametrize(
    "fijada_en, consultada_en",
    [
        ((13, 50, 16), (14, 10, 16)),  # matutino -> vespertino
        ((21, 50, 16), (22, 10, 16)),  # vespertino -> sin turno
        ((9, 0, 16), (9, 0, 17)),  # mismo turno, pero de otro día
    ],
)
def test_rf18_cambio_de_turno_descarta_la_modalidad(conexion, reloj, mensajes, fijada_en, consultada_en):
    reloj.poner(*fijada_en)
    cobro.fijar_modalidad(conexion, "metro")

    reloj.poner(*consultada_en)
    assert cobro._modalidad_vigente() is None
    assert not cobro.modalidad_en_espera()

    # Tras el descarte, el chofer puede volver a fijarla (RF-13).
    cobro.fijar_modalidad(conexion, "metrobus")


def test_rf19_cerrar_sesion_desde_el_menu_descarta_la_modalidad(conexion, reloj, capsys):
    cobro.fijar_modalidad(conexion, "metro")

    master._cerrar_sesion()

    assert cobro._modalidad_fijada is None
    assert cobro._turno_de_modalidad is None


def test_rf19_expiracion_detectada_por_el_menu_descarta_la_modalidad(conexion, reloj, monkeypatch, capsys):
    cobro.fijar_modalidad(conexion, "metro")
    monkeypatch.setattr(sesion, "verificar_expiracion", lambda: True)
    entradas = iter(["99", "4", "12"])  # opción inválida, cerrar sesión, salir
    monkeypatch.setattr("builtins.input", lambda _texto="": next(entradas))

    master._menu()

    assert cobro._modalidad_fijada is None
    assert "expiró por inactividad" in capsys.readouterr().out


def test_rf19_rf20_un_chofer_nuevo_empieza_sin_modalidad(conexion, reloj, mensajes):
    cobro.fijar_modalidad(conexion, "metro")
    master._cerrar_sesion()

    cuentas.crear_cuenta(conexion, "otro.chofer@correo.com", _CONTRASENA, tipo="chofer")
    sesion.iniciar_sesion(conexion, "otro.chofer@correo.com", _CONTRASENA)

    with pytest.raises(cobro.ModalidadNoFijada):
        _cobrar(conexion, mensajes)


# --- RF-20 a RF-28: el cobro ---


def test_rf21_identifica_sin_revelar_el_identificador(conexion, reloj, mensajes):
    cobro.fijar_modalidad(conexion, "metro")

    identificar = _cobrar(conexion, mensajes)

    assert identificar.llamadas == [{"revelar_identificador": False}]


def test_rf22_nadie_identificado_no_cobra(conexion, reloj, mensajes):
    cobro.fijar_modalidad(conexion, "metro")

    _cobrar(conexion, mensajes, _Identificacion(resultado=None))

    assert cuentas.obtener_saldo(conexion, _PASAJERO) == 37
    assert conexion.tabla_transacciones == []
    assert mensajes == [("No se identificó a ningún pasajero. No se realizó ningún cobro.", False)]


@pytest.mark.parametrize("modalidad, monto", [("metro", 5), ("metrobus", 6), ("bici", 10)])
def test_rf23_rf25_cobra_la_tarifa_y_registra_la_transaccion(conexion, reloj, mensajes, modalidad, monto):
    cobro.fijar_modalidad(conexion, modalidad)

    _cobrar(conexion, mensajes)

    assert cuentas.obtener_saldo(conexion, _PASAJERO) == 37 - monto
    assert conexion.tabla_transacciones == [
        {"identificador": _PASAJERO, "modalidad": modalidad, "monto": monto}
    ]
    assert mensajes[-1][1] is True


def test_rf24_saldo_insuficiente_no_descuenta_ni_registra(conexion, reloj, mensajes):
    cuentas.crear_cuenta(conexion, "sin.saldo@correo.com", _CONTRASENA, tipo="pasajero")
    cuentas.recargar_saldo(conexion, "sin.saldo@correo.com", 9)
    cobro.fijar_modalidad(conexion, "bici")

    _cobrar(conexion, mensajes, _Identificacion(resultado="sin.saldo@correo.com"))

    assert cuentas.obtener_saldo(conexion, "sin.saldo@correo.com") == 9
    assert conexion.tabla_transacciones == []
    assert mensajes == [("Cobro rechazado: saldo insuficiente (bici, $10).", False)]


def test_saldo_exactamente_igual_a_la_tarifa_se_cobra(conexion, reloj, mensajes):
    cuentas.crear_cuenta(conexion, "justo@correo.com", _CONTRASENA, tipo="pasajero")
    cuentas.recargar_saldo(conexion, "justo@correo.com", 6)
    cobro.fijar_modalidad(conexion, "metrobus")

    _cobrar(conexion, mensajes, _Identificacion(resultado="justo@correo.com"))

    assert cuentas.obtener_saldo(conexion, "justo@correo.com") == 0
    assert mensajes[-1] == ("Cobro realizado: metrobús, $6.", True)


def test_rf25_descuento_y_registro_se_confirman_juntos(conexion, reloj, mensajes, monkeypatch):
    cobro.fijar_modalidad(conexion, "metro")

    def _falla_al_registrar(*_args):
        raise RuntimeError("fallo simulado de la base de datos")

    monkeypatch.setattr(cobro, "_registrar_transaccion", _falla_al_registrar)

    with pytest.raises(RuntimeError):
        _cobrar(conexion, mensajes)

    # El descuento ya aplicado se revierte: no queda un cobro a medias.
    assert cuentas.obtener_saldo(conexion, _PASAJERO) == 37
    assert mensajes == []


def test_rf26_sesion_cerrada_durante_la_identificacion_cancela_el_cobro(conexion, reloj, mensajes):
    cobro.fijar_modalidad(conexion, "metro")
    identificar = _Identificacion(al_identificar=sesion.cerrar_sesion)

    with pytest.raises(cobro.SesionCerrada):
        _cobrar(conexion, mensajes, identificar)

    assert cuentas.obtener_saldo(conexion, _PASAJERO) == 37
    assert conexion.tabla_transacciones == []
    assert cobro._modalidad_fijada is None


def test_rf26_sesion_expirada_durante_la_identificacion_cancela_el_cobro(conexion, reloj, mensajes, monkeypatch):
    cobro.fijar_modalidad(conexion, "metro")
    monkeypatch.setattr(sesion, "verificar_expiracion", lambda: True)

    with pytest.raises(cobro.SesionCerrada):
        _cobrar(conexion, mensajes)

    assert cuentas.obtener_saldo(conexion, _PASAJERO) == 37
    assert conexion.tabla_transacciones == []


def test_rf27_ningun_mensaje_revela_identificador_ni_saldo(conexion, reloj, mensajes):
    cobro.fijar_modalidad(conexion, "metro")

    _cobrar(conexion, mensajes)  # éxito: saldo 37 -> 32
    cuentas.crear_cuenta(conexion, "pobre@correo.com", _CONTRASENA, tipo="pasajero")
    cuentas.recargar_saldo(conexion, "pobre@correo.com", 3)
    _cobrar(conexion, mensajes, _Identificacion(resultado="pobre@correo.com"))  # rechazo
    _cobrar(conexion, mensajes, _Identificacion(resultado=None))  # nadie

    texto = " ".join(mensaje for mensaje, _ in mensajes)
    for dato_privado in (_PASAJERO, "pobre@correo.com", "@", "37", "32", "$3"):
        assert dato_privado not in texto


def test_rf28_cuenta_de_chofer_identificada_se_rechaza_sin_tirar_el_programa(conexion, reloj, mensajes):
    cobro.fijar_modalidad(conexion, "metro")

    _cobrar(conexion, mensajes, _Identificacion(resultado=_CHOFER))

    assert conexion.tabla_transacciones == []
    assert mensajes[-1][1] is False
    assert _CHOFER not in mensajes[-1][0]
