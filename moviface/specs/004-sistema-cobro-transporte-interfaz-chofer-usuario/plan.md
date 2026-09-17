# Plan — Spec 004: Sistema de cobro de transporte e interfaz chofer/usuario

## Contexto
`spec.md` de esta spec (RF-1 a RF-28, aprobada, sin dudas abiertas) exige: cuentas de chofer junto a las de pasajero, saldo y recarga, turnos fijos por hora del día, una modalidad de transporte fijada por turno, y un cobro automático que identifica al pasajero sin revelar su identidad. Hoy `cuentas.py` solo conoce un tipo de cuenta (sin saldo), `basedatos.py` solo tiene la tabla `cuentas`, y `identificacion.py` siempre revela el identificador de la cuenta identificada (spec003, RF-7).

Las decisiones de diseño relevantes ya se revisaron contigo (opciones con ventajas/desventajas) y quedaron resueltas; se documentan a continuación como decisiones acordadas.

## Archivos que se modifican y por qué (constitution.md, principio 12)
- **`basedatos.py`** (existente) — gana el esquema de tres tablas nuevas: `pasajeros`, `choferes`, `transacciones` (D1).
- **`cuentas.py`** (existente) — `crear_cuenta` gana el parámetro `tipo`; gana funciones nuevas para tipo, saldo, recarga y descuento (D1, D3).
- **`identificacion.py`** (existente, spec003) — `identificar()` gana el parámetro `revelar_identificador: bool = True` (D4); sin cambios de comportamiento cuando se omite (sigue cumpliendo RF-7 de spec003 tal cual para su uso genérico fuera del cobro).
- **`lector_de_caras.py`** (existente) — gana `mostrar_mensaje(mensaje, *, exito: bool)`: misma mecánica de ventana que `mostrar_resultado()` (franja de color, cierre automático/por tecla) pero sin cargar ninguna foto (D7, ver más abajo).
- **`cobro.py`** (nuevo) — orquesta turno, modalidad y cobro (RF-11 a RF-28), análogo a `enrolamiento.py`/`identificacion.py` (D2).
- **`master.py`** (existente) — nuevas opciones de menú: "Crear cuenta de pasajero", "Crear cuenta de chofer" (D6), "Recargar saldo", "Fijar modalidad de transporte", "Cobrar pasajero"; y llama a `cobro.reiniciar_estado()` al cerrar sesión o al detectar expiración.
- **`sesion.py`** — **sin cambios**: RF-4 se cumple reutilizando `iniciar_sesion`/`cerrar_sesion` tal cual (login no distingue tipo de cuenta); el tipo se consulta en `cuentas.py` cuando se necesita (D3).
- **`test/`** — nuevos archivos de prueba (ver sección Pruebas).

Ningún comportamiento ya aprobado de `specs/001`, `specs/002` ni `specs/003` cambia — solo se agregan funciones, un parámetro opcional (con default que preserva el comportamiento actual) y tablas nuevas.

## Decisiones de diseño acordadas

### D1 — Esquema de cuentas: tablas separadas
Se usan tablas separadas `pasajeros` y `choferes`, cada una con `identificador` como clave primaria y foránea hacia `cuentas.identificador` (que ya es `UNIQUE`). El tipo de una cuenta queda **implícito** por en cuál tabla tiene fila — no se agrega ninguna columna `tipo`:

```sql
CREATE TABLE IF NOT EXISTS pasajeros (
    identificador TEXT PRIMARY KEY REFERENCES cuentas(identificador) ON DELETE CASCADE,
    saldo INTEGER NOT NULL DEFAULT 0 CHECK (saldo >= 0)
);

CREATE TABLE IF NOT EXISTS choferes (
    identificador TEXT PRIMARY KEY REFERENCES cuentas(identificador) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transacciones (
    id SERIAL PRIMARY KEY,
    identificador TEXT NOT NULL REFERENCES pasajeros(identificador),
    modalidad TEXT NOT NULL CHECK (modalidad IN ('metro', 'metrobus', 'bici')),
    monto INTEGER NOT NULL CHECK (monto > 0),
    fecha TIMESTAMPTZ NOT NULL DEFAULT now()
);
```
El `CHECK (saldo >= 0)` es una segunda barrera (además de la validación en `cuentas.py`) para RF-28. `transacciones.identificador` referencia `pasajeros` (no `cuentas`) porque solo los pasajeros se cobran (RF-9/RF-25).

