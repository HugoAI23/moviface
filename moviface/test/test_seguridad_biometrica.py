"""Pruebas de seguridad obligatorias sobre datos biométricos
(docs/constitution.md, principio 11). Sin importar qué otras pruebas
se decidan, estas cuatro son innegociables para specs/001.
"""

import ast
from pathlib import Path

import pytest

import almacen_rostros
import enrolamiento
import identificacion
import lector_de_caras

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

MODULOS_ENROLAMIENTO = [
    "sesion.py",
    "lector_de_caras.py",
    "almacen_rostros.py",
    "enrolamiento.py",
    "identificacion.py",
    "cobro.py",
    "eliminacion_cuenta.py",
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


def test_ningun_vector_se_expone_durante_la_identificacion(monkeypatch, capsys):
    """Spec 003: ni el vector capturado ni el de ninguna cuenta enrolada
    pueden aparecer en notificaciones o salidas de consola durante la
    comparación (NFR de confidencialidad acotada).
    """
    vector_enrolado = [0.111111, 0.222222, 0.333333]
    vector_capturado = [0.444444, 0.555555, 0.666666]

    ruta_foto = almacen_rostros.RUTA_BASE.parent / "foto_origen.jpg"
    ruta_foto.parent.mkdir(parents=True, exist_ok=True)
    ruta_foto.write_bytes(b"foto de prueba")
    almacen_rostros.guardar_enrolamiento("cuenta_prueba", ruta_foto, vector_enrolado)

    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: vector_capturado)
    monkeypatch.setattr(lector_de_caras, "calcular_distancia", lambda a, b: 0.10)
    monkeypatch.setattr(lector_de_caras, "es_coincidencia", lambda distancia: True)

    # La ventana de resultado también es una salida hacia quien mira la
    # pantalla: su texto se revisa igual que la consola.
    textos_en_ventana = []
    monkeypatch.setattr(
        lector_de_caras,
        "mostrar_resultado",
        lambda ruta, mensaje, *, identificado: textos_en_ventana.append(mensaje),
    )

    mensajes_capturados = []
    identificado = identificacion.identificar(
        capturar_foto=lambda ruta: ruta.write_bytes(b"BYTES-DE-FOTO-SECRETA"),
        notificar=mensajes_capturados.append,
    )

    assert identificado == "cuenta_prueba"
    assert textos_en_ventana

    salida = (
        "\n".join(mensajes_capturados)
        + "\n".join(textos_en_ventana)
        + capsys.readouterr().out
    )

    for vector in (vector_enrolado, vector_capturado):
        assert str(vector) not in salida
        for componente in vector:
            assert str(componente) not in salida
    assert "BYTES-DE-FOTO-SECRETA" not in salida


