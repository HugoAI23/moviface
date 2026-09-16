# Plan — Spec 002: Login y gestión de cuentas de usuario

## Contexto
Hoy `sesion.py` es un stub que simula una única cuenta demo siempre autenticada (usado por `specs/001-enrolamiento-vectores-faciales` mientras esta spec no existía). `spec.md` de esta spec (RF-1 a RF-13, aprobada, sin dudas abiertas) exige reemplazar ese stub por un mecanismo real de creación de cuenta, login, logout y expiración por inactividad, respaldado por PostgreSQL (constitution.md, principio 10). Al momento de planear esto, el repositorio no tiene ningún código de conexión a PostgreSQL, ni `psycopg`/driver alguno en `requirements.txt` (solo `deepface`, `opencv-python`, `pytest`), ni tabla de cuentas definida.

Este documento no implementa nada. Las decisiones de diseño relevantes ya se revisaron contigo (opciones con ventajas/desventajas) y quedaron resueltas; se documentan a continuación como decisiones acordadas.

## Decisiones de diseño acordadas

### D1 — Hash de contraseña (RF-13)
Se usa **`bcrypt`** (`hashpw`/`checkpw`). Maneja el salt internamente; se agrega como nueva dependencia en `requirements.txt`.

### D2 — Driver de conexión a PostgreSQL
Se usa **`psycopg[binary]`** (psycopg3), sucesor activo de psycopg2 con API similar.

### D3 — Esquema mínimo de la tabla de cuentas
Columnas, acotadas estrictamente a lo que pide `spec.md` (sin saldo ni transacciones, eso es de una spec futura, principio 10):
- `id` — clave primaria.
- `identificador` — correo electrónico, único, sensible a mayúsculas/espacios (ya definido en `spec.md`).
- `contrasena_hash` — nunca la contraseña en claro (RF-13), generado con bcrypt (D1).
- `fecha_creacion` — marca de tiempo de creación de la cuenta.

### D4 — Medición de los 30 minutos de inactividad (RF-11)
**Verificación perezosa**: `sesion.py` guarda el timestamp de la última acción de menú. Cada vez que `master.py` va a ejecutar una opción, primero pregunta a `sesion.py` si ya pasaron 30 minutos desde esa marca; si sí, cierra la sesión antes de ejecutar la acción elegida. No requiere hilos ni concurrencia, y encaja con "cualquier acción del menú reinicia el contador" (ya resuelto en `spec.md`). Como contrapartida asumida: si el usuario deja el programa abierto sin tocar nada, la sesión no se cierra en el segundo exacto en que se cumplen los 30 minutos, sino hasta la siguiente vez que intente hacer algo.

### D5 — Validación del formato de correo electrónico (RF-2)
**Expresión regular simple** (forma general `algo@algo.algo`), sin verificar que el dominio exista de verdad. Sin dependencias nuevas.

### D6 — Pruebas de la capa de PostgreSQL sin base de datos real
Las funciones de `cuentas.py` reciben la conexión/cursor ya abierto como parámetro (inyección de dependencia), del mismo modo en que `enrolamiento.py` ya recibe funciones inyectadas en la spec 001. Las pruebas normales (`pytest test/`) usan un doble en memoria (un diccionario) que imita la tabla de cuentas, así todo pasa sin PostgreSQL instalado. Una prueba de integración aparte, no obligatoria para que el resto del suite pase, confirma la conexión real a PostgreSQL cuando haya una disponible localmente — análogo a la verificación manual con cámara real que quedó pendiente en `specs/001.../tasks.md`.

### D7 — Carga automática de `.env` (decisión tomada durante la verificación manual con PostgreSQL real)
Se usa **`python-dotenv`**: `basedatos.py` llama a `load_dotenv()` al importarse, así `master.py` y `configurar_base_datos.py` (que siempre importan `basedatos`) quedan con las variables de `.env` disponibles sin exportarlas manualmente en cada terminal. Alternativa descartada: exportar las variables a mano (`source .env`) antes de cada ejecución, sin dependencias nuevas pero incómodo para el uso diario.

