# Plan — Spec 003: Identificación facial en tiempo real

## Contexto
`spec.md` de esta spec (RF-1 a RF-9, aprobada, sin dudas abiertas) exige comparar una captura contra los vectores de todas las cuentas enroladas por `specs/001-enrolamiento-vectores-faciales`. Hoy `almacen_rostros.py` solo sabe responder "¿esta cuenta puntual tiene un rostro enrolado?" (`existe_enrolamiento`); no existe ninguna forma de listar todas las cuentas enroladas ni de comparar dos vectores entre sí. Tampoco existe ningún criterio de "cuándo se enroló primero" para el caso de empate.

Las decisiones de diseño relevantes ya se revisaron contigo (opciones con ventajas/desventajas) y quedaron resueltas; se documentan a continuación como decisiones acordadas, junto con la lógica de reintentos que se aclaró para evitar una ambigüedad de `spec.md`.

## Archivos que se modifican y por qué (constitution.md, principio 12)
- **`lector_de_caras.py`** (existente, spec 001) — gana la comparación de vectores (distancia + umbral), porque ya es el módulo responsable de todo lo relacionado con DeepFace.
- **`almacen_rostros.py`** (existente, spec 001) — gana el listado de todas las cuentas enroladas y el campo `fecha_enrolamiento` en `vector.json`, porque ya es el módulo responsable de leer/escribir `enrolled_faces`.
- **`identificacion.py`** (nuevo) — orquesta el flujo completo (RF-1 a RF-9), análogo a como `enrolamiento.py` orquesta la spec 001.
- **`master.py`** (existente) — se agrega la opción de menú "Identificar rostro".
- **`test/`** — nuevos archivos de prueba para el módulo nuevo y las funciones agregadas a los módulos existentes.

Ningún comportamiento ya aprobado de `specs/001` ni `specs/002` cambia — solo se agregan funciones nuevas y un campo nuevo en `vector.json`.

## Decisiones de diseño acordadas

### D1 — Cómo comparar el rostro capturado contra los ya enrolados
**Opción A — distancia manual entre vectores ya guardados.** Se reutiliza el vector que cada cuenta ya tiene en `vector.json` (spec 001) y se calcula la distancia entre ese vector y el vector de la nueva captura, usando las funciones de distancia/umbral que trae DeepFace (`find_distance` / `find_threshold`, confirmadas en `deepface.modules.verification` de la versión instalada — 0.0.100). No vuelve a procesar las fotos ya enroladas (rápido) y es coherente con la decisión de spec 001 de generar y guardar el vector una sola vez.

Se descartaron `DeepFace.verify()` imagen-contra-imagen (recalcula el embedding de cada foto guardada en cada identificación) y `DeepFace.find()` sobre `enrolled_faces/` (usa el caché interno de DeepFace que spec 001 decidió explícitamente no usar).

### D2 — Métrica de distancia
**Opción A — `cosine`.** Métrica por defecto que usa DeepFace en la mayoría de sus flujos de verificación, sin ajuste adicional.

### D3 — Estructura de archivos para el nuevo módulo
- `lector_de_caras.py` gana `calcular_distancia(vector_a, vector_b)` y `es_coincidencia(distancia)` (usa el umbral de DeepFace para el modelo/métrica elegidos, D1/D2). El modelo asumido es `"VGG-Face"`, el mismo que usa por defecto `generar_vector()` (no se modifica esa llamada).
- `almacen_rostros.py` gana `listar_cuentas_enroladas()`: recorre `enrolled_faces/`, ignora carpetas temporales (`.<id>.tmp`) y devuelve, por cada cuenta con `foto.jpg` + `vector.json`, su `id_cuenta`, su vector y su `fecha_enrolamiento` (D4). Si `enrolled_faces/` no existe, devuelve `[]` (caso límite: ninguna cuenta enrolada).
- `identificacion.py` (nuevo): expone `identificar()`. Captura → valida rostro único/calidad (reutiliza `lector_de_caras.validar_rostro`, mismas excepciones que spec 001, con reintento automático — ver "Lógica de reintentos") → genera vector (reutiliza `lector_de_caras.generar_vector`) → obtiene candidatos (`almacen_rostros.listar_cuentas_enroladas`) → calcula distancia contra cada uno → filtra por coincidencia → si no hay ninguno, informa "no identificado" y termina (RF-5, sin reintento automático); si hay uno o más, identifica al de menor distancia, desempatando por `fecha_enrolamiento` más antigua (D4).

