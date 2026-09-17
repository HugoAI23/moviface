# Tareas — Spec 004: Sistema de cobro de transporte e interfaz chofer/usuario

Basado en `plan.md` (decisiones D1–D7 acordadas). Cada tarea indica qué RF de `spec.md` cubre y en qué archivo vive.

## 1. Infraestructura mínima — esquema de base de datos (D1)
- [x] T1.1 — Agregar a `basedatos.py` el esquema SQL de `pasajeros` (`identificador` FK a `cuentas.identificador`, `saldo` entero con `CHECK (saldo >= 0)` y default 0).
- [x] T1.2 — Agregar a `basedatos.py` el esquema SQL de `choferes` (`identificador` FK a `cuentas.identificador`, sin columnas adicionales).
- [x] T1.3 — Agregar a `basedatos.py` el esquema SQL de `transacciones` (`id`, `identificador` FK a `pasajeros.identificador`, `modalidad` con `CHECK (modalidad IN ('metro','metrobus','bici'))`, `monto` con `CHECK (monto > 0)`, `fecha`).
- [x] T1.4 — Actualizar `inicializar_esquema()` para crear las tres tablas nuevas además de `cuentas`, en el orden correcto (`cuentas` → `pasajeros`/`choferes` → `transacciones`, por las referencias foráneas).

## 2. Módulo `cuentas.py` — tipo y saldo (RF-1 a RF-10)
- [x] T2.1 — Definir `TIPOS_VALIDOS = {"pasajero", "chofer"}` y la excepción `TipoInvalido` (RF-3).
- [x] T2.2 — Extender `crear_cuenta` para recibir `tipo`, validarlo contra `TIPOS_VALIDOS` (RF-3), e insertar en la misma transacción la fila correspondiente en `pasajeros` (saldo 0, RF-5) o en `choferes` (RF-1, RF-2, D1).
- [x] T2.3 — `obtener_tipo(conexion, identificador)`: consulta `pasajeros` y `choferes`; devuelve `"pasajero"`, `"chofer"` o `None` (D3; usada por RF-9 y por `cobro.py` para RF-11).
- [x] T2.4 — `obtener_saldo(conexion, identificador)`: lee el saldo de `pasajeros` (usada por RF-24 y por la confirmación de recarga en `master.py`).
- [x] T2.5 — Excepciones `CuentaNoEsPasajero` y `MontoInvalido` (RF-9).
- [x] T2.6 — `recargar_saldo(conexion, identificador, monto)`: valida tipo pasajero (RF-9) y monto entero mayor que cero (RF-7/RF-8) antes de sumarlo; sin tope máximo (RF-10).
- [x] T2.7 — Excepción `SaldoInsuficiente` (RF-24).
- [x] T2.8 — `descontar_saldo(conexion, identificador, monto)`: rechaza si el saldo es menor al monto (RF-24); nunca deja el saldo en negativo (RF-28).

## 3. Módulo `identificacion.py` — excepción acotada (RF-21, D4)
- [x] T3.1 — Agregar el parámetro `revelar_identificador: bool = True` a `identificar()`.
- [x] T3.2 — Cuando es `False`, cambiar el mensaje interno de `"Rostro identificado: cuenta {id}."` a `"Rostro identificado."` (el mensaje de "no identificado" ya es genérico, sin cambios).
- [x] T3.3 — Verificar que el valor por defecto (`True`) preserva exactamente el comportamiento ya probado de `specs/003` (sin regresión en su opción de menú genérica).

## 4. Módulo `lector_de_caras.py` — ventana sin foto (RF-27, D7)
- [x] T4.1 — `mostrar_mensaje(mensaje, *, exito: bool)`: crea un lienzo en blanco (sin `cv2.imread` ni ninguna imagen capturada), reutilizando `_COLOR_IDENTIFICADO`/`_COLOR_NO_IDENTIFICADO` y `_MILISEGUNDOS_RESULTADO` ya existentes.
- [x] T4.2 — Misma mecánica de cierre que `mostrar_resultado()`: automático a los 4 segundos o al pulsar cualquier tecla.
- [x] T4.3 — Confirmar que esta función nunca recibe ni dibuja un identificador de cuenta ni un saldo (respaldo de la confidencialidad de RF-27).

