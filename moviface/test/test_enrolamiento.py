"""Pruebas de specs/001-enrolamiento-vectores-faciales/spec.md (RF-1 a RF-15).

No dependen de cámara real ni de DeepFace: los puntos de captura,
validación y generación de vector se sustituyen por dobles de prueba,
igual que la sesión (ver sesion.py).
"""

from pathlib import Path

import pytest

import almacen_rostros
import enrolamiento
import lector_de_caras


@pytest.fixture(autouse=True)
def _carpeta_enrolados_temporal(tmp_path, monkeypatch):
    """Aísla cada prueba en una carpeta enrolled_faces temporal."""
    monkeypatch.setattr(almacen_rostros, "RUTA_BASE", tmp_path / "enrolled_faces")


def _sesion_activa(id_cuenta="cuenta_prueba"):
    return {"hay_sesion_activa": lambda: True, "obtener_cuenta_activa": lambda: id_cuenta}


def _capturar_foto_falsa(ruta_destino: Path) -> None:
    ruta_destino.write_bytes(b"contenido de prueba, no es una foto real")


def _confirmar_siempre(ruta_imagen: Path) -> bool:
    return True


def test_rf2_rechaza_sin_sesion_iniciada():
    with pytest.raises(enrolamiento.SesionNoIniciada):
        enrolamiento.enrolar(
            capturar_foto=_capturar_foto_falsa,
            confirmar_vista_previa=_confirmar_siempre,
            hay_sesion_activa=lambda: False,
            obtener_cuenta_activa=lambda: None,
        )


def test_rf3_rechaza_si_ya_hay_rostro_enrolado(monkeypatch):
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [0.1, 0.2])

    sesion = _sesion_activa()
    enrolamiento.enrolar(
        capturar_foto=_capturar_foto_falsa,
        confirmar_vista_previa=_confirmar_siempre,
        **sesion,
    )

    with pytest.raises(enrolamiento.RostroYaEnrolado):
        enrolamiento.enrolar(
            capturar_foto=_capturar_foto_falsa,
            confirmar_vista_previa=_confirmar_siempre,
            **sesion,
        )


def test_rf5_a_rf7_reintenta_sin_limite_ante_captura_invalida(monkeypatch):
    intentos = {"n": 0}

    def _validar_rostro_falla_dos_veces(ruta):
        intentos["n"] += 1
        if intentos["n"] <= 2:
            raise lector_de_caras.CapturaInvalida("rostro no detectado")

    monkeypatch.setattr(lector_de_caras, "validar_rostro", _validar_rostro_falla_dos_veces)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [0.1, 0.2])

    enrolamiento.enrolar(
        capturar_foto=_capturar_foto_falsa,
        confirmar_vista_previa=_confirmar_siempre,
        **_sesion_activa(),
    )

    assert intentos["n"] == 3
    assert almacen_rostros.existe_enrolamiento("cuenta_prueba")


def test_cancelar_la_captura_no_se_reintenta():
    intentos = {"n": 0}

    def _capturar_cancelada(ruta_destino):
        intentos["n"] += 1
        raise lector_de_caras.CapturaCancelada("Captura cancelada.")

    with pytest.raises(lector_de_caras.CapturaCancelada):
        enrolamiento.enrolar(
            capturar_foto=_capturar_cancelada,
            confirmar_vista_previa=_confirmar_siempre,
            **_sesion_activa(),
        )

    assert intentos["n"] == 1
    assert not almacen_rostros.existe_enrolamiento("cuenta_prueba")


def test_fallo_de_camara_no_se_reintenta():
    """Caso límite de spec.md: un fallo de cámara se informa y corta el
    flujo, sin dejar un enrolamiento a medias ni reintentar sin fin.
    """
    intentos = {"n": 0}

    def _capturar_falla(ruta_destino):
        intentos["n"] += 1
        raise lector_de_caras.ErrorDeCamara("No se pudo acceder a la cámara.")

    with pytest.raises(lector_de_caras.ErrorDeCamara):
        enrolamiento.enrolar(
            capturar_foto=_capturar_falla,
            confirmar_vista_previa=_confirmar_siempre,
            **_sesion_activa(),
        )

    assert intentos["n"] == 1
    assert not almacen_rostros.existe_enrolamiento("cuenta_prueba")


