"""Pruebas de specs/003-identificacion-facial-tiempo-real/spec.md (RF-1 a RF-9).

No dependen de cámara real ni de DeepFace: la captura, la validación de
rostro, la generación del vector y la comparación de vectores se
sustituyen por dobles de prueba, igual que en test_enrolamiento.py.

El umbral de coincidencia real lo define DeepFace (RF-5); en estas
pruebas se sustituye por un umbral fijo para poder expresar "coincide"
y "no coincide" de forma determinista.
"""

from pathlib import Path

import pytest

import almacen_rostros
import identificacion
import lector_de_caras

UMBRAL_DE_PRUEBA = 0.5


@pytest.fixture(autouse=True)
def _carpeta_enrolados_temporal(tmp_path, monkeypatch):
    """Aísla cada prueba en una carpeta enrolled_faces temporal."""
    monkeypatch.setattr(almacen_rostros, "RUTA_BASE", tmp_path / "enrolled_faces")


@pytest.fixture(autouse=True)
def resultados_mostrados(monkeypatch):
    """Sustituye la ventana de resultado por un registro de lo que mostraría,
    anotando si la foto seguía existiendo en el momento de mostrarla.
    """
    registro = []

    def _mostrar(ruta_imagen, mensaje, *, identificado):
        registro.append(
            {"mensaje": mensaje, "identificado": identificado, "foto_existe": ruta_imagen.exists()}
        )

    monkeypatch.setattr(lector_de_caras, "mostrar_resultado", _mostrar)
    return registro


@pytest.fixture(autouse=True)
def _umbral_de_prueba(monkeypatch):
    monkeypatch.setattr(
        lector_de_caras, "es_coincidencia", lambda distancia: distancia < UMBRAL_DE_PRUEBA
    )


@pytest.fixture
def enrolar_cuenta(tmp_path):
    """Enrola una cuenta con un vector conocido, usando el mismo camino
    de guardado que usa el enrolamiento real (specs/001).
    """

    def _enrolar(id_cuenta: str, vector: list) -> None:
        ruta_foto = tmp_path / f"{id_cuenta}.jpg"
        ruta_foto.write_bytes(b"foto de prueba, no es una imagen real")
        almacen_rostros.guardar_enrolamiento(id_cuenta, ruta_foto, vector)

    return _enrolar


def _capturar_foto_falsa(ruta_destino: Path) -> None:
    ruta_destino.write_bytes(b"contenido de prueba, no es una foto real")


def _distancias_por_vector(mapa: dict):
    """calcular_distancia falsa: la distancia depende del vector de la
    cuenta contra la que se compara.
    """

    def _calcular(vector_captura: list, vector_cuenta: list) -> float:
        return mapa[tuple(vector_cuenta)]

    return _calcular


def test_rf2_rechaza_varios_rostros_y_permite_reintentar(monkeypatch):
    intentos = {"n": 0}

    def _validar_rostro(ruta):
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise lector_de_caras.VariosRostrosDetectados("más de un rostro")

    monkeypatch.setattr(lector_de_caras, "validar_rostro", _validar_rostro)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [0.1, 0.2])

    identificacion.identificar(capturar_foto=_capturar_foto_falsa, notificar=lambda _: None)

    assert intentos["n"] == 2


def test_rf3_rechaza_captura_invalida_y_reintenta_sin_limite(monkeypatch):
    intentos = {"n": 0}

    def _validar_rostro_falla_dos_veces(ruta):
        intentos["n"] += 1
        if intentos["n"] <= 2:
            raise lector_de_caras.CapturaInvalida("rostro no detectado")

    monkeypatch.setattr(lector_de_caras, "validar_rostro", _validar_rostro_falla_dos_veces)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [0.1, 0.2])

    identificacion.identificar(capturar_foto=_capturar_foto_falsa, notificar=lambda _: None)

    assert intentos["n"] == 3


def test_cancelar_la_captura_no_se_reintenta():
    intentos = {"n": 0}

    def _capturar_cancelada(ruta_destino):
        intentos["n"] += 1
        raise lector_de_caras.CapturaCancelada("Captura cancelada.")

    with pytest.raises(lector_de_caras.CapturaCancelada):
        identificacion.identificar(
            capturar_foto=_capturar_cancelada, notificar=lambda _: None
        )

    assert intentos["n"] == 1


def test_fallo_de_camara_no_se_reintenta():
    """Caso límite de spec.md: si la cámara falla, se informa y se corta,
    sin reintentar (ninguna captura nueva arregla una cámara ausente).
    """
    intentos = {"n": 0}

    def _capturar_falla(ruta_destino):
        intentos["n"] += 1
        raise lector_de_caras.ErrorDeCamara("No se pudo acceder a la cámara.")

    with pytest.raises(lector_de_caras.ErrorDeCamara):
        identificacion.identificar(capturar_foto=_capturar_falla, notificar=lambda _: None)

    assert intentos["n"] == 1


