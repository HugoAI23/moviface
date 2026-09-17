"""Gestión de cuentas de usuario.

Implementa specs/002-login/spec.md (RF-1 a RF-5, RF-13) y, de
specs/004-sistema-cobro-transporte-interfaz-chofer-usuario/spec.md, el
tipo de cuenta y el saldo (RF-1 a RF-10, RF-24, RF-28).

Las funciones reciben la conexión/cursor de PostgreSQL ya abierta como
parámetro (inyección de dependencia): así se pueden probar con un
doble en memoria, sin necesitar una base de datos real
(specs/002-login/plan.md, D6).
"""

import re
import string

import bcrypt

_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CARACTERES_ESPECIALES = set(string.punctuation)

LONGITUD_MINIMA_CONTRASENA = 8

# Spec 004, RF-1/RF-3: únicos tipos de cuenta de esta versión.
TIPOS_VALIDOS = {"pasajero", "chofer"}


class IdentificadorInvalido(Exception):
    """RF-2: el identificador no tiene formato de correo electrónico válido."""


class IdentificadorEnUso(Exception):
    """RF-3: ya existe una cuenta con ese identificador."""


class ContrasenaInvalida(Exception):
    """RF-4: la contraseña no cumple los requisitos mínimos de complejidad."""


class TipoInvalido(Exception):
    """Spec 004, RF-3: el tipo de cuenta no es pasajero ni chofer."""


class CuentaNoEsPasajero(Exception):
    """Spec 004, RF-9: la operación solo aplica a cuentas de pasajero."""


class MontoInvalido(Exception):
    """Spec 004, RF-8/RF-9: el monto no es un entero mayor que cero."""


class SaldoInsuficiente(Exception):
    """Spec 004, RF-24: el saldo no alcanza para el monto a cobrar."""


def validar_formato_identificador(identificador: str) -> None:
    """RF-2: el identificador debe tener formato de correo electrónico."""
    if not identificador or not _PATRON_CORREO.match(identificador):
        raise IdentificadorInvalido(
            "El identificador debe ser un correo electrónico válido."
        )


def validar_complejidad_contrasena(contrasena: str) -> None:
    """RF-4: mínimo 8 caracteres, mayúscula, minúscula, número, carácter
    especial y sin espacios. Esta misma regla aplica a cualquier
    operación futura que establezca o cambie una contraseña.
    """
    if " " in contrasena:
        raise ContrasenaInvalida("La contraseña no puede contener espacios.")

    requisitos_faltantes = []
    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA:
        requisitos_faltantes.append(f"al menos {LONGITUD_MINIMA_CONTRASENA} caracteres")
    if not any(caracter.isupper() for caracter in contrasena):
        requisitos_faltantes.append("una letra mayúscula")
    if not any(caracter.islower() for caracter in contrasena):
        requisitos_faltantes.append("una letra minúscula")
    if not any(caracter.isdigit() for caracter in contrasena):
        requisitos_faltantes.append("un número")
    if not any(caracter in _CARACTERES_ESPECIALES for caracter in contrasena):
        requisitos_faltantes.append("un carácter especial")

    if requisitos_faltantes:
        raise ContrasenaInvalida(
            "La contraseña debe tener " + ", ".join(requisitos_faltantes) + "."
        )


def identificador_en_uso(conexion, identificador: str) -> bool:
    """RF-3: revisa si ya existe una cuenta con ese identificador
    (sensible a mayúsculas/espacios, tal como se guardó)."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM cuentas WHERE identificador = %s", (identificador,)
        )
        return cursor.fetchone() is not None


def crear_cuenta(conexion, identificador: str, contrasena: str, tipo: str) -> None:
    """RF-1: crea la cuenta únicamente si el identificador tiene formato
    válido (RF-2), no está en uso (RF-3) y la contraseña cumple los
    requisitos de complejidad (RF-4). Nunca guarda la contraseña en
    claro (RF-13): se guarda su hash con bcrypt.

    Spec 004 (RF-1 a RF-5): `tipo` es obligatorio. En la misma
    transacción se crea la fila en `pasajeros` (saldo 0) o en `choferes`,
    así nunca queda una cuenta sin tipo si algo falla a medias.
    """
    validar_formato_identificador(identificador)

    if identificador_en_uso(conexion, identificador):
        raise IdentificadorEnUso("Ya existe una cuenta con ese identificador.")

    if tipo not in TIPOS_VALIDOS:
        raise TipoInvalido("El tipo de cuenta debe ser pasajero o chofer.")

    validar_complejidad_contrasena(contrasena)

    contrasena_hash = bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt())
    with conexion.cursor() as cursor:
        cursor.execute(
            "INSERT INTO cuentas (identificador, contrasena_hash) VALUES (%s, %s)",
            (identificador, contrasena_hash.decode("utf-8")),
        )
        if tipo == "pasajero":
            cursor.execute(
                "INSERT INTO pasajeros (identificador, saldo) VALUES (%s, 0)",
                (identificador,),
            )
        else:
            # RF-6: las cuentas de chofer no tienen saldo.
            cursor.execute(
                "INSERT INTO choferes (identificador) VALUES (%s)", (identificador,)
            )
    conexion.commit()


def buscar_cuenta(conexion, identificador: str) -> dict | None:
    """Devuelve la cuenta (identificador + hash de contraseña) o None."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT identificador, contrasena_hash FROM cuentas WHERE identificador = %s",
            (identificador,),
        )
        fila = cursor.fetchone()

    if fila is None:
        return None
    return {"identificador": fila[0], "contrasena_hash": fila[1]}