## 5. Módulo `cobro.py` (nuevo) — turno, modalidad y cobro (RF-11 a RF-28)
- [x] T5.1 — Constantes `TARIFAS` (RF-23: metro $5, metrobús $6, bici $10) y `TURNOS` (RF-12: matutino 6-14h, vespertino 14-22h).
- [x] T5.2 — Estado en memoria del módulo: `_modalidad_fijada`, `_turno_de_modalidad` (D2).
- [x] T5.3 — `_turno_vigente(ahora=None)`: calcula el turno vigente a partir de la hora, con parámetro inyectable para las pruebas (RF-12).
- [x] T5.4 — Excepciones `NoEsChofer`, `SinTurnoVigente`, `ModalidadInvalida`, `ModalidadNoFijada`.
- [x] T5.5 — `_requerir_chofer(conexion)`: valida sesión activa y tipo chofer vía `cuentas.obtener_tipo` (RF-11, D3).
- [x] T5.6 — `fijar_modalidad(conexion, modalidad)`: valida chofer (RF-11), valida la modalidad contra `TARIFAS`, fija `_modalidad_fijada`/`_turno_de_modalidad` (RF-13); si no hay turno vigente, queda en espera (RF-14).
- [x] T5.7 — `_modalidad_vigente()`: resuelve perezosamente el estado turno/modalidad — activa la modalidad en espera al comenzar el turno (RF-14), la mantiene mientras el turno no cambie (RF-16/RF-17), la descarta si el turno cambió desde que se fijó (RF-18).
- [x] T5.8 — `reiniciar_estado()`: descarta modalidad y turno fijados (RF-19); pensada para que `master.py` la invoque al cerrar sesión o al detectar expiración.
- [x] T5.9 — `cobrar(conexion, *, identificar=..., notificar=...)`: valida chofer (RF-11) → valida turno vigente (RF-15) → valida modalidad fijada (RF-16) → llama a `identificar(revelar_identificador=False)` (RF-21).
- [x] T5.10 — Manejo de "nadie identificado": notifica sin revelar identificador y termina sin cobrar (RF-22).
- [x] T5.11 — Manejo de sesión de chofer cerrada o expirada durante la identificación: cancela el cobro sin descontar saldo (RF-26).
- [x] T5.12 — Cálculo del monto según la modalidad fijada (RF-23) y llamada a `cuentas.descontar_saldo` (RF-24/RF-28).
- [x] T5.13 — Manejo de `SaldoInsuficiente`: notifica el rechazo sin identificador ni saldo restante (RF-24, RF-27).
- [x] T5.14 — `_registrar_transaccion(conexion, identificador, modalidad, monto)`: inserta la fila en `transacciones` (RF-25).
- [x] T5.15 — Notificación de cobro exitoso, sin identificador ni saldo restante (RF-25, RF-27).
- [x] T5.16 — Dejar documentado (comentario o prueba) por qué RF-20 se cumple por diseño: solo puede haber una sesión de chofer activa a la vez en todo el proceso (`specs/002-login`, RF-8), así que nunca hay dos modalidades de chofer compitiendo por el mismo estado de módulo.

## 6. Punto de entrada `master.py` (RF-1, RF-8, RF-11 a RF-16, D6)
- [x] T6.1 — `_crear_cuenta_pasajero()`: mismo flujo que `_crear_cuenta()` actual, fijando `tipo="pasajero"`.
- [x] T6.2 — `_crear_cuenta_chofer()`: mismo flujo, fijando `tipo="chofer"`.
- [x] T6.3 — Retirar la opción genérica `_crear_cuenta()` actual (D6: no queda una entrada de menú que pida el tipo a mano; se reemplaza por T6.1/T6.2). Nota: `_crear_cuenta(tipo)` se conserva como función interna que comparten T6.1/T6.2, ya no como opción de menú.
- [x] T6.4 — `_recargar_saldo()`: exige sesión iniciada, pide el monto por consola, captura el error de conversión a entero, llama a `cuentas.recargar_saldo`, confirma mostrando el saldo resultante (`cuentas.obtener_saldo`).
- [x] T6.5 — `_fijar_modalidad()`: submenú de 3 opciones (metro/metrobús/bici), llama a `cobro.fijar_modalidad`, atrapa `cobro.NoEsChofer` y `cobro.ModalidadInvalida`.
- [x] T6.6 — `_cobrar_pasajero()`: llama a `cobro.cobrar(conexion)`, atrapa `cobro.NoEsChofer`, `cobro.SinTurnoVigente` y `cobro.ModalidadNoFijada`.
- [x] T6.7 — `_cerrar_sesion()`: agregar la llamada a `cobro.reiniciar_estado()` después de `sesion.cerrar_sesion()` (RF-19).
- [x] T6.8 — `_menu()`: cuando `sesion.verificar_expiracion()` devuelva `True`, agregar también la llamada a `cobro.reiniciar_estado()` (RF-19, cierre por inactividad).
- [x] T6.9 — Agregar al diccionario `opciones` de `_menu()` las cinco entradas nuevas (crear cuenta de pasajero, crear cuenta de chofer, recargar saldo, fijar modalidad de transporte, cobrar pasajero) y renumerar el resto de las opciones existentes.

