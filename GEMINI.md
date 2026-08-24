# Ripley - Lineamientos de Proyecto y Directivas de Gemini / Antigravity

## 1. Visión del Proyecto
`ripley` es una herramienta CLI en Python (gestionada con `uv`) diseñada para automatizar el procesamiento, versionado incremental, compilación segura, análisis estático/estilo, ejecución dinámica y calificación de entregas masivas de Moodle en C para la materia Programación I.

## 2. Convenciones de Desarrollo
- **Gestión de Entorno:** Utilizar `uv` como gestor de paquetes y entornos virtuales.
- **Punto de Entrada:** Wrapper ejecutable `./ripley` que invoca los módulos CLI (`uv run ripley ...`).
- **Commits Semánticos:** Seguir estrictamente la especificación Conventional Commits:
  - `feat(...)`: Nueva funcionalidad
  - `fix(...)`: Corrección de errores
  - `test(...)`: Incorporación o mejora de pruebas
  - `refactor(...)`: Reestructuración de código sin alterar comportamiento
  - `docs(...)`: Documentación
  - `chore(...)`: Tareas de mantenimiento y configuración
- **Testing & QA:** Suite de pruebas con `pytest` y `pytest-mock` cubriendo unit tests e integration tests con 100% de coherencia frente a `docs/referencia/especificacion-original.md`.
- **Estilo de Código Python:** PEP 8, tipado estricto con `typing`, modularidad con responsabilidades aisladas. Sin código muerto, sin `TODO` o `pass` temporales.
- **Plantillas Jinja2:** Nombres de variables estrictamente en `snake_case`.

## 3. Directivas de Interacción con el Asistente
- **Idioma:** Español rioplatense con voseo estricto.
- **Sin Cortesías:** Respuestas directas, sin relleno ni frases de cortesía.
- **Verificabilidad:** Toda afirmación técnica debe basarse en evidencia concreta, ejecución de pruebas o especificación. No especular ni presentar inferencias como hechos comprobados.
- **Rigor y Acción:** Priorizar soluciones comprobables con resultados medibles antes que explicaciones abstractas.
