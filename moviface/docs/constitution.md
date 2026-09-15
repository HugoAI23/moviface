# Constitución - moviface

> **Versión:** 1.2.0 | **Última modificación:** 2026-09-14
> Este documento define los principios innegociables bajo los que se diseña, planea y construye moviface. No contiene requisitos funcionales — esos viven en la spec activa, que sí puede evolucionar. La constitution es de cambio excepcional (ver Gobernanza).

## Metodología

Este proyecto se desarrolla bajo un enfoque **spec-first / spec-anchored** (Spec-Driven Development): no se sigue un framework de SDD específico ni sus artefactos rígidos, pero toda decisión de diseño e implementación debe poder rastrearse a una spec escrita y aprobada. La spec es la guía y especificación de lo que el agente debe entregar; **el código es la fuente de verdad** de lo que el sistema realmente hace — si el código y la spec divergen, se corrige la spec para que refleje el código real, o se corrige el código si la divergencia fue un error de implementación, y se pregunta a Hugo cuando no sea obvio cuál de los dos casos aplica.

## Principios innegociables

1. **Stack mínimo:** Python 3.13+, librería DeepFace, PostgreSQL (cuentas/saldos/transacciones) y el documento `requirements.txt`.

2. **La spec manda:** ningún comportamiento se implementa si no está en la spec activa. Si falta una decisión, se detiene el trabajo y se pregunta a Hugo.

3. **Todo se trabaja en la carpeta `/moviface`**: al ser un proyecto escolar y una simulación de un solo dispositivo (no un sistema multiusuario en producción), no es necesario usar rama staging ni worktree para pruebas. Todo se prueba en la rama `main`.

4. **Naturaleza del dato — rostros:** las fotos, imágenes y los vectores/embeddings faciales derivados de ellas son datos biométricos sensibles. Aunque este es un proyecto de demo local (sin backend compartido ni transferencia de datos), se tratan con el mismo cuidado que si fueran datos de producción:
   - Nunca se suben al repositorio.
   - Nunca se comparten con nadie.
   - Solo el propio usuario dueño del dispositivo puede consultarlas.
   - Nadie más que el propio proceso de enrolamiento puede modificarlas.
   - El vector/embedding recibe el mismo nivel de protección que la imagen fuente — no es un dato "derivado y por lo tanto menos sensible": es, de hecho, el identificador biométrico más crítico del sistema.

5. **Ubicación y exclusión de control de versiones:** la base de datos de rostros — imágenes y cualquier vector/embedding o índice derivado de DeepFace — vive en `/moviface/static/img/enrolled_faces`. Esta carpeta:
   - Debe estar en `.gitignore` — excluida de todos los commits.
   - No debe ser visible para otros usuarios al hacer fork del repositorio ni en ningún otro caso.
   - Debe incluirse un archivo `.gitkeep` o similar (vacío) si se necesita que la carpeta exista tras clonar, sin exponer contenido real.

6. **Datos locales, no transferibles:** los rostros se guardan únicamente en la computadora local del usuario. No existe mecanismo de sincronización, backup remoto, ni transferencia a internet, GitHub, ni ningún servicio externo. Esto es una simulación de un solo dispositivo, no un sistema centralizado multiusuario.

7. **Borrado de rostros:** si el usuario lo solicita, su(s) foto(s) e información de enrolamiento deben poder eliminarse por completo de `enrolled_faces` (y de cualquier caché o índice derivado de DeepFace) mediante una función clara del programa — no un borrado manual de archivos.

8. **Punto de entrada único — `master.py`:** es el único archivo que el usuario ejecuta. Módulos de apoyo (`lector_de_caras.py`, `cobro_de_transporte.py`, etc.) contienen lógica de soporte pero nunca se ejecutan directamente.

9. **Idioma:** español en todo lo que sea posible — comentarios, documentación, nombres de variables y funciones, e interfaz de usuario. Términos técnicos sin equivalente natural o estándar en la industria (ej. nombres de librerías, `commit`, `dataset`, `embedding`, palabras reservadas de Python) se mantienen en inglés tal como se usan comúnmente.

10. **Postgres — alcance:** la base de datos PostgreSQL almacena cuentas de usuario, saldos y transacciones/cargos de movilidad. No almacena imágenes ni vectores faciales — esos viven exclusivamente en `enrolled_faces` (principio 5).

11. **Pruebas — ubicación y alcance obligatorio:** todas las pruebas se ejecutan desde la carpeta `/moviface/test`. El agente define, para cada módulo relevante, el tipo de prueba más adecuado (unitaria, integración, etc.), pero es innegociable — sin importar qué otras pruebas se decidan — contar con pruebas específicas de seguridad dado que el proyecto maneja datos biométricos:
    - Verificar que `enrolled_faces` y cualquier ruta de datos sensibles esté efectivamente excluida por `.gitignore` (test que falle si el patrón se elimina o rompe).
    - Verificar que ninguna imagen, vector o dato biométrico se escriba en logs, mensajes de error o salidas de consola.
    - Verificar que la función de borrado de rostro (principio 7) efectivamente elimina el archivo y cualquier caché derivado, sin dejar residuos.
    - Verificar que no exista ninguna ruta de código que envíe datos de `enrolled_faces` fuera de la máquina local (red, API externa, etc.).

12. **Cambios que tocan múltiples archivos conectados:** cuando una tarea requiera modificar archivos que están interconectados con otros (ej. cambios que afecten tanto a `lector_de_caras.py` como a `master.py` o a la base de datos), el agente debe presentar, **antes de tocar código**, una lista explícita de:
    - Qué archivos se van a modificar.
    - Por qué cada uno necesita cambiar.

    Hugo revisa y aprueba o ajusta esa lista antes de que se ejecute cualquier cambio.

13. **Decisiones de diseño y arquitectura requieren aprobación previa:** dado que Hugo es primerizo en Spec-Driven Development y la arquitectura del proyecto se irá definiendo sobre la marcha, cualquier decisión de diseño o arquitectura que el agente proponga tomar (estructura de módulos, elección de patrones, esquema de base de datos, flujo entre componentes, etc.) debe presentarse a Hugo para su revisión, ajuste y aprobación **antes** de implementarse. El agente no decide arquitectura de forma unilateral.

## Gobernanza de este documento

- Esta constitution es de **cambio excepcional**, no de cambio frecuente. Los requisitos funcionales, el alcance de features, y las decisiones de producto NO viven aquí — viven en la spec activa, que sí evoluciona libremente.
- Un principio solo se modifica, elimina o agrega con aprobación explícita de Hugo, nunca de forma unilateral por el agente.
- Si un principio de esta constitution entra en conflicto con una spec o una tarea puntual, la constitution tiene prioridad — se detiene el trabajo y se pregunta antes de proceder.
- Cada cambio a este documento debe reflejarse actualizando el número de versión y la fecha en el encabezado.