## Estructura de archivos propuesta

**Punto de entrada**
- `master.py` — se agregan tres opciones de menú nuevas: crear cuenta, iniciar sesión, cerrar sesión. Las opciones de enrolamiento ya existentes pasan a depender de la sesión real en vez del stub.

**Módulos de apoyo nuevos**
- `basedatos.py` — abre y entrega la conexión a PostgreSQL a partir de variables de entorno (`.env`, ya contemplado en `.gitignore`); único punto de conexión del proyecto.
- `cuentas.py` — `crear_cuenta(identificador, contraseña)`, `buscar_cuenta(identificador)`, `verificar_contrasena(identificador, contraseña)`. Aquí viven el hash/verificación de contraseña (D1), la validación de formato de correo (D5) y la validación de complejidad de contraseña (RF-4).

**Módulo existente que se reemplaza**
- `sesion.py` — deja de ser un stub. Gestiona el estado de sesión activa en memoria del proceso (id de cuenta + timestamp de última actividad), expone `iniciar_sesion(identificador, contraseña)` y `cerrar_sesion()`, mantiene la misma firma pública que ya usa `enrolamiento.py` (`obtener_cuenta_activa()`, `hay_sesion_activa()`) y agrega la expiración por inactividad (D4).

**Infraestructura**
- `requirements.txt` — se agregan `psycopg[binary]` (D2) y `bcrypt` (D1). La validación de correo (D5) no agrega dependencia (regex de la librería estándar).
- `.env.example` (sin credenciales reales) — documenta qué variables de entorno espera `basedatos.py` (host, puerto, usuario, contraseña, nombre de base de datos) y `configurar_base_datos.py` (`MOVIFACE_DB_ADMIN_NAME`).
- `configurar_base_datos.py` — script standalone de ejecución única (decisión acordada: no forma parte del menú de `master.py`, ver principio 8 de `constitution.md`). Crea la base de datos de PostgreSQL si no existe, conectándose primero a una base administrativa ya existente (`autocommit`, ya que `CREATE DATABASE` no corre dentro de una transacción), y luego reutiliza `basedatos.inicializar_esquema` para crear la tabla `cuentas`.

**Pruebas (`/moviface/test`)**
- `test/test_cuentas.py` — un caso por cada bloque de RF de creación de cuenta (RF-1 a RF-5), usando el doble en memoria de D6.
- `test/test_sesion.py` — un caso por cada bloque de RF de login/logout/expiración (RF-6 a RF-12).
- `test/test_seguridad_credenciales.py` (o extensión de `test_seguridad_biometrica.py`) — verifica que la contraseña nunca aparece en logs/consola, y que no existe ninguna ruta de red fuera de la conexión local a PostgreSQL.

## Verificación
1. Requiere una instancia local de PostgreSQL accesible (levantarla no es parte de este plan; se documenta qué variables de entorno espera `basedatos.py`).
2. `pip install -r requirements.txt` actualizado con `psycopg[binary]` y `bcrypt`.
3. `pytest test/` — deben pasar todos los casos de `test_cuentas.py`, `test_sesion.py` y las pruebas de seguridad, sin necesitar PostgreSQL real (D6).
4. Demo manual con `python master.py`: crear una cuenta, repetir el mismo identificador y ver el rechazo (RF-3), iniciar sesión con credenciales correctas, con credenciales incorrectas (RF-7), cerrar sesión manualmente, provocar la expiración por inactividad y comprobar que el enrolamiento vuelve a exigir sesión (RF-12).

## Pendiente, no cubierto por esta spec
- Recuperación de contraseña, edición o eliminación de cuentas (fuera de alcance de `spec.md`).
- Saldo, transacciones o cobro (spec futura, constitution.md principio 10).
- Login de chofer o administrador.
- Prueba de integración real contra PostgreSQL en un entorno con la base de datos disponible (queda igual de pendiente que la prueba con cámara real de la spec 001).

## Estado del plan
D1 a D6 quedaron resueltas. Este plan está listo para que lo revises antes de redactar `tasks.md`.
