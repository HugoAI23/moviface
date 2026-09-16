"""Orquesta el flujo completo de identificación facial.

Implementa specs/003-identificacion-facial-tiempo-real/spec.md (RF-1 a RF-9).

Excepción documentada al principio 4 de docs/constitution.md: este es el
único proceso, además del propio enrolamiento, autorizado a leer los
vectores de todas las cuentas enroladas — nunca a modificarlos ni a
exponerlos — y exclusivamente para compararlos contra la captura.

A diferencia de enrolamiento.py, aquí no hay sesión de por medio (RF-8):
la persona identificada es un sujeto pasivo del proceso y quien ejecuta
la identificación es el operador del dispositivo.
"""

import tempfile
from pathlib import Path

import almacen_rostros
import lector_de_caras


def identificar(
    *,
    capturar_foto=lector_de_caras.capturar_foto,
    notificar=print,
) -> str | None:
    """Ejecuta el flujo completo de identificación (RF-1 a RF-9).

    Devuelve el id de la cuenta identificada, o None si ninguna cuenta
    enrolada coincidió con el rostro capturado.

    Reintentos (plan.md de spec 003, "Lógica de reintentos"): el ciclo
    interno solo reintenta ante una captura técnicamente inválida
    (RF-2/RF-3), porque ahí una foto nueva sí puede resolver el problema.
    Cuando la captura es válida pero nadie coincide (RF-5), la función
    termina: volver a intentarlo es una decisión consciente del operador,
    que ejecuta la identificación de nuevo desde master.py.

    El resultado se informa por dos vías: en la terminal (notificar) y en
    una ventana con la foto tomada (lector_de_caras.mostrar_resultado),
    para que quien está frente a la cámara lo vea sin buscarlo entre el
    menú. La foto temporal se conserva hasta mostrar esa ventana y se
    borra al salir de la función.
    """
    with tempfile.TemporaryDirectory() as carpeta_temporal:
        ruta_captura = Path(carpeta_temporal) / "captura.jpg"

        while True:
            capturar_foto(ruta_captura)  # RF-1

            try:
                lector_de_caras.validar_rostro(ruta_captura)
            except (
                lector_de_caras.CapturaInvalida,
                lector_de_caras.VariosRostrosDetectados,
            ) as error:
                # RF-2/RF-3: se informa el motivo y se vuelve a capturar,
                # sin límite de intentos.
                notificar(f"Captura rechazada: {error}. Intenta de nuevo.")
                continue
            break

        vector_captura = lector_de_caras.generar_vector(ruta_captura)  # RF-4
        id_identificado = _buscar_coincidencia(vector_captura)

        if id_identificado is None:
            # RF-5: nadie alcanzó el umbral (incluye el caso de que no haya
            # ninguna cuenta enrolada todavía).
            mensaje = "No se identificó a ninguna cuenta enrolada."
        else:
            # RF-7: se informa el identificador de la cuenta, nunca su vector.
            mensaje = f"Rostro identificado: cuenta {id_identificado}."

        notificar(mensaje)
        lector_de_caras.mostrar_resultado(
            ruta_captura, mensaje, identificado=id_identificado is not None
        )
        return id_identificado


def _buscar_coincidencia(vector_captura: list) -> str | None:
    """RF-4/RF-6: compara el vector contra todas las cuentas enroladas y
    devuelve el id de la que mejor coincide, o None si ninguna alcanza el
    umbral.
    """
    coincidencias = []
    for candidato in almacen_rostros.listar_cuentas_enroladas():
        distancia = lector_de_caras.calcular_distancia(
            vector_captura, candidato["vector"]
        )
        if lector_de_caras.es_coincidencia(distancia):
            coincidencias.append(
                (distancia, candidato["fecha_enrolamiento"], candidato["id_cuenta"])
            )

    if not coincidencias:
        return None

    # RF-6: gana la menor distancia (mayor similitud). Ante un empate
    # exacto, gana la cuenta que se enroló primero: orden determinista.
    coincidencias.sort(key=lambda coincidencia: (coincidencia[0], coincidencia[1]))
    _, _, id_identificado = coincidencias[0]
    return id_identificado
