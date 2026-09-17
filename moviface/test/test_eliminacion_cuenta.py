"""Pruebas de la eliminación de cuenta:
specs/004-sistema-cobro-transporte-interfaz-chofer-usuario/spec.md (RF-29 a RF-37).

Usan el doble en memoria de PostgreSQL (conftest.py) y una carpeta
enrolled_faces temporal; no necesitan base de datos, cámara ni DeepFace.
"""

from datetime import datetime

import pytest

import almacen_rostros
import cobro
import cuentas
import eliminacion_cuenta
import sesion

_CONTRASENA = "Abcdef1!"


@pytest.fixture(autouse=True)
def _carpeta_enrolados_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(almacen_rostros, "RUTA_BASE", tmp_path / "enrolled_faces")


@pytest.fixture
def enrolar(tmp_path):
    def _enrolar(identificador: str) -> None:
        ruta_foto = tmp_path / "foto_origen.jpg"
        ruta_foto.write_bytes(b"foto de prueba")
        almacen_rostros.guardar_enrolamiento(identificador, ruta_foto, [0.1, 0.2, 0.3])

    return _enrolar


class _PedirContrasena:
    """Doble de getpass: registra si se pidió la contraseña."""

    def __init__(self, contrasena=_CONTRASENA):
        self.contrasena = contrasena
        self.veces = 0

    def __call__(self):
        self.veces += 1
        return self.contrasena


def _crear_e_iniciar(conexion, identificador, tipo):
    cuentas.crear_cuenta(conexion, identificador, _CONTRASENA, tipo=tipo)
    sesion.iniciar_sesion(conexion, identificador, _CONTRASENA)


def _eliminar(conexion, pedir=None, mensajes=None):
    pedir = pedir or _PedirContrasena()
    mensajes = mensajes if mensajes is not None else []
    eliminacion_cuenta.eliminar_cuenta(conexion, pedir_contrasena=pedir, notificar=mensajes.append)
    return pedir, mensajes


# --- RF-29, RF-34, RF-35: eliminación completa ---


def test_rf29_rf34_rf35_pasajero_con_saldo_cero_se_elimina_por_completo(conexion_fake, enrolar):
    _crear_e_iniciar(conexion_fake, "ana@correo.com", "pasajero")
    enrolar("ana@correo.com")
    conexion_fake.tabla_transacciones.append(
        {"identificador": "ana@correo.com", "modalidad": "metro", "monto": 5}
    )

    pedir, mensajes = _eliminar(conexion_fake)

    assert pedir.veces == 1
    assert not cuentas.identificador_en_uso(conexion_fake, "ana@correo.com")
    assert cuentas.obtener_tipo(conexion_fake, "ana@correo.com") is None
    assert conexion_fake.tabla_transacciones == []
    assert not almacen_rostros.existe_enrolamiento("ana@correo.com")
    assert not sesion.hay_sesion_activa()
    assert mensajes == ["Cuenta eliminada correctamente."]


def test_rf29_solo_se_elimina_la_cuenta_con_sesion_activa(conexion_fake, enrolar):
    cuentas.crear_cuenta(conexion_fake, "beto@correo.com", _CONTRASENA, tipo="pasajero")
    enrolar("beto@correo.com")
    _crear_e_iniciar(conexion_fake, "ana@correo.com", "pasajero")

    _eliminar(conexion_fake)

    assert cuentas.obtener_tipo(conexion_fake, "beto@correo.com") == "pasajero"
    assert almacen_rostros.existe_enrolamiento("beto@correo.com")


def test_rf35_chofer_con_modalidad_fijada_se_elimina_y_descarta_la_modalidad(conexion_fake, monkeypatch):
    monkeypatch.setattr(cobro, "_ahora", lambda: datetime(2026, 9, 16, 9, 0))
    _crear_e_iniciar(conexion_fake, "chofer@correo.com", "chofer")
    cobro.fijar_modalidad(conexion_fake, "metro")

    _eliminar(conexion_fake)

    assert not cuentas.identificador_en_uso(conexion_fake, "chofer@correo.com")
    assert not sesion.hay_sesion_activa()
    assert cobro._modalidad_fijada is None


def test_rf29_cuenta_sin_rostro_se_elimina_igual(conexion_fake):
    _crear_e_iniciar(conexion_fake, "ana@correo.com", "pasajero")

    _, mensajes = _eliminar(conexion_fake)

    assert not cuentas.identificador_en_uso(conexion_fake, "ana@correo.com")
    assert mensajes == ["Cuenta eliminada correctamente."]