### D2 — Módulo nuevo `cobro.py`
Toda la lógica de turno vigente, modalidad fijada/en espera y el flujo de cobro vive en `cobro.py`, con estado en memoria del proceso (mismo patrón que `sesion.py`: variables de módulo, sin persistencia — coherente con que la modalidad se descarta al cerrar sesión, RF-19).

### D3 — Tipo de cuenta: se consulta, no se cachea
`cuentas.py` gana `obtener_tipo(conexion, identificador) -> "pasajero" | "chofer" | None`, que consulta `pasajeros`/`choferes` directamente. `cobro.py` la usa cada vez que necesita validar RF-11; no se guarda el tipo en `sesion.py`.

### D4 — Ocultar el identificador durante el cobro (excepción a spec003 RF-7)
`identificacion.identificar()` gana `revelar_identificador: bool = True`. Con `False`, el mensaje interno pasa de `"Rostro identificado: cuenta {id}."` a `"Rostro identificado."`, y la ventana de resultado (`lector_de_caras.mostrar_resultado`, sin cambios) muestra ese mismo mensaje genérico. El valor por defecto (`True`) preserva el comportamiento actual para la opción de menú genérica de spec003.

### D5 — Ventana de resultado del cobro: gráfica
El mensaje de RF-27 se muestra en una ventana (franja verde/roja), igual que el patrón ya establecido en spec003 para que el resultado no se pierda detrás de la ventana de la cámara.

### D6 — Menú de creación de cuenta: dos opciones separadas
`master.py` tiene dos entradas de menú distintas ("Crear cuenta de pasajero", "Crear cuenta de chofer"), cada una llamando a `cuentas.crear_cuenta(conexion, identificador, contrasena, tipo=...)` con el tipo correspondiente ya fijo — el usuario nunca escribe el tipo a mano.

### D7 — La ventana del cobro no muestra la foto capturada
Al diseñar D5 se encontró que reutilizar `mostrar_resultado()` (que sí muestra la foto) para el cobro expondría visualmente la identidad del pasajero, contradiciendo RF-25/RF-27. Se decidió que la ventana de cobro **no muestra ninguna foto**: solo texto sobre un fondo de color. Esto requiere una función nueva en `lector_de_caras.py`, `mostrar_mensaje(mensaje, *, exito: bool)`, que reutiliza las constantes de color/tiempo ya existentes (`_COLOR_IDENTIFICADO`/`_COLOR_NO_IDENTIFICADO`, `_MILISEGUNDOS_RESULTADO`) sobre un lienzo en blanco en vez de cargar `ruta_imagen`.

## Diseño concreto de las funciones nuevas

