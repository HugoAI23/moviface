# Spec 004 — Sistema de cobro de transporte e interfaz chofer/usuario

## Contexto y objetivo
moviface ya puede identificar, por reconocimiento facial, a qué cuenta pertenece el rostro de un pasajero que aborda el transporte (`specs/003-identificacion-facial-tiempo-real`). Esta spec cierra el ciclo de negocio del proyecto: una vez identificado el pasajero, el chofer debe poder cobrarle la tarifa de la modalidad de transporte que está operando (metro, metrobús o bici, únicas modalidades de esta versión) descontando saldo real de su cuenta, y tanto el chofer como el propio pasajero deben recibir la confirmación de que el cobro se realizó — sin que el mensaje revele qué cuenta específica fue cobrada ni su saldo restante. Para que el chofer pueda operar este cobro, esta spec también introduce su propia cuenta y su propio inicio de sesión — hoy `cuentas.py`/`sesion.py` solo contemplan cuentas de pasajero (`specs/002-login`). También introduce la recarga de saldo, sin la cual no habría saldo real que descontar al cobrar.

La modalidad de transporte no se elige en cada cobro individual ni se pide identificar primero: el chofer la fija mediante una acción propia del menú, independiente de cualquier pasajero, una sola vez por **turno** (un bloque horario fijo del día — ver Requisitos funcionales). Puede fijarla incluso antes de que su turno comience, y el cobro en sí es automático: en cuanto se identifica al pasajero, el sistema calcula y aplica el cobro sin pedir confirmación adicional.

**Ampliación posterior — eliminación de cuenta.** Al preparar la demo del cobro se encontró que no hay forma de eliminar una cuenta: borrar el rostro ya existe (`specs/001`, RF-12), pero la eliminación de cuentas quedó fuera de alcance en `specs/002-login`. Esta spec la incorpora (RF-29 a RF-37): el dueño de una cuenta, con su sesión iniciada, puede eliminarla por completo junto con su rostro, sus datos de pasajero o chofer y su historial. Esto también cubre las cuentas creadas antes de esta spec, que no tienen tipo.

Esta spec **depende de**:
- `specs/002-login`: reutiliza y extiende el mecanismo de cuentas/sesión para admitir un tipo de cuenta "chofer" junto al de "pasajero".
- `specs/003-identificacion-facial-tiempo-real`: reutiliza `identificacion.identificar()` para determinar a qué cuenta de pasajero cobrar, con una excepción acotada a RF-7 de esa spec (ver RF-21).

## Usuarios / actores
- **Pasajero**: cuenta de movilidad ya definida en `specs/002-login`. En esta spec, además, puede recargar saldo a su propia cuenta y es la cuenta a la que se le cobra la tarifa.
- **Chofer**: nuevo tipo de cuenta. Puede crear su propia cuenta, iniciar/cerrar sesión, fijar la modalidad de transporte que opera, y cobrar la tarifa al pasajero identificado por reconocimiento facial.

Pasajero, chofer y las cuentas creadas antes de esta spec (sin tipo) pueden eliminar **únicamente su propia cuenta** (RF-29 a RF-37).

