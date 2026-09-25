# Manual de Uso y Referencia Técnica: ripley

> **RIPLEY** — CLI tool for batch processing, grading, versioning and evaluating Moodle C submissions
> **Versión:** `0.1.0` · **CLI principal:** `ripley` · **Plugin Ripley:** `ripley`

---

## 1. Arquitectura y Propósito Pedagógico

`ripley` forma parte del ecosistema de herramientas de la cátedra de Programación 1 (UNRN). Su objetivo central es resolver de forma modular, determinista y automatizada las tareas asociadas a su dominio específico dentro del ciclo de desarrollo, evaluación y aprendizaje de software en C.

### Alcance Funcional (Qué cubre)
- Microkernel central y orquestador pedagógico de análisis estático y reglas de cátedra de Programación 1 (`0xXXXXh`).
- Publicación y diagnóstico en vivo mediante servidor Language Server Protocol (`ripley lsp`) para VS Code, Neovim y otros editores.
- Modo pedagógico socrático (`--socratic`) que entrega pistas graduales sin revelar la solución directa.
- Modo observador en vivo (`ripley watch`) para desarrollo guiado por pruebas (TDD).
- Generación de reportes unificados en consola Rich, formato Markdown y SARIF v2.1.0 estándar.
- Delegación del 100% de verificaciones y análisis profundos en plugins satélites especializados (`SatellitePluginAdapter`).

### Límites de Responsabilidad y Delegación (Qué no cubre)
- Implementación monolítica de análisis específicos (delega en `gaff`, `spunkmeyer`, `kaneda`, `wierzbowski`, `zhora`, `brett`, `motoko`, etc.).
- Compilación directa de código (delega en `daedalus`).
- Ejecución en sandbox (delega en `nostromo`).
- Calificación masiva de entregas de cursos (delega en `dredd`).

### Principios de Diseño
- **Enfoque Pedagógico:** Diagnósticos y mensajes en español rioplatense orientados a facilitar la comprensión de errores conceptuales.
- **Salida Estructurada Dual:** Soporte nativo para visualización enriquecida en terminal (Rich) y salida parseable para orquestadores (`--json`).
- **Integración Contractual:** Capacidad de emitir secciones de reporte para `dredd` (`dredd-section`) y actuar como satélite orquestado por `ripley`.
- **Idempotencia y Robustez:** Validación de precondiciones y comandos de autodiagnóstico (`doctor`) para verificación del entorno.

---

## 2. Instalación y Requisitos