`cuentas.py`:
```python
TIPOS_VALIDOS = {"pasajero", "chofer"}

class TipoInvalido(Exception): """RF-3."""
class CuentaNoEsPasajero(Exception): """RF-9."""
class MontoInvalido(Exception): """RF-8/RF-9."""
class SaldoInsuficiente(Exception): """RF-24."""

def crear_cuenta(conexion, identificador: str, contrasena: str, tipo: str) -> None:
    """RF-1 a RF-5: agrega la validación de `tipo` al flujo ya existente
    (formato → duplicado → tipo → complejidad) y crea, en la misma
    transacción, la fila en `pasajeros` (saldo 0, RF-5) o `choferes`."""
    validar_formato_identificador(identificador)
    if identificador_en_uso(conexion, identificador):
        raise IdentificadorEnUso(...)
    if tipo not in TIPOS_VALIDOS:
        raise TipoInvalido(f"Tipo de cuenta inválido: {tipo}.")
    validar_complejidad_contrasena(contrasena)
    contrasena_hash = bcrypt.hashpw(...)
    with conexion.cursor() as cursor:
        cursor.execute("INSERT INTO cuentas (identificador, contrasena_hash) VALUES (%s, %s)", ...)
        tabla = "pasajeros" if tipo == "pasajero" else "choferes"
        columnas = "(identificador, saldo)" if tipo == "pasajero" else "(identificador)"
        valores = "(%s, 0)" if tipo == "pasajero" else "(%s)"
        cursor.execute(f"INSERT INTO {tabla} {columnas} VALUES {valores}", (identificador,))
    conexion.commit()

def obtener_tipo(conexion, identificador: str) -> str | None:
    """RF-11/RF-9: consulta cuál tabla tiene la cuenta."""
    ...  # SELECT 1 FROM pasajeros ...; si no, SELECT 1 FROM choferes ...

def obtener_saldo(conexion, identificador: str) -> int:
    """Usado por RF-24 y por master.py para confirmar una recarga."""

def recargar_saldo(conexion, identificador: str, monto: int) -> None:
    """RF-8/RF-9: valida tipo pasajero y monto entero > 0 antes de sumar."""
    if obtener_tipo(conexion, identificador) != "pasajero":
        raise CuentaNoEsPasajero("Solo las cuentas de pasajero pueden recargar saldo.")
    if not isinstance(monto, int) or monto <= 0:
        raise MontoInvalido("El monto de recarga debe ser un entero mayor que cero.")
    # UPDATE pasajeros SET saldo = saldo + %s WHERE identificador = %s; commit.

def descontar_saldo(conexion, identificador: str, monto: int) -> None:
    """RF-24/RF-25/RF-28: usada solo por cobro.py, nunca deja saldo negativo."""
    if obtener_saldo(conexion, identificador) < monto:
        raise SaldoInsuficiente("Saldo insuficiente para este cobro.")
    # UPDATE pasajeros SET saldo = saldo - %s WHERE identificador = %s; commit.
```

`cobro.py` (nuevo):
```python
"""Orquesta turno, modalidad y cobro. specs/004.../spec.md RF-11 a RF-28."""

from datetime import datetime

import cuentas
import identificacion
import lector_de_caras
import sesion

TARIFAS = {"metro": 5, "metrobus": 6, "bici": 10}       # RF-23
TURNOS = {"matutino": (6, 14), "vespertino": (14, 22)}  # RF-12

_modalidad_fijada: str | None = None
_turno_de_modalidad: str | None = None  # None + _modalidad_fijada != None → "en espera" (RF-14)

class NoEsChofer(Exception): """RF-11."""
class SinTurnoVigente(Exception): """RF-15."""
class ModalidadInvalida(Exception): """Modalidad fuera de TARIFAS."""
class ModalidadNoFijada(Exception): """RF-16."""

def _turno_vigente(ahora: datetime | None = None) -> str | None:
    hora = (ahora or datetime.now()).hour
    for turno, (inicio, fin) in TURNOS.items():
        if inicio <= hora < fin:
            return turno
    return None  # RF-12: 22:00-6:00

def _requerir_chofer(conexion) -> None:
    activa = sesion.obtener_cuenta_activa()
    if activa is None or cuentas.obtener_tipo(conexion, activa) != "chofer":
        raise NoEsChofer("Debes iniciar sesión como chofer para continuar.")  # RF-11

def fijar_modalidad(conexion, modalidad: str) -> None:
    """RF-13/RF-14."""
    global _modalidad_fijada, _turno_de_modalidad
    _requerir_chofer(conexion)
    if modalidad not in TARIFAS:
        raise ModalidadInvalida(f"Modalidad inválida: {modalidad}.")
    _modalidad_fijada = modalidad
    _turno_de_modalidad = _turno_vigente()  # None → queda en espera (RF-14)

def _modalidad_vigente() -> str | None:
    """RF-14/RF-16/RF-17/RF-18: resuelve el estado turno/modalidad de forma
    perezosa (mismo patrón que sesion.verificar_expiracion, D4 de spec002)."""
    global _modalidad_fijada, _turno_de_modalidad
    turno_actual = _turno_vigente()
    if turno_actual is None or _modalidad_fijada is None:
        return None
    if _turno_de_modalidad is None:
        _turno_de_modalidad = turno_actual  # RF-14: activa la modalidad en espera
    elif _turno_de_modalidad != turno_actual:
        _modalidad_fijada = _turno_de_modalidad = None  # RF-18: cambió el turno
        return None
    return _modalidad_fijada

def reiniciar_estado() -> None:
    """RF-19: master.py la llama al cerrar sesión (manual o por expiración)."""
    global _modalidad_fijada, _turno_de_modalidad
    _modalidad_fijada = _turno_de_modalidad = None

def cobrar(
    conexion,
    *,
    identificar=identificacion.identificar,
    notificar=lector_de_caras.mostrar_mensaje,
) -> None:
    """RF-15/RF-16/RF-20 a RF-27."""
    _requerir_chofer(conexion)
    chofer_activo = sesion.obtener_cuenta_activa()

    if _turno_vigente() is None:
        raise SinTurnoVigente("No hay un turno vigente (6:00-22:00).")  # RF-15

    modalidad = _modalidad_vigente()
    if modalidad is None:
        raise ModalidadNoFijada("Fija tu modalidad de transporte antes de cobrar.")  # RF-16

    id_identificado = identificar(revelar_identificador=False)  # RF-21

    if id_identificado is None:
        notificar("No se identificó a ningún pasajero.", exito=False)  # RF-22
        return

    # RF-26: la sesión del chofer pudo cerrarse/expirar durante identificar().
    if sesion.obtener_cuenta_activa() != chofer_activo:
        return  # cancela sin descontar y sin notificar (ya no hay chofer activo)

    monto = TARIFAS[modalidad]
    try:
        cuentas.descontar_saldo(conexion, id_identificado, monto)  # RF-24/RF-28
    except cuentas.SaldoInsuficiente:
        notificar(f"Cobro rechazado: saldo insuficiente ({modalidad}, ${monto}).", exito=False)
        return

    _registrar_transaccion(conexion, id_identificado, modalidad, monto)  # RF-25
    notificar(f"Cobro exitoso: {modalidad}, ${monto}.", exito=True)  # RF-27

def _registrar_transaccion(conexion, identificador: str, modalidad: str, monto: int) -> None:
    with conexion.cursor() as cursor:
        cursor.execute(
            "INSERT INTO transacciones (identificador, modalidad, monto) VALUES (%s, %s, %s)",
            (identificador, modalidad, monto),
        )
    conexion.commit()
```

