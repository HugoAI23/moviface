"""Punto de entrada único de moviface (docs/constitution.md, principio 8).

Los módulos de apoyo (sesion.py, cuentas.py, basedatos.py,
lector_de_caras.py, almacen_rostros.py, enrolamiento.py,
identificacion.py) nunca se ejecutan directamente: toda interacción con
el usuario pasa por este archivo.
"""

from getpass import getpass
from pathlib import Path

import basedatos
import cuentas
import enrolamiento
import identificacion
import lector_de_caras
import sesion

_conexion_bd = None


def _obtener_conexion_bd():
    """Abre la conexión a PostgreSQL una sola vez por ejecución del programa."""
    global _conexion_bd
    if _conexion_bd is None:
        _conexion_bd = basedatos.obtener_conexion()
        basedatos.inicializar_esquema(_conexion_bd)
    return _conexion_bd


def _confirmar_vista_previa_consola(ruta_imagen: Path) -> bool:
    print(f"Revisa la foto capturada en: {ruta_imagen}")
    respuesta = input("¿Confirmas esta foto? (s/n): ").strip().lower()
    return respuesta == "s"


def _crear_cuenta() -> None:
    identificador = input("Correo electrónico: ").strip()
    contrasena = getpass("Contraseña: ")
    try:
        conexion = _obtener_conexion_bd()
        cuentas.crear_cuenta(conexion, identificador, contrasena)
    except (
        cuentas.IdentificadorInvalido,
        cuentas.IdentificadorEnUso,
        cuentas.ContrasenaInvalida,
        basedatos.ErrorConexionBaseDatos,
    ) as error:
        print(str(error))
        return
    print("Cuenta creada correctamente. Ahora puedes iniciar sesión.")


def _iniciar_sesion() -> None:
    identificador = input("Correo electrónico: ").strip()
    contrasena = getpass("Contraseña: ")
    try:
        conexion = _obtener_conexion_bd()
        sesion.iniciar_sesion(conexion, identificador, contrasena)
    except (
        sesion.SesionYaActiva,
        sesion.CredencialesInvalidas,
        basedatos.ErrorConexionBaseDatos,
    ) as error:
        print(str(error))
        return
    print("Sesión iniciada correctamente.")


def _cerrar_sesion() -> None:
    try:
        sesion.cerrar_sesion()
    except sesion.SinSesionActiva as error:
        print(str(error))
        return
    print("Sesión cerrada correctamente.")


def _enrolar_rostro() -> None:
    try:
        enrolamiento.enrolar(confirmar_vista_previa=_confirmar_vista_previa_consola)
    except (
        enrolamiento.SesionNoIniciada,
        enrolamiento.RostroYaEnrolado,
        enrolamiento.SesionCerrada,
        lector_de_caras.CapturaCancelada,
        lector_de_caras.ErrorDeCamara,
        lector_de_caras.ErrorDeDeteccion,
    ) as error:
        print(str(error))


def _borrar_rostro() -> None:
    try:
        enrolamiento.borrar()
    except (enrolamiento.SesionNoIniciada, enrolamiento.SinRostroEnrolado) as error:
        print(str(error))


def _identificar_rostro() -> None:
    """Spec 003: cada llamada es un intento completo de identificación.

    Si nadie coincide (RF-5), identificar() informa y termina; reintentar
    es volver a elegir esta opción del menú, no un ciclo automático.
    """
    try:
        identificacion.identificar()
    except (
        lector_de_caras.CapturaCancelada,
        lector_de_caras.ErrorDeCamara,
        lector_de_caras.ErrorDeDeteccion,
    ) as error:
        print(str(error))


def _menu() -> None:
    opciones = {
        "1": ("Crear cuenta", _crear_cuenta),
        "2": ("Iniciar sesión", _iniciar_sesion),
        "3": ("Cerrar sesión", _cerrar_sesion),
        "4": ("Enrolar rostro", _enrolar_rostro),
        "5": ("Borrar rostro", _borrar_rostro),
        "6": ("Identificar rostro", _identificar_rostro),
        "7": ("Salir", None),
    }
    while True:
        print("\n--- moviface ---")
        for clave, (etiqueta, _) in opciones.items():
            print(f"{clave}. {etiqueta}")
        eleccion = input("Elige una opción: ").strip()
        if eleccion == "7":
            break
        accion = opciones.get(eleccion)
        if accion is None:
            print("Opción no válida.")
            continue

        if sesion.verificar_expiracion():
            print("Tu sesión expiró por inactividad. Inicia sesión de nuevo.")
        sesion.registrar_actividad()

        accion[1]()


if __name__ == "__main__":
    _menu()
