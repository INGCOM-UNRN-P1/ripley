Actúa como un ingeniero de software senior y especialista en herramientas de evaluación de código. Desarrolla una herramienta de línea de comandos (CLI) en Python llamada `ripley` (inspirada en Ellen Ripley de Aliens) para procesar, versionar, compilar, probar y evaluar entregas académicas masivas descargadas desde Moodle para la materia Programación I (ejercicios individuales en C).

---

### 1. Contexto y Formato de Entrada de Moodle

1. **Archivo ZIP contenedor (Lote de Moodle):**
   - Patrón de nombre típico: `- (B6003) - 40- Programación I COM 1 - 2026-Entrega #1-1228009.zip`
   - **Regla de extracción:** Ignorar el nombre de la sala/comisión (`- (B6003) - 40- Programación I COM 1 - 2026-`). Extraer el **Nombre de la actividad** (`Entrega #1`) y el **ID interno** (`1228009`).
   - Directorio raíz de la actividad: Slugificar la combinación `nombre-actividad_id` (ejemplo: `entrega-1_1228009/`).

2. **Estructura interna del ZIP y Sanitización de Ingesta:**
   - Subdirectorios por estudiante: `<APELLIDO NOMBRE>_<ID_ENTREGA>_assignsubmission_file/`.
   - **Normalización de Codificación:** Detectar y convertir automáticamente la codificación de caracteres de los archivos fuente (ej. de `ISO-8859-1` o `Windows-1252` a `UTF-8`).
   - **Aplanamiento de Estructura (Flattening):** Si el estudiante incluyó subcarpetas por error dentro de su entrega, extraer todos los archivos `.c` y `.h` a la raíz de la revisión correspondiente.
   - **Filtrado de Archivos No Válidos:** Separar archivos con extensiones no permitidas (`.exe`, `.zip`, `.pdf`, etc.) a un registro de "Archivos ignorados/no permitidos" en los metadatos y el informe.
   - **Detección Determinista de Cambios por Hash:** Calcular el hash SHA-256 de los fuentes. No crear una nueva revisión si el hash del código no ha cambiado respecto a la versión previa.

---

### 2. Configuración Externa y Persistencia de Estado

1. **Archivo de Configuración Externalizado (`ripley.toml`):**
   Toda la lógica configurable reside en un archivo TOML:
   - Compilador (`gcc`), flags (`-Wall -Wextra -pedantic -std=c11 -fsanitize=address,undefined`).
   - Límites de recursos (`timeout_segundos = 5`, `limite_memoria_mb = 128`, `max_tamaño_ejecutable_mb = 10`).
   - Ruta al directorio de plantillas Jinja2 (ej. `ruta_plantillas = "templates/"`).
   - **Configuración de Linter y Reglas Personalizadas (`cppcheck`):**
     - Ruta al ejecutable de Cppcheck (ej. `cppcheck` del sistema o binario local `./cppcheck`).
     - Parámetros adicionales y reglas (ej. `--enable=all`, `--inline-suppr`).
     - Soporte para scripts de reglas/addons personalizados en Python (ej. `reglas_python = ["tools/cppcheck_rules.py"]`).
   - **Análisis de Estilo y Formato Personalizable (`[style]`):**
     - Estilo de llaves (`brace_style`): `K&R`, `Allman` / `BSD` o `attach`/`break`.
     - Obligatoriedad de llaves (`require_braces`): Forzar el uso de llaves `{}` en bloques condicionales e iterativos.
     - Indentación y Espacios (`indent_style`): Espacios vs Tabs y tamaño estricto de sangría (ej. 4 espacios).
     - Espaciado alrededor de operadores y palabras clave (`spacing_operators`, `spacing_keywords`).
     - Espacios finales y líneas en blanco (`no_trailing_whitespace`, `max_blank_lines`).
   - **Auditoría de Memoria con Valgrind y Tolerancia Diferenciada (`[valgrind]`):**
     - Flags de Valgrind (`--leak-check=full`, `--show-leak-kinds=all`, `--track-origins=yes`).
     - `tolerar_fugas_en_error = true`: Permite tolerar o reducir penalizaciones por fugas de memoria ocurridas en salidas anormales por error (`exit(EXIT_FAILURE)`).
   - **Pesos de Rúbrica de Calificación (`[rubric]`):**
     - `peso_compilacion`, `peso_linter`, `peso_estilo`, `peso_pruebas` (suma = 1.0).

