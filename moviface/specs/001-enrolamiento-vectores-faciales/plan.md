# Plan — Spec 001: Enrolamiento y almacenamiento de vectores faciales

## Contexto
Al momento de planear esta spec, el repositorio estaba en blanco: sin código, sin `requirements.txt`, sin `master.py`, sin conexión a Postgres, sin la carpeta `static/img/enrolled_faces`. Esta es la primera funcionalidad implementada en el proyecto, basada en `spec.md` (RF-1 a RF-15, aprobada).

La spec 001 depende de `specs/002-login` (aún no redactada) para RF-1, RF-2 y RF-15. Se avanzó con esta spec usando un **stub de sesión** aislado (`sesion.py`) que simula una sesión activa sobre una cuenta demo fija, para no bloquear el desarrollo. Ese stub se reemplazará cuando se redacte e implemente `specs/002-login`, sin tocar el resto del código de enrolamiento.

## Decisiones de diseño acordadas
- **Formato del vector**: se genera el embedding con `DeepFace.represent()` al confirmar la vista previa, y se guarda en un **archivo propio** (`vector.json`) junto a la imagen (`foto.jpg`) — no se depende del caché interno de `DeepFace.find`.
- **Verificación de duplicado (RF-3)**: se revisa directamente el sistema de archivos (existencia de `foto.jpg` y `vector.json` en la carpeta de la cuenta), sin duplicar ese estado en ninguna base de datos.
- **Estructura de carpetas**: una subcarpeta por cuenta dentro de `enrolled_faces`: `enrolled_faces/<id_cuenta>/foto.jpg` y `enrolled_faces/<id_cuenta>/vector.json`.
- **Postgres queda fuera de esta spec**: ningún RF final de 001 exige verificar la cuenta en una base de datos — esa garantía la da la sesión (`specs/002-login`). `sesion.py` solo devuelve un `id_cuenta`, sin tocar ninguna base de datos.
- **Ubicación del código**: directamente en la raíz de `/moviface` (no dentro de `production/`, que queda para otro uso).
- **Imports diferidos de `cv2` y `deepface`**: dentro de `lector_de_caras.py`, `import cv2` y `from deepface import DeepFace` se colocan dentro de cada función que los usa, no en la cabecera del archivo. Son dependencias pesadas (DeepFace arrastra TensorFlow); con el import diferido, el módulo se puede importar y probar (con dobles de prueba) sin tenerlas instaladas. No cambia ningún comportamiento del programa final.

## Estructura de archivos

**Punto de entrada**
- `master.py` — único archivo ejecutable (constitution.md, principio 8). Menú de consola: enrolar rostro, borrar rostro, salir.

**Módulos de apoyo (raíz de `/moviface`, no ejecutables directamente)**
- `sesion.py` — stub de sesión: `obtener_cuenta_activa() -> id_cuenta | None`, `hay_sesion_activa() -> bool`. Se reemplaza por `specs/002-login` sin tocar el resto del flujo.
- `lector_de_caras.py` — captura de imagen (OpenCV) y validación de rostro (DeepFace): detecta rostro único y evalúa calidad, delegando el umbral de calidad a la propia librería (RF-7). Expone `capturar_foto`, `validar_rostro`, `generar_vector` y las excepciones `CapturaInvalida` / `VariosRostrosDetectados`.
- `almacen_rostros.py` — guardar, verificar existencia y borrar por completo la carpeta de enrolamiento de una cuenta. Escritura atómica (carpeta temporal → `rename`) para no dejar datos a medias si algo falla a mitad de la escritura (RF-10 y casos límite). Implementa las garantías de los principios 5 y 7 de la constitution.
- `enrolamiento.py` — orquesta el flujo completo (RF-1 a RF-15): sesión → duplicado → captura → validación de rostro/calidad → vista previa → confirmar/rechazar → generar y guardar vector → manejo de fallos técnicos → cierre/expiración de sesión a mitad de proceso. Expone `enrolar()` y `borrar()`, con las excepciones `SesionNoIniciada`, `RostroYaEnrolado`, `SinRostroEnrolado`, `SesionCerrada`.

**Infraestructura mínima**
- `requirements.txt` — `deepface`, `opencv-python`, `pytest`.
- `static/img/enrolled_faces/.gitkeep` — para que la carpeta exista tras clonar sin exponer contenido real (principio 5).

**Pruebas (`/moviface/test`, principio 11)**
- `test/conftest.py` — agrega la raíz del proyecto a `sys.path` para poder importar los módulos desde las pruebas.
- `test/test_enrolamiento.py` — un caso por cada bloque de RF (sesión no iniciada, duplicado, captura inválida con reintentos sin límite, varios rostros, vista previa aceptar/rechazar, fallo de generación de vector, borrado exitoso, borrado sobre cuenta vacía, cierre de sesión a medio proceso). Usa dobles de prueba inyectados por parámetro, sin depender de cámara ni de DeepFace real.
- `test/test_seguridad_biometrica.py` — las 4 pruebas de seguridad obligatorias del principio 11: `.gitignore` excluye `enrolled_faces`; ningún dato biométrico aparece en logs/salidas de consola; el borrado no deja residuos en disco; ninguno de los módulos de enrolamiento importa librerías de red (revisión estática de imports vía `ast`).

## Verificación
1. `pip install -r requirements.txt` en un entorno virtual local (`.venv/`, ya cubierto por `.gitignore`).
2. `pytest test/` — deben pasar todos los casos de `test_enrolamiento.py` y `test_seguridad_biometrica.py`.
3. Demo manual con `python master.py`: enrolar la cuenta demo con cámara real, confirmar que se crean `enrolled_faces/demo/foto.jpg` y `vector.json`; intentar un segundo enrolamiento y confirmar el rechazo (RF-3); borrar el enrolamiento y confirmar que la carpeta desaparece por completo; volver a enrolar exitosamente.
4. Inspección manual de que ningún mensaje de consola muestre contenido de la imagen o del vector durante toda la demo.

## Pendiente, no cubierto por esta spec
- El reemplazo del stub `sesion.py` por la implementación real de `specs/002-login`.
- Cualquier lógica de búsqueda/comparación de vectores o cobro (spec futura).
- Prueba manual con cámara física (pendiente de un entorno con cámara disponible).
