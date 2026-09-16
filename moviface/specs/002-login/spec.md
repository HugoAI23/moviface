# Spec 002 — Login y gestión de cuentas de usuario

## Contexto y objetivo
moviface necesita saber, en todo momento, qué usuario de transporte público está usando el sistema, porque el enrolamiento facial (`specs/001-enrolamiento-vectores-faciales`) y el futuro cobro por reconocimiento dependen de una cuenta de movilidad autenticada. Hoy esa dependencia se resuelve con un stub fijo en `sesion.py` que simula una única cuenta demo siempre activa. Esta spec reemplaza ese stub por un mecanismo real: permite que un usuario cree su cuenta de movilidad, inicie sesión con sus credenciales, cierre sesión manualmente, y protege la cuenta cerrando la sesión automáticamente si el usuario se aleja y deja el programa inactivo.

## Usuarios / actores
- **Usuario de transporte público**: único actor de esta spec. Puede crear su propia cuenta, iniciar sesión, cerrar su propia sesión, y no puede acceder ni afectar la cuenta o sesión de nadie más.

El chofer y el administrador no son actores de esta spec: no tienen cuenta ni inician sesión en este alcance.

## Historias de usuario
- H1: Como usuario nuevo quiero crear una cuenta de movilidad con un identificador y una contraseña, para poder empezar a usar moviface.
- H2: Como usuario con cuenta quiero iniciar sesión con mi identificador y contraseña, para acceder a las funciones que requieren una sesión activa (como el enrolamiento).
- H3: Como usuario quiero cerrar mi sesión manualmente cuando termino de usar el sistema, para que nadie más pueda actuar en mi nombre después.
- H4: Como usuario quiero que mi sesión se cierre sola si dejo el programa inactivo demasiado tiempo, para que mi cuenta quede protegida si me alejo sin cerrar sesión.
- H5: Como usuario quiero que el sistema rechace crear una cuenta con un identificador que ya existe, para que no haya conflicto con una cuenta ajena.
- H6: Como usuario quiero recibir un aviso claro cuando mi identificador o contraseña son incorrectos, para saber que debo reintentar o que aún no tengo cuenta.

## Requisitos funcionales (criterios de aceptación en EARS)
- RF-1: CUANDO un usuario solicite crear una cuenta con un identificador y una contraseña, EL SISTEMA creará la cuenta de movilidad únicamente si el identificador tiene formato de correo electrónico válido, no está en uso, y la contraseña cumple los requisitos de RF-4.
- RF-2: SI el identificador proporcionado no tiene formato de correo electrónico válido, ENTONCES EL SISTEMA rechazará la creación de la cuenta e informará el motivo.
- RF-3: SI el identificador elegido ya pertenece a una cuenta existente, ENTONCES EL SISTEMA rechazará la creación de la cuenta e informará que el identificador ya está en uso.
- RF-4: SI la contraseña proporcionada tiene menos de 8 caracteres, no contiene al menos una mayúscula, una minúscula, un número y un carácter especial (símbolo de teclado estándar, ej. `!@#$%^&*`), o contiene espacios, ENTONCES EL SISTEMA rechazará la operación e informará el motivo. Estas mismas reglas aplican a cualquier operación futura que establezca o cambie una contraseña, no solo a la creación de cuenta.
- RF-5: CUANDO se cree una cuenta exitosamente, EL SISTEMA confirmará al usuario que su cuenta fue creada y no la dejará con una sesión iniciada automáticamente (el usuario debe iniciar sesión aparte).
- RF-6: CUANDO un usuario intente iniciar sesión con un identificador y contraseña que coinciden con una cuenta existente, EL SISTEMA iniciará una sesión para esa cuenta.
- RF-7: SI el identificador no corresponde a ninguna cuenta, o la contraseña no coincide con la de la cuenta, ENTONCES EL SISTEMA rechazará el inicio de sesión e informará un mensaje genérico de credenciales inválidas, sin indicar cuál de los dos datos falló, y sin iniciar sesión.
- RF-8: SI ya existe una sesión iniciada dentro del mismo proceso en ejecución y se intenta iniciar sesión de nuevo (misma cuenta u otra), ENTONCES EL SISTEMA rechazará el nuevo inicio de sesión e indicará que debe cerrarse la sesión activa antes de continuar. Este requisito no cubre sesiones iniciadas desde otro proceso u otra ejecución del programa (ver Fuera de alcance).
- RF-9: EL SISTEMA permitirá al usuario con sesión iniciada cerrarla mediante una función explícita del programa.
- RF-10: SI se solicita cerrar sesión y no hay ninguna sesión iniciada, ENTONCES EL SISTEMA informará que no hay sesión activa.
- RF-11: MIENTRAS una sesión esté iniciada y el usuario no realice ninguna acción durante 30 minutos, EL SISTEMA cerrará esa sesión automáticamente. Cualquier acción del menú principal (elegir cualquier opción, no solo las que modifican datos) reinicia este temporizador.
- RF-12: CUANDO una sesión se cierre (manualmente o por inactividad), EL SISTEMA descartará cualquier dato de la sesión activa, de modo que cualquier función que dependa de sesión iniciada (ej. enrolamiento) vuelva a exigir un inicio de sesión nuevo.
- RF-13: EL SISTEMA nunca almacenará la contraseña de una cuenta en texto plano, en ninguna capa de persistencia.