### Requisitos del Sistema
- **Python:** `>= 3.10` (recomendado Python 3.11 o 3.12).
- **Gestor de paquetes:** [`uv`](https://github.com/astral-sh/uv) (entorno estándar de cátedra).
- **Toolchain C (si aplica):** GCC / Clang, Make, GDB y bibliotecas estándar de desarrollo.

### Instalación en el Entorno de Usuario
Para instalar la herramienta de forma global y aislada en el sistema mediante `uv tool`:
```bash
uv tool install --editable /home/mrtin/dev/tools/ripley
```

### Verificación de Instalación
Ejecutá el comando `doctor` para constatar que todas las dependencias y binarios requeridos estén presentes y operativos:
```bash
ripley doctor
```

---

## 3. Guía Integral de Comandos (CLI)

| Comando | Descripción Breve |
| :--- | :--- |
| [`ripley evaluate`](#evaluate) | Ejecuta la compilación, linters, estilo, pruebas y calificación de los estudiantes. |
| [`ripley doctor`](#doctor) | Diagnóstico del entorno: herramientas externas presentes y checks afectados. |
| [`ripley run`](#run) | Verificación temprana completa: compila, corre testcases públicos y aplica los checks del manifiesto. |
| [`ripley check`](#check) | Verificación unificada y pedagógica de código C: AST, reglas P1, compilación y AddressSanitizer. |
| [`ripley show`](#show) | Inspecciona y muestra el contenido, metadatos, enunciado y testcases de un paquete .ripkg. |
| [`ripley watch`](#watch) | Modo Live TDD: recompila y verifica automáticamente al guardar (Ctrl+C para salir). |
| [`ripley explain`](#explain) | Explica una regla pedagógica de cátedra o busca por palabras clave en el catálogo canónico. |
| [`ripley gcc-explain`](#gccexplain) | Traduce mensajes de error y advertencias de GCC/ld a explicaciones claras en español. |
| [`ripley analyze`](#analyze) | Análisis programático sin estado para orquestadores (dredd, CI/CD, scripts). |
| [`ripley report`](#report) | Genera directamente la sección de reporte Markdown de RIPLEY para Dredd. |
| [`ripley badge`](#badge) | Genera un badge SVG con la calificación pedagógica del estudiante. |
| [`ripley lsp`](#lsp) | Inicia el servidor Language Server Protocol (LSP) de Ripley en stdio. |
| [`ripley fix-interactive`](#fixinteractive) | Aplica auto-correcciones pedagógicas para vicios comunes de C. |
| [`ripley style-check`](#stylecheck) | Verifica la conformidad del código con el estándar estilístico oficial de la cátedra. |
| [`ripley history`](#history) | Muestra el historial de evolución de corrección de errores del alumno. |

### `ripley evaluate`

Ejecuta la compilación, linters, estilo, pruebas y calificación de los estudiantes.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `activity` | `<class 'str'>` | Slug de la actividad a evaluar (ej. entrega-1_1228009). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--parallel/--no-parallel` | `<class 'bool'>` | `True` | Procesamiento concurrente. |
| `--check-plagiarism` | `<class 'bool'>` | `False` | Ejecutar análisis de similitud/plagio al finalizar la evaluación. |
| `--workspace`, `-w` | `<class 'str'>` | `.` | Directorio raíz del workspace. |

#### Ejemplo de Invocación
```bash
ripley evaluate <activity>
```

### `ripley doctor`

Diagnóstico del entorno: herramientas externas presentes y checks afectados.

#### Ejemplo de Invocación
```bash
ripley doctor
```

### `ripley run`

Verificación temprana completa: compila, corre testcases públicos y aplica los checks del manifiesto.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `sources` | `List[pathlib._local.Path]` | Archivos .c del estudiante a verificar. |
| `practica` | `<class 'str'>` | Ruta al paquete .ripkg de la práctica. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--strict` | `<class 'bool'>` | `False` | Salir con código 1 si hay hallazgos, no solo errores. |
| `--verify-signature` | `<class 'bool'>` | `False` | Exigir firma GPG válida del paquete. |

#### Ejemplo de Invocación
```bash
ripley run <sources> <practica>
```

### `ripley check`

Verificación unificada y pedagógica de código C: AST, reglas P1, compilación y AddressSanitizer.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--target` | `<class 'pathlib._local.Path'>` | `.` | Ruta al archivo .c o directorio del proyecto a verificar. |
| `--strict` | `<class 'bool'>` | `False` | Salir con código de error si se detectan advertencias. |
| `--format` | `<class 'str'>` | `rich` | Formato de salida: 'rich' (consola interactiva), 'json' o 'sarif'. |
| `--socratic`, `-s` | `<class 'bool'>` | `False` | Modo tutor socrático: muestra pistas conceptuales progresivas en vez de soluciones directas. |
| `--bench` | `Optional[str]` | `None` | complexity-bench: cota esperada (O(1), O(n), O(n log n), O(n^2)). |
| `--bench-pattern` | `<class 'str'>` | `{n}\n` | Entrada por tamaño; '{n}' se reemplaza por N. |
| `--strict-ub` | `<class 'bool'>` | `False` | ub-sentinel: auditoría de comportamiento indefinido tras compilar. |
| `--ub-level` | `<class 'int'>` | `2` | Nivel máximo del pipeline ub-sentinel (1=sanitizers, 2=+clang-analyzer, 3=+Frama-C, 4=+TSan). |
| `--ub-timeout` | `<class 'int'>` | `30` | Timeout en segundos por testcase del ub-sentinel. |
| `--html` | `Optional[pathlib._local.Path]` | `None` | Generar informe interactivo HTML con badges de cátedra. |
| `--md`, `--output-md`, `-o` | `Optional[pathlib._local.Path]` | `None` | Generar sección de reporte en formato Markdown para fusión en Dredd. |
| `--profile`, `-p` | `<class 'str'>` | `strict` | Perfil de rigurosidad: 'strict', 'relaxed' o 'exam'. |
| `--quiet`, `-q` | `<class 'bool'>` | `False` | Modo silencioso sin volcado a consola (para pre-commit hooks). |
| `--exit-zero` | `<class 'bool'>` | `False` | Forzar código de salida 0 incluso ante advertencias o fallas. |
| `--json` | `<class 'bool'>` | `False` | Alias para emitir reporte en formato JSON (--format json). |

#### Ejemplo de Invocación
```bash
ripley check
```

### `ripley show`

Inspecciona y muestra el contenido, metadatos, enunciado y testcases de un paquete .ripkg.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `paquete` | `<class 'str'>` | Ruta al archivo .ripkg (o slug de la práctica). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--enunciado`, `-e` | `<class 'bool'>` | `False` | Mostrar el enunciado / consigna Markdown. |
| `--pistas`, `-p` | `<class 'bool'>` | `False` | Mostrar las pistas progresivas / pautas. |
| `--tests`, `-t` | `<class 'bool'>` | `False` | Mostrar casos de prueba públicos del payload. |
| `--checks`, `-c` | `<class 'bool'>` | `False` | Mostrar checks y reglas habilitadas en el manifiesto. |
| `--archivos`, `-f` | `<class 'bool'>` | `False` | Mostrar listado de archivos del payload e integridad SHA-256. |
| `--meta`, `-m` | `<class 'bool'>` | `False` | Mostrar metadatos del paquete (flags de compilador, versión, firma). |
| `--todos`, `-a` | `<class 'bool'>` | `False` | Mostrar todas las secciones. |
| `--verify-signature` | `<class 'bool'>` | `False` | Verificar criptográficamente la firma GPG del paquete. |
| `--raw` | `<class 'bool'>` | `False` | Salida en texto plano sin formato Rich. |

#### Ejemplo de Invocación
```bash
ripley show <paquete>
```

### `ripley watch`

Modo Live TDD: recompila y verifica automáticamente al guardar (Ctrl+C para salir).

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--paths` | `Optional[List[pathlib._local.Path]]` | `None` | Archivos o directorios .c a vigilar (por defecto: .). |
| `--practica`, `-p` | `Optional[str]` | `None` | Paquete .ripkg para flags oficiales y testcases públicos. |
| `--interval`, `-i` | `<class 'float'>` | `1.0` | Segundos entre sondeos de cambios. |

#### Ejemplo de Invocación
```bash
ripley watch
```

### `ripley explain`

Explica una regla pedagógica de cátedra o busca por palabras clave en el catálogo canónico.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `rule_code` | `<class 'str'>` | Código de regla de cátedra (ej. 0x1001h, 0x0001h, 'all' o palabra clave de búsqueda). |

#### Ejemplo de Invocación
```bash
ripley explain <rule_code>
```

### `ripley gcc-explain`

Traduce mensajes de error y advertencias de GCC/ld a explicaciones claras en español.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--target` | `<class 'str'>` | `-` | Ruta al archivo con la salida de error de GCC/ld o '-' para leer de stdin. |
| `--json` | `<class 'bool'>` | `False` | Emitir diagnósticos traducidos en formato JSON estructurado. |

#### Ejemplo de Invocación
```bash
ripley gcc-explain
```

### `ripley analyze`

Análisis programático sin estado para orquestadores (dredd, CI/CD, scripts).

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--target` | `<class 'pathlib._local.Path'>` | `.` | Ruta al archivo .c o directorio del proyecto a analizar. |
| `--format` | `<class 'str'>` | `json` | Formato de salida ('json'). |
| `--html` | `Optional[pathlib._local.Path]` | `None` | Generar informe interactivo HTML con badges de cátedra. |

#### Ejemplo de Invocación
```bash
ripley analyze
```

### `ripley report`

Genera directamente la sección de reporte Markdown de RIPLEY para Dredd.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--target` | `<class 'pathlib._local.Path'>` | `.` | Ruta al archivo .c o directorio del proyecto a verificar. |
| `--output`, `-o` | `Optional[pathlib._local.Path]` | `None` | Ruta de destino del archivo Markdown. |

#### Ejemplo de Invocación
```bash
ripley report
```

### `ripley badge`

Genera un badge SVG con la calificación pedagógica del estudiante.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--target` | `<class 'pathlib._local.Path'>` | `.` | Ruta al archivo .c o directorio del proyecto a evaluar. |
| `--output`, `-o` | `<class 'pathlib._local.Path'>` | `ripley_badge.svg` | Ruta de destino del archivo SVG. |
| `--label`, `-l` | `<class 'str'>` | `ripley` | Etiqueta izquierda del badge SVG. |

#### Ejemplo de Invocación
```bash
ripley badge
```

### `ripley lsp`

Inicia el servidor Language Server Protocol (LSP) de Ripley en stdio.

#### Ejemplo de Invocación
```bash
ripley lsp
```

### `ripley fix-interactive`

Aplica auto-correcciones pedagógicas para vicios comunes de C.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `source` | `<class 'pathlib._local.Path'>` | Archivo .c a corregir interactivamente. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--auto`, `-y` | `<class 'bool'>` | `True` | Aplicar correcciones sin confirmación manual. |

#### Ejemplo de Invocación
```bash
ripley fix-interactive <source>
```

### `ripley style-check`

Verifica la conformidad del código con el estándar estilístico oficial de la cátedra.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `sources` | `List[pathlib._local.Path]` | Archivos .c/.h a auditar contra el estándar de cátedra. |

#### Ejemplo de Invocación
```bash
ripley style-check <sources>
```

### `ripley history`

Muestra el historial de evolución de corrección de errores del alumno.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--target` | `<class 'pathlib._local.Path'>` | `.` | Directorio raíz del proyecto estudiantil. |

#### Ejemplo de Invocación
```bash
ripley history
```

---

## 4. Formatos de Salida e Integración con el Ecosistema

### Modo Interactivo / Terminal (Rich)
Por defecto, la herramienta renderiza paneles, árboles y tablas estilizadas para facilitar la lectura del estudiante y docente en terminales modernas con soporte ANSI.

### Modo Estructurado JSON (`--json`)
Para integración con pipelines de CI/CD, scripts de automatización u orquestadores externos, la opción `--json` emite un documento JSON estricto por la salida estándar (`stdout`), dirigiendo cualquier mensaje de logging a `stderr`:
```bash
ripley evaluate --json
```

### Integración con Dredd (`dredd-section`)
Cuando la herramienta genera reportes de evaluación para entregas de alumnos, produce una sección Markdown estandarizada conforme al contrato de integración de Dredd (v1.0.0):
```markdown
<!-- dredd-section: ripley, tool=ripley, version=0.1.0, status=ok -->
```
Este encabezado garantiza la agregación determinista de los hallazgos en la rúbrica docente.

### Integración con Ripley
`ripley` está registrada en el catálogo de plugins satélites de Ripley (`SATELLITE_CATALOG`). Puede invocarse directamente a través del motor de evaluación de Ripley configurando el análisis en `ripley.toml`.

---

## 5. Diagnóstico y Códigos de Salida

### Códigos de Retorno (`exit code`)
| Código | Significado |
| :---: | :--- |
| `0` | Ejecución exitosa sin hallazgos críticos ni errores de sintaxis. |
| `1` | Hallazgos pedagógicos detectados, infracción de reglas o advertencias activas. |
| `2` | Error de sintaxis en argumentos CLI o archivo fuente no encontrado. |
| `>2` | Error no recuperable del sistema, fallo de memoria o excepción interna. |

### Diagnóstico del Entorno (`doctor`)
Ante comportamientos inesperados, verificá el estado operativo con:
```bash
ripley doctor
```
Comprueba la presencia de las dependencias requeridas y la integridad de los componentes del paquete.