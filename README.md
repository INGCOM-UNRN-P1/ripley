# Ripley: Motor y CLI de Verificación Pedagógica para C

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
- Multiplataforma (Linux, Windows con MSYS2/WSL, macOS). Python >= 3.10.

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

### 1. Verificación Estudiantil (`ripley check`)
Analiza reglas P1, estilo, convenciones de nomenclatura, números mágicos, compilación protegida con AddressSanitizer y ejecución de testcases:

```bash
# Verificación de archivo único
ripley check solucion.c

# Verificación de proyecto o directorio completo
ripley check . --strict
```

### 2. Análisis Programático para Orquestadores (`ripley analyze`)
Genera salida JSON estructurada con diagnóstico completo para ser consumida por herramientas automáticas (Dredd, CI/CD, scripts):

```bash
ripley analyze src/ --format json
```

### 3. Modo Live TDD (`ripley watch`)
Recompila y verifica automáticamente el código cada vez que se guarda un archivo:

```bash
ripley watch src/
```

### 4. Traductor Pedagógico de Errores GCC (`ripley explain` / `ripley gcc-explain`)
Traduce mensajes crípticos del compilador y enlazador (`ld`) a explicaciones claras en español con sugerencias de corrección:

```bash
gcc -Wall main.c 2>&1 | ripley gcc-explain -
```

---

## 🧱 Estructura del Código

```
src/ripley/
├── cli/                 # Comandos de interfaz estudiantil y orquestación
│   ├── student.py       # check, analyze, watch, doctor, explain
│   └── teacher.py       # gestión de prácticas y esqueletos de testcases
├── core/                # Motor de análisis estático desacoplado
│   ├── engine.py        # Pipeline principal analyze_target() -> AnalysisResult
│   ├── gcc_translator.py# Traductor de errores de gcc/ld a lenguaje pedagógico
│   ├── p1_rules.py      # Chequeador de reglas P1 (0x0001h - 0xEEEEh)
│   ├── linters.py       # Magic numbers, dead code, naming conventions
│   └── ...              # Memory visualizer, flowchart, callgraph
├── pipeline/            # Manifiestos, paquetes .ripkg y catálogo de checks
└── tools/               # Compilador aislado, test runner, sanitizers, sandbox
```

---

## 🧪 Pruebas Unitarias e Integración

```bash
uv run pytest
```
*Toda la suite (245+ tests) ejecuta con cobertura completa sin requerir herramientas externas privativas.*
