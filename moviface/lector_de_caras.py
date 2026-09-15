"""Captura y validación de rostros mediante la cámara.

Usa OpenCV (cv2) para la captura de imagen y DeepFace para la
detección de rostros y la generación del vector facial (embedding).

El criterio de "calidad suficiente" de la captura se delega por
completo a DeepFace (decisión tomada explícitamente en
specs/001-enrolamiento-vectores-faciales/spec.md, RF-7): este módulo
no define un umbral propio de nitidez, brillo, etc.
"""

from pathlib import Path

# cv2 (OpenCV) y DeepFace se importan dentro de cada función, no aquí
# arriba: son dependencias pesadas (DeepFace arrastra TensorFlow) que
# solo hacen falta cuando realmente se captura o procesa una imagen,
# no para poder importar este módulo (p. ej. en las pruebas, que
# sustituyen estas funciones por dobles y no necesitan tenerlas
# instaladas).


class CapturaInvalida(Exception):
    """RF-5/RF-7: DeepFace no pudo detectar un rostro con calidad suficiente.

    DeepFace.extract_faces(enforce_detection=True) no distingue en su
    API pública entre "no hay ningún rostro" y "hay un rostro pero la
    calidad no alcanza para detectarlo": ambos casos producen el mismo
    tipo de error interno de la librería. Por eso RF-5 y RF-7 se
    manejan aquí con una sola excepción, consistente con la decisión
    de la spec de delegar el criterio de calidad a la librería.
    """


class VariosRostrosDetectados(Exception):
    """RF-6: la imagen capturada contiene más de un rostro."""


def capturar_foto(ruta_destino: Path) -> None:
    """Toma una foto con la cámara del dispositivo y la guarda en ruta_destino."""
    import cv2

    camara = cv2.VideoCapture(0)
    try:
        capturado, cuadro = camara.read()
        if not capturado:
            raise RuntimeError("No se pudo acceder a la cámara.")
        cv2.imwrite(str(ruta_destino), cuadro)
    finally:
        camara.release()


def validar_rostro(ruta_imagen: Path) -> None:
    """RF-4/RF-5/RF-6/RF-7: valida que la imagen tenga exactamente un
    rostro detectable con calidad suficiente.

    DeepFace.extract_faces() detecta todos los rostros presentes en la
    imagen. Con enforce_detection=True, la propia librería lanza un
    error si no logra detectar ningún rostro con calidad suficiente,
    en vez de devolver una lista vacía.
    """
    from deepface import DeepFace

    try:
        rostros_detectados = DeepFace.extract_faces(
            img_path=str(ruta_imagen),
            enforce_detection=True,
        )
    except ValueError as error:
        raise CapturaInvalida(str(error)) from error

    if len(rostros_detectados) > 1:
        raise VariosRostrosDetectados("Se detectó más de un rostro en la imagen.")


def generar_vector(ruta_imagen: Path) -> list:
    """RF-9: genera el vector facial (embedding) de la imagen confirmada.

    DeepFace.represent() devuelve una lista de resultados (uno por
    rostro detectado); como validar_rostro() ya garantizó que hay
    exactamente un rostro, se usa el primer y único resultado. El
    embedding es la representación numérica del rostro que, en una
    spec futura, permitirá comparar e identificar usuarios.
    """
    from deepface import DeepFace

    resultados = DeepFace.represent(img_path=str(ruta_imagen), enforce_detection=True)
    return resultados[0]["embedding"]