## 7. Pruebas (`/moviface/test`, principio 11)
- [x] T7.1 — `test/test_cuentas.py`: un caso por bloque de RF-1 a RF-10 (crear cuenta de cada tipo, tipo inválido, saldo inicial en cero para pasajero, chofer sin saldo, recarga válida e inválida, sin tope máximo, rechazo de recarga a una cuenta de chofer).
- [x] T7.2 — `test/test_cobro.py` (nuevo): un caso por bloque de RF-11 a RF-28, inyectando la hora en `_turno_vigente(ahora=...)` para simular ambos turnos y la ausencia de turno, sin depender del reloj real.
- [x] T7.3 — `test/test_identificacion.py`: caso nuevo para `revelar_identificador=False` (RF-21) y confirmación de que el comportamiento por defecto (`True`, RF-7 de spec003) no cambia.
- [x] T7.4 — `test/test_lector_de_caras.py`: caso nuevo para `mostrar_mensaje()` (franja de color según `exito`, sin ninguna imagen, mismo cierre automático/por tecla que `mostrar_resultado()`).
- [x] T7.5 — `test/test_seguridad_biometrica.py` (o extensión): agregar `cobro.py` a los módulos revisados; caso nuevo que confirma que ningún identificador de cuenta ni saldo aparece en consola o en la ventana durante `cobro.cobrar()`.
- [x] T7.6 — Ejecutar `pytest test/` y confirmar 100% en verde, sin cámara, DeepFace ni PostgreSQL reales.

## 8. Verificación manual (pendiente de una instancia real de PostgreSQL y cámara)
- [ ] T8.1 — Ejecutar el esquema nuevo (`pasajeros`, `choferes`, `transacciones`) contra un PostgreSQL local real y confirmar que las tablas se crean correctamente.
- [ ] T8.2 — Crear una cuenta de chofer y una cuenta de pasajero desde `master.py`.
- [ ] T8.3 — Recargar saldo a la cuenta de pasajero y confirmar el monto reflejado.
- [ ] T8.4 — Iniciar sesión como chofer y fijar la modalidad antes de que comience un turno; confirmar que se activa sola al empezar (RF-14).
- [ ] T8.5 — Con un pasajero ya enrolado (`specs/001`) y con saldo suficiente, cobrar con cada una de las tres modalidades y confirmar el mensaje de éxito, sin identificador ni saldo restante.
- [ ] T8.6 — Provocar y confirmar el rechazo por saldo insuficiente.
- [ ] T8.7 — Provocar y confirmar el rechazo por identificación fallida (nadie enrolado coincide).
- [ ] T8.8 — Cambiar de turno con la sesión del chofer abierta (o simular la hora) y confirmar que se vuelve a pedir la modalidad.
- [ ] T8.9 — Intentar cobrar fuera de 6:00-22:00 (o simular la hora) y confirmar el rechazo por falta de turno vigente.
- [ ] T8.10 — Revisar manualmente que ningún mensaje de consola ni ventana muestre el identificador del pasajero ni su saldo durante toda la demo.

---

# Ampliación — eliminación de cuenta (RF-29 a RF-37)
Basado en `plan.md`, sección "Ampliación — eliminación de cuenta" (decisiones D8–D10).

## 9. Módulo `cuentas.py` — borrado en PostgreSQL (RF-34, D9)
- [x] T9.1 — `eliminar_cuenta(conexion, identificador)`: `DELETE` en orden `transacciones` → `pasajeros` → `choferes` → `cuentas`, con un solo `commit()` (D9).
- [x] T9.2 — Ante cualquier error, `rollback()` y volver a lanzar la excepción, para no dejar filas a medio borrar.