2. **Persistencia de Estado (`.metadata.db` / SQLite):**
   - Base de datos SQLite local para almacenar estudiantes, revisiones (`r1`, `r2`, ...), hashes SHA-256 de entregas, resultados de compilación, linter, estilo, testcases, métricas de Valgrind y notas acumulativas.

---

### 3. Estructura de Directorios y Gestión de Prácticas

```text
workspace/
├── ripley.toml                                 # Configuración global
├── templates/                                  # Plantillas base Jinja2 para informes
│   ├── header.jinja2.md
│   ├── version_section.jinja2.md
│   └── footer.jinja2.md
├── practicas/                                  # Prácticas docentes estructuradas
│   └── <slug_practica>/                        # ej. practica-1-punteros/
│       ├── ripley.toml                         # Configuración específica de la práctica
│       ├── enunciado.md                        # Enunciado general
│       ├── pautas_evaluacion.md                # Criterios y rúbrica docente
│       └── ejercicios/
│           ├── <ejercicio>/
│           │   ├── enunciado.md
│           │   ├── solucion_modelo.c           # Solución de referencia docente
│           │   └── tests/                      # Casos de prueba (.in, .out, .argv)
├── tests/                                      # Casos de prueba sincronizados por actividad
│   └── <actividad_slugificada>/                 # ej. entrega-1_1228009/
│       └── <ejercicio>/
│           ├── caso1.in / caso1.out / caso1.argv
│           └── caso2.in / caso2.out
└── <actividad_slugificada>/                     # Entregas procesadas
    ├── dashboard.md                            # Reporte consolidado de la cohorte
    ├── moodle_grades.csv                       # CSV para importar en Moodle
    ├── retroalimentacion_moodle.zip            # ZIP para subida masiva de retroalimentación
    ├── plagiarism_report.md                    # Reporte de plagio y similitud (si fue requerido)
    └── <estudiante_slugificado>/               # ej. perez-juan_123456/
        ├── <estudiante_slugificado>_<actividad>.md # Informe acumulativo
        ├── .metadata.db                        # Estado SQLite local
        ├── mapping.json                        # Mapeo persistente de archivos C a ejercicios
        ├── r1/                                 # Revisión inicial
        └── r2/                                 # Reentregas incrementales
```

---

### 4. Requisitos Funcionales y Comandos CLI

El proyecto está gestionado con `uv` e invocado mediante el wrapper ejecutable `./ripley ...`. Incluye salida visual con Rich Console y barras de progreso.

#### A. Ingesta y Sanitización (`ingest`)
- `./ripley ingest <archivo.zip> [--dry-run]`
- Normalización automática UTF-8, aplanamiento de subdirectorios, filtro de extensiones inválidas y cálculo determinista de hashes SHA-256.

#### B. Gestión de Plantillas Jinja2 (`template`)
- `./ripley template init [--path <dir>] [--force]`
- `./ripley template list [--path <dir>]`
- `./ripley template check [--path <dir>]`: Validación de sintaxis y variables obligatorias `snake_case`.

#### C. Gestión y Esqueletos de Casos de Prueba (`testcase`)
- `./ripley testcase skeleton --activity <act> --exercise <ex> --cases <n> [--with-argv]`
- `./ripley testcase list [--activity <act>]`
- `./ripley testcase check [--activity <act>]`: Verifica integridad de parejas `.in`/`.out` y `.argv`.
- `./ripley testcase map --activity <act> [--student <st>] [--unmapped-only/--all/--auto]`:
  - Herramienta interactiva con heurísticas de similitud textual para vincular archivos `.c` con nombres no estándar a sus ejercicios y testcases correspondientes.
  - Permite visualizar el código fuente en consola, clasificar archivos como `[AUXILIAR]` o `[IGNORAR]`, crear ejercicios en el acto y aplicar mapeos globales a toda la cohorte.
- `./ripley testcase fuzz --activity <act> --exercise <ex> [--reference-source <solucion.c>] [--count 10]`:
  - Generador automático de casos de borde (`INT_MAX`, `INT_MIN`, `0`, cadenas límite, mutaciones) calculando los archivos `.out` esperados contra la solución de referencia docente.

