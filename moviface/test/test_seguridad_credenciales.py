"""Pruebas de seguridad obligatorias sobre credenciales
(docs/constitution.md, principio 11; specs/002-login/spec.md, NFR de
confidencialidad y localidad).
"""

import ast
from pathlib import Path

import cuentas

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

MODULOS_LOGIN = [
    "basedatos.py",
    "cuentas.py",
    "sesion.py",
    "master.py",
    "configurar_base_datos.py",
]

LIBRERIAS_DE_RED_PROHIBIDAS = {
    "requests", "urllib", "urllib2", "urllib3", "http", "httpx",
    "socket", "ftplib", "smtplib", "boto3", "paramiko",
}

_CONTRASENA_SECRETA = "Sup3r$ecreta!"


def test_modulos_de_login_no_importan_librerias_de_red_prohibidas():
    """No debe existir ninguna ruta de red fuera de la conexión local a
    PostgreSQL (spec.md, NFR de localidad). psycopg no está en la lista
    de librerías prohibidas: es la conexión local esperada.
    """
    for nombre_archivo in MODULOS_LOGIN:
        ruta = RAIZ_PROYECTO / nombre_archivo
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=nombre_archivo)
        for nodo in ast.walk(arbol):
            modulos_importados = []
            if isinstance(nodo, ast.Import):
                modulos_importados = [alias.name.split(".")[0] for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos_importados = [nodo.module.split(".")[0]]

            for modulo in modulos_importados:
                assert modulo not in LIBRERIAS_DE_RED_PROHIBIDAS, (
                    f"{nombre_archivo} importa '{modulo}', una librería de red prohibida "
                    "para código que maneja credenciales (constitution.md, principio 11)."
                )


def test_contrasena_nunca_aparece_en_salida_de_consola(conexion_fake, capsys):
    cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", _CONTRASENA_SECRETA, tipo="pasajero")

    salida = capsys.readouterr().out
    assert _CONTRASENA_SECRETA not in salida


def test_hash_de_contrasena_nunca_es_igual_ni_contiene_la_contrasena_en_claro(conexion_fake):
    cuentas.crear_cuenta(conexion_fake, "usuario@correo.com", _CONTRASENA_SECRETA, tipo="pasajero")

    cuenta = cuentas.buscar_cuenta(conexion_fake, "usuario@correo.com")
    assert cuenta["contrasena_hash"] != _CONTRASENA_SECRETA
    assert _CONTRASENA_SECRETA not in cuenta["contrasena_hash"]


def test_error_de_conexion_no_expone_credenciales(monkeypatch):
    """T2.2: el mensaje de error de conexión fallida nunca debe incluir
    host, usuario o contraseña de la base de datos.
    """
    import basedatos

    monkeypatch.delenv("MOVIFACE_DB_HOST", raising=False)
    monkeypatch.delenv("MOVIFACE_DB_NAME", raising=False)
    monkeypatch.delenv("MOVIFACE_DB_USER", raising=False)
    monkeypatch.setenv("MOVIFACE_DB_PASSWORD", "clave-secreta-de-prueba")

    try:
        basedatos.obtener_conexion()
    except basedatos.ErrorConexionBaseDatos as error:
        assert "clave-secreta-de-prueba" not in str(error)
    else:
        raise AssertionError("Se esperaba ErrorConexionBaseDatos con variables incompletas.")
