# Spec 003 — Identificación facial en tiempo real

## Contexto y objetivo
`specs/001-enrolamiento-vectores-faciales` guarda la imagen y el vector facial de cada cuenta enrolada, pero no los usa para nada más: no existe ninguna forma de comparar un rostro capturado contra lo ya enrolado para saber de quién se trata. Esta spec cubre exactamente eso: capturar una foto y determinar, comparándola contra los vectores de todas las cuentas enroladas, a cuál cuenta pertenece ese rostro (o que no pertenece a ninguna).

Esta es la pieza que, en el futuro, usará la interfaz del chofer para reconocer a un pasajero al abordar. Como esa interfaz (`specs/006-...` o la que se defina) todavía no existe, esta spec expone la identificación como una función genérica del programa, sin asumir quién la ejecuta.

El cobro de la tarifa, el descuento de saldo y cualquier confirmación visual para el chofer quedan fuera de esta spec — aquí solo se resuelve la pregunta "¿de quién es este rostro?".

**Excepción documentada al principio 4 de `docs/constitution.md`**: ese principio dice que solo el dueño de un rostro enrolado puede consultar sus propios datos biométricos. Identificar a alguien exige, por definición, comparar una captura contra los vectores de **todas** las cuentas enroladas — no contra una sola. Se deja establecido aquí, explícitamente, que el **proceso de identificación** (no una cuenta, no una persona) es la única función además del propio enrolamiento autorizada a **leer** (nunca modificar, nunca exponer) los vectores de todas las cuentas, exclusivamente para compararlos y determinar una coincidencia.

## Usuarios / actores
- **Operador del dispositivo**: quien ejecuta la identificación desde `master.py`. Es un rol provisional: hasta que exista una spec de chofer, cualquiera con acceso físico al programa puede activarla.
- **Usuario de transporte público enrolado**: la persona cuyo rostro se captura para identificar. No necesita sesión iniciada ni interactúa con el programa: es un sujeto pasivo del proceso.

## Historias de usuario
- H1: Como operador del dispositivo quiero capturar el rostro de un pasajero y que el sistema me diga a qué cuenta enrolada pertenece, para saber quién está abordando.
- H2: Como operador quiero que el sistema me avise claramente cuando no reconoce a nadie, para poder reintentar o resolverlo de otra forma.
- H3: Como usuario de transporte público enrolado quiero que me identifiquen correctamente incluso si mi rostro se parece al de otra cuenta, para que no me confundan con alguien más.

## Requisitos funcionales (criterios de aceptación en EARS)
- RF-1: CUANDO el operador inicie la identificación, EL SISTEMA capturará una imagen con la cámara.
- RF-2: SI la imagen capturada contiene más de un rostro, ENTONCES EL SISTEMA rechazará la captura, informará el motivo y permitirá reintentar sin límite de intentos.
- RF-3: SI la imagen capturada no contiene ningún rostro detectable, o su calidad es insuficiente según el criterio de la librería utilizada, ENTONCES EL SISTEMA rechazará la captura, informará el motivo y permitirá reintentar sin límite de intentos.
- RF-4: CUANDO una captura pase la validación de rostro único, EL SISTEMA generará su vector facial y lo comparará contra los vectores de todas las cuentas que tengan un rostro enrolado.
- RF-5: SI ninguna cuenta enrolada alcanza el umbral de similitud suficiente (definido por la librería utilizada, no por moviface), ENTONCES EL SISTEMA informará que no identificó a nadie y permitirá reintentar sin límite de intentos.
- RF-6: SI más de una cuenta enrolada alcanza el umbral de similitud suficiente, ENTONCES EL SISTEMA identificará la cuenta cuya similitud sea mayor entre las candidatas.
- RF-7: CUANDO el sistema identifique una cuenta, informará su identificador al operador, sin exponer el vector facial de ninguna cuenta.
- RF-8: EL SISTEMA no exigirá ninguna sesión iniciada (ni del operador ni del usuario identificado) para ejecutar la identificación.
- RF-9: EL SISTEMA únicamente leerá los vectores ya enrolados durante la identificación: no crea, modifica ni borra ningún dato de enrolamiento en este proceso.

## Requisitos no funcionales
- **Excepción de confidencialidad acotada** (ver Contexto): el proceso de identificación puede leer los vectores de todas las cuentas enroladas exclusivamente para compararlos; ninguna otra función nueva de esta spec obtiene ese permiso, y en ningún caso se expone el contenido de un vector (ni el propio ni el de otra cuenta) al operador ni en consola.
- **Seguridad de datos biométricos**: igual que en `specs/001...`, ninguna imagen ni vector se registra en logs, mensajes de error o salidas de consola.
- **Localidad**: la comparación ocurre enteramente en el dispositivo local; ninguna ruta de esta spec envía datos biométricos a un servicio externo.
- **Idioma**: toda la interacción con el usuario es en español.

## Casos límite
- No existe ninguna cuenta enrolada todavía: la identificación siempre informa que no se identificó a nadie.
- Falla la cámara o no hay una disponible al iniciar la identificación.
- Dos cuentas enroladas tienen una similitud exactamente idéntica frente a la captura (empate): se identifica la cuenta que se enroló primero entre las empatadas (orden determinista, sin importar que la similitud sea igual).
- Se borra el enrolamiento de una cuenta justo mientras se está comparando contra ella (concurrencia): riesgo bajo en esta simulación de un solo dispositivo, no se maneja explícitamente en esta spec.
- El rostro capturado es de alguien enrolado que además tiene su cuenta con sesión iniciada en otra parte del programa: no afecta el resultado, la identificación es independiente de cualquier sesión (RF-8).

## Fuera de alcance
- Cobro, descuento de saldo o cualquier transacción asociada a la identificación (spec futura).
- Interfaz real del chofer: esta spec solo expone una función genérica en `master.py` como reemplazo provisional.
- Registro histórico o auditoría de identificaciones realizadas.
- Detección de suplantación (ej. mostrar una foto de una foto en vez de un rostro real, "liveness detection").
- Detección de que un mismo rostro físico esté enrolado en más de una cuenta (ya fuera de alcance de `specs/001...`).
- Login o rol de chofer o administrador (specs futuras).

## Criterios de finalización
- RF-1 a RF-9 tienen prueba en verde en `/moviface/test`.
- Pruebas de seguridad: ningún vector facial (ni el de la captura ni el de ninguna cuenta enrolada) se expone en logs, mensajes de error o salidas de consola durante la comparación.
- Demo manual: enrolar al menos dos cuentas distintas, identificar correctamente a cada una por separado, y capturar un rostro no enrolado para confirmar el mensaje de "no identificado".

## Dudas abiertas
Ninguna pendiente.
