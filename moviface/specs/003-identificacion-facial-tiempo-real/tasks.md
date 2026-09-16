# Tareas — Spec 003: Identificación facial en tiempo real

Basado en `plan.md` (decisiones D1–D4 acordadas). Cada tarea indica qué RF de `spec.md` cubre y en qué archivo vive.

## 1. Módulo `lector_de_caras.py` (extensión, RF-4/RF-5/RF-6, D1/D2)
- [x] T1.1 — `calcular_distancia(vector_a, vector_b)`: distancia entre dos vectores con `deepface.modules.verification.find_distance`, métrica `cosine` (D2).
- [x] T1.2 — `es_coincidencia(distancia)`: compara contra `verification.find_threshold("VGG-Face", "cosine")`.

## 2. Módulo `almacen_rostros.py` (extensión, RF-9, D4)
- [x] T2.1 — `guardar_enrolamiento()`: agregar el campo `fecha_enrolamiento` (`datetime.now(timezone.utc).isoformat()`) a `vector.json` (D4).
- [x] T2.2 — `listar_cuentas_enroladas()`: recorre `enrolled_faces/`, ignora carpetas temporales (`.<id>.tmp`) y carpetas incompletas, devuelve `id_cuenta`/`vector`/`fecha_enrolamiento` por cuenta; `[]` si `enrolled_faces/` no existe (caso límite: ninguna cuenta enrolada).

## 3. Módulo `identificacion.py` (nuevo, RF-1 a RF-9)
- [x] T3.1 — `identificar()`: captura la imagen (RF-1).
- [x] T3.2 — Ciclo de validación de rostro único/calidad con reintento automático interno (RF-2/RF-3), reutilizando `lector_de_caras.validar_rostro` y sus excepciones `CapturaInvalida`/`VariosRostrosDetectados`.
- [x] T3.3 — Generar el vector de la captura válida con `lector_de_caras.generar_vector` (RF-4).
- [x] T3.4 — Obtener candidatos (`almacen_rostros.listar_cuentas_enroladas`) y calcular la distancia contra cada uno (RF-4).
- [x] T3.5 — Filtrar candidatos por `es_coincidencia`; si ninguno coincide, notificar "no identificado" y **terminar sin reintento automático** — un intento por llamada (RF-5).
- [x] T3.6 — Si hay una o más coincidencias, identificar la de menor distancia; desempate por `fecha_enrolamiento` más antigua ante distancias idénticas (RF-6).
- [x] T3.7 — Notificar únicamente el `id_cuenta` identificado, nunca el vector de ninguna cuenta (RF-7).
- [x] T3.8 — No exigir sesión iniciada: `identificacion.py` no importa `sesion` (RF-8).
- [x] T3.9 — Confirmar que el flujo solo lee vectores (`listar_cuentas_enroladas`, `calcular_distancia`) y no crea/modifica/borra ningún dato de enrolamiento (RF-9).

## 4. Punto de entrada `master.py`
- [x] T4.1 — `import identificacion`.
- [x] T4.2 — Nueva función `_identificar_rostro()`: llama a `identificacion.identificar()`.
- [x] T4.3 — Nueva entrada "Identificar rostro" en el diccionario `opciones` de `_menu()`.

## 5. Pruebas (`/moviface/test`, principio 11)
- [x] T5.1 — `test/test_identificacion.py`: RF-2/RF-3 — captura inválida (varios rostros / calidad insuficiente) reintenta automáticamente hasta una captura válida.
- [x] T5.2 — RF-5 — sin ninguna cuenta enrolada, `identificar()` devuelve `None`, notifica "no identificado" y no reintenta internamente.
- [x] T5.3 — RF-4/RF-6 — un solo candidato coincidente: se identifica esa cuenta.
- [x] T5.4 — RF-6 — varios candidatos coincidentes: se identifica el de menor distancia.
- [x] T5.5 — RF-6/empate — dos candidatos con distancia idéntica: se identifica el de `fecha_enrolamiento` más antigua.
- [x] T5.6 — RF-9 — `listar_cuentas_enroladas()` no se altera (no crea/modifica/borra nada) tras `identificar()`.
- [x] T5.7 — `test/test_seguridad_biometrica.py`: agregar `"identificacion.py"` a `MODULOS_ENROLAMIENTO` (revisión estática de imports de red).
- [x] T5.8 — `test/test_seguridad_biometrica.py`: ningún vector (capturado o de cualquier cuenta enrolada) se expone en notificaciones ni salida de consola durante `identificar()`.
- [x] T5.9 — Ejecutar `pytest test/` y confirmar 100% en verde, sin cámara ni DeepFace real.

## 6. Verificación manual (pendiente de cámara real)

