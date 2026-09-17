"""Punto de entrada único de moviface (docs/constitution.md, principio 8).

Los módulos de apoyo (sesion.py, cuentas.py, basedatos.py,
lector_de_caras.py, almacen_rostros.py, enrolamiento.py,
identificacion.py, cobro.py, eliminacion_cuenta.py) nunca se ejecutan
directamente: toda interacción con el usuario pasa por este archivo.
"""

from getpass import getpass
from pathlib import Path

import basedatos
import cobro
import cuentas
import eliminacion_cuenta
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


def _crear_cuenta(tipo: str) -> None:
    identificador = input("Correo electrónico: ").strip()
    contrasena = getpass("Contraseña: ")
    try:
        conexion = _obtener_conexion_bd()
        cuentas.crear_cuenta(conexion, identificador, contrasena, tipo)
    except (
        cuentas.IdentificadorInvalido,
        cuentas.IdentificadorEnUso,
        cuentas.TipoInvalido,
        cuentas.ContrasenaInvalida,
        basedatos.ErrorConexionBaseDatos,
    ) as error:
        print(str(error))
        return
    print(f"Cuenta de {tipo} creada correctamente. Ahora puedes iniciar sesión.")


def _crear_cuenta_pasajero() -> None:
    """Spec 004, D6: el tipo lo fija la opción del menú, nunca se escribe a mano."""
    _crear_cuenta("pasajero")


def _crear_cuenta_chofer() -> None:
    _crear_cuenta("chofer")


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
    cobro.reiniciar_estado()  # Spec 004, RF-19
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


def _recargar_saldo() -> None:
    """Spec 004, RF-8 a RF-10: solo el pasajero con sesión recarga su propia cuenta."""
    identificador = sesion.obtener_cuenta_activa()
    if identificador is None:
        print("Debes iniciar sesión como pasajero para recargar saldo.")
        return

    texto_monto = input("Monto a recargar (pesos enteros): ").strip()
    try:
        monto = int(texto_monto)
    except ValueError:
        print("El monto de recarga debe ser un número entero mayor que cero.")
        return

    try:
        conexion = _obtener_conexion_bd()
        cuentas.recargar_saldo(conexion, identificador, monto)
        saldo = cuentas.obtener_saldo(conexion, identificador)
    except (
        cuentas.CuentaNoEsPasajero,
        cuentas.MontoInvalido,
        basedatos.ErrorConexionBaseDatos,
    ) as error:
        print(str(error))
        return
    # El saldo solo se muestra aquí, a su propio dueño; nunca en el cobro (RF-27).
    print(f"Saldo recargado correctamente. Tu saldo actual es ${saldo}.")


def _fijar_modalidad() -> None:
    """Spec 004, RF-13/RF-14: acción propia del menú, independiente del cobro."""
    print("1. Metro ($5)\n2. Metrobús ($6)\n3. Bici ($10)")
    eleccion = input("Elige la modalidad de este turno: ").strip()
    modalidad = {"1": "metro", "2": "metrobus", "3": "bici"}.get(eleccion, eleccion)

    try:
        conexion = _obtener_conexion_bd()
        cobro.fijar_modalidad(conexion, modalidad)
    except (
        cobro.NoEsChofer,
        cobro.ModalidadInvalida,
        cobro.ModalidadYaFijada,
        basedatos.ErrorConexionBaseDatos,
    ) as error:
        print(str(error))
        return

    if cobro.modalidad_en_espera():
        print("Modalidad fijada en espera: se activará al comenzar el siguiente turno.")
    else:
        print("Modalidad fijada para el turno vigente.")


def _cobrar_pasajero() -> None:
    """Spec 004, RF-15 a RF-28: el resultado se muestra en una ventana (D5)."""
    try:
        conexion = _obtener_conexion_bd()
        cobro.cobrar(conexion)
    except (
        cobro.NoEsChofer,
        cobro.SinTurnoVigente,
        cobro.ModalidadNoFijada,
        cobro.SesionCerrada,
        lector_de_caras.CapturaCancelada,
        lector_de_caras.ErrorDeCamara,
        lector_de_caras.ErrorDeDeteccion,
        basedatos.ErrorConexionBaseDatos,
    ) as error:
        print(str(error))


def _eliminar_cuenta() -> None:
    """Spec 004, RF-29 a RF-37: elimina la cuenta con sesión activa."""
    try:
        conexion = _obtener_conexion_bd()
        eliminacion_cuenta.eliminar_cuenta(
            conexion,
            # RF-31: getpass no muestra la contraseña mientras se escribe.
            pedir_contrasena=lambda: getpass(
                "Esta acción no se puede deshacer. Escribe tu contraseña para confirmar: "
            ),
        )
    except (
        eliminacion_cuenta.SesionNoIniciada,
        eliminacion_cuenta.SaldoPendiente,
        eliminacion_cuenta.ContrasenaIncorrecta,
        eliminacion_cuenta.ErrorAlEliminar,
        basedatos.ErrorConexionBaseDatos,
    ) as error:
        print(str(error))


def _menu() -> None:
    opciones = {
        "1": ("Crear cuenta de pasajero", _crear_cuenta_pasajero),
        "2": ("Crear cuenta de chofer", _crear_cuenta_chofer),
        "3": ("Iniciar sesión", _iniciar_sesion),
        "4": ("Cerrar sesión", _cerrar_sesion),
        "5": ("Enrolar rostro", _enrolar_rostro),
        "6": ("Borrar rostro", _borrar_rostro),
        "7": ("Identificar rostro", _identificar_rostro),
        "8": ("Recargar saldo", _recargar_saldo),
        "9": ("Fijar modalidad de transporte", _fijar_modalidad),
        "10": ("Cobrar pasajero", _cobrar_pasajero),
        "11": ("Eliminar mi cuenta", _eliminar_cuenta),
        "12": ("Salir", None),
    }
    while True:
        print("\n--- moviface ---")
        for clave, (etiqueta, _) in opciones.items():
            print(f"{clave}. {etiqueta}")
        eleccion = input("Elige una opción: ").strip()
        accion = opciones.get(eleccion)
        if accion is None:
            print("Opción no válida.")
            continue
        if accion[1] is None:
            break

        if sesion.verificar_expiracion():
            cobro.reiniciar_estado()  # Spec 004, RF-19
            print("Tu sesión expiró por inactividad. Inicia sesión de nuevo.")
        sesion.registrar_actividad()

        accion[1]()


if __name__ == "__main__":
    _menu()
