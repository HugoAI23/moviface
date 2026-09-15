"""Pruebas de seguridad obligatorias sobre datos biométricos
(docs/constitution.md, principio 11). Sin importar qué otras pruebas
se decidan, estas cuatro son innegociables para specs/001.
"""

import ast
from pathlib import Path

import pytest

import almacen_rostros
import enrolamiento
import lector_de_caras

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

MODULOS_ENROLAMIENTO = [
    "sesion.py",
    "lector_de_caras.py",
    "almacen_rostros.py",
    "enrolamiento.py",
    "master.py",
]

LIBRERIAS_DE_RED_PROHIBIDAS = {
    "requests", "urllib", "urllib2", "urllib3", "http", "httpx",
    "socket", "ftplib", "smtplib", "boto3", "paramiko",
}


def test_gitignore_excluye_enrolled_faces():
    """Falla si el patrón de exclusión de datos biométricos se rompe o se elimina."""
    contenido = (RAIZ_PROYECTO / ".gitignore").read_text(encoding="utf-8")
    assert "static/img/enrolled_faces" in contenido


@pytest.fixture(autouse=True)
def _carpeta_enrolados_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(almacen_rostros, "RUTA_BASE", tmp_path / "enrolled_faces")


def test_borrado_no_deja_residuos(monkeypatch):
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: [0.11, 0.22, 0.33])

    id_cuenta = "cuenta_prueba"
    enrolamiento.enrolar(
        capturar_foto=lambda ruta: ruta.write_bytes(b"foto de prueba"),
        confirmar_vista_previa=lambda ruta: True,
        hay_sesion_activa=lambda: True,
        obtener_cuenta_activa=lambda: id_cuenta,
    )

    carpeta_cuenta = almacen_rostros.RUTA_BASE / id_cuenta
    assert carpeta_cuenta.exists()

    enrolamiento.borrar(
        hay_sesion_activa=lambda: True,
        obtener_cuenta_activa=lambda: id_cuenta,
    )

    assert not carpeta_cuenta.exists()
    assert list(almacen_rostros.RUTA_BASE.glob("**/*")) == []


def test_ningun_dato_biometrico_se_notifica_por_consola(monkeypatch, capsys):
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    vector_secreto = [0.123456, 0.654321, 0.999999]
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: vector_secreto)

    contenido_foto = b"BYTES-DE-FOTO-SECRETA"
    mensajes_capturados = []

    enrolamiento.enrolar(
        capturar_foto=lambda ruta: ruta.write_bytes(contenido_foto),
        confirmar_vista_previa=lambda ruta: True,
        notificar=mensajes_capturados.append,
        hay_sesion_activa=lambda: True,
        obtener_cuenta_activa=lambda: "cuenta_prueba",
    )

    salida = "\n".join(mensajes_capturados) + capsys.readouterr().out

    assert str(vector_secreto) not in salida
    for componente in vector_secreto:
        assert str(componente) not in salida
    assert contenido_foto.decode("latin-1") not in salida


def test_modulos_de_enrolamiento_no_importan_librerias_de_red():
    for nombre_archivo in MODULOS_ENROLAMIENTO:
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
                    "para código que maneja datos biométricos (constitution.md, principio 11)."
                )