### D4 — Cómo determinar "quién se enroló primero" para el desempate
**Opción B — campo `fecha_enrolamiento` dentro de `vector.json`.** Se modifica `almacen_rostros.guardar_enrolamiento()` (spec 001) para escribir `datetime.now(timezone.utc).isoformat()` junto al vector al momento de guardar. Dato explícito y confiable, no depende del sistema de archivos ni de si la carpeta se copia/restaura desde otro lado. No hay cuentas ya enroladas en este entorno, así que no hay problema de compatibilidad con datos guardados en el formato viejo.

## Lógica de reintentos — por qué RF-5 no reintenta igual que RF-2/RF-3
`spec.md` usa la misma frase ("permitirá reintentar sin límite de intentos") tanto en RF-2/RF-3 (captura inválida) como en RF-5 (nadie coincide), pero describen fallas de naturaleza distinta:

- **RF-2/RF-3 — falla de la captura.** El problema es la foto (varios rostros, sin rostro, mala calidad); una nueva captura sí puede resolverlo. `enrolamiento.py` ya estableció el precedente de resolver esto con un bucle automático interno (`while True` + `continue`); `identificacion.py` reutiliza el mismo patrón.
- **RF-5 — falla de identidad.** La foto fue técnicamente válida; el problema es que nadie enrolado coincidió. Repetir la captura automáticamente no resuelve nada en el caso general (si la persona no está enrolada, ninguna foto nueva lo cambia), y arriesga que el sistema quede "insistiendo" solo con el rostro de alguien no identificado, sin que nadie decida conscientemente reintentar.

**Regla acordada:** "sin límite de intentos" se cumple en dos niveles según qué se reintenta. Captura (RF-2/RF-3) reintenta automáticamente dentro de la misma llamada a `identificar()`, sin ningún contador. Identificación (RF-5) termina la función tras un solo intento; "sin límite" significa que el operador puede volver a elegir "Identificar rostro" en el menú tantas veces como quiera, pero cada vez es una acción consciente suya, no un loop de cámara. Esto replica el patrón ya usado en `enrolamiento.py` para `RostroYaEnrolado`/`SinRostroEnrolado` (RF-13 de spec 001): una falla de resultado termina la función; una falla de proceso reintenta sola.

**Actores y momento afectados:** esta regla aplica únicamente al flujo de identificación (este documento), disparado por el operador del dispositivo cuando un pasajero aborda — no al flujo de enrolamiento (spec 001, sin cambios), que es cuando el propio usuario, con sesión iniciada, registra su rostro por primera vez. El usuario de transporte identificado es un sujeto pasivo (RF-8): no puede forzar reintentos: cada intento nace y muere en una sola llamada a `identificar()` (una foto, una comparación, un mensaje), y es el operador quien decide si vale la pena volver a intentarlo.

## Diseño concreto de las funciones nuevas

`lector_de_caras.py`:
```python
_MODELO = "VGG-Face"           # mismo modelo por defecto que ya usa generar_vector()
_METRICA_DISTANCIA = "cosine"  # D2

def calcular_distancia(vector_a: list, vector_b: list) -> float:
    """RF-4: distancia entre el vector capturado y el de una cuenta enrolada."""
    from deepface.modules import verification
    return float(verification.find_distance(vector_a, vector_b, _METRICA_DISTANCIA))

def es_coincidencia(distancia: float) -> bool:
    """RF-4/RF-5/RF-6: usa el umbral pre-calibrado de DeepFace para el modelo/métrica."""
    from deepface.modules import verification
    return distancia <= verification.find_threshold(_MODELO, _METRICA_DISTANCIA)
```
Import perezoso dentro de la función, igual que el resto del módulo (DeepFace es una dependencia pesada). **Corrección durante la implementación:** el comparador es `<=`, no `<` — `DeepFace.verify()` usa `distancia <= umbral` internamente (confirmado en el código fuente de `verification.py`); se replica ese criterio exacto en vez de inventar uno propio, para no contradecir RF-5 ("el umbral lo define la librería, no moviface").