def test_error_tecnico_de_deteccion_no_se_reintenta(monkeypatch):
    """Un fallo de entorno/configuración de DeepFace no debe disfrazarse
    de captura inválida ni provocar reintentos sin fin.
    """
    intentos = {"n": 0}

    def _validar_rostro(ruta):
        intentos["n"] += 1
        raise lector_de_caras.ErrorDeDeteccion("faltan los archivos haarcascade")

    monkeypatch.setattr(lector_de_caras, "validar_rostro", _validar_rostro)

    with pytest.raises(lector_de_caras.ErrorDeDeteccion):
        enrolamiento.enrolar(
            capturar_foto=_capturar_foto_falsa,
            confirmar_vista_previa=_confirmar_siempre,
            **_sesion_activa(),
        )

    assert intentos["n"] == 1
    assert not almacen_rostros.existe_enrolamiento("cuenta_prueba")


def test_rf6_rechaza_varios_rostros_y_permite_reintentar(monkeypatch):
    intentos = {"n": 0}

    def _validar_rostro(ruta):
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise lector_de_caras.VariosRostrosDetectados("más de un rostro")

    monkeypatch.setattr(lector_de_caras, "validar_rostro", _validar_rostro)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [0.1, 0.2])

    enrolamiento.enrolar(
        capturar_foto=_capturar_foto_falsa,
        confirmar_vista_previa=_confirmar_siempre,
        **_sesion_activa(),
    )

    assert intentos["n"] == 2
    assert almacen_rostros.existe_enrolamiento("cuenta_prueba")


def test_rf9_confirmar_vista_previa_guarda_imagen_y_vector(monkeypatch):
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [0.5, 0.6, 0.7])

    enrolamiento.enrolar(
        capturar_foto=_capturar_foto_falsa,
        confirmar_vista_previa=_confirmar_siempre,
        **_sesion_activa(),
    )

    assert almacen_rostros.existe_enrolamiento("cuenta_prueba")


def test_rf10_falla_generar_vector_descarta_y_vuelve_a_capturar(monkeypatch):
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)

    intentos = {"n": 0}

    def _generar_vector_falla_una_vez(ruta):
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise RuntimeError("fallo técnico simulado")
        return [0.1, 0.2]

    monkeypatch.setattr(lector_de_caras, "generar_vector", _generar_vector_falla_una_vez)

    enrolamiento.enrolar(
        capturar_foto=_capturar_foto_falsa,
        confirmar_vista_previa=_confirmar_siempre,
        **_sesion_activa(),
    )

    assert intentos["n"] == 2
    assert almacen_rostros.existe_enrolamiento("cuenta_prueba")


def test_rf11_rechazar_vista_previa_permite_nueva_captura(monkeypatch):
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [0.1, 0.2])

    llamadas = {"n": 0}

    def _confirmar(ruta_imagen: Path) -> bool:
        llamadas["n"] += 1
        return llamadas["n"] > 1

    enrolamiento.enrolar(
        capturar_foto=_capturar_foto_falsa,
        confirmar_vista_previa=_confirmar,
        **_sesion_activa(),
    )

    assert llamadas["n"] == 2
    assert almacen_rostros.existe_enrolamiento("cuenta_prueba")


def test_rf13_borrar_sin_rostro_enrolado_informa_error():
    with pytest.raises(enrolamiento.SinRostroEnrolado):
        enrolamiento.borrar(**_sesion_activa())


def test_rf12_a_rf14_borrar_elimina_enrolamiento_existente(monkeypatch):
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [0.1, 0.2])

    sesion = _sesion_activa()
    enrolamiento.enrolar(
        capturar_foto=_capturar_foto_falsa,
        confirmar_vista_previa=_confirmar_siempre,
        **sesion,
    )
    assert almacen_rostros.existe_enrolamiento("cuenta_prueba")

    enrolamiento.borrar(**sesion)

    assert not almacen_rostros.existe_enrolamiento("cuenta_prueba")


def test_rf15_sesion_cerrada_a_mitad_del_proceso():
    llamadas = {"n": 0}

    def _hay_sesion_activa():
        llamadas["n"] += 1
        # Activa para RF-1/RF-2/RF-3; se cierra justo al entrar al ciclo
        # de captura, simulando un cierre/expiración a mitad del proceso.
        return llamadas["n"] <= 1

    with pytest.raises(enrolamiento.SesionCerrada):
        enrolamiento.enrolar(
            capturar_foto=_capturar_foto_falsa,
            confirmar_vista_previa=_confirmar_siempre,
            hay_sesion_activa=_hay_sesion_activa,
            obtener_cuenta_activa=lambda: "cuenta_prueba",
        )
