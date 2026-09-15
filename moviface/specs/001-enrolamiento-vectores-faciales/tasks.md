# Tareas — Spec 001: Enrolamiento y almacenamiento de vectores faciales

Basado en `plan.md`. Cada tarea indica qué RF de `spec.md` cubre y en qué archivo vive.

## 1. Infraestructura mínima
- [x] T1.1 — Crear `requirements.txt` (`deepface`, `opencv-python`, `pytest`).
- [x] T1.2 — Crear `static/img/enrolled_faces/.gitkeep` (principio 5 de la constitution).
- [x] T1.3 — Confirmar que `.gitignore` excluye `static/img/enrolled_faces/*` y no excluye el `.gitkeep`.
- [x] T1.4 — Instalar `deepface` y `opencv-python` en el entorno local (`.venv/`).

## 2. Módulo `sesion.py` (stub, precondición de RF-1/RF-2/RF-15)
- [x] T2.1 — `obtener_cuenta_activa()`: devuelve el id de cuenta con sesión iniciada, o `None`.
- [x] T2.2 — `hay_sesion_activa()`: indica si hay sesión iniciada.

## 3. Módulo `lector_de_caras.py` (RF-4 a RF-7, RF-9)
- [x] T3.1 — `capturar_foto(ruta_destino)`: captura con OpenCV y guarda la imagen.
- [x] T3.2 — `validar_rostro(ruta_imagen)`: valida rostro único con DeepFace; lanza `CapturaInvalida` (RF-5/RF-7) o `VariosRostrosDetectados` (RF-6).
- [x] T3.3 — `generar_vector(ruta_imagen)`: genera el embedding facial con `DeepFace.represent()` (RF-9).
- [x] T3.4 — Imports de `cv2`/`deepface` diferidos dentro de cada función (decisión técnica documentada en `plan.md`).

## 4. Módulo `almacen_rostros.py` (RF-3, RF-9, RF-12, RF-13)
- [x] T4.1 — `existe_enrolamiento(id_cuenta)`: revisa el sistema de archivos (fuente única de verdad).
- [x] T4.2 — `guardar_enrolamiento(id_cuenta, ruta_imagen, vector)`: escritura atómica (carpeta temporal → `rename`) para no dejar datos parciales.
- [x] T4.3 — `borrar_enrolamiento(id_cuenta)`: borrado completo de la carpeta de la cuenta, sin residuos.

## 5. Módulo `enrolamiento.py` (orquestación, RF-1 a RF-15)
- [x] T5.1 — `enrolar()`: valida sesión (RF-1/RF-2) → valida duplicado (RF-3) → ciclo de captura/validación con reintentos sin límite (RF-5/RF-6/RF-7) → vista previa (RF-8) → confirmar/rechazar (RF-9/RF-11) → generar y guardar vector, con manejo de fallo técnico (RF-10) → revalidación de sesión durante el ciclo (RF-15).
- [x] T5.2 — `borrar()`: valida sesión → valida que exista enrolamiento (RF-13) → borra (RF-12) → confirma (RF-14).
- [x] T5.3 — Excepciones específicas por caso: `SesionNoIniciada`, `RostroYaEnrolado`, `SinRostroEnrolado`, `SesionCerrada`.

## 6. Punto de entrada `master.py` (principio 8)
- [x] T6.1 — Menú de consola: enrolar rostro / borrar rostro / salir.
- [x] T6.2 — Vista previa por consola con confirmación `s/n` conectada a `enrolamiento.enrolar`.
- [x] T6.3 — Manejo e impresión de los mensajes de error de `enrolamiento.py` sin exponer datos biométricos.

## 7. Pruebas (`/moviface/test`, principio 11)
- [x] T7.1 — `test/conftest.py`: agrega la raíz del proyecto a `sys.path`.
- [x] T7.2 — `test/test_enrolamiento.py`: un caso por bloque de RF (10 casos).
- [x] T7.3 — `test/test_seguridad_biometrica.py`: las 4 pruebas obligatorias del principio 11.
- [x] T7.4 — Ejecutar `pytest test/` y confirmar 100% en verde.

## 8. Verificación manual (pendiente de cámara real)
- [ ] T8.1 — Enrolar la cuenta demo con cámara física y confirmar que se crean `foto.jpg` y `vector.json`.
- [ ] T8.2 — Intentar un segundo enrolamiento sobre la misma cuenta y confirmar el rechazo (RF-3).
- [ ] T8.3 — Borrar el enrolamiento y confirmar que la carpeta desaparece por completo.
- [ ] T8.4 — Volver a enrolar exitosamente tras el borrado.
- [ ] T8.5 — Revisar manualmente que ningún mensaje de consola muestre contenido de la imagen o del vector durante la demo.

## Fuera de esta lista de tareas
- Todo lo que dependa de `specs/002-login` real (reemplazo de `sesion.py`).
- Cualquier tarea de búsqueda/comparación de vectores o cobro (spec futura).