`identificacion.py`:
```python
def identificar(*, capturar_foto=lector_de_caras.capturar_foto, notificar=print) -> str | None:
    """RF-1 a RF-9. Devuelve el id_cuenta identificado, o None si no se identificó a nadie."""
    while True:  # RF-2/RF-3: solo este bucle reintenta automáticamente
        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_captura = Path(carpeta_temporal) / "captura.jpg"
            capturar_foto(ruta_captura)
            try:
                lector_de_caras.validar_rostro(ruta_captura)
            except (lector_de_caras.CapturaInvalida, lector_de_caras.VariosRostrosDetectados) as error:
                notificar(f"Captura rechazada: {error}. Intenta de nuevo.")
                continue
            vector_captura = lector_de_caras.generar_vector(ruta_captura)
            break

    coincidencias = []
    for candidato in almacen_rostros.listar_cuentas_enroladas():
        distancia = lector_de_caras.calcular_distancia(vector_captura, candidato["vector"])
        if lector_de_caras.es_coincidencia(distancia):
            coincidencias.append((distancia, candidato["fecha_enrolamiento"], candidato["id_cuenta"]))

    if not coincidencias:
        notificar("No se identificó a nadie. Intenta de nuevo.")  # RF-5: un intento por llamada
        return None

    coincidencias.sort(key=lambda c: (c[0], c[1]))  # RF-6: menor distancia; empate → fecha_enrolamiento más antigua
    _, _, id_identificado = coincidencias[0]
    notificar(f"Rostro identificado: cuenta {id_identificado}.")  # RF-7: solo el id, nunca el vector
    return id_identificado
```
No requiere sesión (RF-8): no importa `sesion`. Solo lee (`listar_cuentas_enroladas`, `calcular_distancia`) — nunca modifica ni borra (RF-9).

`master.py`: `import identificacion`; nueva función `_identificar_rostro()` que llama a `identificacion.identificar()` sin manejo especial de excepciones (mismo precedente que `_enrolar_rostro()` con fallo de cámara: no se captura explícitamente, caso límite ya aceptado sin manejo en spec 001); nueva entrada en el diccionario `opciones` del `_menu()`.

## Hallazgos de la demo con cámara y DeepFace reales

La demo manual (T6.1 en adelante) expuso una cadena de problemas que no aparecían en `pytest test/` porque toda la suite sustituye cámara y DeepFace por dobles. Se documentan aquí para trazabilidad, en el orden en que se descubrieron; el detalle técnico de cada uno vive en `tasks.md`.

### 1–4. Bloqueos de entorno (`tf_keras`, `opencv-python` 5.x, enmascarado de errores, pesos de VGG-Face)
Ver `tasks.md`, sección "Bloqueos de entorno resueltos" (T6.0–T6.0d). Resumen: TensorFlow 2.21 exige `tf-keras`; `opencv-python` 5.x dejó de traer los archivos haarcascade que el detector por defecto de DeepFace necesita (sin ellos, **ninguna** captura se habría podido validar); `validar_rostro()` atrapaba `ValueError` genérico, lo que disfrazaba ese error de entorno como "captura inválida" y habría causado un reintento infinito; y faltaban los pesos de VGG-Face (553 MB, se descargan una sola vez). Los tres primeros ya estaban latentes desde spec 001 — spec 003 solo los hizo evidentes al ser la primera vez que se ejecutó el flujo con cámara real.

