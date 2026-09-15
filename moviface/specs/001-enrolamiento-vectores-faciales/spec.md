# Spec 001 — Enrolamiento y almacenamiento de vectores faciales

## Contexto y objetivo
moviface necesita registrar el rostro de cada usuario de transporte público para que, en una futura funcionalidad de cobro por reconocimiento facial, el sistema pueda identificarlo. Esta spec cubre exclusivamente el proceso de **enrolamiento**: capturar la foto del rostro del usuario, validarla, generar su vector facial y guardarlo (junto con la imagen) vinculado a la cuenta de movilidad del usuario autenticado. La búsqueda/comparación de vectores para identificar a un usuario en tiempo real y el cobro asociado quedan fuera de esta spec y se abordarán en una spec futura.

Esta spec **depende de `specs/002-login`** (sistema de autenticación, aún no redactada): asume que el usuario ya inició sesión en su cuenta de movilidad antes de llegar al enrolamiento. Esta spec no define cómo se crea una cuenta, ni cómo se inicia o cierra sesión.

## Usuarios / actores
- **Usuario de transporte público autenticado**: único actor que se enrola, y el único que puede consultar, crear o borrar su propio enrolamiento.

El chofer y el administrador no son actores de esta spec: no se enrolan ni participan en este proceso.

## Historias de usuario
- H1: Como usuario de transporte público quiero enrolar mi rostro, una vez iniciada mi sesión, para que el sistema pueda identificarme en el futuro al abordar el transporte.
- H2: Como usuario quiero ver una vista previa de mi foto antes de guardarla, para poder tomar otra si no quedó bien.
- H3: Como usuario quiero poder borrar por completo mi rostro enrolado, para poder enrolarme de nuevo con una foto distinta.
- H4: Como usuario quiero que el sistema rechace un segundo enrolamiento mientras ya tengo uno activo, para evitar duplicados accidentales.

## Requisitos funcionales (criterios de aceptación en EARS)
- RF-1: CUANDO el usuario inicie el proceso de enrolamiento, EL SISTEMA requerirá que exista una sesión iniciada (ver spec 002-login) antes de continuar.
- RF-2: SI no hay una sesión iniciada, ENTONCES EL SISTEMA rechazará el acceso al enrolamiento e indicará que debe iniciar sesión primero.
- RF-3: SI la cuenta de movilidad del usuario autenticado ya tiene un rostro enrolado, ENTONCES EL SISTEMA rechazará el nuevo enrolamiento e indicará que debe borrar el enrolamiento existente antes de continuar.
- RF-4: CUANDO el usuario capture una imagen durante el enrolamiento, EL SISTEMA validará que se detecta exactamente un rostro en la imagen.
- RF-5: SI la imagen capturada no contiene ningún rostro detectable, ENTONCES EL SISTEMA rechazará la captura, informará el motivo y permitirá reintentar sin límite de intentos.
- RF-6: SI la imagen capturada contiene más de un rostro, ENTONCES EL SISTEMA rechazará la captura, informará el motivo y permitirá reintentar sin límite de intentos.
- RF-7: SI la calidad de la imagen capturada es insuficiente según el criterio de detección de la librería utilizada, ENTONCES EL SISTEMA rechazará la captura, informará el motivo y permitirá reintentar sin límite de intentos.
- RF-8: CUANDO una captura pase la validación de rostro único y calidad, EL SISTEMA mostrará al usuario una vista previa de la imagen antes de guardarla.
- RF-9: CUANDO el usuario confirme la vista previa, EL SISTEMA generará el vector facial a partir de la imagen y lo guardará junto con la imagen, vinculados a la cuenta de movilidad del usuario autenticado.
- RF-10: SI la generación o el guardado del vector facial falla después de que el usuario confirmó la vista previa, ENTONCES EL SISTEMA informará el error, descartará cualquier dato parcial que haya llegado a guardarse, y regresará al usuario al paso de captura de foto.
- RF-11: CUANDO el usuario rechace la vista previa, EL SISTEMA descartará la captura y permitirá al usuario tomar una nueva foto, sin límite de intentos.
- RF-12: EL SISTEMA permitirá al usuario autenticado borrar por completo su propio enrolamiento (imagen, vector y cualquier caché o índice derivado) mediante una función explícita del programa.
- RF-13: SI el usuario solicita borrar su enrolamiento y su cuenta no tiene ningún rostro guardado, ENTONCES EL SISTEMA informará el error correspondiente.
- RF-14: CUANDO se complete el borrado de un enrolamiento, EL SISTEMA confirmará al usuario que el rostro fue eliminado.
- RF-15: SI la sesión del usuario se cierra o expira en cualquier momento durante el proceso de enrolamiento, ENTONCES EL SISTEMA descartará cualquier dato parcial capturado y el usuario deberá iniciar sesión nuevamente y comenzar el enrolamiento desde el inicio.