`identificacion.py` (cambio mínimo):
```python
def identificar(*, capturar_foto=..., notificar=print, revelar_identificador: bool = True) -> str | None:
    ...
    if id_identificado is None:
        mensaje = "No se identificó a ninguna cuenta enrolada."
    elif revelar_identificador:
        mensaje = f"Rostro identificado: cuenta {id_identificado}."  # RF-7 de spec003, sin cambios
    else:
        mensaje = "Rostro identificado."  # RF-21 de spec004: excepción acotada a este flujo
    ...
```

`lector_de_caras.py` (función nueva, D7):
```python
def mostrar_mensaje(mensaje: str, *, exito: bool) -> None:
    """RF-27: misma mecánica que mostrar_resultado() (franja de color,
    cierre automático/por tecla) pero sobre un lienzo en blanco, sin foto
    (D7: no debe exponer el rostro del pasajero cobrado)."""
    # Reutiliza _COLOR_IDENTIFICADO/_COLOR_NO_IDENTIFICADO y
    # _MILISEGUNDOS_RESULTADO ya definidos; crea un np.zeros(...) en vez
    # de cv2.imread(ruta_imagen).
```

`master.py` (extensión del patrón ya existente en `_menu()`/`opciones`):
- `_crear_cuenta_pasajero()` / `_crear_cuenta_chofer()`: como `_crear_cuenta()` actual, pero cada una fija `tipo="pasajero"`/`tipo="chofer"` y también atrapa `cuentas.TipoInvalido` (defensivo, no debería ocurrir).
- `_recargar_saldo()`: exige sesión iniciada, pide el monto (`int`, captura `ValueError` como monto inválido), llama a `cuentas.recargar_saldo`, confirma con el saldo resultante (`cuentas.obtener_saldo`).
- `_fijar_modalidad()`: pide la modalidad (submenú de 3 opciones: metro/metrobús/bici), llama a `cobro.fijar_modalidad`, atrapa `cobro.NoEsChofer`.
- `_cobrar_pasajero()`: llama a `cobro.cobrar(conexion)`, atrapa `cobro.NoEsChofer`, `cobro.SinTurnoVigente`, `cobro.ModalidadNoFijada`.
- `_cerrar_sesion()`: agrega `cobro.reiniciar_estado()` después de `sesion.cerrar_sesion()` (RF-19).
- `_menu()`: cuando `sesion.verificar_expiracion()` devuelve `True`, agrega `cobro.reiniciar_estado()` (RF-19, cierre por inactividad).

