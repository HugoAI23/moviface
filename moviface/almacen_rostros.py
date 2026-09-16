"""Almacenamiento local de imágenes y vectores faciales por cuenta.

Implementa las garantías de los principios 5 y 7 de docs/constitution.md:
los datos biométricos viven únicamente bajo static/img/enrolled_faces
(nunca se suben al repo, ver .gitignore) y el borrado debe ser completo,
sin residuos, mediante una función explícita del programa — nunca un
borrado manual de archivos.

El sistema de archivos es la única fuente de verdad sobre si una cuenta
ya tiene un rostro enrolado (decisión tomada en el plan de specs/001):
no se duplica ese estado en ninguna base de datos.
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

RUTA_BASE = Path(__file__).resolve().parent / "static" / "img" / "enrolled_faces"

NOMBRE_FOTO = "foto.jpg"
NOMBRE_VECTOR = "vector.json"


def _carpeta_cuenta(id_cuenta: str) -> Path:
    return RUTA_BASE / id_cuenta


def existe_enrolamiento(id_cuenta: str) -> bool:
    """RF-3/RF-13: revisa el sistema de archivos para saber si la cuenta
    ya tiene un rostro (imagen + vector) guardado.
    """
    carpeta = _carpeta_cuenta(id_cuenta)
    return (carpeta / NOMBRE_FOTO).exists() and (carpeta / NOMBRE_VECTOR).exists()


def guardar_enrolamiento(id_cuenta: str, ruta_imagen_confirmada: Path, vector: list) -> None:
    """RF-9: guarda la imagen confirmada y su vector facial, vinculados a la cuenta.

    Escribe primero en una carpeta temporal y solo la mueve a su
    ubicación final al terminar sin errores. Así, si algo falla a
    mitad de la escritura (RF-10), no queda un enrolamiento a medias
    bajo el nombre real de la cuenta.

    Junto al vector se guarda la fecha de enrolamiento
    (specs/003-identificacion-facial-tiempo-real/plan.md, D4): es el
    criterio de desempate cuando dos cuentas empatan en similitud
    durante una identificación.
    """
    RUTA_BASE.mkdir(parents=True, exist_ok=True)

    carpeta_final = _carpeta_cuenta(id_cuenta)
    carpeta_temporal = RUTA_BASE / f".{id_cuenta}.tmp"

    if carpeta_temporal.exists():
        shutil.rmtree(carpeta_temporal)
    carpeta_temporal.mkdir(parents=True)

    try:
        shutil.copyfile(ruta_imagen_confirmada, carpeta_temporal / NOMBRE_FOTO)
        with open(carpeta_temporal / NOMBRE_VECTOR, "w", encoding="utf-8") as archivo_vector:
            json.dump(
                {
                    "vector": vector,
                    "fecha_enrolamiento": datetime.now(timezone.utc).isoformat(),
                },
                archivo_vector,
            )
    except Exception:
        shutil.rmtree(carpeta_temporal, ignore_errors=True)
        raise

    if carpeta_final.exists():
        shutil.rmtree(carpeta_final)
    carpeta_temporal.rename(carpeta_final)


def listar_cuentas_enroladas() -> list[dict]:
    """RF-4/RF-9 (spec 003): devuelve los datos de comparación de cada
    cuenta que tiene un rostro enrolado.

    Es la única lectura de los vectores de todas las cuentas permitida
    en el proyecto, y existe exclusivamente para que el proceso de
    identificación pueda compararlos (excepción documentada al
    principio 4 de docs/constitution.md, en el Contexto de
    specs/003-identificacion-facial-tiempo-real/spec.md). Solo lee: no
    crea, modifica ni borra ningún enrolamiento (RF-9).
    """
    if not RUTA_BASE.exists():
        return []

    cuentas_enroladas = []
    for carpeta in sorted(RUTA_BASE.iterdir()):
        # Las carpetas ".<id_cuenta>.tmp" son escrituras a medias de
        # guardar_enrolamiento(); no representan un enrolamiento válido.
        if not carpeta.is_dir() or carpeta.name.startswith("."):
            continue
        if not existe_enrolamiento(carpeta.name):
            continue

        with open(carpeta / NOMBRE_VECTOR, "r", encoding="utf-8") as archivo_vector:
            datos = json.load(archivo_vector)

        cuentas_enroladas.append(
            {
                "id_cuenta": carpeta.name,
                "vector": datos["vector"],
                "fecha_enrolamiento": datos.get("fecha_enrolamiento", ""),
            }
        )
    return cuentas_enroladas


def borrar_enrolamiento(id_cuenta: str) -> None:
    """RF-12: borra por completo el enrolamiento de una cuenta (imagen,
    vector y la carpeta que los contiene), sin dejar residuos.
    """
    carpeta = _carpeta_cuenta(id_cuenta)
    if carpeta.exists():
        shutil.rmtree(carpeta)
