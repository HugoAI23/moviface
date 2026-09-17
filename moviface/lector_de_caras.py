"""Captura y validación de rostros mediante la cámara.

Usa OpenCV (cv2) para la captura de imagen y DeepFace para la
detección de rostros y la generación del vector facial (embedding).

El criterio de "calidad suficiente" de la captura se delega por
completo a DeepFace (decisión tomada explícitamente en
specs/001-enrolamiento-vectores-faciales/spec.md, RF-7): este módulo
no define un umbral propio de nitidez, brillo, etc.
"""

import unicodedata
from pathlib import Path

# cv2 (OpenCV) y DeepFace se importan dentro de cada función, no aquí
# arriba: son dependencias pesadas (DeepFace arrastra TensorFlow) que
# solo hacen falta cuando realmente se captura o procesa una imagen,
# no para poder importar este módulo (p. ej. en las pruebas, que
# sustituyen estas funciones por dobles y no necesitan tenerlas
# instaladas).

# Modelo y métrica usados para comparar vectores faciales
# (specs/003-identificacion-facial-tiempo-real/plan.md, D1 y D2).
# "VGG-Face" es el modelo que DeepFace usa por defecto y, por lo tanto,
# el que ya usa generar_vector(): el umbral de coincidencia solo es
# válido si se consulta para el mismo modelo con el que se generaron
# los vectores que se están comparando.
_MODELO = "VGG-Face"
_METRICA_DISTANCIA = "cosine"

# Ventana de vista previa en vivo de capturar_foto().
_VENTANA_CAPTURA = "moviface - captura de rostro"
# Ventana de mostrar_resultado(): se cierra sola o al pulsar cualquier tecla.
_VENTANA_RESULTADO = "moviface - resultado"
_MILISEGUNDOS_RESULTADO = 4000
_COLOR_IDENTIFICADO = (0, 200, 0)  # verde (OpenCV usa orden BGR)
_COLOR_NO_IDENTIFICADO = (0, 0, 220)  # rojo
_TECLA_CAPTURAR = 32  # barra espaciadora
_TECLA_CANCELAR = 27  # Esc
_MENSAJE_SIN_CAMARA = (
    "No se pudo acceder a la cámara. Revisa que haya una conectada "
    "y que el sistema le haya dado permiso de cámara a la aplicación "
    "desde la que ejecutas moviface."
)


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


class ErrorDeCamara(Exception):
    """No se pudo usar la cámara del dispositivo.

    Caso límite contemplado en specs/001 y specs/003 ("falla la cámara o
    no hay una disponible"). Se trata igual que ErrorDeDeteccion: no se
    reintenta —ninguna captura nueva va a arreglar una cámara ausente o
    sin permiso— y se informa para volver al menú, en vez de tirar el
    programa entero (constitution.md, principio 8).
    """


class CapturaCancelada(Exception):
    """La persona cerró la vista previa con Esc sin tomar la foto.

    No se reintenta: es una decisión explícita de salir, así que el flujo
    termina y se vuelve al menú.
    """


class ErrorDeDeteccion(Exception):
    """DeepFace falló por una razón técnica, no por la foto.

    Se separa de CapturaInvalida a propósito: un problema de entorno o de
    configuración (p. ej. que falten los archivos haarcascade de OpenCV)
    haría que *toda* captura fuera rechazada, y como RF-5/RF-6/RF-7 de
    spec 001 y RF-2/RF-3 de spec 003 reintentan sin límite, el programa
    quedaría en un ciclo infinito culpando a la foto. Este error no se
    reintenta: se informa y se corta el flujo.
    """