#### D. Inicialización y Gestión de Prácticas (`practica`)
- `./ripley practica init --name "Nombre de la Práctica" [--exercises "ej1,ej2"]`
- `./ripley practica list`: Muestra tabla de prácticas docentes con estado de enunciados, pautas y casos de prueba.
- `./ripley practica sync --activity <slug>`: Sincroniza casos de prueba desde `./practicas/<slug>/` a `./tests/<slug>/`.


#### E. Evaluación Dinámica, Diagnósticos y AST (`evaluate`)
- `./ripley evaluate --activity <slug> [--parallel/--no-parallel] [--check-plagiarism]`:
  - **Compilación Modular por Mapeo:** Agrupa y compila fuentes `.c` vinculados al ejercicio correspondiente según `mapping.json`.
  - **Diff Semántico por AST:** Análisis estructural de funciones C ($r_N$ vs $r_{N-1}$), clasificando altas, bajas, modificaciones lógicas y cambios cosméticos.
  - **Diagnósticos Especializados de Ejecución:**
    - *Stack Overflow y Recursión Infinita:* Detección dinámica de agotamiento de stack con sugerencias pedagógicas.
    - *Bloqueos en Stdin (I/O Deadlocks):* Detección de programas colgados esperando más datos por `scanf`/`getchar` de los provistos por el caso de prueba.
    - *Punteros Colgantes (Dangling Pointers):* Captura de *Use-After-Free*, *Double Free* y reuso de variables tras `free()`.
  - **Verificación de Restricciones del Enunciado:** Blacklist/Whitelist a nivel AST para estructuras prohibidas (`for`, `while`, `goto`), cabeceras vetadas (`<string.h>`) o requisitos obligatorios (`struct`, `malloc`, recursión).
  - **Comparación Flexible de Salidas:** Soporte para directivas `REGEX:` en `.out` y comparación normalizada fuzzy (tolerante a espacios, mayúsculas y puntuación redundante).
  - **Auditoría de Memoria (Valgrind):** Con soporte para tolerancia de fugas en salidas de error (`tolerar_fugas_en_error`).

#### F. Análisis de Plagio y Similitud de Código (`plagiarism`)
- `./ripley plagiarism --activity <slug> [--threshold 0.70] [--output <report.md>]`:
  - Algoritmo Winnowing con tokenización AST de C ($k$-gramas y ventanas deslizantes) y cálculo de coeficientes de Jaccard y contención entre todas las entregas de la cohorte.

#### G. Diagramas de Flujo Tradicionales (`flowchart`)
- `./ripley flowchart --file <path.c> [--function <nombre>] [--format mermaid|dot] [--output <archivo>]`:
  - Generación de diagramas de flujo según la norma tradicional ISO/ANSI 5807: óvalos para Inicio/Fin, paralelogramos para Entrada (`scanf`/`getchar`) y Salida (`printf`/`puts`), rombos de decisión (`if`, `while`, `for`) con ramas `Sí`/`No` y rectángulos de proceso.

#### H. Árboles de Llamadas (`callgraph`)
- `./ripley callgraph --file <path.c> [--format mermaid|dot] [--stdlib] [--output <archivo>]`:
  - Extracción y visualización de grafos de invocación entre funciones C, detección de recursión y llamadas a librerías estándar.

#### I. Linters Especializados de Calidad, AST y Buenas Prácticas (`lint`)
- `./ripley lint --file <path.c> [--magic-numbers] [--clones] [--naming] [--dead-code] [--doxygen] [--advanced]`:
  - *Números Mágicos:* Detección de literales numéricos sin nombre fuera de `#define`/`enum`.
  - *Detector de Clones Internos (Copy-Paste):* Detección de secuencias duplicadas de tokens entre funciones dentro de la misma entrega.
  - *Convenciones de Nombres:* Validación de nomenclatura (`snake_case`, `UPPER_CASE`, prefijos `t_`).
  - *Código Muerto y Sentencias Inalcanzables:* Identificación de funciones inalcanzables desde `main()` y código posterior a `return`/`exit()`.
  - *Doxygen:* Fiscalización de completitud de comentarios `@brief`, `@param` y `@return`.
  - *Comparaciones de Punto Flotante:* Detección de `==` / `!=` directos en `float`/`double` sin margen épsilon.
  - *Inclusiones Innecesarias (IWYU):* Detección de `#include` de librerías cuyos símbolos no se utilizan.
  - *Calificación `const` (Const-Correctness):* Validación de parámetros puntero de solo lectura que deben ser `const`.
  - *Efectos Colaterales en Cortocircuitos:* Alerta de `++`, `--` o asignaciones dentro de `&&` / `||`.
  - *Deep Free Verifier:* Detección de `free(nodo)` en estructuras sin liberar antes sus campos dinámicos internos.
  - *Protección contra NULL en `<string.h>`:* Invocación de `strlen`/`strcmp`/`strcpy` sin validación previa.
  - *Variable Shadowing:* Ocultamiento de parámetros de funciones por variables locales con el mismo identificador.
  - *Dangling Stack Pointer Return:* Detección de retorno de direcciones de memoria local del stack `&var` (severidad `ERROR`).
  - *Sobre-Ingeniería:* Detección de trucos de intercambio con XOR (`a ^= b`) y ternarios triplemente anidados.

