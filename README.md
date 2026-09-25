# Ripley: Motor y CLI de Verificación Pedagógica para C

> 📖 **Manual de Usuario:** Para una guía exhaustiva de comandos, banderas, arquitectura y ejemplos, consultá el [Manual de Uso](MANUAL.md).

Motor de análisis estático, reglas de cátedra P1 (0xXXXXh), compilación sandbox y feedback temprano para código C universitario.

---

## 🎯 Alcance

### Qué cubre
- Microkernel central y orquestador pedagógico de análisis estático y reglas de cátedra de Programación 1 (`0xXXXXh`).
- Publicación y diagnóstico en vivo mediante servidor Language Server Protocol (`ripley lsp`) para VS Code, Neovim y otros editores.
- Modo pedagógico socrático (`--socratic`) que entrega pistas graduales sin revelar la solución directa.
- Modo observador en vivo (`ripley watch`) para desarrollo guiado por pruebas (TDD).
- Generación de reportes unificados en consola Rich, formato Markdown y SARIF v2.1.0 estándar.
- Delegación del 100% de verificaciones y análisis profundos en plugins satélites especializados (`SatellitePluginAdapter`).

### Qué no cubre (Límites y Delegación)
- Implementación monolítica de análisis específicos (delega en `gaff`, `spunkmeyer`, `kaneda`, `wierzbowski`, `zhora`, `brett`, `motoko`, etc.).
- Compilación directa de código (delega en `daedalus`).
- Ejecución en sandbox (delega en `nostromo`).
- Calificación masiva de entregas de cursos (delega en `dredd`).

---

## 📋 Requisitos

### Requisitos de Sistema y Entorno
- Multiplataforma (Linux, Windows con MSYS2/WSL, macOS). Python >= 3.11.

### Dependencias Externas y Binarios
- `gcc`, y herramientas satélites en PATH o virtualenv (`daedalus`, `nostromo`).

### Integración en el Ecosistema
- CLI `ripley` y `ripley-check`. Empaquetable como zipapp autónomo (`ripley.pyz`). Subcomando `ripley doctor`.

---

## 🚀 Instalación y Uso Rápido

```bash
# Instalación en modo desarrollo
cd ripley
uv sync --extra dev

# Verificación de entorno y herramientas instaladas
uv run ripley doctor
```

### Ejecución Standalone (Zipapp)
Podés generar o descargar el binario `ripley.pyz` ejecutable directamente en cualquier máquina con Python 3:

```bash
# Construir zipapp standalone
uv run python scripts/build_zipapp.py

# Ejecutar verificación pedagógica en un archivo o directorio
./dist/ripley.pyz check src/ejercicio1.c
```

#### Publicación de Releases (CI)

El workflow [`.github/workflows/release.yml`](.github/workflows/release.yml) publica el zipapp automáticamente:

- **Disparo**: push de un tag `v*` (ej: `git tag v1.0.0 && git push origin v1.0.0`) o ejecución manual (`workflow_dispatch`).
- **Pipeline**: compila `dist/ripley.pyz` (+ alias `ripley_check.pyz`) con `scripts/build_zipapp.py`, verifica que el zipapp sea ejecutable y responde, genera `SHA256SUMS`.
- **Publicación**: con tag crea un GitHub Release con los tres assets y notas automáticas; sin tag deja los artefactos en el run.
- **Consumo estable**: el entorno del alumno aprovisiona desde la URL fija `https://github.com/ingcom-unrn-p1/ripley/releases/latest/download/ripley.pyz` (usada por `entorno/bin/update-env.sh`, `setup.ps1` y `plantilla-TP/tp.sh`), por lo que el nombre del artefacto no debe cambiarse.

---

## 🛠️ Comandos Principales

