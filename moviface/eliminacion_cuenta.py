"""Orquesta la eliminación de la propia cuenta.

Implementa specs/004-sistema-cobro-transporte-interfaz-chofer-usuario/spec.md
(RF-29 a RF-37), con las decisiones D8-D10 de su plan.md.

Siempre se elimina la cuenta con sesión activa, nunca una recibida por
parámetro: nadie puede eliminar la cuenta de otra persona (RF-29).
"""

import almacen_rostros
import cobro
import cuentas
import sesion


class SesionNoIniciada(Exception):
    """RF-30: se pidió eliminar una cuenta sin sesión iniciada."""


class SaldoPendiente(Exception):
    """RF-33: un pasajero con saldo mayor que cero no puede eliminar su cuenta."""


class ContrasenaIncorrecta(Exception):
    """RF-32: la contraseña de confirmación no coincide."""


class ErrorAlEliminar(Exception):
    """RF-37: la eliminación no pudo completarse."""


def eliminar_cuenta(conexion, *, pedir_contrasena, notificar=print) -> None:
    """RF-29 a RF-37.

    `pedir_contrasena` se inyecta (master.py usa getpass) para que la
    contraseña nunca pase por print y se pueda probar sin teclado, igual
    que confirmar_vista_previa en enrolamiento.py.
    """
    identificador = sesion.obtener_cuenta_activa()
    if identificador is None:
        raise SesionNoIniciada("Debes iniciar sesión para eliminar tu cuenta.")

    # D10: el saldo se revisa antes de pedir la contraseña, para no pedirla
    # en vano. Una cuenta de chofer o sin tipo no tiene saldo (RF-6, RF-36).
    if (
        cuentas.obtener_tipo(conexion, identificador) == "pasajero"
        and cuentas.obtener_saldo(conexion, identificador) > 0
    ):
        raise SaldoPendiente(
            "Tu saldo debe estar en $0 para eliminar tu cuenta. No se eliminó nada."
        )

    # RF-31/RF-32: aunque haya sesión, se confirma la identidad otra vez.
    if not cuentas.verificar_contrasena(conexion, identificador, pedir_contrasena()):
        raise ContrasenaIncorrecta("Contraseña incorrecta. No se eliminó nada.")

    # D10/RF-37: primero el rostro. Si esto falla, la base de datos no se
    # tocó; si después falla la base, queda la cuenta sin rostro (válido
    # según spec 001), pero nunca un rostro sin cuenta.
    try:
        almacen_rostros.borrar_enrolamiento(identificador)
    except OSError as error:
        raise ErrorAlEliminar(
            "No se pudo borrar tu rostro. No se eliminó nada; vuelve a intentarlo."
        ) from error

    try:
        cuentas.eliminar_cuenta(conexion, identificador)
    except Exception as error:
        # La sesión sigue abierta para que el dueño pueda reintentar (RF-37).
        raise ErrorAlEliminar(
            "Tu rostro fue borrado, pero no se pudo eliminar la cuenta. Vuelve a intentarlo."
        ) from error

    # RF-35
    sesion.cerrar_sesion()
    cobro.reiniciar_estado()
    notificar("Cuenta eliminada correctamente.")