## Pruebas
- `test/test_cuentas.py` (extiende) — un caso por cada bloque de RF-1 a RF-10: crear cuenta de cada tipo, tipo inválido (RF-3), saldo inicial en cero para pasajero (RF-5), chofer sin saldo (RF-6), recarga válida/inválida (RF-7 a RF-9), sin tope máximo (RF-10), `CuentaNoEsPasajero` al recargar una cuenta de chofer.
- `test/test_cobro.py` (nuevo) — un caso por cada bloque de turnos/modalidad/cobro (RF-11 a RF-28), inyectando `_turno_vigente` (parámetro `ahora`) para simular horas distintas sin depender del reloj real: rechazo sin sesión de chofer, cálculo de los dos turnos y su ausencia (22:00-6:00), fijar modalidad en turno vigente y en espera (RF-14), descarte al cambiar de turno (RF-18) y al cerrar sesión (RF-19), independencia entre choferes (RF-20), identificación sin revelar id (RF-21, con `identificar` inyectado como doble), sin coincidencia (RF-22), monto correcto por modalidad (RF-23), saldo insuficiente (RF-24), cobro exitoso y registro de transacción (RF-25), cancelación por cierre de sesión a medio proceso (RF-26), mensaje sin identificador ni saldo (RF-27), saldo nunca negativo (RF-28).
- `test/test_identificacion.py` (extiende) — nuevo caso: `revelar_identificador=False` omite el id del mensaje y de la ventana; el comportamiento por defecto (`True`) no cambia (regresión de spec003).
- `test/test_lector_de_caras.py` (extiende) — nuevo caso para `mostrar_mensaje()`: franja verde/roja según `exito`, sin ninguna carga de imagen, cierre automático/por tecla igual que `mostrar_resultado()`.
- `test/test_seguridad_biometrica.py` (extiende) — agregar `cobro.py` a los módulos revisados; nuevo caso: durante `cobro.cobrar()`, ningún identificador ni saldo aparece en la ventana ni en consola (RF-27, confidencialidad).
- Todas las pruebas de `cobro.py`/`cuentas.py` usan el doble en memoria ya establecido (specs/002, D6) para la conexión; no requieren PostgreSQL real.

## Verificación
1. `pytest test/` — deben pasar todos los casos nuevos y existentes, sin cámara, DeepFace ni PostgreSQL reales.
2. Demo manual con `python master.py` (requiere PostgreSQL real, como en specs/002-003): crear una cuenta de chofer y una de pasajero; recargar saldo al pasajero; iniciar sesión como chofer, fijar modalidad antes/después de que inicie un turno; cobrar con las tres modalidades a un pasajero enrolado (specs/001) con saldo suficiente; provocar saldo insuficiente; provocar identificación fallida; cambiar de turno con la sesión abierta y confirmar que se vuelve a pedir la modalidad; intentar cobrar fuera de 6:00-22:00.

## Pendiente, no cubierto por esta spec
- Roles/cuentas de administrador, tarifas configurables, historial de transacciones, recarga con pago real (todos fuera de alcance de `spec.md`).
- Prueba de integración automatizada contra PostgreSQL real (queda como verificación manual, igual que en specs/002-003).

## Ampliación — eliminación de cuenta (RF-29 a RF-37)
Se agregó a `spec.md` después de implementar RF-1 a RF-28, al preparar la demo del cobro. Las decisiones D8–D10 ya se revisaron contigo.

### Archivos que se modifican y por qué (constitution.md, principio 12)
- **`eliminacion_cuenta.py`** (nuevo) — orquesta la eliminación (RF-29 a RF-37) (D8).
- **`cuentas.py`** (existente) — gana `eliminar_cuenta(conexion, identificador)`: solo la parte de PostgreSQL (D9).
- **`master.py`** (existente) — nueva opción de menú "Eliminar mi cuenta"; "Salir" pasa de la opción 11 a la 12. Pide la contraseña con `getpass`, igual que el inicio de sesión.
- **`test/`** — `test_eliminacion_cuenta.py` (nuevo); `conftest.py` gana soporte de `DELETE` en el doble; `test_seguridad_biometrica.py` suma el módulo nuevo y una prueba de residuos; `test_cobro.py` actualiza el número de la opción "Salir" en su prueba de menú.
- **Sin cambios**, se reutilizan tal cual: `almacen_rostros.borrar_enrolamiento()` (spec 001, ya tolera que no haya rostro), `cuentas.verificar_contrasena()` y `sesion.cerrar_sesion()` (spec 002), `cobro.reiniciar_estado()` (RF-19). `basedatos.py` tampoco cambia: el esquema queda igual (D9).