### Flujo Estudiantil y Verificación Temprana (`ripley-check` / `ripley`)
- **`ripley check <archivo.c|dir>`**: Verificación unificada de código C (reglas P1, estilo, convenciones de nombres, compilación con sanitizers y testcases). Opciones: `--json`, `--strict`, `--socratic`, `--bench`.
- **`ripley analyze <archivo.c|dir>`**: Análisis programático sin estado con diagnósticos en JSON o SARIF v2.1.0 para CI/CD o integración con `dredd`.
- **`ripley watch <dir>`**: Modo observador en vivo (TDD): recompila y verifica automáticamente cada vez que se guarda un archivo.
- **`ripley explain <0xXXXXh|all|palabra>`**: Explicación interactiva de reglas pedagógicas de cátedra con ejemplos de código erróneo vs refactorizado, o búsqueda por palabras clave.
- **`ripley gcc-explain [-|<archivo>]`**: Traductor pedagógico de diagnósticos de GCC/ld desde archivo o stdin (`-`), con soporte `--json`.
- **`ripley doctor`**: Diagnóstico integral de dependencias, herramientas satélites en PATH y matriz de verificaciones habilitadas.
- **`ripley report <archivo.c>`**: Generación de informes de calidad y feedback en Markdown o HTML interactivo.
- **`ripley badge <archivo.c>`**: Generación de badges SVG de puntaje de calidad.
- **`ripley lsp`**: Servidor Language Server Protocol para diagnósticos en vivo directamente en el editor de código.
- **`ripley fix-interactive <archivo.c>`**: Asistente interactivo guiado para corregir violaciones frecuentes.
- **`ripley style-check <archivo.c>`**: Verificación rápida de pautas y formato de estilo.
- **`ripley history`**: Visualización de histórico y métricas de progreso de entregas locales.

### Flujo Docente y Gestión de Actividades
- **`ripley evaluate <directorio>`**: Evaluación docente por lotes de entregas con rúbricas de calificación.
- **`ripley practica`**: Creación, empaquetado (`.ripkg`) y gestión del ciclo de vida de actividades prácticas.
- **`ripley template`**: Generación y verificación de plantillas y esqueletos de ejercicios.
- **`ripley testcase`**: Generación y validación de suites de casos de prueba.
- **`ripley audit`**: Auditoría docente completa de entregas y consistencia.
- **`ripley checks list`**: Listado del catálogo unificado de verificaciones y sus dependencias.
- **`ripley plugins list`**: Detección e inspección de plugins satélites registrados y disponibles.

---

## 🧱 Estructura del Código

```
src/ripley/
├── cli/                 # Comandos de interfaz estudiantil y orquestación
│   ├── student.py       # Comandos estudiantiles (check, analyze, watch, doctor, explain, gcc-explain)
│   ├── teacher.py       # Comandos docentes y gestión de prácticas
│   └── __init__.py      # App Typer unificada combinando ambos flujos
├── core/                # Motor de análisis estático, dinámico y compilación
│   ├── engine.py        # Pipeline principal analyze_target() -> AnalysisResult
│   ├── entrypoints.py   # Adaptador de plugins satélites y SATELLITE_CATALOG
│   ├── gcc_translator.py# Traductor didáctico de diagnósticos de GCC/ld
│   ├── p1_rules.py      # Catálogo y evaluador de reglas P1 (0x0001h - 0xEEEEh)
│   ├── linters.py       # Magic numbers, dead code, naming conventions
│   ├── compiler.py      # Abstracción de compilación C y toolchain
│   ├── runner.py        # Ejecución protegida de testcases
│   └── ...              # Memory visualizer, flowchart, callgraph, sanitizers
├── pipeline/            # Manifiestos, paquetes .ripkg y catálogo de checks
├── teacher/             # Flujos docentes de evaluación, rúbricas y templates
└── models/              # Modelos de datos del ecosistema
```

---

## 🧪 Pruebas Unitarias e Integración

```bash
uv run pytest
```
*Toda la suite (230+ tests) ejecuta con cobertura completa sin requerir herramientas externas privativas.*
