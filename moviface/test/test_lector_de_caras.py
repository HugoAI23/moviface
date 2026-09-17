"""Pruebas de la vista previa en vivo de lector_de_caras.capturar_foto().

Sustituyen el módulo cv2 completo por un doble que simula cuadros de la
cámara y teclas pulsadas, así no hace falta cámara ni ventana real.
"""

import sys
import types

import numpy as np
import pytest

import lector_de_caras

TECLA_NINGUNA = 255


class _CamaraFalsa:
    def __init__(self, cuadros, abre=True):
        self._cuadros = list(cuadros)
        self._abre = abre
        self.liberada = False

    def isOpened(self):
        return self._abre

    def read(self):
        if not self._cuadros:
            return False, None
        return True, self._cuadros.pop(0)

    def release(self):
        self.liberada = True


def _cv2_falso(camara, teclas, imagen_en_disco=None):
    """Construye un cv2 falso que registra lo que se guarda y se muestra."""
    teclas = list(teclas)
    registro = {
        "guardado": None,
        "ventanas_creadas": 0,
        "ventanas_destruidas": 0,
        "textos": [],
        "colores_franja": [],
        "esperas": [],
        "mostrado": None,
    }

    def _wait_key(milisegundos):
        registro["esperas"].append(milisegundos)
        return teclas.pop(0) if teclas else TECLA_NINGUNA

    def _put_text(_imagen, texto, *_args):
        registro["textos"].append(texto)

    def _rectangle(_imagen, _inicio, _fin, color, _grosor):
        registro["colores_franja"].append(color)

    def _imshow(_ventana, imagen):
        registro["mostrado"] = imagen

    def _imwrite(ruta, cuadro):
        registro["guardado"] = cuadro
        return True

    def _named_window(*_args):
        registro["ventanas_creadas"] += 1

    def _destroy_window(*_args):
        registro["ventanas_destruidas"] += 1

    modulo = types.SimpleNamespace(
        VideoCapture=lambda _indice: camara,
        namedWindow=_named_window,
        resizeWindow=lambda *_args: None,
        setWindowProperty=lambda *_args: None,
        destroyWindow=_destroy_window,
        imshow=_imshow,
        waitKey=_wait_key,
        imwrite=_imwrite,
        imread=lambda _ruta: imagen_en_disco,
        flip=lambda cuadro, _eje: cuadro[:, ::-1].copy(),
        putText=_put_text,
        rectangle=_rectangle,
        WINDOW_NORMAL=0,
        WND_PROP_TOPMOST=0,
        FONT_HERSHEY_SIMPLEX=0,
        LINE_AA=0,
        FILLED=-1,
    )
    return modulo, registro


def _cuadro(valor):
    return np.full((720, 1280, 3), valor, dtype=np.uint8)


def test_espacio_guarda_el_cuadro_original_sin_texto_ni_espejo(monkeypatch, tmp_path):
    negro, bueno = _cuadro(4), _cuadro(150)
    bueno[0, 0] = [1, 2, 3]  # marca para detectar si se guardó volteado
    camara = _CamaraFalsa([negro, negro, bueno])
    cv2, registro = _cv2_falso(
        camara, [TECLA_NINGUNA, TECLA_NINGUNA, lector_de_caras._TECLA_CAPTURAR]
    )
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    lector_de_caras.capturar_foto(tmp_path / "captura.jpg")

    # Se guarda el cuadro del momento en que se pulsó espacio, no el
    # primer cuadro negro del calentamiento de la cámara.
    assert registro["guardado"] is bueno
    assert tuple(registro["guardado"][0, 0]) == (1, 2, 3)
    assert camara.liberada
    assert registro["ventanas_destruidas"] == 1


def test_esc_cancela_sin_guardar_nada(monkeypatch, tmp_path):
    camara = _CamaraFalsa([_cuadro(150), _cuadro(150)])
    cv2, registro = _cv2_falso(camara, [TECLA_NINGUNA, lector_de_caras._TECLA_CANCELAR])
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    with pytest.raises(lector_de_caras.CapturaCancelada):
        lector_de_caras.capturar_foto(tmp_path / "captura.jpg")

    assert registro["guardado"] is None
    assert camara.liberada
    assert registro["ventanas_destruidas"] == 1


