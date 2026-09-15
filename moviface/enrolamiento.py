"""Orquesta el flujo completo de enrolamiento y borrado de rostros.

Implementa specs/001-enrolamiento-vectores-faciales/spec.md (RF-1 a RF-15).

Los pasos que dependen de hardware o de interacción con el usuario
(capturar_foto, confirmar_vista_previa) y los que dependen de la
sesión (hay_sesion_activa, obtener_cuenta_activa) se reciben como
parámetros con un valor por defecto: así master.py puede conectarlos
a la cámara/consola reales, y las pruebas pueden sustituirlos por
dobles sin depender de hardware ni de specs/002-login.
"""

import tempfile
from pathlib import Path

import almacen_rostros
import lector_de_caras
import sesion


class SesionNoIniciada(Exception):
    """RF-2: no hay una sesión iniciada."""


class RostroYaEnrolado(Exception):
    """RF-3: la cuenta ya tiene un rostro enrolado."""


class SinRostroEnrolado(Exception):
    """RF-13: se pidió borrar un enrolamiento que no existe."""


class SesionCerrada(Exception):
    """RF-15: la sesión se cerró o expiró a mitad del enrolamiento."""


def enrolar(
    *,
    capturar_foto=lector_de_caras.capturar_foto,
    confirmar_vista_previa,
    notificar=print,
    hay_sesion_activa=sesion.hay_sesion_activa,
    obtener_cuenta_activa=sesion.obtener_cuenta_activa,
) -> None:
    """Ejecuta el flujo completo de enrolamiento (RF-1 a RF-11)."""
    if not hay_sesion_activa():
        raise SesionNoIniciada("Debes iniciar sesión antes de enrolar tu rostro.")

    id_cuenta = obtener_cuenta_activa()

    if almacen_rostros.existe_enrolamiento(id_cuenta):
        raise RostroYaEnrolado(
            "Ya tienes un rostro enrolado. Bórralo antes de enrolar uno nuevo."
        )

    while True:
        if not hay_sesion_activa():
            raise SesionCerrada(
                "La sesión se cerró durante el enrolamiento. "
                "Inicia sesión de nuevo para volver a empezar."
            )

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_captura = Path(carpeta_temporal) / "captura.jpg"
            capturar_foto(ruta_captura)

            try:
                lector_de_caras.validar_rostro(ruta_captura)
            except (lector_de_caras.CapturaInvalida, lector_de_caras.VariosRostrosDetectados) as error:
                notificar(f"Captura rechazada: {error}. Intenta de nuevo.")
                continue

            if not confirmar_vista_previa(ruta_captura):
                notificar("Captura descartada. Intenta de nuevo.")
                continue

            if not hay_sesion_activa():
                raise SesionCerrada(
                    "La sesión se cerró durante el enrolamiento. "
                    "Inicia sesión de nuevo para volver a empezar."
                )

            try:
                vector = lector_de_caras.generar_vector(ruta_captura)
                almacen_rostros.guardar_enrolamiento(id_cuenta, ruta_captura, vector)
            except Exception as error:
                notificar(
                    f"No se pudo completar el enrolamiento ({error}). "
                    "Intenta capturar de nuevo."
                )
                continue

            notificar("Rostro enrolado correctamente.")
            return


def borrar(
    *,
    notificar=print,
    hay_sesion_activa=sesion.hay_sesion_activa,
    obtener_cuenta_activa=sesion.obtener_cuenta_activa,
) -> None:
    """RF-12/RF-13/RF-14: borra el enrolamiento de la cuenta con sesión activa."""
    if not hay_sesion_activa():
        raise SesionNoIniciada("Debes iniciar sesión antes de borrar tu enrolamiento.")

    id_cuenta = obtener_cuenta_activa()

    if not almacen_rostros.existe_enrolamiento(id_cuenta):
        raise SinRostroEnrolado("Esta cuenta no tiene ningún rostro enrolado.")

    almacen_rostros.borrar_enrolamiento(id_cuenta)
    notificar("Rostro eliminado correctamente.")
