# AGENTS.md — moviface

## Proyecto
moviface es un proyecto que busca mediante el reconocimiento facial agilizar el tiempo de cobro en el trasporte publico. Esto mediante el reconocimeinto facial para el usuurio de transporte publico, el chofer y el sistema administrativo que permite el monitoreo y gestion del sistema. Importante mencionar que solo es un proyecto escolar.

## Comandos
- Ejecutar: por ahora no hay comando, pero se pueden proopner y preguntarme para añadirlo a este .md
- Tests: el agente decide que tests ejecutar pero sienmpre llevarlo aabo en la carpeta tests. Cuando sea util mencionarme que el test lo va añadir a una SKILL.md para que yo pida que se escriba y modificarlo y ponerle un nombre. 
- Lint/formato: omitir esta parte.

## Estilo y convenciones
- Esto esta aclarado en constitution.md en cuanto a idioma, variables, funciones, etc.
- Colocar comentarios en las líenas de codigo, sobre todo explicar funciones d ela libreria deepface.

## Herramientas
- Antigravity IDE
- Git
- antigravity 2.0
- DeepFace
postgresql
- librerias en requirements.txt

## Reglas
- Lee docs/constitution.md y la spec activa antes de tocar código.
- Todo se puede tocar, pero siempre con mi permisos y mencionando las razones.
- Todo se trabaja en la arpeta /moviface en la raíz, no puedes trabajar en worktree y no hay otra branch para hacer pruebas, todo se hace en main.
- Las deciones de ariqutectura y diseño yo las tomo, tu mencionas las opciones ocn ventajas y desventajas, pero no debes de implementar nada sin mi permiso.
- Las specs las modifico yo, pero siempre que haya un choque entre la spec, task y mis solicitudes debemos detenernos para alinear todo antes de tocar el código.
- No puedes cambiar la forma de trabajo que se describe en AGENTS.md a menos que yo lo apruebe.
- Los commits y los git push solo los ejecuto yo.

## Durante la ejecución de las tareas.
- Realiza preguntas si no tienes el contexto claro.
- Si tienes varias formas de querer implementar algo preguntame.
- Trabajaremos con el modo plan, por lo que simepre antes de ejecutar la tarea pulimos bien el plan su ejecución.
- El plan esta basado en una spec, pero la fuente de verdad esta en el código.
- Si hay contradicciones simepre mencinarlas para eliminarlas y poder alinear todo.

## Al terminar cualquier tarea
- Ofrecer resumen entre 500 y 250 palabras.
- Resumen de los tests ejecutados cuando se ejecuten.
- Al tratar con los datos faciales ejecuta pruebas de seguridad y comprueba que nada quede expuesto.