### D8 — Módulo nuevo `eliminacion_cuenta.py`
Orquestador propio, igual que `enrolamiento.py`, `identificacion.py` y `cobro.py`. `master.py` solo pide la contraseña y muestra mensajes.

### D9 — Borrado en PostgreSQL con DELETE explícitos
`cuentas.eliminar_cuenta` ejecuta, con un solo `commit()`, `DELETE` en este orden: `transacciones` → `pasajeros` → `choferes` → `cuentas` (primero las tablas que referencian a las demás). No se usa `ON DELETE CASCADE` desde `transacciones`: `CREATE TABLE IF NOT EXISTS` no modificaría una tabla ya creada, así que funciona igual en cualquier base. Ante cualquier error hace `rollback()` y vuelve a lanzar la excepción.

### D10 — Orden de las validaciones y del borrado
1. Sesión iniciada (RF-30).
2. Si es pasajero, saldo en cero (RF-33) — **antes** de pedir la contraseña, para no pedirla en vano.
3. Contraseña (RF-31/RF-32), verificada con `cuentas.verificar_contrasena`.
4. **Primero el rostro, después la cuenta** (RF-37): si falla el disco, no se tocó nada; si falla PostgreSQL, queda la cuenta sin rostro (estado válido de spec 001) y la sesión sigue abierta para reintentar. Nunca queda un rostro sin cuenta.
5. Cerrar sesión y descartar la modalidad (RF-35).

### Diseño concreto
`cuentas.py`:
```python
def eliminar_cuenta(conexion, identificador: str) -> None:
    """RF-34 (parte de PostgreSQL), D9: un solo commit; rollback ante error."""
    try:
        with conexion.cursor() as cursor:
            cursor.execute("DELETE FROM transacciones WHERE identificador = %s", (identificador,))
            cursor.execute("DELETE FROM pasajeros WHERE identificador = %s", (identificador,))
            cursor.execute("DELETE FROM choferes WHERE identificador = %s", (identificador,))
            cursor.execute("DELETE FROM cuentas WHERE identificador = %s", (identificador,))
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
```

`eliminacion_cuenta.py` (nuevo):
```python
class SesionNoIniciada(Exception): """RF-30."""
class SaldoPendiente(Exception): """RF-33."""
class ContrasenaIncorrecta(Exception): """RF-32."""
class ErrorAlEliminar(Exception): """RF-37."""

def eliminar_cuenta(conexion, *, pedir_contrasena, notificar=print) -> None:
    identificador = sesion.obtener_cuenta_activa()
    if identificador is None:
        raise SesionNoIniciada("Debes iniciar sesión para eliminar tu cuenta.")

    if cuentas.obtener_tipo(conexion, identificador) == "pasajero" \
            and cuentas.obtener_saldo(conexion, identificador) > 0:
        raise SaldoPendiente("Tu saldo debe estar en $0 para eliminar tu cuenta.")

    if not cuentas.verificar_contrasena(conexion, identificador, pedir_contrasena()):
        raise ContrasenaIncorrecta("Contraseña incorrecta. No se eliminó nada.")

    try:
        almacen_rostros.borrar_enrolamiento(identificador)  # D10: rostro primero
    except OSError as error:
        raise ErrorAlEliminar("No se pudo borrar tu rostro. No se eliminó nada.") from error

    try:
        cuentas.eliminar_cuenta(conexion, identificador)
    except Exception as error:
        raise ErrorAlEliminar(
            "Tu rostro fue borrado, pero no se pudo eliminar la cuenta. Vuelve a intentarlo."
        ) from error

    sesion.cerrar_sesion()
    cobro.reiniciar_estado()
    notificar("Cuenta eliminada correctamente.")
```
`pedir_contrasena` se inyecta (en `master.py`, `lambda: getpass(...)`), igual que `confirmar_vista_previa` en `enrolamiento.py`: así se prueba sin teclado y la contraseña nunca pasa por `print`.

