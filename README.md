
# ⚠️ AVISO IMPORTANTE — PROYECTO 100% GENERADO CON IA

# ⚠️⚠️⚠️ TODO EL CÓDIGO Y LA BASE DE DATOS DE ESTE PROYECTO FUERON DESARROLLADOS ÍNTEGRAMENTE POR INTELIGENCIA ARTIFICIAL ⚠️⚠️⚠️

**Este repositorio es un proyecto escolar hecho para practicar la técnica de desarrollo Spec-Driven Development (SDD). Ni una sola línea de código, del esquema de base de datos, de las pruebas ni de la documentación técnica fue escrita a mano por una persona: todo fue generado por un agente de IA a partir de especificaciones (`specs/`) redactadas y aprobadas por el autor humano.**

**El autor humano definió el alcance, la arquitectura, las reglas del proyecto (`AGENTS.md`, `docs/constitution.md`) y las specs funcionales, y revisó/aprobó cada cambio — pero la implementación, incluyendo el manejo de datos biométricos y la base de datos de PostgreSQL, fue producida por IA.**

**No se debe considerar código de producción ni una referencia de buenas prácticas de seguridad sin una auditoría humana independiente adicional.**

---

# moviface

Proyecto escolar de visión por computadora para practicar la técnica de desarrollo **spec-driven (SDD)**. Busca, mediante reconocimiento facial, agilizar el cobro en transporte público: identificar al usuario, cobrarle la tarifa de la modalidad de transporte operada por el chofer, y dar soporte a un futuro sistema administrativo de monitoreo y gestión.

> La simulación corre en un solo dispositivo. Los datos biométricos (fotos y vectores faciales) nunca salen de la computadora local ni se suben al repositorio — ver `moviface/docs/constitution.md`, principios 4 y 5.

## Requisitos previos

- **Python 3.13+**
- **PostgreSQL** en ejecución (local o accesible por red) — guarda cuentas, saldos y transacciones, nunca datos biométricos
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

1. **Crear cuenta de pasajero** — correo electrónico y contraseña; saldo inicial en $0.
2. **Crear cuenta de chofer** — mismas reglas de credenciales que la de pasajero; sin saldo asociado.
3. **Iniciar sesión** — válido para cuentas de pasajero, de chofer y para cuentas creadas antes de esta spec (sin tipo).
4. **Cerrar sesión**.
5. **Enrolar rostro** — requiere sesión iniciada; captura una foto con la cámara, la muestra para confirmarla y guarda el vector facial derivado con DeepFace. (Las cuentas de chofer no pueden enrolar rostro.)
6. **Borrar rostro** — elimina por completo el enrolamiento de la cuenta activa (foto, vector y cualquier caché derivado).
7. **Identificar rostro** — captura una foto y la compara contra todos los rostros enrolados para determinar a qué cuenta pertenece. No requiere sesión iniciada (uso genérico/de prueba, distinto del flujo de cobro).
8. **Recargar saldo** — solo cuentas de pasajero con sesión iniciada; monto entero de pesos mexicanos, mayor que cero.
9. **Fijar modalidad de transporte** — solo cuentas de chofer con sesión iniciada; elige metro ($5), metrobús ($6) o bici ($10) para el turno vigente (matutino 6:00–14:00 o vespertino 14:00–22:00). Si se fija antes de que el turno empiece, queda en espera y se activa sola.
10. **Cobrar pasajero** — solo chofer, con modalidad ya fijada y turno vigente; identifica al pasajero por reconocimiento facial y descuenta automáticamente la tarifa de su saldo, sin confirmación adicional y sin revelar el identificador ni el saldo restante en el mensaje de resultado.
11. **Eliminar mi cuenta** — cualquier tipo de cuenta, con sesión iniciada; pide reconfirmar la contraseña, rechaza la eliminación si el pasajero tiene saldo mayor a cero, y borra por completo la cuenta, su rostro enrolado y su historial de transacciones.
12. **Salir**.

Las fotos e índices de rostros enrolados se guardan localmente en `moviface/static/img/enrolled_faces`, excluida del control de versiones.

## Ejecutar las pruebas

Todas las pruebas viven en `moviface/test` y se corren con `pytest` desde la carpeta `moviface/`:

```bash
pytest
```

