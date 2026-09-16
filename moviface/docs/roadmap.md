# Roadmap — specs faltantes de moviface

> Este documento no es una spec: es un recálculo de qué queda fuera de las specs ya escritas (001–003), para que Hugo decida qué redactar después y en qué orden. Las specs las sigue escribiendo Hugo (`AGENTS.md`); esto solo consolida lo que ya quedó anotado disperso en cada `spec.md`.
>
> Última recalculación: se generó tras cerrar la implementación de `specs/003-identificacion-facial-tiempo-real`.

## Specs ya escritas
| Spec | Cubre | Estado |
|---|---|---|
| `001-enrolamiento-vectores-faciales` | Enrolar/borrar el rostro de un usuario ya logueado | Implementada, pruebas en verde |
| `002-login` | Crear cuenta, iniciar/cerrar sesión, expiración por inactividad | Implementada, pruebas en verde |
| `003-identificacion-facial-tiempo-real` | Capturar un rostro y determinar a qué cuenta enrolada pertenece | Implementada, pruebas en verde; falta cerrar la demo manual (T6.1–T6.4 de su `tasks.md`) |

## Candidatas a spec futura

Cada una junto a dónde quedó mencionada, para trazabilidad.

### 1. Cobro y saldo
Mencionada como fuera de alcance en las tres specs existentes: "Cobro o cargo a la cuenta de movilidad" (001), "Saldo, transacciones o cualquier operación de cobro asociada a la cuenta" (002), "Cobro, descuento de saldo o cualquier transacción asociada" (003). Es la pieza que le da sentido de negocio al proyecto (constitution.md, principio 10, ya reserva columnas de Postgres para esto). Probablemente depende de que exista primero la interfaz de chofer (#2), porque es el chofer quien dispara el cobro tras identificar al pasajero.

### 2. Interfaz de chofer
Mencionada en las tres specs: "Confirmación del reconocimiento en la interfaz del chofer" y "Visualización de la tarifa cobrada" (001), "Login de chofer o administrador" (002), "Interfaz real del chofer" e "Identificación como opción genérica de `master.py`, reemplazo provisional" (003). Hoy la identificación vive en `master.py` como una opción de menú genérica precisamente a la espera de esta spec — `identificacion.identificar()` ya está diseñada para no asumir quién la ejecuta.

### 3. Roles y cuentas de chofer/administrador
Mencionada en 001 ("Enrolamiento de choferes o administradores"), 002 ("Login de chofer o administrador", "Roles, permisos o niveles de acceso distintos entre cuentas") y 003 ("Login o rol de chofer o administrador"). Es un prerequisito de las specs #1 y #2: sin un tipo de cuenta distinto al de "usuario de transporte", no hay quién opere la interfaz de chofer con permisos propios.

### 4. Sistema administrativo (monitoreo y gestión)
Mencionado en `AGENTS.md` como parte del objetivo del proyecto ("...el chofer y el sistema administrativo que permite el monitoreo y gestión del sistema"), pero **todavía no aparece explícitamente en ningún `spec.md`** como fuera de alcance — es un hueco entre la visión del proyecto y lo que las specs ya escritas contemplan. Candidata a incluir: edición/eliminación de cuentas (fuera de alcance de 002), y el registro histórico/auditoría de identificaciones (fuera de alcance de 003).

### 5. Recuperación de contraseña
Mencionada solo en 002 ("Recuperación o restablecimiento de contraseña olvidada"). Es independiente de las demás — no depende de que existan cuentas de chofer ni de cobro.

### 6. Detección de suplantación (liveness detection)
Mencionada solo en 003 ("Detección de suplantación... 'liveness detection'"). Es una mejora de seguridad sobre la identificación ya implementada, no bloquea a ninguna otra spec futura.

## Limitaciones conocidas del MVP (no son specs, son decisiones de alcance ya tomadas)
Documentadas explícitamente como tal en sus specs de origen — no requieren una spec nueva, pero conviene no perderlas de vista si el proyecto crece:
- Un solo rostro/vector activo por cuenta a la vez (001).
- No se detecta si un mismo rostro físico ya está enrolado en otra cuenta distinta (001, repetida como limitación en 003).
- Sin sesiones concurrentes de la misma cuenta desde más de un proceso (002).

## Orden sugerido (a validar por Hugo)
Es una lectura de dependencias, no una decisión tomada: **#3 (roles de chofer/admin) → #2 (interfaz de chofer) → #1 (cobro)**, porque cada una necesita la anterior para tener sentido. **#4, #5 y #6** son independientes entre sí y de esa cadena; pueden intercalarse cuando convenga.