### Pruebas
- `test/test_eliminacion_cuenta.py` (nuevo): un caso por bloque de RF-29 a RF-37 — elimina pasajero con saldo $0, chofer y cuenta sin tipo (RF-29/RF-36); sin sesión (RF-30); contraseña incorrecta no borra nada y mantiene la sesión (RF-32); pasajero con saldo se rechaza **sin pedir la contraseña** (RF-33, D10); borra filas, historial y carpeta del rostro, sin tocar otras cuentas (RF-34); cierra sesión y descarta la modalidad (RF-35); falla de PostgreSQL deja la cuenta sin rostro y la sesión abierta (RF-37); el identificador se puede reutilizar después.
- `test/test_seguridad_biometrica.py`: agregar `eliminacion_cuenta.py` a los módulos revisados; nuevo caso: tras eliminar una cuenta enrolada, `enrolled_faces` queda sin residuos y la contraseña no aparece en consola.

## Correcciones durante la implementación
El código es la fuente de verdad (constitution.md, Metodología). Estos ajustes al pseudocódigo de arriba se hicieron para cumplir `spec.md`; ninguno cambia una decisión D1–D7.

1. **`tipo` obligatorio rompe llamadas existentes.** Como RF-3 exige rechazar una cuenta sin tipo válido, `crear_cuenta` no tiene valor por defecto para `tipo`. Las pruebas de specs/002 que llamaban `crear_cuenta` con 3 argumentos (`test_cuentas.py`, `test_sesion.py`, `test_seguridad_credenciales.py`) se actualizaron a `tipo="pasajero"`, sin cambiar lo que verifican. El doble en memoria de `conftest.py` ganó las tablas nuevas y `rollback()`.
2. **Descuento y registro en una sola confirmación.** El pseudocódigo confirmaba el descuento y la transacción por separado; si el registro fallaba, quedaba saldo descontado sin transacción (contradice el caso límite "no queda saldo ni transacción parcial aplicada"). Ahora `descontar_saldo` y `_registrar_transaccion` no confirman; `cobrar()` hace un solo `commit()` y un `rollback()` ante cualquier error.
3. **RF-26 sí detecta la expiración.** La expiración de sesión es perezosa (specs/002, D4): solo `master.py` la revisaba antes de cada opción, así que una sesión que expirara durante la identificación nunca se habría detectado. `cobrar()` llama a `sesion.verificar_expiracion()` después de identificar. Además, en vez de cancelar en silencio, lanza `SesionCerrada` con un mensaje (mismo precedente que `enrolamiento.SesionCerrada`, spec 001): cancelar sin avisar dejaría al chofer creyendo que se cobró.
4. **No se puede volver a fijar la modalidad en el mismo turno.** `spec.md` (Casos límite y Fuera de alcance) dice que no hay forma de cambiarla sin cerrar sesión; `fijar_modalidad` lanza `ModalidadYaFijada` si ya hay una vigente o en espera.
5. **El turno se guarda con su fecha.** Con solo el nombre del turno, el matutino de mañana se confundiría con el de hoy y no se aplicaría RF-18. `_turno_de_modalidad` guarda `(fecha, turno)`.
6. **Cuenta identificada que no es de pasajero.** Si ocurriera (caso límite que "no debería" pasar), `descontar_saldo` lanza `CuentaNoEsPasajero` y `cobrar()` lo rechaza con un mensaje genérico, en vez de tirar `master.py`.
7. **`cobro.modalidad_en_espera()`** (función pública nueva): solo para que `master.py` le diga al chofer si su modalidad quedó en espera (RF-14) o vigente.

## Estado del plan
D1 a D7 quedaron resueltas e implementadas (T1–T7 de `tasks.md`), con 124 pruebas en verde (57 nuevas). D8 a D10 (eliminación de cuenta) quedaron resueltas e implementadas tal como están diseñadas arriba (T9–T12 de `tasks.md`), sin correcciones; la suite queda en 139 pruebas en verde (15 nuevas). Pendiente: la verificación manual con PostgreSQL y cámara reales (T8 y T13).