El administrador **no** es actor de esta spec (roadmap #4, sin fecha decidida).

## Historias de usuario
- H1: Como persona que va a operar como chofer quiero crear mi propia cuenta de chofer con identificador y contraseña, para poder iniciar sesión y cobrar tarifas.
- H2: Como chofer quiero iniciar sesión con mis credenciales, para acceder a las funciones de cobro.
- H3: Como chofer con sesión iniciada quiero fijar, mediante una acción propia del menú, la modalidad de transporte que opero (metro, metrobús o bici) — incluso antes de que empiece mi turno —, para no tener que elegirla en cada cobro.
- H4: Como chofer quiero identificar al pasajero que aborda y que el sistema le cobre automáticamente la tarifa de la modalidad ya fijada, sin pasos adicionales de confirmación, para agilizar el cobro.
- H5: Como chofer quiero que, si cambia el turno mientras sigo con sesión abierta, el sistema descarte la modalidad anterior y me la vuelva a pedir antes de mi siguiente cobro, para que el monto cobrado siempre corresponda al turno vigente.
- H6: Como chofer quiero ver confirmado en pantalla que el cobro se realizó (o por qué no se realizó), sin que se me muestre a qué cuenta específica pertenece ese pasajero, para saber si la operación fue exitosa sin exponer su privacidad.
- H7: Como pasajero quiero ver, en esa misma pantalla, que se me cobró correctamente al abordar, para tener certeza de la transacción sin depender de otro dispositivo.
- H8: Como pasajero con sesión iniciada quiero recargar saldo a mi propia cuenta, para tener fondos suficientes al abordar el transporte.
- H9: Como pasajero quiero que el sistema rechace el cobro si no tengo saldo suficiente, en vez de dejarme con saldo negativo.
- H10: Como pasajero quiero que el sistema rechace una recarga con un monto inválido (negativo, cero o no entero), para que mi saldo nunca quede en un estado corrupto.
- H11: Como dueño de una cuenta (pasajero, chofer o cuenta antigua sin tipo) quiero eliminar mi cuenta por completo, incluido mi rostro enrolado, para que el sistema no conserve mis datos cuando ya no lo use.
- H12: Como dueño de una cuenta quiero que se me pida mi contraseña otra vez antes de eliminarla, para que nadie pueda eliminarla si dejé mi sesión abierta.
- H13: Como pasajero quiero que el sistema no me deje eliminar mi cuenta mientras tenga saldo, para no perder dinero por accidente.

## Requisitos funcionales (criterios de aceptación en EARS)

### Cuentas de chofer
- RF-1: CUANDO se solicite crear una cuenta indicando un identificador, una contraseña y un tipo de cuenta (pasajero o chofer), EL SISTEMA creará la cuenta únicamente si el identificador tiene formato de correo válido, no está en uso por ninguna cuenta existente sin importar su tipo, y la contraseña cumple los requisitos ya definidos en `specs/002-login` (RF-2 a RF-4).
- RF-2: EL SISTEMA asociará permanentemente a la cuenta el tipo (pasajero o chofer) indicado en su creación; ninguna función de esta spec permite cambiar el tipo de una cuenta ya creada.
- RF-3: SI no se indica un tipo de cuenta válido (pasajero o chofer) al crearla, ENTONCES EL SISTEMA rechazará la creación e informará el motivo.
- RF-4: EL SISTEMA aplicará a las cuentas de chofer las mismas reglas de inicio y cierre de sesión ya definidas en `specs/002-login` (RF-6 a RF-12): credenciales inválidas, sesión única por proceso, cierre manual y expiración por inactividad.

### Saldo y recarga (solo pasajero)
- RF-5: CUANDO se cree una cuenta de tipo pasajero, EL SISTEMA inicializará su saldo en cero.
- RF-6: EL SISTEMA no asociará saldo a las cuentas de tipo chofer.
- RF-7: EL SISTEMA representará el saldo, los montos de recarga y las tarifas de RF-23 siempre como cantidades **enteras** de pesos mexicanos, sin decimales.
- RF-8: CUANDO un pasajero con sesión iniciada solicite recargar saldo indicando un monto, EL SISTEMA sumará ese monto entero al saldo de su propia cuenta únicamente si es mayor que cero.
- RF-9: SI el monto de recarga es menor o igual a cero, no es un número entero válido, o quien la solicita no es una cuenta de pasajero con sesión iniciada (incluye cuentas de chofer y solicitudes sin ninguna sesión activa), ENTONCES EL SISTEMA rechazará la recarga, informará el motivo, y no modificará el saldo.
- RF-10: EL SISTEMA no impone un monto máximo por operación de recarga; solo exige que el monto cumpla RF-8/RF-9.

### Turnos y modalidad de transporte
- RF-11: SI la cuenta con sesión iniciada no es de tipo chofer, o no hay ninguna sesión iniciada, e intenta fijar una modalidad de transporte o iniciar un cobro, ENTONCES EL SISTEMA rechazará la operación con el mismo mensaje, indicando que debe iniciar sesión como chofer, sin distinguir cuál de los dos casos ocurrió.
- RF-12: EL SISTEMA reconoce dos turnos fijos según la hora local del dispositivo: **matutino** (de 6:00 inclusive a 14:00 exclusive) y **vespertino** (de 14:00 inclusive a 22:00 exclusive). Entre las 22:00 y las 6:00 no hay ningún turno vigente.
- RF-13: EL SISTEMA ofrecerá al chofer con sesión iniciada una función explícita de menú para fijar su modalidad de transporte (metro, metrobús o bici), independiente de cualquier intento de cobro.
- RF-14: SI el chofer fija su modalidad mientras no hay ningún turno vigente, EL SISTEMA la guardará en espera y la aplicará automáticamente, sin que el chofer deba volver a fijarla, en cuanto comience el turno siguiente.
- RF-15: SI un chofer con sesión iniciada intenta cobrar fuera de las 6:00–22:00 (sin turno vigente), ENTONCES EL SISTEMA rechazará el cobro e informará que no hay un turno vigente. Esta limitación de horario es intencional en esta versión (ver Fuera de alcance).
- RF-16: SI un chofer con sesión iniciada intenta cobrar dentro de un turno vigente sin haber fijado antes una modalidad para ese turno (RF-13/RF-14), ENTONCES EL SISTEMA rechazará el cobro e indicará que debe fijar su modalidad primero.
- RF-17: EL SISTEMA mantendrá fija la modalidad elegida por un chofer durante el resto del turno vigente y de su sesión, salvo lo indicado en RF-18 y RF-19.
- RF-18: CUANDO el turno vigente cambie de un turno a otro distinto, o de un turno a ningún turno vigente, mientras la sesión del chofer permanece abierta, EL SISTEMA descartará la modalidad fijada para el turno que terminó; el chofer deberá volver a fijarla (RF-13) antes de su siguiente cobro, si el turno nuevo lo permite. Este descarte no aplica a la transición de "ningún turno vigente" a un turno nuevo (ese caso lo cubre RF-14, no un descarte).
- RF-19: CUANDO la sesión de un chofer se cierre (manualmente o por inactividad), EL SISTEMA descartará la modalidad que tuviera fijada (fijada o en espera), consistente con el descarte general de datos de sesión de `specs/002-login` (RF-12); en su siguiente sesión deberá volver a fijarla.
- RF-20: La modalidad fijada por un chofer es independiente de la modalidad fijada por cualquier otro chofer, incluso dentro del mismo turno vigente.

### Cobro
- RF-21: CUANDO el chofer tenga una modalidad fijada para el turno vigente e inicie un cobro, EL SISTEMA ejecutará la identificación facial del pasajero (`specs/003-identificacion-facial-tiempo-real`) para determinar la cuenta a cobrar, sin mostrar el identificador de esa cuenta en ningún mensaje de este flujo. **Excepción acotada**: esto sustituye, únicamente dentro de este flujo de cobro, a RF-7 de `specs/003` (que exige informar el identificador al operador); esa spec sigue aplicando sin cambios a su función genérica de identificación fuera del cobro.
- RF-22: SI la identificación facial no encuentra ninguna cuenta de pasajero coincidente, ENTONCES EL SISTEMA informará que no se identificó a nadie, sin mostrar ningún identificador, y no realizará ningún cobro.
- RF-23: CUANDO se identifique al pasajero, EL SISTEMA calculará de inmediato, sin pedir confirmación al chofer, el monto a cobrar según la modalidad fijada: **metro $5 MXN, metrobús $6 MXN, bici $10 MXN**.
- RF-24: SI el saldo de la cuenta del pasajero identificado es menor al monto de la modalidad fijada, ENTONCES EL SISTEMA rechazará el cobro, no descontará nada del saldo, y mostrará el mensaje de RF-27 indicando saldo insuficiente.
- RF-25: CUANDO el saldo del pasajero identificado sea suficiente, EL SISTEMA descontará de inmediato el monto de la modalidad fijada del saldo de esa cuenta y registrará la transacción (cuenta cobrada, modalidad, monto, fecha).
- RF-26: SI la sesión del chofer se cierra o expira por inactividad después de que la identificación facial determinó una cuenta pero antes de que el descuento de RF-25 se aplique, ENTONCES EL SISTEMA cancelará ese cobro por completo, sin descontar nada del saldo del pasajero.
- RF-27: CUANDO un cobro se complete o se rechace, EL SISTEMA mostrará un único mensaje/pantalla con el resultado (modalidad, monto, éxito o motivo de rechazo — **sin el identificador del pasajero ni su saldo restante**), que sirve como feedback tanto para el chofer como para el pasajero, ya que comparten el mismo dispositivo.
- RF-28: EL SISTEMA nunca dejará el saldo de una cuenta en un valor negativo como resultado de un cobro.

### Eliminación de cuenta
- RF-29: EL SISTEMA permitirá a la cuenta con sesión iniciada eliminar su propia cuenta mediante una función explícita del programa, sin importar si es de pasajero, de chofer o una cuenta sin tipo.
- RF-30: SI se solicita eliminar una cuenta sin que haya ninguna sesión iniciada, ENTONCES EL SISTEMA rechazará la operación e indicará que debe iniciar sesión primero.
- RF-31: CUANDO se solicite eliminar la cuenta, EL SISTEMA pedirá volver a escribir la contraseña de esa cuenta, sin mostrarla en pantalla, antes de eliminar cualquier dato.
- RF-32: SI la contraseña escrita no coincide con la de la cuenta, ENTONCES EL SISTEMA rechazará la eliminación, no eliminará ningún dato y mantendrá la sesión iniciada.
- RF-33: SI la cuenta es de pasajero y su saldo es mayor que cero, ENTONCES EL SISTEMA rechazará la eliminación, no eliminará ningún dato e informará que el saldo debe estar en cero para eliminar la cuenta.
- RF-34: CUANDO se confirme la eliminación, EL SISTEMA borrará por completo la cuenta, su registro de pasajero o de chofer, su historial de transacciones y su rostro enrolado (imagen, vector y cualquier caché o índice derivado), sin dejar residuos (`docs/constitution.md`, principio 7).
- RF-35: CUANDO se complete la eliminación, EL SISTEMA cerrará la sesión, descartará la modalidad fijada si la cuenta era de chofer (RF-19) y confirmará que la cuenta fue eliminada.
- RF-36: EL SISTEMA no asignará ningún tipo a las cuentas creadas antes de esta spec: solo pueden iniciar sesión y eliminarse; la recarga y el cobro les siguen rechazados (RF-9, RF-11).
- RF-37: SI la eliminación falla a medias (por ejemplo, falla la conexión a PostgreSQL o la escritura en disco), ENTONCES EL SISTEMA informará el error y nunca dejará un rostro enrolado sin su cuenta; sí puede quedar la cuenta sin rostro (estado ya válido según `specs/001`), con la sesión todavía iniciada para que el dueño vuelva a solicitar la eliminación.

## Requisitos no funcionales
- **Persistencia**: el saldo y las transacciones de cobro se almacenan en PostgreSQL (`docs/constitution.md`, principio 10), igual que las cuentas.
- **Aislamiento entre cuentas**: solo el pasajero dueño de una cuenta puede recargar saldo a esa cuenta; ninguna cuenta puede modificar el saldo de otra directamente (el cobro lo descuenta el sistema, no otra cuenta).
- **Confidencialidad de identidad en el cobro**: durante todo el flujo de cobro (identificación, cálculo, resultado), el sistema nunca muestra en pantalla ni en consola el identificador de la cuenta del pasajero cobrado, incluso aunque el chofer sea quien opera el proceso (RF-21, RF-22, RF-27).
- **Confidencialidad de credenciales y saldo**: ni el saldo ni las credenciales se registran en logs, mensajes de error ni salidas de consola fuera de los mensajes de feedback explícitos de esta spec.
- **Borrado completo**: después de eliminar una cuenta no queda ningún dato suyo en PostgreSQL ni en `enrolled_faces`; la contraseña escrita para confirmar nunca se muestra ni se registra en logs o consola (igual que en `specs/002-login`).
- **Localidad**: ninguna ruta de recarga, cobro o eliminación envía datos a un servicio externo a la máquina local, más allá de la conexión a la PostgreSQL local del proyecto.
- **Idioma**: toda la interacción con el usuario (mensajes, confirmaciones, errores) es en español.

## Casos límite
- El chofer inicia un cobro y la identificación facial no encuentra a nadie (RF-22): no se descuenta saldo, el chofer puede reintentar sin límite (heredado de `specs/003`, RF-5).
- El pasajero identificado no tiene saldo suficiente (RF-24): el cobro se rechaza por completo, no hay cobro parcial. Si el saldo es exactamente igual al monto de la tarifa, el cobro se acepta y el saldo queda en cero (cubierto por exclusión en RF-24, que solo rechaza si el saldo es *menor*).
- El chofer intenta cobrar entre las 22:00 y las 6:00: se rechaza por no haber turno vigente (RF-15) — limitación conocida y aceptada del MVP, no un error.
- El chofer fija su modalidad antes de que su turno comience: queda en espera y se activa sola al iniciar el turno, sin descartarse (RF-14, distinto del descarte de RF-18).
- El chofer permanece con sesión iniciada cuando el turno cambia (ej. de matutino a vespertino): se descarta la modalidad fijada y se le vuelve a pedir antes de su siguiente cobro (RF-18).
- La sesión del chofer se cierra o expira justo después de identificar al pasajero pero antes de aplicar el descuento: el cobro se cancela por completo, sin descontar nada (RF-26).
- El chofer cierra sesión y vuelve a iniciarla dentro del mismo turno: debe fijar la modalidad de nuevo, ya que se descarta al cerrar sesión (RF-19) — esta es también la forma de corregir una modalidad mal elegida, no hay una función dedicada para cambiarla sin cerrar sesión.
- El chofer cierra el programa por completo (no solo la sesión) con una modalidad fijada: se pierde igual que cualquier otro dato de sesión, por herencia de la persistencia de sesión de `specs/002-login`.
- Un chofer nunca fija una modalidad ni intenta cobrar durante todo su turno: es un estado válido, sin ninguna consecuencia.
- Falla la conexión a PostgreSQL durante una recarga o un cobro: se informa el error y no queda saldo ni transacción parcial aplicada.
- Un mismo pasajero es identificado y cobrado dos veces consecutivas (por error del chofer o doble intento): cada llamada al cobro es independiente y se procesa por separado; esta spec no detecta ni previene cobros duplicados accidentales (ver Fuera de alcance).
- Un pasajero intenta recargar saldo sin tener sesión iniciada, o una cuenta de chofer intenta recargar saldo (RF-9).
- Una cuenta de chofer intenta enrolar su rostro: sigue fuera de alcance, ya establecido en `specs/001-enrolamiento-vectores-faciales`; por lo tanto, la identificación facial durante un cobro nunca debería devolver una cuenta de tipo chofer bajo el comportamiento esperado del sistema.
- La cuenta del pasajero identificado se elimina justo entre la identificación y el descuento del saldo: riesgo bajo en esta simulación de un solo dispositivo, no se maneja explícitamente en esta spec (misma postura que `specs/003` ante condiciones de carrera equivalentes).
- El reloj del dispositivo está mal configurado o cambia por horario de verano: esta spec usa la hora que reporte el sistema operativo tal cual, sin corrección ni validación adicional (ver Fuera de alcance).
- Se elimina una cuenta que no tiene rostro enrolado: se elimina igual; no es un error (a diferencia de borrar solo el rostro, `specs/001` RF-13).
- Un pasajero con saldo mayor que cero quiere eliminar su cuenta: se rechaza (RF-33). Como no existe retiro ni reembolso de saldo, la única forma de dejarlo en cero es consumirlo en cobros — limitación conocida del MVP.
- Un pasajero con saldo en cero y con historial de cobros elimina su cuenta: se elimina también todo su historial (RF-34).
- La contraseña de confirmación se escribe mal varias veces: se rechaza cada vez, sin límite de intentos ni bloqueo, igual que el inicio de sesión de `specs/002-login`.
- Tras eliminar una cuenta, alguien crea una cuenta nueva con el mismo identificador: se permite, porque el identificador ya no está en uso (RF-1); la cuenta nueva no hereda nada de la eliminada.
- Un chofer con una modalidad fijada elimina su cuenta: la modalidad se descarta junto con la sesión (RF-35).

## Fuera de alcance
- Roles/cuentas de administrador y cualquier gestión administrativa (roadmap #4).
- Tarifas configurables o editables desde el sistema (los montos de RF-23 son fijos en esta versión).
- Modalidades de transporte distintas a metro, metrobús y bici.
- Turnos con horarios distintos a los dos bloques fijos de RF-12, turnos configurables por el chofer o por un administrador, u operación de cobro entre las 22:00 y las 6:00 (RF-15).
- Corrección o validación de la hora del sistema (reloj mal configurado, cambios de horario de verano) para el cálculo de turnos.
- Montos con decimales/centavos (RF-7 los define como enteros).
- Una función dedicada para cambiar la modalidad fijada sin cerrar sesión (la única forma de corregirla dentro del mismo turno es cerrar sesión y volver a iniciarla, ver Casos límite).
- Recarga de saldo mediante un método de pago real (tarjeta, efectivo en terminal, pasarela externa, etc.): el monto de recarga se declara directamente en el sistema, sin integración de pago real.
- Historial de transacciones o reportes de cobros/recargas más allá del mensaje inmediato de feedback (RF-27).
- Prevención de cobros duplicados accidentales al mismo pasajero.
- Transferencia de saldo entre cuentas.
- Cambiar el tipo (pasajero/chofer) de una cuenta ya creada.
- Recuperación de contraseña (heredado como fuera de alcance de `specs/002-login`).
- Enrolamiento facial de cuentas de chofer (heredado como fuera de alcance de `specs/001-enrolamiento-vectores-faciales`).
- Eliminar la cuenta de otra persona, o que un administrador elimine cuentas (roadmap #4).
- Recuperar o deshacer la eliminación de una cuenta.
- Retiro, reembolso o transferencia del saldo restante antes de eliminar una cuenta.
- Asignar un tipo (pasajero o chofer) a las cuentas creadas antes de esta spec (RF-36).

## Criterios de finalización
- RF-1 a RF-37 tienen prueba en verde en `/moviface/test`.
- Prueba de seguridad de la eliminación: tras eliminar una cuenta con rostro enrolado no queda ningún residuo en `enrolled_faces` ni en PostgreSQL, y la contraseña de confirmación no aparece en consola.
- Pasan las pruebas de seguridad obligatorias de `constitution.md` (principio 11, sobre datos biométricos). Además, esta spec agrega sus propias pruebas de que ni el saldo ni las transacciones aparezcan en logs, mensajes de error o salidas de consola, y de que ningún identificador de pasajero aparezca durante el flujo de cobro (RF-21/RF-22/RF-27).
- Demo manual: crear una cuenta de chofer e iniciar sesión con ella; crear una cuenta de pasajero, iniciar sesión y recargarle saldo; con la sesión de chofer iniciada, fijar una modalidad antes de que inicie un turno y verificar que se activa sola al comenzar; cobrar a varios pasajeros sin repetir la selección de modalidad, verificando que el mensaje de resultado no revela el identificador ni el saldo restante; ver el rechazo por saldo insuficiente; ver el rechazo por identificación fallida; ver que al cambiar de turno con la sesión abierta se vuelve a pedir la modalidad; ver el rechazo por cobrar fuera de horario de turno.
- Demo manual de eliminación: eliminar la cuenta antigua `hugopocia23@gmail.com` (sin tipo, con rostro enrolado) y confirmar que desaparecen la cuenta y su carpeta en `enrolled_faces`; intentar eliminar un pasajero con saldo y ver el rechazo; escribir mal la contraseña de confirmación y ver el rechazo.

## Dudas abiertas
Ninguna pendiente.