### 5. Fallo de cámara tiraba el programa completo
`capturar_foto()` lanzaba `RuntimeError` genérico cuando `camara.read()` fallaba, y ni `enrolamiento.py` ni (el entonces nuevo) `identificacion.py` lo atrapaban: un fallo de cámara —incluido no tener el permiso del sistema operativo concedido, que fue justo lo que pasó en la demo— tiraba `master.py` completo con un traceback, violando el principio 8 (punto de entrada único que no debe cerrarse solo). Se creó `ErrorDeCamara` (excepción propia, ya no `RuntimeError`) y se agregó a los `except` de `_enrolar_rostro()` y `_identificar_rostro()` en `master.py`: se informa y se vuelve al menú, sin reintentar (ninguna captura nueva arregla una cámara sin permiso).

### 6. Ventana de vista previa en vivo (cambio de UX, decisión explícita de Hugo)
Sin vista previa, `capturar_foto()` guardaba el primer cuadro que entregaba la cámara — y se midió que ese primer cuadro tiene un brillo medio de ~4/255 (casi negro), porque el sensor apenas está encendiendo. Eso producía rechazos en cadena de `validar_rostro()` ("Face could not be detected"), todos con la razón correcta (no había ningún rostro visible en una imagen negra) pero sin que la persona supiera por qué.

Se evaluaron tres opciones: (a) descartar automáticamente los primeros N cuadros, (b) esperar a que el brillo se estabilizara con un umbral propio, (c) una ventana de vista previa en vivo donde la persona misma decide cuándo tomar la foto. Hugo eligió (c): `capturar_foto()` ahora abre una ventana con la imagen de la cámara en espejo, con las instrucciones "ESPACIO: tomar foto — ESC: cancelar" superpuestas. El cuadro que se guarda es siempre el original (sin espejo ni texto), tomado en el instante exacto en que se pulsa espacio — así la persona controla el encuadre y el momento, y el problema del calentamiento del sensor queda resuelto como efecto secundario, sin que moviface tenga que definir un umbral propio de brillo (RF-7 de spec 001 sigue intacto: la calidad la sigue juzgando solo DeepFace).

Pulsar Esc cancela y lanza la nueva excepción `CapturaCancelada`, que tampoco se reintenta (es una decisión consciente de salir) y que `master.py` atrapa en ambos flujos para volver al menú.

### 7. El resultado de la identificación pasaba desapercibido (cambio de UX, decisión explícita de Hugo)
Con cámara real, la identificación funcionó (reconoció la cuenta `hugopocia23@gmail.com`), pero Hugo no vio el resultado: RF-5/RF-7 se informaban con una sola línea en la terminal, y el menú se reimprimía justo debajo mientras la atención estaba en la ventana de la cámara. Se evaluaron tres opciones: (a) pausa "Presiona Enter" antes del menú, (b) mostrar el resultado en una ventana, (c) dejarlo igual. Hugo eligió (b).

Como DeepFace y la comparación corren **después** de cerrar la vista previa, el resultado se muestra en una ventana nueva (`lector_de_caras.mostrar_resultado()`) con la foto recién tomada, en espejo como en la vista previa, y el mensaje sobre una franja **verde** (identificado) o **roja** (no identificado). Se cierra sola a los 4 segundos o al pulsar cualquier tecla. El mensaje de la terminal se mantiene idéntico (es el canal que verifican las pruebas de RF-5/RF-7).

Consecuencias en el diseño:
- `identificacion.identificar()` se reorganizó para que la carpeta temporal con la foto siga viva hasta mostrar la ventana (antes se borraba justo después de generar el vector). La foto se sigue borrando al terminar la función. La búsqueda de coincidencias se extrajo a `_buscar_coincidencia()`, sin cambiar su lógica (RF-4/RF-6).
- Las fuentes de `cv2.putText` solo dibujan ASCII, así que la ventana quita acentos y eñes ("identificó" → "identifico"); la terminal conserva el texto en español correcto.
- La ventana solo muestra la foto y el mismo mensaje de la terminal: nunca un vector (RF-7). La prueba de seguridad de spec 003 ahora también revisa el texto de la ventana.
- Solo aplica al flujo de identificación. Las capturas rechazadas (RF-2/RF-3) no abren ventana de resultado: siguen informándose en la terminal y reabriendo la vista previa.

