"""Conexión a PostgreSQL (docs/constitution.md, principio 10).

Único punto de conexión del proyecto: el resto de módulos (cuentas.py)
reciben la conexión ya abierta como parámetro y no importan psycopg
directamente, para poder probarse con un doble en memoria sin
necesitar una base de datos real (specs/002-login/plan.md, D6).
"""

import os

from dotenv import load_dotenv

# Carga las variables de .env al proceso (si existe). Es el único
# lugar del proyecto que lo hace: basta con importar basedatos (lo
# hacen tanto master.py como configurar_base_datos.py) para que las
# variables queden disponibles vía os.environ.
load_dotenv()

ESQUEMA_CUENTAS = """
CREATE TABLE IF NOT EXISTS cuentas (
    id SERIAL PRIMARY KEY,
    identificador TEXT NOT NULL UNIQUE,
    contrasena_hash TEXT NOT NULL,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

# Spec 004 (plan.md, D1): el tipo de una cuenta no es una columna, sino
# en cuál de estas dos tablas tiene fila. Ambas usan `identificador`
# como clave, igual que el resto del proyecto.
ESQUEMA_PASAJEROS = """
CREATE TABLE IF NOT EXISTS pasajeros (
    identificador TEXT PRIMARY KEY REFERENCES cuentas(identificador) ON DELETE CASCADE,
    saldo INTEGER NOT NULL DEFAULT 0 CHECK (saldo >= 0)
);
"""

ESQUEMA_CHOFERES = """
CREATE TABLE IF NOT EXISTS choferes (
    identificador TEXT PRIMARY KEY REFERENCES cuentas(identificador) ON DELETE CASCADE
);
"""

# Solo se cobra a pasajeros (RF-25), por eso referencia `pasajeros` y no
# `cuentas`. Los CHECK son una segunda barrera además de cuentas.py/cobro.py.
ESQUEMA_TRANSACCIONES = """
CREATE TABLE IF NOT EXISTS transacciones (
    id SERIAL PRIMARY KEY,
    identificador TEXT NOT NULL REFERENCES pasajeros(identificador),
    modalidad TEXT NOT NULL CHECK (modalidad IN ('metro', 'metrobus', 'bici')),
    monto INTEGER NOT NULL CHECK (monto > 0),
    fecha TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


class ErrorConexionBaseDatos(Exception):
    """No se pudo establecer conexión con PostgreSQL.

    El mensaje nunca incluye host/usuario/contraseña: solo un aviso
    genérico, para no filtrar credenciales en logs o consola.
    """


def obtener_conexion():
    """Abre una conexión a PostgreSQL a partir de variables de entorno.

    Variables esperadas (ver .env.example): MOVIFACE_DB_HOST,
    MOVIFACE_DB_PORT, MOVIFACE_DB_NAME, MOVIFACE_DB_USER,
    MOVIFACE_DB_PASSWORD.
    """
    import psycopg

    try:
        return psycopg.connect(
            host=os.environ["MOVIFACE_DB_HOST"],
            port=os.environ.get("MOVIFACE_DB_PORT", "5432"),
            dbname=os.environ["MOVIFACE_DB_NAME"],
            user=os.environ["MOVIFACE_DB_USER"],
            password=os.environ["MOVIFACE_DB_PASSWORD"],
        )
    except (psycopg.OperationalError, KeyError) as error:
        raise ErrorConexionBaseDatos(
            "No se pudo conectar a la base de datos. Revisa la configuración."
        ) from error


def inicializar_esquema(conexion) -> None:
    """Crea las tablas si todavía no existen (specs/002-login D3, specs/004 D1).

    El orden importa: cada tabla se crea después de las que referencia.
    """
    with conexion.cursor() as cursor:
        cursor.execute(ESQUEMA_CUENTAS)
        cursor.execute(ESQUEMA_PASAJEROS)
        cursor.execute(ESQUEMA_CHOFERES)
        cursor.execute(ESQUEMA_TRANSACCIONES)
    conexion.commit()
