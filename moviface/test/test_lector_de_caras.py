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
