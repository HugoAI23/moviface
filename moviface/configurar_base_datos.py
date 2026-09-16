"""Aprovisiona la base de datos de PostgreSQL usada por moviface.

Script de ejecución única: se corre una sola vez (o cada vez que se
levanta un entorno nuevo), antes de usar moviface por primera vez, para
crear la base de datos y su esquema. No es parte del menú de
master.py (constitution.md, principio 8): master.py sigue siendo el
único archivo que el usuario ejecuta para USAR la aplicación; este
script es infraestructura previa, igual que "pip install -r
requirements.txt".

Uso:
    python configurar_base_datos.py

Requiere las mismas variables de entorno que basedatos.py (ver
.env.example), más MOVIFACE_DB_ADMIN_NAME: el nombre de una base de
datos que ya exista en el servidor (normalmente "postgres"), a la que
conectarse para poder crear la base de datos de moviface — PostgreSQL
no permite crear una base de datos mientras se está conectado a ella.
"""

import os

import basedatos


def _nombre_base_datos_admin() -> str:
    return os.environ.get("MOVIFACE_DB_ADMIN_NAME", "postgres")


def _conectar_a_base_administrativa():
    import psycopg

    try:
        conexion = psycopg.connect(
            host=os.environ["MOVIFACE_DB_HOST"],
            port=os.environ.get("MOVIFACE_DB_PORT", "5432"),
            dbname=_nombre_base_datos_admin(),
            user=os.environ["MOVIFACE_DB_USER"],
            password=os.environ["MOVIFACE_DB_PASSWORD"],
        )
    except (psycopg.OperationalError, KeyError) as error:
        raise basedatos.ErrorConexionBaseDatos(
            "No se pudo conectar al servidor de PostgreSQL. Revisa la configuración."
        ) from error

    # CREATE DATABASE no puede ejecutarse dentro de una transacción.
    conexion.autocommit = True
    return conexion


def _base_de_datos_existe(conexion, nombre: str) -> bool:
    with conexion.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (nombre,))
        return cursor.fetchone() is not None


def crear_base_de_datos_si_no_existe() -> None:
    """Crea la base de datos de moviface si todavía no existe en el servidor."""
    from psycopg import sql

    nombre_bd = os.environ["MOVIFACE_DB_NAME"]

    conexion_admin = _conectar_a_base_administrativa()
    try:
        if _base_de_datos_existe(conexion_admin, nombre_bd):
            print(f"La base de datos '{nombre_bd}' ya existe.")
            return

        with conexion_admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre_bd)))
        print(f"Base de datos '{nombre_bd}' creada correctamente.")
    finally:
        conexion_admin.close()


def main() -> None:
    crear_base_de_datos_si_no_existe()

    conexion = basedatos.obtener_conexion()
    try:
        basedatos.inicializar_esquema(conexion)
        print("Tabla 'cuentas' verificada/creada correctamente.")
    finally:
        conexion.close()


if __name__ == "__main__":
    try:
        main()
    except basedatos.ErrorConexionBaseDatos as error:
        print(str(error))
