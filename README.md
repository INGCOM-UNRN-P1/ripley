# Ripley: Motor y CLI de Verificación Pedagógica para C

> 📖 **Manual de Usuario:** Para una guía exhaustiva de comandos, banderas, arquitectura y ejemplos, consultá el [Manual de Uso](MANUAL.md).

Motor de análisis estático, reglas de cátedra P1 (0xXXXXh), compilación sandbox y feedback temprano para código C universitario.

---

## 🎯 Alcance

### Qué cubre
- Microkernel central y orquestador pedagógico de análisis estático y reglas de cátedra de Programación 1 (`0xXXXXh`).
- Publicación y diagnóstico en vivo mediante servidor Language Server Protocol (`ripley lsp`) para VS Code, Neovim y otros editores.
- Modo pedagógico socrático (`--socratic`) que entrega pistas graduales sin revelar la solución directa.
- Modo pista para evaluaciones (`[general] pistas = true` en el `ripley.toml` de la práctica, o `ripley-check check --pista`): exporta `P1_PISTA=1` a daedalus, tetsuo y hal, que dicen el tipo de error y la función sin la línea ni la corrección; el `.ripkg` lo lleva al estudiante.
- Reglas que la actividad no evalúa (`[reglas] ignorar = ["0x40*h", "gaff:0x0101h"]` en el `ripley.toml`, o un `.ripleyignore` con un patrón por línea): para el TP1 sin reglas de módulos. La supresión puntual del estudiante sigue siendo `// ripley:disable-line=0x1001h`.
- Verificación incremental (`ripley-check diff-check --base main`): analiza el proyecto pero informa solo las observaciones en las líneas que cambiaron desde la referencia de git (por defecto, lo no commiteado) y en los archivos nuevos; pensado para sulaco en cada push.
- Perfil de satélites por actividad: `[actividad] tema = "punteros"` en el `ripley.toml` corre los de base (gaff, spunkmeyer, kaneda) y los del tema (bishop y tetsuo para punteros; motoko, corbel y wierzbowski para TAD; kane y vasquez para archivos…), incluidos los dinámicos; `satelites = ["gaff", "motoko"]` los fija a mano.
- Sobre JSON único: además de `ast_findings`, `--json` emite `hallazgos`, cada observación en la forma común del ecosistema (`yutani.hallazgos`: id, categoría y enlace al apunte).
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
uv sync                      # incluye el grupo de desarrollo (pytest)

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

<!-- p1:referencia:inicio — generado por p1-tools/scripts/readme_generado.py: no editar a mano -->

## Referencia rápida

### Requisitos

