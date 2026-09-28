# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
versiones según [SemVer](https://semver.org/lang/es/).

## [1.1.0] - 2026-09-28

Primera versión con registro de cambios; lo anterior está en el historial de git.

### Agregado

- **cli**: cumplir el contrato de línea de comandos de LINEAMIENTOS §3.2 (N-ECO-04) (`1257dc7`)

### Corregido

- **zipapp**: incluir las dependencias de ejecución en ripley.pyz (N-RIPLEY-07, N-RIPLEY-02) (`f6aa898`)
- **tipos**: importar los nombres de typing usados en anotaciones (N-ECO-08) (`2a5a4a5`)
- **doctor**: tomar las descripciones de los satélites del catálogo único (N-RIPLEY-01) (`8125faa`)

### Documentación

- agregar el texto de la licencia GPL-3.0-or-later que declara pyproject (N-ECO-06) (`3752620`)
- **referencia**: corregir los enlaces a módulos movidos o extraídos a satélites (N-ECO-17) (`4f95dee`)
- **paquete**: describir ripley en español según su rol actual (N-RIPLEY-06) (`dd79642`)
- **instalacion**: instalar ripley desde el repositorio y no con pipx por nombre (N-ECO-02) (`18a40c8`)
- incorporar manual de uso integral y referencia tecnica (ripley) (`f4cb73d`)

### Mantenimiento

- **calidad**: verificar errores de Python y dependencias vulnerables (N-ECO-08, N-ECO-13) (`f4a773a`)
- **deps**: mover las dependencias de desarrollo a dependency-groups (N-ECO-07) (`87cc5b0`)
- **release**: apuntar el comentario del workflow al repositorio real (N-RIPLEY-02) (`c437521`)