### Bloqueos de entorno resueltos (preexistentes, afectaban también a spec 001)
- [x] T6.0 — `tf_keras`/Keras 3: `from deepface import DeepFace` fallaba porque TensorFlow 2.21 trae Keras 3 y DeepFace/`retina-face` usan la API de Keras 2. Se instaló `tf-keras==2.21.0` y se agregó `tf-keras` a `requirements.txt`.
- [x] T6.0b — `opencv-python` 5.x dejó de incluir los archivos haarcascade en `cv2/data/`, que es lo que usa el detector por defecto de DeepFace: **ninguna** captura se habría podido validar. Se bajó a `opencv-python 4.14.0.94` y se fijó `opencv-python<5` en `requirements.txt`.
- [x] T6.0c — `validar_rostro` atrapaba `ValueError`, y como todas las excepciones de DeepFace heredan de `ValueError`, disfrazaba errores técnicos (como el de T6.0b) de "captura inválida" — provocando reintentos infinitos culpando a la foto. Ahora atrapa `FaceNotDetected` y eleva cualquier otro fallo como `ErrorDeDeteccion`, que no se reintenta y que `master.py` informa. Cubierto por pruebas nuevas en `test_enrolamiento.py` y `test_identificacion.py`.
- [x] T6.0d — Descargados los pesos de VGG-Face (553 MB en `~/.deepface/weights/`). Verificado contra DeepFace real: embedding de 4096 dimensiones, `calcular_distancia(v, v) = 0.0` con `es_coincidencia = True`, umbral `VGG-Face/cosine = 0.68`, y `validar_rostro` lanzando `CapturaInvalida` por falta real de rostro.
- [x] T6.0e — Corrección de `es_coincidencia()`: el comparador es `distancia <= umbral`, no `<` — así es como lo implementa `DeepFace.verify()` internamente. Con `<` se habrían rechazado por error los casos límite de distancia exactamente igual al umbral.

### Hallazgos adicionales de la demo con cámara real (ver `plan.md`, "Hallazgos de la demo")
- [x] T6.0f — `capturar_foto()` lanzaba `RuntimeError` genérico ante un fallo de cámara (incluido no tener permiso del sistema operativo, que fue el caso real en la demo), y ningún flujo lo atrapaba: `master.py` se cerraba con un traceback en vez de volver al menú (viola constitution.md, principio 8). Se creó `ErrorDeCamara` en `lector_de_caras.py`; `_enrolar_rostro()` y `_identificar_rostro()` en `master.py` la atrapan e informan sin reintentar.
- [x] T6.0g — `capturar_foto()` guardaba el primer cuadro entregado por la cámara, casi negro por el calentamiento del sensor (brillo medio ~4/255, medido), lo que producía rechazos en cadena de `validar_rostro()` sin que la persona supiera por qué. Decisión de Hugo (con opciones presentadas): agregar una **ventana de vista previa en vivo** — `capturar_foto()` muestra la cámara en espejo con "ESPACIO: tomar foto — ESC: cancelar" superpuesto; se guarda el cuadro original (sin espejo/texto) del instante en que se pulsa espacio. Nueva excepción `CapturaCancelada` si se pulsa Esc, atrapada en ambos flujos de `master.py`, sin reintento.
- [x] T6.0h — `test/test_lector_de_caras.py` (nuevo): sustituye `cv2` completo por un doble (cuadros de cámara + teclas simuladas) para probar la ventana sin cámara real. 4 casos: guarda el cuadro correcto al pulsar espacio, Esc cancela sin guardar, cámara que no abre, cámara que deja de entregar imagen a medio flujo.
- [x] T6.0i — Casos nuevos en `test_enrolamiento.py` y `test_identificacion.py` para `ErrorDeDeteccion`, `ErrorDeCamara` y `CapturaCancelada`: cada uno confirma un solo intento (sin reintento automático) y, en enrolamiento, que no queda un enrolamiento a medias.
- [x] T6.0j — `pytest test/` reconfirmado en verde tras todos los cambios anteriores: **60 pruebas, 0 fallas.**
- [x] T6.0k — Resultado de la identificación visible en ventana (hallazgo #7 de `plan.md`, decisión de Hugo): con cámara real, la cuenta `hugopocia23@gmail.com` se identificó bien, pero el aviso de una sola línea en la terminal quedaba tapado por el menú. Nueva `lector_de_caras.mostrar_resultado()`: muestra la foto tomada con el mensaje sobre franja verde (identificado) o roja (no identificado), se cierra a los 4 s o con cualquier tecla, y quita acentos porque `cv2.putText` solo dibuja ASCII. `identificacion.identificar()` reorganizado para conservar la foto temporal hasta mostrar la ventana (se borra al terminar); la búsqueda de coincidencias se extrajo a `_buscar_coincidencia()` sin cambios de lógica. El mensaje de la terminal no cambia.
- [x] T6.0l — Pruebas del hallazgo #7: 4 casos en `test_identificacion.py` (ventana con resultado identificado, con no identificado, sin ventana por captura rechazada, foto temporal borrada al terminar), 3 casos en `test_lector_de_caras.py` (verde, rojo sin acentos, sin foto legible no abre ventana), y la prueba de seguridad de `test_seguridad_biometrica.py` ahora también revisa que el texto de la ventana no contenga vectores. `pytest test/`: **67 pruebas, 0 fallas.**

- [ ] T6.1 — Enrolar al menos dos cuentas distintas (`python master.py`). *Avance: `hugopocia23@gmail.com` enrolada con cámara real; falta la segunda cuenta.*
- [ ] T6.2 — Identificar correctamente a cada una por separado. *Avance: `hugopocia23@gmail.com` identificada correctamente con cámara real; falta la segunda cuenta.*
- [ ] T6.3 — Capturar un rostro no enrolado y confirmar el mensaje de "no identificado" (RF-5), sin que el programa siga capturando solo.
- [ ] T6.4 — Revisar manualmente que ningún mensaje de consola muestre contenido del vector de la captura ni de ninguna cuenta enrolada durante la demo.

## Fuera de esta lista de tareas
- Cobro, descuento de saldo o cualquier transacción asociada (spec futura).
- Interfaz real del chofer (spec futura); por ahora la identificación es una opción genérica de `master.py`.
- Registro histórico o auditoría de identificaciones.
- Detección de suplantación ("liveness detection").