### 8. `tf-keras` faltante cerraba `master.py` al importar DeepFace (encontrado en la demo de la spec 004)
Al elegir "Enrolar rostro", `master.py` se cerró con `ValueError: You have tensorflow 2.21.0 and this requires tf-keras package`. Es el mismo bloqueo de entorno del punto 1–4, que había reaparecido: `tf-keras` figuraba en `requirements.txt` pero no estaba instalado en `.venv` (el entorno no se había recreado, así que no se pudo determinar cómo se perdió).

Dos causas, dos correcciones (aprobadas por Hugo):
- **Entorno.** Se instaló `tf-keras==2.21.0` y se fijaron `tensorflow==2.21.0` y `tf-keras==2.21.0` en `requirements.txt`: sin versión fija, una reinstalación podía traer un `tf-keras` que no empatara con TensorFlow, o no traerlo.
- **Código.** La importación de DeepFace estaba **fuera** del `try` que convierte errores técnicos en `ErrorDeDeteccion` (punto 3), así que la falla de importación no la atrapaba nadie y cerraba el programa, igual que el fallo de cámara del punto 5 (principio 8). Se creó `lector_de_caras._importar_deepface()`, que usan las cuatro funciones que cargan DeepFace (`validar_rostro`, `generar_vector`, `calcular_distancia`, `es_coincidencia`): cualquier excepción al importar —incluido este `ValueError`, que no es un `ImportError`— se convierte en `ErrorDeDeteccion` con un mensaje que menciona `tf-keras`. `master.py` ya la atrapaba en Enrolar, Identificar y Cobrar: ahora informa y vuelve al menú, sin reintentar.

Pruebas agregadas en `test_lector_de_caras.py`: la falla de importación (módulo faltante y el `ValueError` real) se convierte en `ErrorDeDeteccion` en las cuatro funciones, y las tres opciones de menú informan el error sin cerrar `master.py`.

**Segunda diferencia del mismo origen: `opencv-python` 5.x.** Ya con `tf-keras`, el enrolamiento siguió fallando con `Expected path .../cv2/data/haarcascade_frontalface_default.xml violated`: el `.venv` tenía `opencv-python` 5.0.0.93 instalado desde su creación, aunque `requirements.txt` ya exigía `<5` por el punto 2. Esta vez la protección del punto 3 funcionó: se informó como `ErrorDeDeteccion`, sin cerrar el programa, sin reintentar y sin dejar archivos en `enrolled_faces`. Se sincronizó el entorno con `pip install -r requirements.txt` (instaló `opencv-python` 4.14.0.94; una simulación previa confirmó que era la única diferencia pendiente) y se comprobó con DeepFace real que una imagen sin rostro se rechaza como `CapturaInvalida`, no como error de entorno.

**Lección:** los puntos 1–4 y este se resolvieron en `requirements.txt`, pero el `.venv` nunca se volvió a sincronizar con él. Ante cualquier error de entorno, lo primero es correr `pip install -r requirements.txt --dry-run` para ver qué diferencias hay.

## Pruebas
Mismo patrón que `test_enrolamiento.py`: `capturar_foto` se inyecta como parámetro y `lector_de_caras.validar_rostro`/`generar_vector`/`calcular_distancia` se sustituyen con `monkeypatch`, para no depender de cámara ni de DeepFace real. `almacen_rostros.listar_cuentas_enroladas()` se prueba contra una carpeta `enrolled_faces` temporal (fixture `autouse` ya existente en `test_enrolamiento.py`/`test_seguridad_biometrica.py`).