## 10. Módulo `eliminacion_cuenta.py` (nuevo) — orquestación (RF-29 a RF-37, D8/D10)
- [x] T10.1 — Excepciones `SesionNoIniciada` (RF-30), `SaldoPendiente` (RF-33), `ContrasenaIncorrecta` (RF-32) y `ErrorAlEliminar` (RF-37).
- [x] T10.2 — `eliminar_cuenta(conexion, *, pedir_contrasena, notificar=print)`: exige sesión iniciada y toma la cuenta activa, nunca una cuenta recibida por parámetro (RF-29/RF-30).
- [x] T10.3 — Si la cuenta es de pasajero y su saldo es mayor que cero, rechazar **antes** de pedir la contraseña (RF-33, D10).
- [x] T10.4 — Pedir la contraseña con la función inyectada `pedir_contrasena` y verificarla con `cuentas.verificar_contrasena`; si no coincide, rechazar sin borrar nada y sin cerrar la sesión (RF-31/RF-32).
- [x] T10.5 — Borrar primero el rostro con `almacen_rostros.borrar_enrolamiento` (tolera que no exista); si falla el disco, lanzar `ErrorAlEliminar` sin haber tocado la base (RF-34/RF-37, D10).
- [x] T10.6 — Después, borrar en PostgreSQL con `cuentas.eliminar_cuenta`; si falla, lanzar `ErrorAlEliminar` indicando que el rostro ya se borró y que puede reintentar, con la sesión todavía abierta (RF-37).
- [x] T10.7 — Al terminar: `sesion.cerrar_sesion()`, `cobro.reiniciar_estado()` y confirmar "Cuenta eliminada correctamente." (RF-35).
- [x] T10.8 — Confirmar que funciona igual con una cuenta sin tipo, sin asignarle ninguno (RF-36).

## 11. Punto de entrada `master.py` (RF-29, RF-31)
- [x] T11.1 — `_eliminar_cuenta()`: llama a `eliminacion_cuenta.eliminar_cuenta` pasando `pedir_contrasena` con `getpass` (la contraseña nunca se muestra), y atrapa `SesionNoIniciada`, `SaldoPendiente`, `ContrasenaIncorrecta`, `ErrorAlEliminar` y `basedatos.ErrorConexionBaseDatos`.
- [x] T11.2 — Agregar "Eliminar mi cuenta" como opción 11 del menú y mover "Salir" a la opción 12.
- [x] T11.3 — Actualizar el número de "Salir" en la prueba de menú de `test/test_cobro.py` (`test_rf19_expiracion_detectada_por_el_menu_descarta_la_modalidad`).

## 12. Pruebas (`/moviface/test`, principio 11)
- [x] T12.1 — `test/conftest.py`: el doble en memoria reconoce los cuatro `DELETE` de T9.1 y permite simular una falla para probar el `rollback()`.
- [x] T12.2 — `test/test_cuentas.py`: `cuentas.eliminar_cuenta` borra las filas de la cuenta y su historial sin tocar otras cuentas; ante un error no borra nada.
- [x] T12.3 — `test/test_eliminacion_cuenta.py` (nuevo): un caso por bloque de RF-29 a RF-37 (pasajero con saldo $0, chofer, cuenta sin tipo, sin sesión, contraseña incorrecta, saldo pendiente sin pedir contraseña, borrado completo, cierre de sesión y modalidad, falla de PostgreSQL con cuenta sin rostro y sesión abierta, identificador reutilizable).
- [x] T12.4 — `test/test_seguridad_biometrica.py`: agregar `eliminacion_cuenta.py` a los módulos revisados; caso nuevo: tras eliminar una cuenta enrolada no quedan residuos en `enrolled_faces` y la contraseña de confirmación no aparece en consola.
- [x] T12.5 — Ejecutar `pytest test/` y confirmar 100% en verde, sin cámara, DeepFace ni PostgreSQL reales.

## 13. Verificación manual de la eliminación (pendiente de PostgreSQL real)
- [ ] T13.1 — Iniciar sesión con `hugopocia23@gmail.com` (cuenta sin tipo, con rostro), eliminarla y confirmar que desaparecen su fila en `cuentas` y su carpeta en `enrolled_faces`.
- [ ] T13.2 — Con un pasajero con saldo, intentar eliminar su cuenta y confirmar el rechazo sin que se pida la contraseña.
- [ ] T13.3 — Escribir mal la contraseña de confirmación y confirmar que no se borra nada y la sesión sigue iniciada.
- [ ] T13.4 — Eliminar una cuenta de chofer con modalidad fijada y confirmar que la sesión se cierra.
- [ ] T13.5 — Revisar manualmente que la contraseña de confirmación nunca aparezca en pantalla.

## Fuera de esta lista de tareas
- Roles/cuentas de administrador, tarifas configurables, historial de transacciones, recarga con pago real (fuera de alcance de `spec.md`).
- Prueba de integración automatizada contra PostgreSQL real (queda como verificación manual, T8.1–T8.10, igual que en specs/002 y specs/003).