Incluyen pruebas funcionales por módulo (cuentas, sesión, enrolamiento, identificación, lector de caras, cobro, eliminación de cuenta) y pruebas de seguridad obligatorias (constitution.md, principio 11): exclusión de `enrolled_faces` en `.gitignore`, ausencia de datos biométricos, saldos, transacciones o contraseñas en logs/salidas de consola, borrado efectivo sin residuos tras eliminar rostro o cuenta, y ausencia de rutas de código que envíen esos datos fuera de la máquina local.

## Alcance actual del proyecto

El desarrollo sigue un enfoque spec-first: cada feature nace de una spec en `moviface/specs/`, y el código es la fuente de verdad de lo que el sistema realmente hace. Estado de las specs ya escritas:

| Spec | Cubre | Estado |
|---|---|---|
| `001-enrolamiento-vectores-faciales` | Enrolar y borrar el rostro de un usuario ya logueado | Implementada, pruebas en verde |
| `002-login` | Crear cuenta, iniciar/cerrar sesión, expiración de sesión por inactividad | Implementada, pruebas en verde |
| `003-identificacion-facial-tiempo-real` | Capturar un rostro y determinar a qué cuenta enrolada pertenece | Implementada, pruebas en verde |
| `004-sistema-cobro-transporte-interfaz-chofer-usuario` | Cuentas de chofer, saldo y recarga, turnos y modalidad de transporte, cobro automático al identificar al pasajero, y eliminación completa de cuenta | Implementada, pruebas en verde |

Con la spec 004, moviface ya cubre el ciclo de negocio completo del MVP: crear cuenta → enrolar rostro → un chofer fija su modalidad → identificar al pasajero → cobrar la tarifa descontando su saldo → cualquier cuenta puede eliminarse por completo cuando ya no se necesite.

### Limitaciones conocidas del MVP (decisiones de alcance ya tomadas)

- Un solo rostro/vector activo por cuenta a la vez; no se detecta si un mismo rostro físico ya está enrolado en otra cuenta distinta.
- Sin sesiones concurrentes de la misma cuenta desde más de un proceso.
- Tarifas y modalidades de transporte fijas (metro, metrobús, bici); no configurables.
- Turnos fijos (matutino/vespertino); no se puede cobrar fuera de 6:00–22:00.
- Sin historial de transacciones consultable ni reportes, más allá del mensaje inmediato de cada cobro/recarga.
- Sin recuperación de contraseña, ni retiro/reembolso de saldo, ni transferencia de saldo entre cuentas.
- No se cambia el tipo de una cuenta (pasajero/chofer) ya creada, ni las cuentas antiguas (previas a esta spec) reciben tipo.

## Qué falta por construir

El detalle completo, con trazabilidad a cada spec, vive en [`moviface/docs/roadmap.md`](moviface/docs/roadmap.md) — aunque ese documento aún no refleja el cierre de la spec 004 y debe actualizarse. Como candidata a spec futura queda, principalmente:

1. **Sistema administrativo** (monitoreo y gestión) — roles/cuentas de administrador, edición/eliminación de cuentas ajenas, registro histórico/auditoría de identificaciones y cobros.
2. **Recuperación de contraseña** — independiente de las demás.
3. **Detección de suplantación (liveness detection)** — mejora de seguridad sobre la identificación ya implementada.
4. Mejoras dentro del propio dominio de cobro ya cubiertas como "fuera de alcance" en la spec 004: tarifas/modalidades configurables, turnos configurables, historial de transacciones consultable, prevención de cobros duplicados, transferencia de saldo entre cuentas.

## Stack

- Python 3.13+
- [DeepFace](https://github.com/serengil/deepface) (detección y comparación facial)
- PostgreSQL (cuentas, saldos y transacciones — nunca imágenes ni vectores faciales)
- Ver `moviface/requirements.txt` para el detalle de dependencias y por qué cada versión está fijada así.

## Documentación del proyecto

- [`moviface/docs/constitution.md`](moviface/docs/constitution.md) — principios innegociables del proyecto (idioma, manejo de datos biométricos, alcance de Postgres, pruebas obligatorias, gobernanza).
- [`moviface/docs/roadmap.md`](moviface/docs/roadmap.md) — qué queda fuera de las specs actuales y en qué orden se sugiere abordarlo (pendiente de actualizar tras la spec 004).
- [`moviface/AGENTS.md`](moviface/AGENTS.md) — reglas de colaboración para agentes de IA que trabajen en este repositorio.
- `moviface/specs/*/spec.md` — especificación funcional de cada feature implementada.
