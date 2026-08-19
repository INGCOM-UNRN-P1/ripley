# Guía de Configuración de Herramientas Externas para Análisis y Revisión de Código C

Este documento detalla la configuración técnica, archivos de parámetros, banderas de compilación y comandos de ejecución para las herramientas externas estándar de la industria y el ámbito académico para el análisis estático, análisis dinámico, auditoría de seguridad, verificación formal y formateo de programas en C.

---

## 1. Compiladores y Sanitizers de Runtime (GCC / Clang)

### 1.1 Banderas de Compilación Pedagógicas y de Máximo Rigor
Para evaluar programas en C (estándar C11/C99), se recomienda la combinación de advertencias estrictas y detección de comportamiento indefinido:

```bash
gcc -std=c11 -Wall -Wextra -pedantic \
    -Wshadow -Wconversion -Wformat=2 -Wnull-dereference \
    -Wdouble-promotion -Wvla -Wstrict-prototypes \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -O1 -g -o programa entrega.c
```

| Bandera | Propósito Técnico |
| :--- | :--- |
| `-std=c11` | Fija el estándar formal ISO/IEC 9899:2011. |
| `-Wall -Wextra -pedantic` | Activa advertencias estándar, extendidas y de estricta conformidad ISO. |
| `-Wshadow` | Advierte si una variable local oculta a otra en un ámbito externo. |
| `-Wconversion` | Advierte sobre conversiones implícitas que pueden alterar el valor (ej. `int` a `short`). |
| `-Wnull-dereference` | Detecta rutas de ejecución donde se desreferencia un puntero `NULL`. |
| `-Wvla` | Prohíbe arreglos de longitud variable (Variable Length Arrays - VLA) en el stack. |
| `-Wdouble-promotion` | Advierte si un `float` se promueve implícitamente a `double`. |
| `-fsanitize=address` | **ASan**: Detecta use-after-free, buffer overflows (stack/heap/global) y fugas. |
| `-fsanitize=undefined` | **UBSan**: Detecta desbordamientos con signo, división por cero, shifts inválidos. |
| `-fno-omit-frame-pointer` | Conserva el puntero de marco de pila para trazas de error legibles. |

### 1.2 Variables de Entorno para Sanitizers
Para controlar el comportamiento de ASan y UBSan durante la ejecución de pruebas automatizadas:

```bash
export ASAN_OPTIONS="detect_leaks=1:abort_on_error=1:halt_on_error=1:symbolize=1:print_stacktrace=1"
export UBSAN_OPTIONS="abort_on_error=1:halt_on_error=1:print_stacktrace=1"
```

---

## 2. Analizadores Estáticos de Código Fuente

### 2.1 Cppcheck

`cppcheck` realiza análisis semántico profundo sin compilar el binario.

#### Invocación por Línea de Comandos
```bash
cppcheck --enable=all \
         --inconclusive \
         --std=c11 \
         --inline-suppr \
         --suppress=missingIncludeSystem \
         --suppress=staticFunction \
         --suppress=unusedFunction \
         --error-exitcode=1 \
         entrega.c
```

#### Archivo de Configuración de Proyecto (`.cppcheck` / `cppcheck.cfg`)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<project version="1">
    <root name="."/>
    <standards>
        <c version="c11"/>
    </standards>
    <suppressions>
        <suppression>missingIncludeSystem</suppression>
        <suppression>staticFunction</suppression>
        <suppression>unusedFunction</suppression>
    </suppressions>
    <addons>
        <addon>cert</addon>
        <addon>threadsafety</addon>
    </addons>
</project>
```

---

### 2.2 Clang-Tidy

`clang-tidy` es el linter basado en el frontend Clang AST.

#### Archivo de Configuración (`.clang-tidy`)
Ubicá este archivo en la raíz del espacio de trabajo o de la práctica:

```yaml
---
Checks: >
  -*,
  clang-diagnostic-*,
  clang-analyzer-*,
  bugprone-*,
  readability-*,
  cert-*,
  -readability-identifier-length,
  -readability-magic-numbers

WarningsAsErrors: 'clang-analyzer-*,bugprone-*,cert-*'

CheckOptions:
  readability-braces-around-statements.ShortStatementLines: 0
  readability-function-cognitive-complexity.Threshold: 15
  readability-isolate-declaration.Threshold: 1
  bugprone-sizeof-expression.WarnOnSizeOfPointer: true