## Requisitos no funcionales
- **Seguridad de datos biométricos**: la imagen y el vector facial nunca se registran en logs, mensajes de error ni salidas de consola.
- **Confidencialidad**: solo el usuario autenticado dueño del enrolamiento puede consultar, crear o borrar sus propios datos biométricos; ninguna otra cuenta puede acceder a ellos, y solo las funciones definidas en esta spec (captura/guardado y borrado) pueden modificarlos.
- **Localidad**: la imagen y el vector se almacenan únicamente en el dispositivo local; ninguna ruta del enrolamiento envía estos datos a red o servicio externo.
- **Idioma**: toda la interacción con el usuario (mensajes, confirmaciones, errores) es en español.

## Casos límite
- El usuario cancela el proceso antes de confirmar la vista previa: no debe quedar ningún dato residual guardado (ni imagen ni vector parcial).
- Falla la cámara o no hay una disponible al iniciar el enrolamiento.
- Falla la escritura en disco al guardar la imagen o el vector, o la generación del vector falla tras la confirmación (RF-10): no debe quedar imagen ni vector parcial/huérfano asociado a la cuenta.
- El programa se cierra o falla a mitad del enrolamiento, después de capturar pero antes de confirmar: sin datos residuales.
- El usuario borra su enrolamiento y no vuelve a enrolarse: la cuenta queda sin rostro asociado, lo cual es válido.
- El usuario intenta borrar un enrolamiento que no existe (RF-13).
- La sesión del usuario se cierra o expira a mitad del enrolamiento: se descarta todo lo capturado y debe reiniciar el proceso desde el inicio, con una nueva sesión (RF-15).

## Fuera de alcance
- Búsqueda/comparación de vectores para identificar a un usuario en tiempo real.
- Cobro o cargo a la cuenta de movilidad.
- Confirmación del reconocimiento en la interfaz del chofer.
- Visualización de la tarifa cobrada.
- Sistema de login/autenticación completo: creación de cuentas, inicio de sesión, cierre de sesión, recuperación de contraseña, expiración de sesión, etc. (se define en `specs/002-login`; esta spec solo asume una sesión ya iniciada como precondición).
- Enrolamiento de choferes o administradores.
- Más de un rostro/vector activo por cuenta (solo un enrolamiento vigente a la vez).
- Detección de que un mismo rostro físico ya esté enrolado en una cuenta distinta a la del usuario autenticado (limitación conocida del MVP).

## Criterios de finalización
- RF-1 a RF-15 tienen prueba en verde en `/moviface/test`. RF-1, RF-2 y RF-15 dependen de que exista un mecanismo de sesión (de `specs/002-login`) contra el cual probar.
- Pasan las pruebas de seguridad obligatorias de `constitution.md` (principio 11): `.gitignore` excluye `enrolled_faces`, ningún dato biométrico aparece en logs/errores, el borrado no deja residuos, no existe ruta de red que envíe estos datos fuera de la máquina local.
- Demo manual: con sesión iniciada, enrolar un usuario, intentar un segundo enrolamiento y ver el rechazo por duplicado, borrar el enrolamiento y volver a enrolarse exitosamente.

## Dudas abiertas
Ninguna pendiente.