def verificar_contrasena(conexion, identificador: str, contrasena: str) -> bool:
    """RF-6/RF-7: True si el identificador existe y la contraseña coincide."""
    cuenta = buscar_cuenta(conexion, identificador)
    if cuenta is None:
        return False
    return bcrypt.checkpw(
        contrasena.encode("utf-8"), cuenta["contrasena_hash"].encode("utf-8")
    )


def obtener_tipo(conexion, identificador: str) -> str | None:
    """Spec 004 (plan.md, D3): el tipo se consulta siempre en la base de
    datos, nunca se guarda en memoria. Devuelve "pasajero", "chofer" o
    None si la cuenta no tiene fila en ninguna de las dos tablas.
    """
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pasajeros WHERE identificador = %s", (identificador,)
        )
        if cursor.fetchone() is not None:
            return "pasajero"
        cursor.execute(
            "SELECT 1 FROM choferes WHERE identificador = %s", (identificador,)
        )
        if cursor.fetchone() is not None:
            return "chofer"
    return None


def obtener_saldo(conexion, identificador: str) -> int:
    """Spec 004: saldo entero (RF-7) de una cuenta de pasajero."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT saldo FROM pasajeros WHERE identificador = %s", (identificador,)
        )
        fila = cursor.fetchone()

    if fila is None:
        raise CuentaNoEsPasajero("Solo las cuentas de pasajero tienen saldo.")
    return fila[0]


def recargar_saldo(conexion, identificador: str, monto: int) -> None:
    """Spec 004, RF-8 a RF-10: suma un monto entero mayor que cero al
    saldo de una cuenta de pasajero, sin tope máximo.

    Quién llama es responsable de pasar la cuenta con sesión activa: esta
    función no conoce la sesión, solo valida la cuenta y el monto.
    """
    if obtener_tipo(conexion, identificador) != "pasajero":
        raise CuentaNoEsPasajero("Solo las cuentas de pasajero pueden recargar saldo.")

    # bool es subclase de int en Python: se excluye para que True no
    # cuente como un monto de 1.
    if isinstance(monto, bool) or not isinstance(monto, int) or monto <= 0:
        raise MontoInvalido("El monto de recarga debe ser un número entero mayor que cero.")

    with conexion.cursor() as cursor:
        cursor.execute(
            "UPDATE pasajeros SET saldo = saldo + %s WHERE identificador = %s",
            (monto, identificador),
        )
    conexion.commit()


def descontar_saldo(conexion, identificador: str, monto: int) -> None:
    """Spec 004, RF-24/RF-25/RF-28: descuenta el monto solo si el saldo
    alcanza, así el saldo nunca queda negativo.

    No confirma la transacción: la confirma cobro.py junto con el
    registro de la transacción, para que nunca quede un descuento sin su
    registro ni un registro sin su descuento.
    """
    if obtener_saldo(conexion, identificador) < monto:
        raise SaldoInsuficiente("Saldo insuficiente para este cobro.")

    with conexion.cursor() as cursor:
        cursor.execute(
            "UPDATE pasajeros SET saldo = saldo - %s WHERE identificador = %s",
            (monto, identificador),
        )


def eliminar_cuenta(conexion, identificador: str) -> None:
    """Spec 004, RF-34 (solo la parte de PostgreSQL, plan.md D9).

    Borra primero las tablas que referencian a las demás y confirma todo
    en un solo commit: si algo falla, rollback y no queda la cuenta a
    medio borrar. El rostro lo borra eliminacion_cuenta.py.
    """
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "DELETE FROM transacciones WHERE identificador = %s", (identificador,)
            )
            cursor.execute(
                "DELETE FROM pasajeros WHERE identificador = %s", (identificador,)
            )
            cursor.execute(
                "DELETE FROM choferes WHERE identificador = %s", (identificador,)
            )
            cursor.execute(
                "DELETE FROM cuentas WHERE identificador = %s", (identificador,)
            )
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
