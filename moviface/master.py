"""Punto de entrada único de moviface (docs/constitution.md, principio 8).

Los módulos de apoyo (sesion.py, lector_de_caras.py, almacen_rostros.py,
enrolamiento.py) nunca se ejecutan directamente: toda interacción con
el usuario pasa por este archivo.
"""

from pathlib import Path

import enrolamiento


def _confirmar_vista_previa_consola(ruta_imagen: Path) -> bool:
    print(f"Revisa la foto capturada en: {ruta_imagen}")
    respuesta = input("¿Confirmas esta foto? (s/n): ").strip().lower()
    return respuesta == "s"


def _enrolar_rostro() -> None:
    try:
        enrolamiento.enrolar(confirmar_vista_previa=_confirmar_vista_previa_consola)
    except (
        enrolamiento.SesionNoIniciada,
        enrolamiento.RostroYaEnrolado,
        enrolamiento.SesionCerrada,
    ) as error:
        print(str(error))


def _borrar_rostro() -> None:
    try:
        enrolamiento.borrar()
    except (enrolamiento.SesionNoIniciada, enrolamiento.SinRostroEnrolado) as error:
        print(str(error))


def _menu() -> None:
    opciones = {
        "1": ("Enrolar rostro", _enrolar_rostro),
        "2": ("Borrar rostro", _borrar_rostro),
        "3": ("Salir", None),
    }
    while True:
        print("\n--- moviface ---")
        for clave, (etiqueta, _) in opciones.items():
            print(f"{clave}. {etiqueta}")
        eleccion = input("Elige una opción: ").strip()
        if eleccion == "3":
            break
        accion = opciones.get(eleccion)
        if accion is None:
            print("Opción no válida.")
            continue
        accion[1]()


if __name__ == "__main__":
    _menu()