HeaderFilterRegex: '.*'
FormatStyle: 'file'
...
```

#### Invocación
```bash
clang-tidy entrega.c -- -std=c11 -Wall
```

---

### 2.3 Flawfinder (Auditoría de Vulnerabilidades y Seguridad C/C++)

`flawfinder` busca funciones inseguras susceptibles a vulnerabilidades de memoria (CWE/OWASP):

```bash
flawfinder --minlevel=1 --dataonly --singleline entrega.c
```

| Nivel Mínimo (`--minlevel`) | Descripción |
| :--- | :--- |
| `1` | Detecta todas las funciones de riesgo potencial (`strcpy`, `strcat`, `sprintf`, `gets`, etc.). |
| `3` | Reporta únicamente vulnerabilidades de riesgo medio o alto. |
| `5` | Reporta vulnerabilidades críticas directas. |

---

### 2.4 Splint (Secure Programming Lint)

`splint` aplica verificación estática de desreferenciación nula y tipos booleanos en C:

```bash
splint -standard -nullpass -nullret -nullstate +posixlib entrega.c
```

#### Archivo de Opciones (`.splintrc`)
```text
-standard
+nullpass
+nullret
+nullstate
-boolops
+posixlib
+trytorecover
```

---

### 2.5 Frama-C (Verificación Formal e Interpretación Abstracta)

`frama-c` permite verificar formalmente la ausencia total de errores de ejecución (RTE) mediante el plugin EVA (Evolved Value Analysis):

```bash
frama-c -eva -eva-precision 2 -eva-no-results entrega.c
```

---

## 3. Análisis Dinámico, Detección de Fugas y Rendimiento

### 3.1 Valgrind (Memcheck)

`memcheck` es la herramienta de referencia para depuración de memoria dinámica en sistemas Linux.

#### Archivo de Configuración (`.valgrindrc`)
```text
--memcheck:leak-check=full
--memcheck:show-leak-kinds=all
--memcheck:track-origins=yes
--memcheck:error-exitcode=1
--memcheck:errors-for-leak-kinds=all
--show-below-main=no
```

#### Invocación por Consola
```bash
valgrind --leak-check=full \
         --show-leak-kinds=all \
         --track-origins=yes \
         --error-exitcode=1 \
         ./binario_estudiante < entrada.in
```

---

### 3.2 Valgrind Massif (Perfilador de Consumo Heap)

Para registrar la memoria máxima (*peak heap memory*) y detectar asignaciones excesivas:

```bash
valgrind --tool=massif --massif-out-file=massif.out ./binario_estudiante
ms_print massif.out
```

---

### 3.3 Cobertura de Código con GCC / Gcov / Lcov

Permite verificar qué líneas y ramas de control del estudiante fueron ejercitadas por los casos de prueba:

#### 1. Compilación con Instrumentación
```bash
gcc -std=c11 --coverage -g entrega.c -o binario_cov
```

#### 2. Ejecución con Entradas de Prueba
```bash
./binario_cov < caso1.in
./binario_cov < caso2.in
```

#### 3. Generación del Informe de Cobertura
```bash
gcov -b -c entrega.c
# Para informe HTML acumulado con lcov:
lcov --capture --directory . --output-file coverage.info
genhtml coverage.info --output-directory coverage_html/
```

---

### 3.4 Contador de Instrucciones y Complejidad (Perf / Valgrind Callgrind)

Para detectar soluciones con bucles redundantes o complejidad algorítmica excesiva:

#### Opción A: Valgrind Callgrind (Determinista e independiente del CPU)
```bash
valgrind --tool=callgrind --callgrind-out-file=callgrind.out ./binario_estudiante < caso1.in
callgrind_annotate callgrind.out | grep "PROGRAM TOTALS"
```

#### Opción B: Linux `perf stat`
```bash
perf stat -e instructions,cycles,cpu-clock ./binario_estudiante < caso1.in
```

---

## 4. Estilo, Indentación y Formato de Código

### 4.1 Clang-Format (Estilo Allman / Programación I)

#### Archivo de Configuración (`.clang-format`)
```yaml
---
BasedOnStyle: LLVM
Language: Cpp
Standard: c++11

# Convención de Llaves Allman
BreakBeforeBraces: Allman
AllowShortIfStatementsOnASingleLine: false
AllowShortBlocksOnASingleLine: false
AllowShortLoopsOnASingleLine: false
AllowShortFunctionsOnASingleLine: None

# Indentación
IndentWidth: 4
TabWidth: 4
UseTab: Never
IndentCaseLabels: true

# Espaciado y Límites
ColumnLimit: 79
SpaceBeforeParens: ControlStatements
SpaceBeforeAssignmentOperators: true
SpaceAroundPointerQualifiers: Both
SpacesInParentheses: false
SpacesInSquareBrackets: false

# Punteros y Referencias
DerivePointerAlignment: false
PointerAlignment: Right
...
```

#### Invocación
- **Verificación sin modificar (modo linter):**
  ```bash
  clang-format --dry-run --Werror -style=file entrega.c
  ```
- **Autoformateo:**
  ```bash
  clang-format -i -style=file entrega.c
  ```

---

### 4.2 Uncrustify (Alternativa de Formateo C)

#### Archivo de Configuración (`uncrustify.cfg`)
```ini
# Estilo Allman / BSD
input_tab_size                  = 4
output_tab_size                 = 4
indent_columns                  = 4
indent_with_tabs                = 0
code_width                      = 79