#### J. Visualizador Gráfico de Estructuras Dinámicas en Memoria (`memory-visualize`)
- `./ripley memory-visualize --file <path.c> [--format mermaid|dot] [--output <archivo>]`:
  - Generación de diagramas de topología de nodos y estructuras dinámicas en memoria (Graphviz DOT y Mermaid).

#### K. Emulador de Memoria Restringida para Sistemas Embebidos (`embedded-test`)
- `./ripley embedded-test --binary <path_binario> [--limit-kb 64] [--stdin <data>]`:
  - Ejecución de binarios bajo límites estrictos de heap/stack en memoria física (`RLIMIT_AS` y `RLIMIT_DATA`).

#### L. Generador de Mocks para Pruebas Unitarias en C (`mock generate`)
- `./ripley mock generate --header <header.h> [--output-dir <dir>]`:
  - Generación automática de stubs y mocks (`mock_<fn>.h` y `.c`) con contadores de invocaciones (`mock_<fn>_call_count`), configuración de retornos (`mock_<fn>_set_return`) y reseteo global (`reset_all_mocks`).

#### M. Testing Basado en Propiedades / Property-Based Testing (`property-test`)
- `./ripley property-test --source <path.c> --function <fn> --property <IDEMPOTENCE|COMMUTATIVITY|SORT_INVARIANT> [--iterations 100]`:
  - Generación y ejecución automatizada de arneses de prueba aleatorios en C para verificar invariantes formales con reporte de contraejemplos.

#### N. Auditoría de Documentación Doxygen (`doxygen`)
- `./ripley doxygen --file <path.c>`:
  - Verificación exhaustiva de parámetros y retornos documentados en funciones C.

#### O. Exportación y Reportería Moodle (`export`)
- `./ripley export --activity <actividad>`:
  - Generación de `moodle_grades.csv`, empaquetado de `retroalimentacion_moodle.zip` y reporte de métricas consolidadas en `dashboard.md`.

---

### 5. Sanitizadores y Diagnósticos de Bajo Nivel

- **UndefinedBehaviorSanitizer (UBSan):**
  - Detección y explicación pedagógica de desbordamientos de enteros con signo (`signed-integer-overflow`), división por cero (`division by zero`) y accesos a memoria no alineada (`-fsanitize=alignment`).
- **MemorySanitizer / GCC Warnings:**
  - Identificación de lectura de variables locales no inicializadas (`-Wuninitialized`, `-Wmaybe-uninitialized`).
- **Conversiones Peligrosas:**
  - Detección de cambios de signo y pérdida de precisión con `-Wsign-conversion` y `-Wconversion`.
- **Contador Determinista de Instrucciones CPU:**
  - Medición de instrucciones con Callgrind para detectar loops infinitos independientemente de la carga del servidor.

---

### 6. Estrategia de Testing y QA

Suite completa de pruebas automatizadas con `pytest` y `pytest-mock` en `tests/`:
- **`tests/unit/`:** Pruebas unitarias de ingesta, mapping, templates, esqueletos, compilador, config, base de datos, diagnósticos especializados, diffing y AST, evaluador, exportador, diagramas de flujo, árboles de llamadas, fuzzing, linters, ast auditors, memory visualizer, embedded runner, doxygen, mocks, sanitizers, restricciones, runner flexible y property testing.
- **`tests/integration/`:** Pipeline completo de evaluación end-to-end, timeouts, fallas de compilación y generación de reportes consolidados.
- **Estado Actual:** 87 pruebas pasando al 100% sin dependencias de placeholders temporales.

---