def test_camara_que_no_abre_no_crea_ventana(monkeypatch, tmp_path):
    camara = _CamaraFalsa([], abre=False)
    cv2, registro = _cv2_falso(camara, [])
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    with pytest.raises(lector_de_caras.ErrorDeCamara):
        lector_de_caras.capturar_foto(tmp_path / "captura.jpg")

    assert registro["ventanas_creadas"] == 0
    assert camara.liberada


def test_resultado_identificado_se_muestra_en_verde_sin_acentos(monkeypatch, tmp_path):
    foto = _cuadro(150)
    cv2, registro = _cv2_falso(_CamaraFalsa([]), [], imagen_en_disco=foto)
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    lector_de_caras.mostrar_resultado(
        tmp_path / "captura.jpg",
        "Rostro identificado: cuenta ana@correo.com.",
        identificado=True,
    )

    assert registro["colores_franja"] == [lector_de_caras._COLOR_IDENTIFICADO]
    assert registro["textos"] == ["Rostro identificado: cuenta ana@correo.com."]
    assert registro["esperas"][0] == lector_de_caras._MILISEGUNDOS_RESULTADO
    assert registro["ventanas_destruidas"] == 1
    # Se dibuja sobre una copia: la foto leída del disco queda intacta.
    assert registro["mostrado"] is not foto


def test_resultado_no_identificado_se_muestra_en_rojo_sin_acentos(monkeypatch, tmp_path):
    cv2, registro = _cv2_falso(_CamaraFalsa([]), [], imagen_en_disco=_cuadro(150))
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    lector_de_caras.mostrar_resultado(
        tmp_path / "captura.jpg",
        "No se identificó a ninguna cuenta enrolada.",
        identificado=False,
    )

    assert registro["colores_franja"] == [lector_de_caras._COLOR_NO_IDENTIFICADO]
    # Las fuentes de OpenCV solo dibujan ASCII: "identificó" -> "identifico".
    assert registro["textos"] == ["No se identifico a ninguna cuenta enrolada."]


def test_resultado_sin_foto_legible_no_abre_ventana(monkeypatch, tmp_path):
    cv2, registro = _cv2_falso(_CamaraFalsa([]), [], imagen_en_disco=None)
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    lector_de_caras.mostrar_resultado(tmp_path / "no_existe.jpg", "x", identificado=True)

    assert registro["ventanas_creadas"] == 0


def test_camara_que_deja_de_entregar_imagen_cierra_la_ventana(monkeypatch, tmp_path):
    camara = _CamaraFalsa([_cuadro(150)])
    cv2, registro = _cv2_falso(camara, [TECLA_NINGUNA, TECLA_NINGUNA])
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    with pytest.raises(lector_de_caras.ErrorDeCamara):
        lector_de_caras.capturar_foto(tmp_path / "captura.jpg")

    assert registro["guardado"] is None
    assert camara.liberada
    assert registro["ventanas_destruidas"] == 1


# --- Spec 004: ventana de resultado del cobro, sin foto (RF-27, plan.md D7) ---


def _cv2_sin_lectura_de_imagenes():
    cv2, registro = _cv2_falso(_CamaraFalsa([]), [])

    def _imread_prohibido(_ruta):
        raise AssertionError("mostrar_mensaje() no debe leer ninguna imagen del disco")

    cv2.imread = _imread_prohibido
    cv2.VideoCapture = lambda _indice: (_ for _ in ()).throw(
        AssertionError("mostrar_mensaje() no debe abrir la cámara")
    )
    return cv2, registro


def test_spec004_mensaje_de_cobro_exitoso_en_verde_sin_foto(monkeypatch):
    cv2, registro = _cv2_sin_lectura_de_imagenes()
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    lector_de_caras.mostrar_mensaje("Cobro realizado: metrobús, $6.", exito=True)

    assert registro["colores_franja"] == [lector_de_caras._COLOR_IDENTIFICADO]
    # Las fuentes de OpenCV solo dibujan ASCII: "metrobús" -> "metrobus".
    assert registro["textos"] == ["Cobro realizado: metrobus, $6."]
    assert registro["esperas"][0] == lector_de_caras._MILISEGUNDOS_RESULTADO
    assert registro["ventanas_creadas"] == 1
    assert registro["ventanas_destruidas"] == 1
    # Lo mostrado es un lienzo generado, no una foto: nada más que el color de fondo.
    assert registro["mostrado"] is not None