def test_error_tecnico_de_deteccion_no_se_reintenta(monkeypatch):
    """Un fallo de entorno/configuración de DeepFace no es una captura
    inválida: debe cortar el flujo en vez de reintentar sin límite.
    """
    intentos = {"n": 0}

    def _validar_rostro(ruta):
        intentos["n"] += 1
        raise lector_de_caras.ErrorDeDeteccion("faltan los archivos haarcascade")

    monkeypatch.setattr(lector_de_caras, "validar_rostro", _validar_rostro)

    with pytest.raises(lector_de_caras.ErrorDeDeteccion):
        identificacion.identificar(
            capturar_foto=_capturar_foto_falsa, notificar=lambda _: None
        )

    assert intentos["n"] == 1


def test_rf5_sin_cuentas_enroladas_no_identifica_a_nadie(monkeypatch):
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [0.1, 0.2])

    capturas = {"n": 0}

    def _capturar(ruta_destino):
        capturas["n"] += 1
        _capturar_foto_falsa(ruta_destino)

    mensajes = []
    identificado = identificacion.identificar(
        capturar_foto=_capturar, notificar=mensajes.append
    )

    assert identificado is None
    # RF-5: un intento por llamada, sin ciclo automático de recaptura.
    assert capturas["n"] == 1
    assert "No se identificó" in mensajes[-1]


def test_rf5_ninguna_cuenta_alcanza_el_umbral(monkeypatch, enrolar_cuenta):
    enrolar_cuenta("cuenta_lejana", [9.0, 9.0])

    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [0.1, 0.2])
    monkeypatch.setattr(
        lector_de_caras,
        "calcular_distancia",
        _distancias_por_vector({(9.0, 9.0): 0.95}),
    )

    capturas = {"n": 0}

    def _capturar(ruta_destino):
        capturas["n"] += 1
        _capturar_foto_falsa(ruta_destino)

    identificado = identificacion.identificar(
        capturar_foto=_capturar, notificar=lambda _: None
    )

    assert identificado is None
    assert capturas["n"] == 1


def test_rf4_identifica_la_unica_cuenta_coincidente(monkeypatch, enrolar_cuenta):
    enrolar_cuenta("cuenta_ana", [1.0, 1.0])
    enrolar_cuenta("cuenta_beto", [2.0, 2.0])

    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [1.0, 1.0])
    monkeypatch.setattr(
        lector_de_caras,
        "calcular_distancia",
        _distancias_por_vector({(1.0, 1.0): 0.10, (2.0, 2.0): 0.90}),
    )

    identificado = identificacion.identificar(
        capturar_foto=_capturar_foto_falsa, notificar=lambda _: None
    )

    assert identificado == "cuenta_ana"


def test_rf6_entre_varias_coincidencias_gana_la_mayor_similitud(monkeypatch, enrolar_cuenta):
    enrolar_cuenta("cuenta_ana", [1.0, 1.0])
    enrolar_cuenta("cuenta_beto", [2.0, 2.0])
    enrolar_cuenta("cuenta_carla", [3.0, 3.0])

    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [2.0, 2.0])
    monkeypatch.setattr(
        lector_de_caras,
        "calcular_distancia",
        # Ana y Beto coinciden (bajo el umbral); Beto es el más parecido.
        _distancias_por_vector({(1.0, 1.0): 0.40, (2.0, 2.0): 0.05, (3.0, 3.0): 0.80}),
    )

    identificado = identificacion.identificar(
        capturar_foto=_capturar_foto_falsa, notificar=lambda _: None
    )

    assert identificado == "cuenta_beto"


def test_rf6_empate_exacto_gana_la_cuenta_enrolada_primero(monkeypatch, enrolar_cuenta):
    # "zeta" se enrola primero pero va al final por orden alfabético: así
    # la prueba falla si el desempate dependiera del orden de carpetas y
    # no de la fecha de enrolamiento.
    enrolar_cuenta("zeta_primera", [1.0, 1.0])
    enrolar_cuenta("alfa_segunda", [2.0, 2.0])

    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [1.5, 1.5])
    monkeypatch.setattr(
        lector_de_caras,
        "calcular_distancia",
        _distancias_por_vector({(1.0, 1.0): 0.20, (2.0, 2.0): 0.20}),
    )

    identificado = identificacion.identificar(
        capturar_foto=_capturar_foto_falsa, notificar=lambda _: None
    )

    assert identificado == "zeta_primera"