def capturar_foto(ruta_destino: Path) -> None:
    """Muestra la cámara en vivo y guarda la foto cuando se pulsa espacio.

    La vista previa en vivo resuelve además el calentamiento del sensor:
    al abrirse, la cámara entrega unos primeros cuadros casi negros (se
    midió un brillo medio de 4 sobre 255 en el primer cuadro). Como la
    persona decide el momento de la foto, esos cuadros nunca se guardan.

    Lanza ErrorDeCamara si la cámara no abre o deja de entregar imagen,
    y CapturaCancelada si se pulsa Esc.
    """
    import cv2

    camara = cv2.VideoCapture(0)
    ventana_abierta = False
    try:
        if not camara.isOpened():
            raise ErrorDeCamara(_MENSAJE_SIN_CAMARA)

        # WINDOW_NORMAL permite redimensionar la ventana: la cámara entrega
        # 1920x1080 y a tamaño real no cabría en pantalla. TOPMOST la trae
        # al frente, porque se abre desde una terminal.
        cv2.namedWindow(_VENTANA_CAPTURA, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(_VENTANA_CAPTURA, 960, 540)
        cv2.setWindowProperty(_VENTANA_CAPTURA, cv2.WND_PROP_TOPMOST, 1)
        ventana_abierta = True

        while True:
            capturado, cuadro = camara.read()
            if not capturado:
                raise ErrorDeCamara(_MENSAJE_SIN_CAMARA)

            # La vista previa va en espejo y con instrucciones encima, pero
            # se dibuja sobre una copia: la foto guardada es el cuadro
            # original, sin texto ni volteo.
            vista = cv2.flip(cuadro, 1)
            escala = cuadro.shape[1] / 1280
            cv2.putText(
                vista,
                "ESPACIO: tomar foto    ESC: cancelar",
                (int(30 * escala), int(60 * escala)),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2 * escala,
                (0, 255, 0),
                max(1, int(3 * escala)),
                cv2.LINE_AA,
            )
            cv2.imshow(_VENTANA_CAPTURA, vista)

            # waitKey() además de leer el teclado es lo que hace que OpenCV
            # dibuje la ventana; sin llamarlo en cada vuelta no se ve nada.
            tecla = cv2.waitKey(1) & 0xFF
            if tecla == _TECLA_CAPTURAR:
                cv2.imwrite(str(ruta_destino), cuadro)
                return
            if tecla == _TECLA_CANCELAR:
                raise CapturaCancelada("Captura cancelada.")
    finally:
        camara.release()
        if ventana_abierta:
            cv2.destroyWindow(_VENTANA_CAPTURA)
            # En macOS la ventana solo se cierra de verdad después de que
            # OpenCV procesa sus eventos pendientes.
            for _ in range(5):
                cv2.waitKey(1)


def _texto_para_ventana(texto: str) -> str:
    """Quita acentos y eñes: las fuentes de cv2.putText solo dibujan ASCII
    y mostrarían "??" en su lugar ("identificó" -> "identifico").
    """
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def mostrar_resultado(ruta_imagen: Path, mensaje: str, *, identificado: bool) -> None:
    """Spec 003: muestra la foto tomada con el resultado encima, en verde si
    se identificó a alguien y en rojo si no.

    La ventana se cierra sola a los pocos segundos o al pulsar cualquier
    tecla. Solo muestra la foto y el mensaje ya informado en la terminal
    (RF-7): nunca el vector de ninguna cuenta.
    """
    import cv2

    foto = cv2.imread(str(ruta_imagen))
    if foto is None:
        return

    # Misma orientación en espejo que la vista previa, para que la persona
    # reconozca la foto tal como la vio al tomarla.
    vista = cv2.flip(foto, 1)
    alto, ancho = vista.shape[:2]
    escala = ancho / 1280
    color = _COLOR_IDENTIFICADO if identificado else _COLOR_NO_IDENTIFICADO

    # Franja de color en la parte inferior para que el texto se lea sobre
    # cualquier fondo.
    alto_franja = int(90 * escala)
    cv2.rectangle(vista, (0, alto - alto_franja), (ancho, alto), color, cv2.FILLED)
    cv2.putText(
        vista,
        _texto_para_ventana(mensaje),
        (int(30 * escala), alto - int(30 * escala)),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1 * escala,
        (255, 255, 255),
        max(1, int(3 * escala)),
        cv2.LINE_AA,
    )

    cv2.namedWindow(_VENTANA_RESULTADO, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(_VENTANA_RESULTADO, 960, 540)
    cv2.setWindowProperty(_VENTANA_RESULTADO, cv2.WND_PROP_TOPMOST, 1)
    try:
        cv2.imshow(_VENTANA_RESULTADO, vista)
        # waitKey(n) espera hasta n milisegundos o hasta que se pulse una tecla.
        cv2.waitKey(_MILISEGUNDOS_RESULTADO)
    finally:
        cv2.destroyWindow(_VENTANA_RESULTADO)
        for _ in range(5):
            cv2.waitKey(1)


def mostrar_mensaje(mensaje: str, *, exito: bool) -> None:
    """Spec 004, RF-27: ventana de resultado del cobro, en verde si se cobró
    y en rojo si no.

    A diferencia de mostrar_resultado(), no carga ninguna foto (plan.md,
    D7): mostrar el rostro del pasajero lo identificaría visualmente
    aunque el mensaje no diga su cuenta. Se dibuja sobre un lienzo vacío
    con la misma mecánica de cierre (sola a los pocos segundos o al
    pulsar cualquier tecla).
    """
    import cv2
    import numpy as np

    ancho, alto = 1280, 360
    lienzo = np.zeros((alto, ancho, 3), dtype=np.uint8)
    color = _COLOR_IDENTIFICADO if exito else _COLOR_NO_IDENTIFICADO

    cv2.rectangle(lienzo, (0, 0), (ancho, alto), color, cv2.FILLED)
    cv2.putText(
        lienzo,
        _texto_para_ventana(mensaje),
        (40, alto // 2 + 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    cv2.namedWindow(_VENTANA_RESULTADO, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(_VENTANA_RESULTADO, ancho, alto)
    cv2.setWindowProperty(_VENTANA_RESULTADO, cv2.WND_PROP_TOPMOST, 1)
    try:
        cv2.imshow(_VENTANA_RESULTADO, lienzo)
        # waitKey(n) espera hasta n milisegundos o hasta que se pulse una tecla.
        cv2.waitKey(_MILISEGUNDOS_RESULTADO)
    finally:
        cv2.destroyWindow(_VENTANA_RESULTADO)
        for _ in range(5):
            cv2.waitKey(1)


def _importar_deepface():
    """Carga DeepFace y convierte cualquier falla del entorno en ErrorDeDeteccion.

    Importar DeepFace también importa TensorFlow y sus detectores; si falta
    una dependencia (p. ej. tf-keras con TensorFlow >= 2.16, que lanza
    ValueError, no ImportError) la importación misma falla. Antes esa falla
    ocurría fuera de cualquier try y cerraba master.py por completo; así se
    informa y se vuelve al menú, sin reintentar (ninguna foto nueva la arregla).
    """
    try:
        from deepface import DeepFace
        from deepface.modules import verification
        from deepface.modules.exceptions import FaceNotDetected
    except Exception as error:
        raise ErrorDeDeteccion(
            "No se pudo cargar DeepFace por un problema del entorno de Python, "
            "no de la foto. Instala las dependencias de requirements.txt "
            f"(por ejemplo tf-keras). Detalle: {error}"
        ) from error
    return DeepFace, verification, FaceNotDetected


def validar_rostro(ruta_imagen: Path) -> None:
    """RF-4/RF-5/RF-6/RF-7: valida que la imagen tenga exactamente un
    rostro detectable con calidad suficiente.

    DeepFace.extract_faces() detecta todos los rostros presentes en la
    imagen. Con enforce_detection=True, la propia librería lanza
    FaceNotDetected si no logra detectar ningún rostro con calidad
    suficiente, en vez de devolver una lista vacía.

    Se atrapa FaceNotDetected y no ValueError: todas las excepciones de
    DeepFace heredan de ValueError, así que atrapar ValueError también
    disfrazaría de "foto inválida" errores técnicos ajenos a la captura
    (ver ErrorDeDeteccion).
    """
    DeepFace, _, FaceNotDetected = _importar_deepface()

    try:
        rostros_detectados = DeepFace.extract_faces(
            img_path=str(ruta_imagen),
            enforce_detection=True,
        )
    except FaceNotDetected as error:
        raise CapturaInvalida(str(error)) from error
    except Exception as error:
        raise ErrorDeDeteccion(str(error)) from error

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
    DeepFace, _, _ = _importar_deepface()

    resultados = DeepFace.represent(img_path=str(ruta_imagen), enforce_detection=True)
    return resultados[0]["embedding"]


def calcular_distancia(vector_a: list, vector_b: list) -> float:
    """RF-4 (spec 003): distancia entre dos vectores faciales.

    verification.find_distance() es la misma función que DeepFace usa
    internamente en DeepFace.verify(); se llama directamente para poder
    comparar vectores ya guardados, sin volver a procesar las fotos
    enroladas (plan.md de spec 003, D1). A menor distancia, más parecidos
    son los dos rostros.
    """
    _, verification, _ = _importar_deepface()

    return float(verification.find_distance(vector_a, vector_b, _METRICA_DISTANCIA))


def es_coincidencia(distancia: float) -> bool:
    """RF-4/RF-5/RF-6 (spec 003): indica si la distancia alcanza el umbral
    de similitud suficiente para considerar que son la misma persona.

    verification.find_threshold() devuelve el umbral ya calibrado por
    DeepFace para el par modelo/métrica: el criterio de "suficiente" lo
    define la librería, no moviface (RF-5 de spec 003). Se compara con
    "<=" para replicar exactamente el criterio que usa DeepFace.verify()
    al decidir si dos rostros son la misma persona.
    """
    _, verification, _ = _importar_deepface()

    return distancia <= verification.find_threshold(_MODELO, _METRICA_DISTANCIA)