- Python ≥ 3.11 y [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Programas del sistema: `gcc`.

| Sistema | `gcc` |
|:--|:--|
| Debian / Ubuntu | `sudo apt install gcc` |
| Fedora | `sudo dnf install gcc` |
| Windows | incluido en el entorno de la cátedra (MSYS2 UCRT64) |
| macOS | `xcode-select --install` (clang como `gcc`) |

### Comandos de `ripley`

| Comando | Descripción |
|:--|:--|
| `ripley evaluate` | Ejecuta la compilación, linters, estilo, pruebas y calificación de los estudiantes. |
| `ripley doctor` | Diagnóstico del entorno: herramientas externas presentes y checks afectados. |
| `ripley run` | Verificación temprana completa: compila, corre testcases públicos y aplica los checks del manifiesto. |
| `ripley diff-check` | Verificación incremental: solo las observaciones en lo que cambió desde --base (QoL #818). |
| `ripley check` | Verificación unificada y pedagógica de código C: AST, reglas P1, compilación y AddressSanitizer. |
| `ripley show` | Inspecciona y muestra el contenido, metadatos, enunciado y testcases de un paquete .ripkg. |
| `ripley watch` | Modo Live TDD: recompila y verifica automáticamente al guardar (Ctrl+C para salir). |
| `ripley explain` | Explica una regla pedagógica de cátedra o busca por palabras clave en el catálogo canónico. |
| `ripley gcc-explain` | Traduce mensajes de error y advertencias de GCC/ld a explicaciones claras en español. |
| `ripley analyze` | Análisis programático sin estado para orquestadores (dredd, CI/CD, scripts). |
| `ripley report` | Genera directamente la sección de reporte Markdown de RIPLEY para Dredd. |
| `ripley badge` | Genera un badge SVG con la calificación pedagógica del estudiante. |
| `ripley lsp` | Inicia el servidor Language Server Protocol (LSP) de Ripley en stdio. |
| `ripley fix-interactive` | Aplica auto-correcciones pedagógicas para vicios comunes de C. |
| `ripley style-check` | Verifica la conformidad del código con el estándar estilístico oficial de la cátedra. |
| `ripley history` | Muestra el historial de evolución de corrección de errores del alumno. |
| `ripley template` | Gestión y verificación de plantillas Markdown Jinja2. |
| `ripley testcase` | Gestión y esqueletos de casos de prueba. |
| `ripley practica` | Gestión de prácticas en ./practicas. |
| `ripley audit` | Flujo de auditoría docente: tablero de estados, transiciones e historia. |
| `ripley checks` | Catálogo unificado de verificaciones. |
| `ripley plugins` | Plugins de usuario en plugins/: hooks de ciclo de vida y git hooks. |

Ayuda de cada comando: `ripley <comando> -h`.

### Salida JSON de `ripley`

Con `--json`, estos comandos emiten el resultado como JSON por la salida estándar, para usarlo desde scripts, ripley o dredd: `ripley doctor`, `ripley diff-check`, `ripley check`, `ripley gcc-explain`. El de `doctor --json` lleva `schema_version` y `ok`.

### Comandos de `ripley-check`

| Comando | Descripción |
|:--|:--|
| `ripley-check doctor` | Diagnóstico del entorno: herramientas externas presentes y checks afectados. |
| `ripley-check run` | Verificación temprana completa: compila, corre testcases públicos y aplica los checks del manifiesto. |
| `ripley-check diff-check` | Verificación incremental: solo las observaciones en lo que cambió desde --base (QoL #818). |
| `ripley-check check` | Verificación unificada y pedagógica de código C: AST, reglas P1, compilación y AddressSanitizer. |
| `ripley-check show` | Inspecciona y muestra el contenido, metadatos, enunciado y testcases de un paquete .ripkg. |
| `ripley-check watch` | Modo Live TDD: recompila y verifica automáticamente al guardar (Ctrl+C para salir). |
| `ripley-check explain` | Explica una regla pedagógica de cátedra o busca por palabras clave en el catálogo canónico. |
| `ripley-check gcc-explain` | Traduce mensajes de error y advertencias de GCC/ld a explicaciones claras en español. |
| `ripley-check analyze` | Análisis programático sin estado para orquestadores (dredd, CI/CD, scripts). |
| `ripley-check report` | Genera directamente la sección de reporte Markdown de RIPLEY para Dredd. |
| `ripley-check badge` | Genera un badge SVG con la calificación pedagógica del estudiante. |
| `ripley-check lsp` | Inicia el servidor Language Server Protocol (LSP) de Ripley en stdio. |
| `ripley-check fix-interactive` | Aplica auto-correcciones pedagógicas para vicios comunes de C. |
| `ripley-check style-check` | Verifica la conformidad del código con el estándar estilístico oficial de la cátedra. |
| `ripley-check history` | Muestra el historial de evolución de corrección de errores del alumno. |
| `ripley-check checks` | Catálogo unificado de verificaciones. |
| `ripley-check plugins` | Plugins de usuario en plugins/: hooks de ciclo de vida y git hooks. |

Ayuda de cada comando: `ripley-check <comando> -h`.

### Salida JSON de `ripley-check`

Con `--json`, estos comandos emiten el resultado como JSON por la salida estándar, para usarlo desde scripts, ripley o dredd: `ripley-check doctor`, `ripley-check diff-check`, `ripley-check check`, `ripley-check gcc-explain`. El de `doctor --json` lleva `schema_version` y `ok`.

### Códigos de salida

| Código | Significado |
|:--|:--|
| `0` | Terminó bien (en `doctor`: está todo lo requerido). |
| `1` | El comando encontró problemas (hallazgos, pruebas que fallan, un umbral que no se alcanza) o un dato no se pudo usar (un archivo ilegible, un formato inválido). |
| `2` | Error de uso: comando, opción o argumento inválido. |

<!-- p1:referencia:fin -->
