# moviface

Proyecto escolar de visión por computadora para practicar la técnica de desarrollo **spec-driven (SDD)**. Busca, mediante reconocimiento facial, agilizar el cobro en transporte público: identificar al usuario, al chofer y, eventualmente, dar soporte a un sistema administrativo de monitoreo y gestión.

> ⚠️ Es una simulación de un solo dispositivo, no un sistema en producción. Los datos biométricos (fotos y vectores faciales) nunca salen de la computadora local ni se suben al repositorio — ver `moviface/docs/constitution.md`, principio 4 y 5.

## Requisitos previos

- **Python 3.13+**
- **PostgreSQL** en ejecución (local o accesible por red) — guarda cuentas, no datos biométricos
- Una cámara web (usada por `lector_de_caras.py` para capturar el rostro)
- macOS/Linux/Windows con soporte para las dependencias de `opencv-python` y `tensorflow` (usadas por DeepFace)

## Instalación

1. Clona el repositorio y entra a la carpeta del proyecto:

   ```bash
   git clone <url-del-repositorio>
   cd moviface/moviface
   ```

   Todo el código y los comandos siguientes se ejecutan desde esta carpeta interna `moviface/` (no desde la raíz del repositorio).

2. Crea y activa un entorno virtual:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # En Windows: .venv\Scripts\activate
   ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Copia el archivo de variables de entorno y complétalo con los datos de tu servidor de PostgreSQL:

   ```bash
   cp .env.example .env
   ```

   Variables esperadas en `.env`:

   | Variable | Descripción |
   |---|---|
   | `MOVIFACE_DB_HOST` | Host del servidor PostgreSQL (ej. `localhost`) |
   | `MOVIFACE_DB_PORT` | Puerto (por defecto `5432`) |
   | `MOVIFACE_DB_NAME` | Nombre de la base de datos de moviface |
   | `MOVIFACE_DB_USER` | Usuario de PostgreSQL |
   | `MOVIFACE_DB_PASSWORD` | Contraseña de ese usuario |
   | `MOVIFACE_DB_ADMIN_NAME` | Base de datos existente en el servidor (normalmente `postgres`) usada solo para poder crear `MOVIFACE_DB_NAME` si no existe |

5. Aprovisiona la base de datos (solo la primera vez, o al levantar un entorno nuevo):

   ```bash
   python configurar_base_datos.py
   ```

   Este script crea la base de datos si no existe y verifica/crea el esquema de tablas. No es parte del menú de la app — es un paso de infraestructura previo, igual que instalar las dependencias.

## Uso

El único archivo que se ejecuta para usar la aplicación es `master.py` (constitution.md, principio 8):

```bash
python master.py
```

Muestra un menú por consola con las siguientes opciones:

1. **Crear cuenta** — correo electrónico y contraseña.
2. **Iniciar sesión**.
3. **Cerrar sesión**.
4. **Enrolar rostro** — requiere sesión iniciada; captura una foto con la cámara, la muestra para confirmarla y guarda el vector facial derivado con DeepFace.
5. **Borrar rostro** — elimina por completo el enrolamiento de la cuenta activa (foto, vector y cualquier caché derivado).
6. **Identificar rostro** — captura una foto y la compara contra todos los rostros enrolados para determinar a qué cuenta pertenece. No requiere sesión iniciada (simula el rol del chofer/dispositivo, que identifica a un pasajero).
7. **Salir**.

Las fotos e índices de rostros enrolados se guardan localmente en `moviface/static/img/enrolled_faces`, excluida del control de versiones.

## Ejecutar las pruebas

Todas las pruebas viven en `moviface/test` y se corren con `pytest` desde la carpeta `moviface/`:

```bash
pytest
```

Incluyen pruebas funcionales por módulo (cuentas, sesión, enrolamiento, identificación, lector de caras) y pruebas de seguridad biométrica obligatorias (constitution.md, principio 11): exclusión de `enrolled_faces` en `.gitignore`, ausencia de datos biométricos en logs/salidas de consola, borrado efectivo sin residuos, y ausencia de rutas de código que envíen esos datos fuera de la máquina local.

## Alcance actual del proyecto

El desarrollo sigue un enfoque spec-first: cada feature nace de una spec en `moviface/specs/`, y el código es la fuente de verdad de lo que el sistema realmente hace. Estado de las specs ya escritas:

| Spec | Cubre | Estado |
|---|---|---|
| `001-enrolamiento-vectores-faciales` | Enrolar y borrar el rostro de un usuario ya logueado | Implementada, pruebas en verde |
| `002-login` | Crear cuenta, iniciar/cerrar sesión, expiración de sesión por inactividad | Implementada, pruebas en verde |
| `003-identificacion-facial-tiempo-real` | Capturar un rostro y determinar a qué cuenta enrolada pertenece | Implementada, pruebas en verde; falta cerrar la demo manual |

### Limitaciones conocidas del MVP (decisiones de alcance ya tomadas)

- Un solo rostro/vector activo por cuenta a la vez.
- No se detecta si un mismo rostro físico ya está enrolado en otra cuenta distinta.
- Sin sesiones concurrentes de la misma cuenta desde más de un proceso.

## Qué falta por construir

El detalle completo, con trazabilidad a cada spec, vive en [`moviface/docs/roadmap.md`](moviface/docs/roadmap.md). En resumen, quedan como candidatas a spec futura (orden sugerido, a validar):

1. **Roles y cuentas de chofer/administrador** — hoy solo existe un tipo de cuenta ("usuario de transporte").
2. **Interfaz de chofer** — la identificación (opción 6 del menú) hoy es genérica en `master.py`, a la espera de esta spec.
3. **Cobro y saldo** — la pieza que le da sentido de negocio al proyecto; depende de que exista la interfaz de chofer.
4. **Sistema administrativo** (monitoreo y gestión) — edición/eliminación de cuentas, registro histórico/auditoría de identificaciones.
5. **Recuperación de contraseña** — independiente de las demás.
6. **Detección de suplantación (liveness detection)** — mejora de seguridad sobre la identificación ya implementada.

## Stack

- Python 3.13+
- [DeepFace](https://github.com/serengil/deepface) (detección y comparación facial)
- PostgreSQL (cuentas — nunca imágenes ni vectores faciales)
- Ver `moviface/requirements.txt` para el detalle de dependencias y por qué cada versión está fijada así.

## Documentación del proyecto

- [`moviface/docs/constitution.md`](moviface/docs/constitution.md) — principios innegociables del proyecto (idioma, manejo de datos biométricos, alcance de Postgres, pruebas obligatorias, gobernanza).
- [`moviface/docs/roadmap.md`](moviface/docs/roadmap.md) — qué queda fuera de las specs actuales y en qué orden se sugiere abordarlo.
- [`moviface/AGENTS.md`](moviface/AGENTS.md) — reglas de colaboración para agentes de IA que trabajen en este repositorio.
- `moviface/specs/*/spec.md` — especificación funcional de cada feature implementada.