## Requisitos no funcionales
- **Confidencialidad de credenciales**: la contraseña de un usuario nunca se registra en logs, mensajes de error ni salidas de consola, y nunca se muestra en pantalla al escribirla.
- **Aislamiento entre cuentas**: ninguna cuenta puede consultar, iniciar sesión o afectar la sesión de otra cuenta; solo el propio usuario dueño de las credenciales puede autenticarse como esa cuenta.
- **Persistencia de cuentas**: las cuentas creadas persisten entre ejecuciones del programa (se guardan en PostgreSQL, según `docs/constitution.md` principio 10); la sesión iniciada, en cambio, nunca persiste más allá de la ejecución del programa en curso: al cerrar el programa, cualquier sesión activa queda invalidada, y al volver a abrirlo el usuario debe iniciar sesión de nuevo sin excepción.
- **Localidad**: ninguna ruta de creación de cuenta, login o logout envía identificador o contraseña a un servicio externo a la máquina local (más allá de la conexión a la PostgreSQL local del proyecto).
- **Idioma**: toda la interacción con el usuario (mensajes, confirmaciones, errores) es en español.

## Casos límite
- El usuario intenta crear una cuenta con identificador o contraseña vacíos.
- El usuario intenta iniciar sesión sin tener ninguna cuenta creada todavía.
- El usuario cierra el programa con una sesión iniciada y sin cerrarla explícitamente: al volver a abrir el programa no debe quedar sesión activa (debe iniciar sesión de nuevo).
- El usuario alcanza el tiempo de inactividad estando a mitad de otra operación que depende de sesión (ej. enrolamiento): la sesión se cierra igualmente y esa operación debe descartar sus datos parciales (ver `specs/001-enrolamiento-vectores-faciales` RF-15).
- Falla la conexión a PostgreSQL al intentar crear la cuenta o iniciar sesión.
- El usuario intenta crear una cuenta con un identificador que ya existe pero con mayúsculas/minúsculas o espacios distintos: al ser sensible a mayúsculas y espacios (RF-1/RF-3), esto se trata como un identificador distinto y no como duplicado.
- El usuario intenta crear una cuenta con un identificador sin formato de correo válido (ej. sin `@` o sin dominio) (RF-2).

## Fuera de alcance
- Recuperación o restablecimiento de contraseña olvidada.
- Edición de datos de cuenta ya creada (cambiar identificador, cambiar contraseña, cambiar nombre, etc.).
- Eliminación de cuentas.
- Login de chofer o administrador.
- Roles, permisos o niveles de acceso distintos entre cuentas (todas las cuentas de esta spec son del mismo tipo: usuario de transporte público).
- Saldo, transacciones o cualquier operación de cobro asociada a la cuenta (solo se crea la cuenta; el saldo y su manejo se definen en una spec futura).
- Sesiones concurrentes de la misma cuenta desde más de un proceso a la vez.

## Criterios de finalización
- RF-1 a RF-13 tienen prueba en verde en `/moviface/test`.
- `sesion.py` deja de usar la cuenta demo fija y sus funciones públicas (`obtener_cuenta_activa`, `hay_sesion_activa`) quedan respaldadas por el mecanismo real de esta spec, sin que `enrolamiento.py` necesite cambiar cómo las consume. `master.py` sí necesita cambiar: agrega las nuevas opciones de menú para crear cuenta, iniciar sesión y cerrar sesión (H1-H3).
- Demo manual: crear una cuenta, intentar crearla de nuevo y ver el rechazo por duplicado, iniciar sesión con credenciales correctas, iniciar sesión con credenciales incorrectas y ver el rechazo, cerrar sesión manualmente, y provocar el cierre automático por inactividad.

## Dudas abiertas
Ninguna pendiente.
