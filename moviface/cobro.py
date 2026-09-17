"""Orquesta el turno, la modalidad de transporte y el cobro al pasajero.

Implementa specs/004-sistema-cobro-transporte-interfaz-chofer-usuario/spec.md
(RF-11 a RF-28), análogo a como enrolamiento.py e identificacion.py
orquestan las specs 001 y 003.

El estado de turno/modalidad vive solo en memoria de este proceso, igual
que la sesión (sesion.py): se pierde al cerrar el programa y master.py lo
descarta al cerrar sesión (RF-19).

RF-20 (modalidad independiente por chofer) se cumple por diseño: solo
puede haber una sesión iniciada a la vez en el proceso (specs/002-login,
RF-8), así que este estado siempre pertenece al único chofer activo y se
reinicia antes de que otro pueda iniciar sesión.
"""

from datetime import date, datetime

import cuentas
import identificacion
import lector_de_caras
import sesion

# RF-23: montos enteros en pesos mexicanos (RF-7). Las claves van sin
# acento porque también son los valores guardados en `transacciones`.
TARIFAS = {"metro": 5, "metrobus": 6, "bici": 10}
NOMBRES_MODALIDAD = {"metro": "metro", "metrobus": "metrobús", "bici": "bici"}

# RF-12: hora de inicio inclusive, hora de fin exclusive.
TURNOS = {"matutino": (6, 14), "vespertino": (14, 22)}

# Fuente de la hora actual, sustituible en las pruebas para simular
# cualquier turno sin depender del reloj real.
_ahora = datetime.now

_modalidad_fijada: str | None = None
# (fecha, turno) al que quedó atada la modalidad. None con una modalidad
# fijada significa "en espera": se fijó sin turno vigente (RF-14). Se
# guarda la fecha para que el mismo turno de otro día cuente como un
# turno distinto (RF-18).
_turno_de_modalidad: tuple[date, str] | None = None


class NoEsChofer(Exception):
    """RF-11: no hay sesión iniciada o la cuenta activa no es de chofer."""


class SinTurnoVigente(Exception):
    """RF-15: se intentó cobrar entre las 22:00 y las 6:00."""


class ModalidadInvalida(Exception):
    """La modalidad elegida no es metro, metrobús ni bici."""


class ModalidadYaFijada(Exception):
    """Ya hay una modalidad fijada; solo se cambia cerrando sesión (spec.md, Casos límite)."""


class ModalidadNoFijada(Exception):
    """RF-16: se intentó cobrar sin haber fijado la modalidad del turno."""


class SesionCerrada(Exception):
    """RF-26: la sesión del chofer se cerró durante el cobro."""


def _turno_vigente(ahora: datetime | None = None) -> str | None:
    """RF-12: devuelve "matutino", "vespertino" o None si no hay turno."""
    hora = (ahora or _ahora()).hour
    for turno, (inicio, fin) in TURNOS.items():
        if inicio <= hora < fin:
            return turno
    return None


def _requerir_chofer(conexion) -> None:
    """RF-11: mismo mensaje sin importar si no hay sesión o si es de otro tipo."""
    cuenta_activa = sesion.obtener_cuenta_activa()
    if cuenta_activa is None or cuentas.obtener_tipo(conexion, cuenta_activa) != "chofer":
        raise NoEsChofer("Debes iniciar sesión como chofer para continuar.")


def _resolver_estado() -> None:
    """Aplica de forma perezosa las transiciones de turno, el mismo patrón
    que sesion.verificar_expiracion() (specs/002-login, plan.md D4): el
    estado se revisa cuando alguien lo consulta, sin hilos ni temporizadores.
    """
    global _modalidad_fijada, _turno_de_modalidad

    if _modalidad_fijada is None:
        return

    ahora = _ahora()
    turno_actual = _turno_vigente(ahora)

    if _turno_de_modalidad is None:
        # RF-14: la modalidad en espera se activa sola al comenzar un turno.
        # Si todavía no hay turno, sigue en espera.
        if turno_actual is not None:
            _turno_de_modalidad = (ahora.date(), turno_actual)
        return

    if _turno_de_modalidad != (ahora.date(), turno_actual):
        # RF-18: terminó el turno al que estaba atada la modalidad. La
        # transición de "ningún turno" a un turno no pasa por aquí: esa es
        # la rama de espera de arriba.
        _modalidad_fijada = None
        _turno_de_modalidad = None