def test_rf36_cuenta_antigua_sin_tipo_se_elimina_sin_asignarle_tipo(conexion_fake, enrolar, monkeypatch):
    # Simula una cuenta creada antes de la spec 004: está en `cuentas`,
    # pero no en `pasajeros` ni en `choferes`.
    cuentas.crear_cuenta(conexion_fake, "antigua@correo.com", _CONTRASENA, tipo="pasajero")
    conexion_fake.tabla_pasajeros.pop("antigua@correo.com")
    conexion_fake.commit()
    sesion.iniciar_sesion(conexion_fake, "antigua@correo.com", _CONTRASENA)
    enrolar("antigua@correo.com")

    obtener_tipo_original = cuentas.obtener_tipo
    tipos_vistos = []

    def _registrar_tipo(conexion, identificador):
        tipo = obtener_tipo_original(conexion, identificador)
        tipos_vistos.append(tipo)
        return tipo

    monkeypatch.setattr(cuentas, "obtener_tipo", _registrar_tipo)

    _eliminar(conexion_fake)

    assert tipos_vistos == [None]  # nunca se le asignó un tipo
    assert not cuentas.identificador_en_uso(conexion_fake, "antigua@correo.com")
    assert not almacen_rostros.existe_enrolamiento("antigua@correo.com")


# --- RF-30 a RF-33: rechazos que no borran nada ---


def test_rf30_sin_sesion_se_rechaza_sin_pedir_contrasena(conexion_fake):
    pedir = _PedirContrasena()

    with pytest.raises(eliminacion_cuenta.SesionNoIniciada):
        _eliminar(conexion_fake, pedir)

    assert pedir.veces == 0


def test_rf31_rf32_contrasena_incorrecta_no_borra_nada_y_mantiene_la_sesion(conexion_fake, enrolar):
    _crear_e_iniciar(conexion_fake, "ana@correo.com", "pasajero")
    enrolar("ana@correo.com")

    with pytest.raises(eliminacion_cuenta.ContrasenaIncorrecta):
        _eliminar(conexion_fake, _PedirContrasena("Incorrecta1!"))

    assert cuentas.obtener_tipo(conexion_fake, "ana@correo.com") == "pasajero"
    assert almacen_rostros.existe_enrolamiento("ana@correo.com")
    assert sesion.obtener_cuenta_activa() == "ana@correo.com"


def test_rf33_pasajero_con_saldo_se_rechaza_antes_de_pedir_contrasena(conexion_fake, enrolar):
    _crear_e_iniciar(conexion_fake, "ana@correo.com", "pasajero")
    cuentas.recargar_saldo(conexion_fake, "ana@correo.com", 1)
    enrolar("ana@correo.com")
    pedir = _PedirContrasena()

    with pytest.raises(eliminacion_cuenta.SaldoPendiente):
        _eliminar(conexion_fake, pedir)

    assert pedir.veces == 0  # D10
    assert cuentas.obtener_saldo(conexion_fake, "ana@correo.com") == 1
    assert almacen_rostros.existe_enrolamiento("ana@correo.com")
    assert sesion.hay_sesion_activa()


# --- RF-37: fallas a medias ---


def test_rf37_si_falla_postgresql_queda_la_cuenta_sin_rostro_y_se_puede_reintentar(conexion_fake, enrolar):
    _crear_e_iniciar(conexion_fake, "ana@correo.com", "pasajero")
    enrolar("ana@correo.com")
    conexion_fake.fallar_en = "DELETE FROM cuentas"

    with pytest.raises(eliminacion_cuenta.ErrorAlEliminar):
        _eliminar(conexion_fake)

    # Nunca un rostro sin cuenta: el rostro ya no está, la cuenta sí.
    assert not almacen_rostros.existe_enrolamiento("ana@correo.com")
    assert cuentas.identificador_en_uso(conexion_fake, "ana@correo.com")
    assert sesion.obtener_cuenta_activa() == "ana@correo.com"

    conexion_fake.fallar_en = None
    _eliminar(conexion_fake)

    assert not cuentas.identificador_en_uso(conexion_fake, "ana@correo.com")
    assert not sesion.hay_sesion_activa()


def test_rf37_si_falla_el_disco_no_se_toca_la_base_de_datos(conexion_fake, enrolar, monkeypatch):
    _crear_e_iniciar(conexion_fake, "ana@correo.com", "pasajero")
    enrolar("ana@correo.com")

    def _falla_disco(_identificador):
        raise OSError("fallo simulado del disco")

    monkeypatch.setattr(almacen_rostros, "borrar_enrolamiento", _falla_disco)

    with pytest.raises(eliminacion_cuenta.ErrorAlEliminar):
        _eliminar(conexion_fake)

    assert cuentas.obtener_tipo(conexion_fake, "ana@correo.com") == "pasajero"
    assert sesion.obtener_cuenta_activa() == "ana@correo.com"


# --- Caso límite: el identificador queda libre ---


def test_el_identificador_eliminado_se_puede_volver_a_usar(conexion_fake):
    _crear_e_iniciar(conexion_fake, "ana@correo.com", "pasajero")
    _eliminar(conexion_fake)

    cuentas.crear_cuenta(conexion_fake, "ana@correo.com", _CONTRASENA, tipo="chofer")

    assert cuentas.obtener_tipo(conexion_fake, "ana@correo.com") == "chofer"