def test_rf7_el_resultado_identificado_se_muestra_en_ventana(
    monkeypatch, enrolar_cuenta, resultados_mostrados
):
    enrolar_cuenta("cuenta_ana", [1.0, 1.0])
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [1.0, 1.0])
    monkeypatch.setattr(
        lector_de_caras, "calcular_distancia", _distancias_por_vector({(1.0, 1.0): 0.10})
    )

    mensajes = []
    identificacion.identificar(capturar_foto=_capturar_foto_falsa, notificar=mensajes.append)

    assert len(resultados_mostrados) == 1
    mostrado = resultados_mostrados[0]
    assert mostrado["identificado"] is True
    assert "cuenta_ana" in mostrado["mensaje"]
    # La ventana muestra lo mismo que la terminal.
    assert mostrado["mensaje"] == mensajes[-1]
    # La foto temporal todavía existe cuando se muestra la ventana.
    assert mostrado["foto_existe"]


def test_spec004_rf21_sin_revelar_identificador_devuelve_la_cuenta_pero_no_la_muestra(
    monkeypatch, enrolar_cuenta, resultados_mostrados
):
    """Excepción acotada de specs/004 (RF-21). El caso por defecto sigue
    cubierto sin cambios por test_rf7_el_resultado_identificado_se_muestra_en_ventana.
    """
    enrolar_cuenta("cuenta_ana", [1.0, 1.0])
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [1.0, 1.0])
    monkeypatch.setattr(
        lector_de_caras, "calcular_distancia", _distancias_por_vector({(1.0, 1.0): 0.10})
    )

    mensajes = []
    identificado = identificacion.identificar(
        capturar_foto=_capturar_foto_falsa,
        notificar=mensajes.append,
        revelar_identificador=False,
    )

    # Quien llama (cobro.py) sí recibe la cuenta para poder cobrarle...
    assert identificado == "cuenta_ana"
    # ...pero no aparece ni en la terminal ni en la ventana.
    assert mensajes == ["Rostro identificado."]
    assert [mostrado["mensaje"] for mostrado in resultados_mostrados] == ["Rostro identificado."]


def test_rf5_el_resultado_no_identificado_se_muestra_en_ventana(
    monkeypatch, resultados_mostrados
):
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [1.0, 1.0])

    identificacion.identificar(capturar_foto=_capturar_foto_falsa, notificar=lambda _: None)

    assert len(resultados_mostrados) == 1
    assert resultados_mostrados[0]["identificado"] is False
    assert "No se identificó" in resultados_mostrados[0]["mensaje"]
    assert resultados_mostrados[0]["foto_existe"]


def test_captura_rechazada_no_muestra_ventana_de_resultado(monkeypatch, resultados_mostrados):
    """Solo se muestra un resultado por identificación, no uno por cada
    captura rechazada (RF-2/RF-3).
    """
    intentos = {"n": 0}

    def _validar_rostro(ruta):
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise lector_de_caras.CapturaInvalida("rostro no detectado")

    monkeypatch.setattr(lector_de_caras, "validar_rostro", _validar_rostro)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [1.0, 1.0])

    identificacion.identificar(capturar_foto=_capturar_foto_falsa, notificar=lambda _: None)

    assert intentos["n"] == 2
    assert len(resultados_mostrados) == 1


def test_la_foto_temporal_se_borra_al_terminar(monkeypatch):
    rutas = []

    def _capturar(ruta_destino):
        rutas.append(ruta_destino)
        _capturar_foto_falsa(ruta_destino)

    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [1.0, 1.0])

    identificacion.identificar(capturar_foto=_capturar, notificar=lambda _: None)

    assert rutas and not rutas[0].exists()
    assert not rutas[0].parent.exists()


def test_rf8_no_exige_sesion_iniciada(monkeypatch, enrolar_cuenta):
    import sesion

    assert not sesion.hay_sesion_activa()

    enrolar_cuenta("cuenta_ana", [1.0, 1.0])
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [1.0, 1.0])
    monkeypatch.setattr(
        lector_de_caras, "calcular_distancia", _distancias_por_vector({(1.0, 1.0): 0.10})
    )

    identificado = identificacion.identificar(
        capturar_foto=_capturar_foto_falsa, notificar=lambda _: None
    )

    assert identificado == "cuenta_ana"


def test_rf9_no_crea_modifica_ni_borra_ningun_enrolamiento(monkeypatch, enrolar_cuenta):
    enrolar_cuenta("cuenta_ana", [1.0, 1.0])
    enrolar_cuenta("cuenta_beto", [2.0, 2.0])

    def _instantanea() -> dict:
        return {
            ruta.relative_to(almacen_rostros.RUTA_BASE).as_posix(): ruta.read_bytes()
            for ruta in sorted(almacen_rostros.RUTA_BASE.glob("**/*"))
            if ruta.is_file()
        }

    antes = _instantanea()

    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [1.0, 1.0])
    monkeypatch.setattr(
        lector_de_caras,
        "calcular_distancia",
        _distancias_por_vector({(1.0, 1.0): 0.10, (2.0, 2.0): 0.90}),
    )

    identificacion.identificar(capturar_foto=_capturar_foto_falsa, notificar=lambda _: None)

    assert _instantanea() == antes