- `test/test_identificacion.py`:
  - RF-2/RF-3 — captura inválida (varios rostros / calidad insuficiente) reintenta automáticamente hasta lograr una captura válida.
  - RF-5 — sin ninguna cuenta enrolada, `identificar()` devuelve `None` y notifica "no identificado", sin reintentar internamente.
  - RF-4/RF-6 — un solo candidato coincidente: se identifica esa cuenta.
  - RF-6 — varios candidatos coincidentes: se identifica el de menor distancia.
  - RF-6/empate — dos candidatos con distancia idéntica: se identifica el de `fecha_enrolamiento` más antigua.
  - RF-9 — `listar_cuentas_enroladas()` no se altera (no crea/modifica/borra nada) tras `identificar()`.
- `test/test_seguridad_biometrica.py`:
  - Agregar `"identificacion.py"` a `MODULOS_ENROLAMIENTO` (revisión de imports de red).
  - Nuevo caso: con `capsys`, confirma que ni el vector capturado ni los vectores de las cuentas enroladas aparecen en ninguna notificación ni salida de consola durante `identificar()`.
- `test/test_lector_de_caras.py` (nuevo, agregado por el hallazgo #6): sustituye el módulo `cv2` completo por un doble que simula cuadros de cámara y teclas pulsadas — sin cámara ni ventana real. Cubre: espacio guarda el cuadro original (sin espejo/texto) en el momento exacto de la tecla, no el primer cuadro del calentamiento; Esc cancela sin guardar nada (`CapturaCancelada`); cámara que no abre (`ErrorDeCamara`, sin crear ventana); cámara que dejar de entregar imagen a medio flujo (`ErrorDeCamara`, cerrando la ventana igual).
- `test_enrolamiento.py`/`test_identificacion.py`: un caso nuevo en cada uno por `ErrorDeDeteccion`, `ErrorDeCamara` y `CapturaCancelada`, confirmando que ninguno se reintenta (un solo intento de captura) y, en enrolamiento, que no queda un enrolamiento a medias.

- Hallazgo #7 (ventana de resultado): en `test_identificacion.py`, la ventana se sustituye por un registro (fixture `autouse`) y se verifica que se muestra una sola vez por identificación (no por cada captura rechazada), con el mismo mensaje que la terminal, con la foto todavía existente al mostrarla y borrada al terminar. En `test_lector_de_caras.py`: franja verde/roja según el resultado, texto sin acentos, cierre de la ventana, y que no se abre ventana si la foto no se puede leer.

## Verificación
1. `pytest test/` — deben pasar todos los casos, sin cámara ni DeepFace real (todo mockeado). Estado actual: 67 pruebas en verde.
2. Demo manual con `python master.py`: enrolar al menos dos cuentas distintas, identificar correctamente a cada una por separado, y capturar un rostro no enrolado para confirmar el mensaje de "no identificado". El entorno ya quedó resuelto (ver "Hallazgos de la demo" arriba): `tf_keras` instalado, `opencv-python` fijado en la serie 4.x, pesos de VGG-Face descargados. Pendiente: completar T6.1–T6.4 de `tasks.md` con cámara real.

## Pendiente, no cubierto por esta spec
- Cobro, descuento de saldo o cualquier transacción asociada (spec futura).
- Interfaz real del chofer (spec futura); por ahora la identificación es una opción genérica de `master.py`.
- Registro histórico o auditoría de identificaciones.
- Detección de suplantación ("liveness detection").

## Estado del plan
D1 a D4 quedaron resueltas, junto con la lógica de reintentos de RF-5 vs RF-2/RF-3. Implementación completa (T1–T5 de `tasks.md`) y suite automatizada en verde. La demo con cámara real expuso 7 hallazgos adicionales, y la demo de la spec 004 un octavo (`tf-keras` faltante); todos ya resueltos en código y cubiertos por pruebas nuevas (ver "Hallazgos de la demo" arriba). Queda pendiente únicamente repetir la demo manual completa (T6.1–T6.4) para cerrar la spec.