def fijar_modalidad(conexion, modalidad: str) -> None:
    """RF-13/RF-14: fija la modalidad del turno vigente, o la deja en espera
    si todavía no hay turno.
    """
    global _modalidad_fijada, _turno_de_modalidad

    _requerir_chofer(conexion)

    if modalidad not in TARIFAS:
        raise ModalidadInvalida("La modalidad debe ser metro, metrobús o bici.")

    _resolver_estado()
    if _modalidad_fijada is not None:
        raise ModalidadYaFijada(
            "Ya fijaste tu modalidad para este turno. "
            "Para cambiarla, cierra sesión y vuelve a iniciarla."
        )

    ahora = _ahora()
    turno_actual = _turno_vigente(ahora)
    _modalidad_fijada = modalidad
    _turno_de_modalidad = None if turno_actual is None else (ahora.date(), turno_actual)


def modalidad_en_espera() -> bool:
    """Indica si la modalidad quedó fijada sin turno vigente (RF-14), para
    que master.py lo informe al chofer."""
    _resolver_estado()
    return _modalidad_fijada is not None and _turno_de_modalidad is None


def _modalidad_vigente() -> str | None:
    """RF-16/RF-17: modalidad aplicable al turno vigente, o None."""
    _resolver_estado()
    if _turno_de_modalidad is None:
        return None
    return _modalidad_fijada


def reiniciar_estado() -> None:
    """RF-19: descarta la modalidad (fijada o en espera). master.py la
    llama al cerrar sesión, manualmente o por inactividad."""
    global _modalidad_fijada, _turno_de_modalidad
    _modalidad_fijada = None
    _turno_de_modalidad = None


def cobrar(
    conexion,
    *,
    identificar=identificacion.identificar,
    notificar=lector_de_caras.mostrar_mensaje,
) -> None:
    """RF-15/RF-16 y RF-20 a RF-28: identifica al pasajero y le cobra de
    inmediato la tarifa de la modalidad fijada, sin pedir confirmación.

    Ningún mensaje de este flujo incluye el identificador del pasajero ni
    su saldo (RF-21, RF-22, RF-27).
    """
    _requerir_chofer(conexion)
    chofer_activo = sesion.obtener_cuenta_activa()

    if _turno_vigente() is None:
        raise SinTurnoVigente("No hay un turno vigente (de 6:00 a 22:00). No se puede cobrar.")

    modalidad = _modalidad_vigente()
    if modalidad is None:
        raise ModalidadNoFijada("Fija tu modalidad de transporte antes de cobrar.")

    # RF-21: la identificación no muestra la cuenta encontrada.
    id_pasajero = identificar(revelar_identificador=False)

    if id_pasajero is None:
        notificar("No se identificó a ningún pasajero. No se realizó ningún cobro.", exito=False)
        return

    # RF-26: la identificación usa la cámara y puede tardar; si la sesión
    # del chofer expiró o cambió mientras tanto, se cancela sin descontar.
    if sesion.verificar_expiracion() or sesion.obtener_cuenta_activa() != chofer_activo:
        reiniciar_estado()
        raise SesionCerrada(
            "La sesión del chofer se cerró durante el cobro. No se descontó ningún saldo."
        )

    monto = TARIFAS[modalidad]
    nombre = NOMBRES_MODALIDAD[modalidad]

    try:
        cuentas.descontar_saldo(conexion, id_pasajero, monto)
        _registrar_transaccion(conexion, id_pasajero, modalidad, monto)
        # Descuento y registro se confirman juntos: nunca queda uno sin el otro.
        conexion.commit()
    except cuentas.SaldoInsuficiente:
        conexion.rollback()
        notificar(f"Cobro rechazado: saldo insuficiente ({nombre}, ${monto}).", exito=False)
        return
    except cuentas.CuentaNoEsPasajero:
        # No debería ocurrir (los choferes no enrolan rostro, spec 001), pero
        # si ocurre se rechaza sin tirar el programa ni revelar la cuenta.
        conexion.rollback()
        notificar(f"Cobro rechazado: la cuenta no es de pasajero ({nombre}, ${monto}).", exito=False)
        return
    except Exception:
        conexion.rollback()
        raise

    notificar(f"Cobro realizado: {nombre}, ${monto}.", exito=True)  # RF-25/RF-27


def _registrar_transaccion(conexion, identificador: str, modalidad: str, monto: int) -> None:
    """RF-25: no confirma la transacción, la confirma cobrar()."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "INSERT INTO transacciones (identificador, modalidad, monto) VALUES (%s, %s, %s)",
            (identificador, modalidad, monto),
        )