def test_spec004_el_cobro_no_expone_identificador_saldo_ni_vector(conexion_fake, monkeypatch, capsys):
    """Spec 004 (NFR de confidencialidad de identidad, RF-21/RF-27): durante
    todo el cobro, con la identificación real de spec 003 (solo cámara y
    DeepFace sustituidos), no aparece en consola ni en ninguna ventana el
    identificador del pasajero, su saldo ni ningún vector.
    """
    from datetime import datetime

    import cobro
    import cuentas
    import sesion

    pasajero = "pasajera.secreta@correo.com"
    vector_enrolado = [0.111111, 0.222222, 0.333333]
    vector_capturado = [0.444444, 0.555555, 0.666666]

    cuentas.crear_cuenta(conexion_fake, "chofer@correo.com", "Abcdef1!", tipo="chofer")
    cuentas.crear_cuenta(conexion_fake, pasajero, "Abcdef1!", tipo="pasajero")
    cuentas.recargar_saldo(conexion_fake, pasajero, 4321)
    sesion.iniciar_sesion(conexion_fake, "chofer@correo.com", "Abcdef1!")

    ruta_foto = almacen_rostros.RUTA_BASE.parent / "foto_origen.jpg"
    ruta_foto.parent.mkdir(parents=True, exist_ok=True)
    ruta_foto.write_bytes(b"foto de prueba")
    almacen_rostros.guardar_enrolamiento(pasajero, ruta_foto, vector_enrolado)

    monkeypatch.setattr(cobro, "_ahora", lambda: datetime(2026, 9, 16, 9, 0))
    monkeypatch.setattr(lector_de_caras, "validar_rostro", lambda ruta: None)
    monkeypatch.setattr(lector_de_caras, "generar_vector", lambda ruta: vector_capturado)
    monkeypatch.setattr(lector_de_caras, "calcular_distancia", lambda a, b: 0.10)
    monkeypatch.setattr(lector_de_caras, "es_coincidencia", lambda distancia: True)

    textos_en_ventanas = []
    monkeypatch.setattr(
        lector_de_caras,
        "mostrar_resultado",
        lambda ruta, mensaje, *, identificado: textos_en_ventanas.append(mensaje),
    )

    def _identificar_real_sin_camara(**kwargs):
        # La identificación de spec 003 corre completa; solo la cámara es un
        # doble. Se inyecta aquí porque los valores por defecto de los
        # parámetros se fijan al importar el módulo y monkeypatch no los alcanza.
        return identificacion.identificar(
            capturar_foto=lambda ruta: ruta.write_bytes(b"BYTES-DE-FOTO-SECRETA"),
            **kwargs,
        )

    cobro.fijar_modalidad(conexion_fake, "metro")
    cobro.cobrar(
        conexion_fake,
        identificar=_identificar_real_sin_camara,
        notificar=lambda mensaje, *, exito: textos_en_ventanas.append(mensaje),
    )

    assert cuentas.obtener_saldo(conexion_fake, pasajero) == 4316  # sí se cobró
    assert len(textos_en_ventanas) == 2  # ventana de identificación + ventana de cobro

    salida = "\n".join(textos_en_ventanas) + capsys.readouterr().out
    assert pasajero not in salida
    assert "@" not in salida
    assert "4321" not in salida and "4316" not in salida
    for vector in (vector_enrolado, vector_capturado):
        for componente in vector:
            assert str(componente) not in salida
    assert "BYTES-DE-FOTO-SECRETA" not in salida


def test_spec004_eliminar_cuenta_no_deja_residuos_ni_expone_la_contrasena(conexion_fake, capsys):
    """Spec 004, RF-34 y NFR de borrado completo (constitution.md, principio 7):
    tras eliminar una cuenta enrolada no queda nada suyo en enrolled_faces, y
    la contraseña de confirmación no aparece en ninguna salida.
    """
    import cuentas
    import eliminacion_cuenta
    import sesion

    contrasena_secreta = "Sup3r$ecreta!"
    identificador = "pasajera.secreta@correo.com"
    cuentas.crear_cuenta(conexion_fake, identificador, contrasena_secreta, tipo="pasajero")
    sesion.iniciar_sesion(conexion_fake, identificador, contrasena_secreta)

    ruta_foto = almacen_rostros.RUTA_BASE.parent / "foto_origen.jpg"
    ruta_foto.parent.mkdir(parents=True, exist_ok=True)
    ruta_foto.write_bytes(b"foto de prueba")
    almacen_rostros.guardar_enrolamiento(identificador, ruta_foto, [0.123456, 0.654321])
    assert (almacen_rostros.RUTA_BASE / identificador).exists()

    mensajes = []
    eliminacion_cuenta.eliminar_cuenta(
        conexion_fake, pedir_contrasena=lambda: contrasena_secreta, notificar=mensajes.append
    )

    # Ningún archivo ni carpeta (incluidas las temporales ".<id>.tmp") de la cuenta.
    assert [ruta for ruta in almacen_rostros.RUTA_BASE.glob("**/*") if identificador in str(ruta)] == []
    assert not cuentas.identificador_en_uso(conexion_fake, identificador)

    salida = "\n".join(mensajes) + capsys.readouterr().out
    assert contrasena_secreta not in salida


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