nl_fdef_brace                   = force   # Llave de función en nueva línea
nl_if_brace                     = force   # Llave de if en nueva línea
nl_for_brace                    = force   # Llave de for en nueva línea
nl_while_brace                  = force   # Llave de while en nueva línea
nl_switch_brace                 = force   # Llave de switch en nueva línea
nl_brace_while                  = force   # Llave de do-while
mod_full_brace_if               = force   # Exigir llaves en bloques if
mod_full_brace_for              = force   # Exigir llaves en bloques for
mod_full_brace_while            = force   # Exigir llaves en bloques while
```

---

## 5. Documentación y Diagramación

### 5.1 Doxygen

#### Archivo de Configuración Mínimo (`Doxyfile`)
```ini
PROJECT_NAME           = "Entrega Programacion I"
OUTPUT_DIRECTORY       = "doc/"
INPUT                  = "."
FILE_PATTERNS          = *.c *.h
RECURSIVE              = YES
OPTIMIZE_OUTPUT_FOR_C  = YES
EXTRACT_ALL            = YES
EXTRACT_STATIC         = YES

# Verificación de Advertencias
WARNINGS               = YES
WARN_IF_DOC_ERROR      = YES
WARN_IF_UNDOCUMENTED   = YES
WARN_NO_PARAMDOC       = YES
WARN_LOGFILE           = "doxygen_warnings.log"

# Generación de Grafos (requiere graphviz)
HAVE_DOT               = YES
CALL_GRAPH             = YES
CALLER_GRAPH           = YES
GENERATE_LATEX         = NO
GENERATE_HTML          = YES
```

#### Invocación
```bash
doxygen Doxyfile
```

---

### 5.2 Graphviz (Generación de Diagramas de Flujo y Memoria)

Para compilar archivos de descripción gráfica `.dot` a imágenes vectoriales SVG o raster PNG:

```bash
dot -Tsvg diagrama_flujo.dot -o diagrama_flujo.svg
dot -Tpng estructura_memoria.dot -o estructura_memoria.png
```

---

## 6. Seguridad y Sandboxing en Linux

### 6.1 Bubblewrap (`bwrap`)

`bubblewrap` ejecuta el binario compilado en un entorno de namespace aislado, de solo lectura y sin privilegios de red o sistema de archivos:

```bash
bwrap --ro-bind /usr /usr \
      --ro-bind /lib /lib \
      --ro-bind /lib64 /lib64 \
      --tmpfs /tmp \
      --tmpfs /var \
      --proc /proc \
      --dev /dev \
      --unshare-all \
      --unshare-net \
      --die-with-parent \
      --dir /workspace \
      --ro-bind ./binario_estudiante /workspace/binario \
      /workspace/binario < entrada.in
```

### 6.2 Firejail

Perfil de sandbox estricto para C (`c-sandbox.profile`):

```ini
include /etc/firejail/default.profile
net none
noroot
nogroups
nonewprivs
private-tmp
private-dev
rlimit-as 134217728       # 128 MB RAM
rlimit-cpu 5              # 5 segundos CPU
rlimit-fsize 10485760     # 10 MB tamaño máx. archivo generado
```

---

## 7. Integración Completa en Ripley (`ripley.toml`)

Podés integrar cualquiera de estas herramientas directamente en la suite de corrección de Ripley mediante la directiva `[[custom_tools]]`:

```toml
[compiler]
executable = "gcc"
flags = [
    "-Wall",
    "-Wextra",
    "-pedantic",
    "-std=c11",
    "-fsanitize=address,undefined",
]

[limits]
timeout_segundos = 5
limite_memoria_mb = 128

[cppcheck]
enabled = true
ejecutable = "cppcheck"
parametros = [
    "--enable=all",
    "--inline-suppr",
    "--suppress=missingIncludeSystem",
    "--suppress=staticFunction",
]

[valgrind]
enabled = true
flags = [
    "--leak-check=full",
    "--show-leak-kinds=all",
    "--track-origins=yes",
    "--error-exitcode=1",
]

# Herramienta Externa 1: Auditoría Clang-Tidy por archivo fuente
[[custom_tools]]
name = "clang-tidy"
command = "clang-tidy {source} -- -std=c11 -Wall"
stage = "source"
fail_on_error = false
timeout_segundos = 10

# Herramienta Externa 2: Verificación de Vulnerabilidades con Flawfinder
[[custom_tools]]
name = "flawfinder"
command = "flawfinder --minlevel=1 --dataonly {source}"
stage = "source"
fail_on_error = false

# Herramienta Externa 3: Verificación de Formato con Clang-Format
[[custom_tools]]
name = "clang-format-check"
command = "clang-format --dry-run --Werror -style=file {source}"
stage = "source"
fail_on_error = false

# Herramienta Externa 4: Contador de Instrucciones con Valgrind Callgrind
[[custom_tools]]
name = "callgrind-complexity"
command = "valgrind --tool=callgrind --callgrind-out-file=/tmp/{stem}.callgrind {binary}"
stage = "binary"
fail_on_error = false
timeout_segundos = 10
```