### 7. Resumen de Archivos y Módulos del Proyecto

| Módulo | Responsabilidad Principal |
| :--- | :--- |
| [`src/ripley/cli.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/cli.py) | Punto de entrada y orquestación de subcomandos Typer y visualización Rich. |
| [`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py) | Linters avanzados AST: punto flotante, IWYU, const, short-circuit, deep free, string NULL, shadowing, dangling stack, overengineering. |
| [`src/ripley/memory_visualizer.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/memory_visualizer.py) | Visualizador de topología de estructuras dinámicas de datos en memoria (DOT/Mermaid). |
| [`src/ripley/embedded.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/embedded.py) | Emulador y ejecutor bajo límites estrictos de memoria para sistemas embebidos. |
| [`src/ripley/ingest.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ingest.py) | Parseo de ZIPs de Moodle, descompresión, sanitización UTF-8 y aplanamiento. |
| [`src/ripley/db.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/db.py) | Persistencia y modelos SQLite para estudiantes, revisiones y evaluaciones. |
| [`src/ripley/config.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/config.py) | Carga, validación y modelos tipados de configuración TOML (`ripley.toml`). |
| [`src/ripley/mapping.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/mapping.py) | Mapeo interactivo y heurístico de archivos `.c` a ejercicios y testcases. |
| [`src/ripley/practice.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/practice.py) | Inicialización, gestión y sincronización de prácticas docentes en `./practicas/`. |
| [`src/ripley/compiler.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/compiler.py) | Compilación con GCC, sanitizadores y límites de recursos Unix. |
| [`src/ripley/runner.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/runner.py) | Ejecución dinámica de testcases, comparación regex/fuzzy y auditoría Valgrind. |
| [`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py) | Diagnóstico de Stack Overflow, Deadlocks de Stdin y Dangling Pointers. |
| [`src/ripley/restrictions.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/restrictions.py) | Validador de restricciones del enunciado (blacklist/whitelist AST). |
| [`src/ripley/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/sanitizers.py) | Analizador de UBSan (overflows, alineación), variables no asignadas y conversiones. |
| [`src/ripley/fuzzing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/fuzzing.py) | Generación automática de casos de borde por fuzzing con solución modelo. |
| [`src/ripley/plagiarism.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/plagiarism.py) | Detección de similitud y plagio con algoritmo Winnowing y similitud Jaccard. |
| [`src/ripley/flowchart.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/flowchart.py) | Generador de diagramas de flujo tradicionales (ISO/ANSI 5807) en Mermaid y DOT. |
| [`src/ripley/callgraph.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/callgraph.py) | Extracción de árboles de llamadas y análisis de alcanzabilidad de funciones. |
| [`src/ripley/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/linters.py) | Linters de números mágicos, código duplicado (copy-paste), convenciones y código muerto. |
| [`src/ripley/doxygen.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/doxygen.py) | Auditor de completitud de documentación Doxygen en C. |
| [`src/ripley/mocks.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/mocks.py) | Generador automático de arneses y stubs mock para pruebas unitarias en C. |
| [`src/ripley/property_testing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/property_testing.py) | Framework de pruebas basadas en propiedades (Property-Based Testing) en C. |
| [`src/ripley/instruction_counter.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/instruction_counter.py) | Contador determinista de instrucciones CPU con Callgrind. |
| [`src/ripley/semantic_diff.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/semantic_diff.py) | Diff semántico por AST para código fuente C. |
| [`src/ripley/diffing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diffing.py) | Generación de diffs unificados y resúmenes semánticos entre revisiones. |
| [`src/ripley/style.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/style.py) | Analizador estático de reglas de estilo configurables (Allman, K&R, indentación). |
| [`src/ripley/security.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/security.py) | Escáner de llamadas al sistema peligrosas (`system`, `fork`, `exec`). |
| [`src/ripley/templates.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/templates.py) | Gestor, inicializador y validador de plantillas Jinja2 en `snake_case`. |
| [`src/ripley/reporter.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/reporter.py) | Motor de renderizado Jinja2 para generar informes Markdown acumulativos. |
| [`src/ripley/exporter.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/exporter.py) | Exportador de `moodle_grades.csv`, ZIP de retroalimentación y `dashboard.md`. |
| [`src/ripley/evaluate.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/evaluate.py) | Evaluador integral que orquesta compilación, diff, estilo, linter, tests y Valgrind. |
