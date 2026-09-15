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
            json.dump({"vector": vector}, archivo_vector)
    except Exception:
        shutil.rmtree(carpeta_temporal, ignore_errors=True)
        raise

    if carpeta_final.exists():
        shutil.rmtree(carpeta_final)
    carpeta_temporal.rename(carpeta_final)


def borrar_enrolamiento(id_cuenta: str) -> None:
    """RF-12: borra por completo el enrolamiento de una cuenta (imagen,
    vector y la carpeta que los contiene), sin dejar residuos.
    """
    carpeta = _carpeta_cuenta(id_cuenta)
    if carpeta.exists():
        shutil.rmtree(carpeta)
