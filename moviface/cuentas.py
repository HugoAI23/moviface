"""Gestión de cuentas de usuario.

Implementa specs/002-login/spec.md (RF-1 a RF-5, RF-13).

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


class IdentificadorInvalido(Exception):
    """RF-2: el identificador no tiene formato de correo electrónico válido."""


class IdentificadorEnUso(Exception):
    """RF-3: ya existe una cuenta con ese identificador."""


class ContrasenaInvalida(Exception):
    """RF-4: la contraseña no cumple los requisitos mínimos de complejidad."""


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


def crear_cuenta(conexion, identificador: str, contrasena: str) -> None:
    """RF-1: crea la cuenta únicamente si el identificador tiene formato
    válido (RF-2), no está en uso (RF-3) y la contraseña cumple los
    requisitos de complejidad (RF-4). Nunca guarda la contraseña en
    claro (RF-13): se guarda su hash con bcrypt.
    """
    validar_formato_identificador(identificador)

    if identificador_en_uso(conexion, identificador):
        raise IdentificadorEnUso("Ya existe una cuenta con ese identificador.")

    validar_complejidad_contrasena(contrasena)

    contrasena_hash = bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt())
    with conexion.cursor() as cursor:
        cursor.execute(
            "INSERT INTO cuentas (identificador, contrasena_hash) VALUES (%s, %s)",
            (identificador, contrasena_hash.decode("utf-8")),
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
