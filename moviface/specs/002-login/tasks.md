# Tareas — Spec 002: Login y gestión de cuentas de usuario

Basado en `plan.md` (decisiones D1–D6 acordadas). Cada tarea indica qué RF de `spec.md` cubre y en qué archivo vive.

## 1. Infraestructura mínima
- [x] T1.1 — Agregar `psycopg[binary]` (D2) y `bcrypt` (D1) a `requirements.txt`.
- [x] T1.2 — Crear `.env.example` (sin credenciales reales) documentando las variables que espera `basedatos.py` (host, puerto, usuario, contraseña, nombre de base de datos).
- [x] T1.3 — Confirmar que `.env` sigue excluido por `.gitignore`.
- [x] T1.4 — Definir el script/sentencia SQL de creación de la tabla `cuentas` (`id`, `identificador`, `contrasena_hash`, `fecha_creacion`), según D3.
- [x] T1.5 — Instalar `psycopg[binary]` y `bcrypt` en el entorno local (`.venv/`).

## 2. Módulo `basedatos.py` (conexión a PostgreSQL)
- [x] T2.1 — Función que lee las variables de entorno y abre una conexión a PostgreSQL con `psycopg` (D2).
- [x] T2.2 — Manejo del error de conexión fallida (caso límite de `spec.md`), sin exponer credenciales en el mensaje de error.

## 3. Módulo `cuentas.py` (RF-1 a RF-5, RF-13)
- [x] T3.1 — `validar_formato_identificador(identificador)`: expresión regular de correo electrónico (RF-2, D5).
- [x] T3.2 — `validar_complejidad_contrasena(contrasena)`: mínimo 8 caracteres, mayúscula, minúscula, número, carácter especial, sin espacios (RF-4).
- [x] T3.3 — `identificador_en_uso(conexion, identificador)`: revisa si ya existe una cuenta con ese identificador, sensible a mayúsculas/espacios (RF-3).
- [x] T3.4 — `crear_cuenta(conexion, identificador, contrasena)`: valida formato (RF-2) → valida duplicado (RF-3) → valida complejidad (RF-4) → genera el hash con `bcrypt` (D1, RF-13) → guarda la fila y confirma (RF-1, RF-5).
- [x] T3.5 — `buscar_cuenta(conexion, identificador)` y `verificar_contrasena(conexion, identificador, contrasena)`: usados por `sesion.py` para el login (RF-6/RF-7), comparando con `bcrypt.checkpw`.
- [x] T3.6 — Excepciones específicas: `IdentificadorInvalido`, `IdentificadorEnUso`, `ContrasenaInvalida`.

## 4. Módulo `sesion.py` (reemplaza el stub; RF-6 a RF-12)
- [x] T4.1 — Estado de sesión en memoria del proceso: cuenta activa + timestamp de última actividad.
- [x] T4.2 — `iniciar_sesion(conexion, identificador, contrasena)`: rechaza si ya hay sesión activa en el proceso (RF-8) → valida credenciales vía `cuentas.verificar_contrasena` con mensaje genérico si fallan (RF-6/RF-7).
- [x] T4.3 — `cerrar_sesion()`: cierra sesión manual (RF-9); informa si no había sesión activa (RF-10).
- [x] T4.4 — Verificación perezosa de expiración (D4): función que compara el timestamp de última actividad contra el umbral de inactividad (30 min, configurable/inyectable para poder probarla rápido) y cierra la sesión si se cumplió (RF-11).
- [x] T4.5 — Toda acción de menú reinicia el timestamp de última actividad antes de ejecutarse (RF-11).
- [x] T4.6 — Al cerrar sesión (manual o por expiración), descartar todo el estado en memoria (RF-12).
- [x] T4.7 — Mantener la firma pública ya usada por `enrolamiento.py` (`obtener_cuenta_activa()`, `hay_sesion_activa()`) sin cambios de interfaz.
- [x] T4.8 — Excepciones específicas: `SesionYaActiva`, `CredencialesInvalidas`, `SinSesionActiva`.

