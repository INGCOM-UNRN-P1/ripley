# Ripley: Motor y CLI de Verificación Pedagógica para C

Motor de análisis estático, reglas de cátedra P1 (0xXXXXh), compilación sandbox y feedback temprano para código C universitario.

---

## 🎯 Rol en el Ecosistema

- **`ripley` (Motor & CLI)**: Análisis estático determinista y sin estado (`ripley check`, `ripley analyze`), traducción de errores de GCC en lenguaje llano, auditoría de AST, reglas de estilo, contratos ACSL, sandbox de ejecución y soporte TDD.
- **Distribución Estudiantil**: Empaquetado autónomo en un único archivo ejecutable sin dependencias externas pesadas (`ripley.pyz`).
- **Orquestación Masiva**: La gestión de lotes masivos de Moodle, sincronización de repositorios de GitHub Classroom, generación de Pull Requests y detección de plagio a nivel cohorte es delegada al orquestador docente **`dredd`**.

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