def test_spec004_mensaje_de_cobro_rechazado_en_rojo(monkeypatch):
    cv2, registro = _cv2_sin_lectura_de_imagenes()
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    lector_de_caras.mostrar_mensaje("Cobro rechazado: saldo insuficiente (bici, $10).", exito=False)

    assert registro["colores_franja"] == [lector_de_caras._COLOR_NO_IDENTIFICADO]


def test_spec004_mensaje_de_cobro_se_cierra_aunque_falle_la_ventana(monkeypatch):
    cv2, registro = _cv2_sin_lectura_de_imagenes()

    def _imshow_falla(*_args):
        raise RuntimeError("fallo simulado de la ventana")

    cv2.imshow = _imshow_falla
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    with pytest.raises(RuntimeError):
        lector_de_caras.mostrar_mensaje("x", exito=True)

    assert registro["ventanas_destruidas"] == 1


# --- DeepFace no se puede importar por un problema del entorno ---
# Reproduce el error real visto en la demo: TensorFlow 2.21 sin tf-keras hace
# que la importación de DeepFace lance ValueError y cerraba master.py.

import builtins
from pathlib import Path

import cobro
import enrolamiento
import identificacion
import master

_IMPORT_ORIGINAL = builtins.__import__


def _import_sin_deepface(error):
    def _importar(nombre, *args, **kwargs):
        if nombre == "deepface" or nombre.startswith("deepface."):
            raise error
        return _IMPORT_ORIGINAL(nombre, *args, **kwargs)

    return _importar


_ERRORES_DE_ENTORNO = [
    ModuleNotFoundError("No module named 'tf_keras'"),
    ValueError("You have tensorflow 2.21.0 and this requires tf-keras package."),
]


@pytest.mark.parametrize("error", _ERRORES_DE_ENTORNO, ids=["sin_modulo", "valueerror_tf_keras"])
@pytest.mark.parametrize(
    "llamar",
    [
        lambda: lector_de_caras.validar_rostro(Path("captura.jpg")),
        lambda: lector_de_caras.generar_vector(Path("captura.jpg")),
        lambda: lector_de_caras.calcular_distancia([0.1], [0.2]),
        lambda: lector_de_caras.es_coincidencia(0.1),
    ],
    ids=["validar_rostro", "generar_vector", "calcular_distancia", "es_coincidencia"],
)
def test_falla_al_importar_deepface_se_convierte_en_error_de_deteccion(monkeypatch, error, llamar):
    monkeypatch.setattr(builtins, "__import__", _import_sin_deepface(error))

    with pytest.raises(lector_de_caras.ErrorDeDeteccion) as capturado:
        llamar()

    assert "tf-keras" in str(capturado.value)
    assert capturado.value.__cause__ is error


@pytest.mark.parametrize(
    "opcion_menu, modulo, funcion",
    [
        ("_enrolar_rostro", enrolamiento, "enrolar"),
        ("_identificar_rostro", identificacion, "identificar"),
        ("_cobrar_pasajero", cobro, "cobrar"),
    ],
)
def test_master_informa_la_falla_de_deepface_sin_cerrarse(monkeypatch, capsys, opcion_menu, modulo, funcion):
    monkeypatch.setattr(builtins, "__import__", _import_sin_deepface(_ERRORES_DE_ENTORNO[1]))
    monkeypatch.setattr(master, "_obtener_conexion_bd", lambda: None)
    # El flujo llega hasta validar_rostro, que es donde falló en la demo.
    monkeypatch.setattr(
        modulo, funcion, lambda *args, **kwargs: lector_de_caras.validar_rostro(Path("captura.jpg"))
    )

    getattr(master, opcion_menu)()  # no debe lanzar ninguna excepción

    assert "No se pudo cargar DeepFace" in capsys.readouterr().out