## 5. Punto de entrada `master.py`
- [x] T5.1 — Nueva opción de menú "Crear cuenta": pide identificador/contraseña por consola y llama a `cuentas.crear_cuenta`, mostrando los errores de `cuentas.py` sin exponer la contraseña.
- [x] T5.2 — Nueva opción de menú "Iniciar sesión": pide identificador/contraseña sin eco en pantalla (`getpass`) y llama a `sesion.iniciar_sesion`.
- [x] T5.3 — Nueva opción de menú "Cerrar sesión": llama a `sesion.cerrar_sesion`.
- [x] T5.4 — Antes de ejecutar cualquier opción del menú, invocar la verificación de expiración (T4.4/T4.5) e informar al usuario si su sesión expiró.
- [x] T5.5 — Revisar los mensajes de error de "Enrolar rostro"/"Borrar rostro" para que reflejen que dependen de la sesión real (ya no del stub).

## 6. Pruebas (`/moviface/test`, principio 11)
- [x] T6.1 — `test/test_cuentas.py`: un caso por bloque de RF-1 a RF-5 y RF-13, usando un doble en memoria (diccionario) en vez de una conexión real a PostgreSQL (D6).
- [x] T6.2 — `test/test_sesion.py`: un caso por bloque de RF-6 a RF-12 (login correcto, credenciales inválidas con mensaje genérico, sesión ya activa, logout manual, logout sin sesión, expiración por inactividad, descarte de estado tras cierre).
- [x] T6.3 — `test/test_seguridad_credenciales.py` (o extensión de `test_seguridad_biometrica.py`): la contraseña y su hash nunca aparecen en logs/salidas de consola; no existe ninguna ruta de código que envíe datos fuera de la conexión local a PostgreSQL.
- [x] T6.4 — Ejecutar `pytest test/` y confirmar 100% en verde sin necesitar una instancia real de PostgreSQL.

## 7. Script de aprovisionamiento `configurar_base_datos.py`
- [x] T7.1 — Script standalone de ejecución única (no forma parte del menú de `master.py`, decisión acordada por Hugo respecto al principio 8 de `constitution.md`): crea la base de datos de PostgreSQL si no existe (usando una conexión administrativa a una base ya existente, ej. `postgres`, con `autocommit`) y luego crea la tabla `cuentas` reutilizando `basedatos.inicializar_esquema`.
- [x] T7.2 — Nueva variable de entorno `MOVIFACE_DB_ADMIN_NAME` documentada en `.env.example`.
- [x] T7.3 — Agregar `python-dotenv` a `requirements.txt` y cargar `.env` automáticamente desde `basedatos.py` (D7), para no tener que exportar variables a mano en cada terminal.

## 8. Verificación manual (pendiente de una instancia real de PostgreSQL)
- [ ] T8.1 — Ejecutar `python configurar_base_datos.py` contra un servidor PostgreSQL local y confirmar que crea la base de datos y la tabla `cuentas`.
- [ ] T8.2 — Crear una cuenta desde `master.py` y confirmar en la base que se guardó el hash de `bcrypt`, nunca la contraseña en texto plano.
- [ ] T8.3 — Repetir el mismo identificador y confirmar el rechazo por duplicado (RF-3).
- [ ] T8.4 — Iniciar sesión con credenciales correctas y luego con incorrectas, confirmando el mensaje genérico (RF-7).
- [ ] T8.5 — Intentar iniciar sesión mientras ya hay una sesión activa y confirmar el rechazo (RF-8).
- [ ] T8.6 — Cerrar sesión manualmente y confirmar que el enrolamiento vuelve a exigir sesión (RF-12).
- [ ] T8.7 — Provocar la expiración por inactividad (con un umbral reducido de prueba) y confirmar el mismo efecto que el cierre manual.
- [ ] T8.8 — Revisar manualmente que ningún mensaje de consola muestre la contraseña ni su hash durante toda la demo.

## Fuera de esta lista de tareas
- Recuperación de contraseña, edición o eliminación de cuentas (fuera de alcance de `spec.md`).
- Saldo, transacciones o cobro (spec futura, constitution.md principio 10).
- Login de chofer o administrador.
- Prueba de integración automatizada contra PostgreSQL real (queda como verificación manual, T8.1–T8.8, igual que la cámara real en spec 001).
