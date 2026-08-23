# Manual de Usuario y Referencia Técnica de Ripley CLI

`ripley` es una herramienta de línea de comandos en Python (gestionada con `uv`) diseñada para automatizar la ingesta, versionado incremental, compilación segura, análisis estático/AST, ejecución dinámica, auditoría de memoria y calificación de entregas masivas de Moodle en C para la materia **Programación I**.

---

## Índice

1. [Requisitos y Configuración de Entorno](#1-requisitos-y-configuración-de-entorno)
2. [Flujo de Trabajo Docente Recomendado](#2-flujo-de-trabajo-docente-recomendado)
3. [Estructura del Proyecto y Archivos de Configuración](#3-estructura-del-proyecto-y-archivos-de-configuración)
4. [Referencia Completa de Comandos CLI](#4-referencia-completa-de-comandos-cli)
   - [4.1 Ingesta y Sanitización (`ingest`)](#41-ingesta-y-sanitización-ingest)
   - [4.2 Gestión de Prácticas Docentes (`practica`)](#42-gestión-de-prácticas-docentes-practica)
   - [4.3 Mapeo de Archivos Fuente (`map` / `testcase map`)](#43-mapeo-de-archivos-fuente-map--testcase-map)
   - [4.4 Gestión y Esqueletos de Casos de Prueba (`testcase`)](#44-gestión-y-esqueletos-de-casos-de-prueba-testcase)
   - [4.5 Fuzzing y Generación de Casos de Prueba (`testcase fuzz`)](#45-fuzzing-y-generación-de-casos-de-prueba-testcase-fuzz)
   - [4.6 Evaluación Integral de Entregas (`evaluate`)](#46-evaluación-integral-de-entregas-evaluate)
   - [4.7 Análisis de Plagio y Similitud (`plagiarism`)](#47-análisis-de-plagio-y-similitud-plagiarism)
   - [4.8 Linters de Calidad, AST y Buenas Prácticas (`lint`)](#48-linters-de-calidad-ast-y-buenas-prácticas-lint)
   - [4.9 Auditoría de Funciones Puras (`pure-audit`)](#49-auditoría-de-funciones-puras-pure-audit)
   - [4.10 Simulador de Fragmentación de Memoria Heap (`heap-simulate`)](#410-simulador-de-fragmentación-de-memoria-heap-heap-simulate)
   - [4.11 Emulación de Memoria Embebida Restringida (`embedded-test`)](#411-emulación-de-memoria-embebida-restringida-embedded-test)
   - [4.12 Diagramas de Flujo Tradicionales ISO/ANSI (`flowchart`)](#412-diagramas-de-flujo-tradicionales-isoansi-flowchart)
   - [4.13 Árboles de Llamadas Call Graph (`callgraph`)](#413-árboles-de-llamadas-call-graph-callgraph)
   - [4.14 Visualizador de Estructuras Dinámicas en Memoria (`memory-visualize`)](#414-visualizador-de-estructuras-dinámicas-en-memoria-memory-visualize)
   - [4.15 Generador de Mocks en C (`mock generate`)](#415-generador-de-mocks-en-c-mock-generate)
   - [4.16 Testing Basado en Propiedades (`property-test`)](#416-testing-basado-en-propiedades-property-test)
   - [4.17 Auditoría de Documentación Doxygen (`doxygen`)](#417-auditoría-de-documentación-doxygen-doxygen)
   - [4.18 Gestión de Plantillas Jinja2 (`template`)](#418-gestión-de-plantillas-jinja2-template)
   - [4.19 Exportación a Moodle y Tablero Docente (`export`)](#419-exportación-a-moodle-y-tablero-docente-export)
5. [Diagnósticos Especializados y Sanitizadores](#5-diagnósticos-especializados-y-sanitizadores)
6. [Estructura del Archivo de Configuración `ripley.toml`](#6-estructura-del-archivo-de-configuración-ripleytoml)

---

## 1. Requisitos y Configuración de Entorno

### Dependencias del Sistema
- **Python:** 3.11 o superior.
- **Gestor de Entorno:** `uv` (Fast Python package installer).
- **Herramientas de Compilación y Diagnóstico:** `gcc`, `valgrind`, `graphviz` (`dot`).

### Inicialización
```bash
# Sincronizar el entorno virtual con uv
uv sync

# Ejecutar ripley mediante el wrapper
./ripley --help
```

---

## 2. Flujo de Trabajo Docente Recomendado

```mermaid
flowchart TD
    A["1. Crear Práctica<br/><code>./ripley practica init</code>"] --> B["2. Descargar ZIP de Moodle e Ingestar<br/><code>./ripley ingest lote.zip</code>"]
    B --> C["3. Revisar Mapeo de Archivos C<br/><code>./ripley map --activity entrega-1</code>"]
    C --> D["4. Fuzzing / Completar Casos de Prueba<br/><code>./ripley testcase fuzz ...</code>"]
    D --> E["5. Evaluar Cohorte con Sanitizers y Valgrind<br/><code>./ripley evaluate --activity entrega-1</code>"]
    E --> F["6. Detección de Plagio Cruzado<br/><code>./ripley plagiarism --activity entrega-1</code>"]
    F --> G["7. Exportar Calificaciones y Feedback ZIP<br/><code>./ripley export --activity entrega-1</code>"]
```

---

## 3. Estructura del Proyecto y Archivos de Configuración

```text
workspace/
├── ripley.toml                       # Configuración global de compilación, linter, estilo y rúbricas
├── templates/                        # Plantillas Jinja2 para generar reportes Markdown
│   ├── header.jinja2.md
│   ├── version_section.jinja2.md
│   └── footer.jinja2.md
├── practicas/                        # Repositorio de prácticas estructuradas de la cátedra
│   └── practica-1-punteros_1228009/
│       ├── ripley.toml
│       ├── enunciado.md
│       ├── pautas_evaluacion.md
│       └── ejercicios/
│           ├── ejercicio1/
│           │   ├── enunciado.md
│           │   ├── solucion_modelo.c
│           │   └── tests/ (caso1.in, caso1.out, caso1.argv)
├── tests/                            # Casos de prueba sincronizados por actividad
│   └── entrega-1_1228009/
│       └── ejercicio1/
└── entrega-1_1228009/                 # Entregas procesadas por estudiante
    ├── dashboard.md                  # Reporte consolidado de la cohorte
    ├── moodle_grades.csv             # CSV listo para importar en Moodle
    ├── retroalimentacion_moodle.zip  # ZIP con informes Markdown por alumno
    └── perez-juan_123456/
        ├── .metadata.db              # Base SQLite con notas, revisiones y hashes
        ├── mapping.json              # Mapeo persistente de archivos C a ejercicios
        └── r1/                       # Fuentes C de la primera entrega
```

---

## 4. Referencia Completa de Comandos CLI

### 4.1 Ingesta y Sanitización (`ingest`)
Procesa un archivo ZIP descargado directamente de Moodle. Normaliza codificaciones a UTF-8, aplana subcarpetas accidentales, filtra binarios no permitidos y calcula hashes SHA-256 para evitar reprocesar reentregas idénticas.

```bash
./ripley ingest <archivo_moodle.zip> [--dry-run] [--yes]
```

**Opciones:**
- `<archivo_moodle.zip>`: Ruta al archivo comprimido exportado de Moodle.
- `--dry-run`, `-d`: Simula la ingesta mostrando en consola la estructura resultante sin escribir en disco.
- `--workspace`, `-w`: Directorio raíz del workspace (por defecto `.`).
- `--yes`, `-y`: Si no existe una práctica coincidente en `./practicas/<activity_slug>`, inicializa automáticamente un enunciado en blanco con la configuración por defecto sin requerir confirmación interactiva.

> [!NOTE]
> Si la práctica no existe en `./practicas/` al ejecutar `ingest`, Ripley consulta interactivamente si se desea inicializar un enunciado en blanco con `ripley.toml` por defecto y sincronizar automáticamente con `tests/<activity_slug>/`.


---

### 4.2 Gestión de Prácticas Docentes (`practica`)
Gestiona el ciclo de vida de enunciados, pautas, rúbricas y casos de prueba docentes dentro de `./practicas/`.

#### `practica init`
Crea interactivamente o por parámetros la estructura completa de una nueva práctica:
```bash
./ripley practica init \
  --name "Práctica 1 - Punteros" \
  --activity-id "1228009" \
  --exercises "ejercicio1,ejercicio2" \
  --cases-per-exercise 3 \
  --with-argv
```
**Opciones:**
- `--name`, `-n`: Nombre de la práctica (ej. "Práctica 2 - Memoria Dinámica").
- `--activity-id`, `-i`: ID de la actividad de Moodle.
- `--exercises`, `-e`: Lista separada por comas de slugs de ejercicios.
- `--cases-per-exercise`, `-c`: Cantidad de casos de prueba iniciales por ejercicio (por defecto: `2`).
- `--with-argv`: Genera archivos `.argv` para pasar argumentos de línea de comandos.
- `--force`, `-f`: Sobrescribe una práctica existente si ya fue inicializada.

#### `practica list`
Muestra una tabla con todas las prácticas registradas en `./practicas/`, el estado de sus enunciados, soluciones de referencia y cantidad de tests:
```bash
./ripley practica list [--path practicas]
```

#### `practica sync`
Sincroniza los casos de prueba docentes desde `./practicas/<slug>/ejercicios/<ej>/tests/` hacia `./tests/<slug>/`:
```bash
./ripley practica sync --activity "practica-1-punteros_1228009"
```

---

### 4.3 Mapeo de Archivos Fuente (`map` / `testcase map`)
Asocia los archivos `.c` entregados por los alumnos con los ejercicios y casos de prueba correspondientes.

```bash
./ripley map --activity <slug_actividad> [--student <slug_alumno>] [--unmapped-only/--all/--auto]
```

**Opciones:**
- `--activity`, `-a`: Slug del directorio de la actividad (ej. `entrega-1_1228009`).
- `--student`, `-s`: Filtra la revisión a un único estudiante específico.
- `--unmapped-only`: (Por defecto) Muestra únicamente archivos que no pudieron vincularse automáticamente.
- `--all`: Revisa interactivamente todos los archivos de la cohorte.
- `--auto`: Aplica heurísticas de similitud de texto sin solicitar confirmación manual.

---

### 4.4 Gestión y Esqueletos de Casos de Prueba (`testcase`)

#### `testcase skeleton`
Crea plantillas vacías `.in`, `.out` y `.argv` para un ejercicio:
```bash
./ripley testcase skeleton --activity "entrega-1" --exercise "ejercicio1" --cases 5 --with-argv
```

#### `testcase list`
Lista todos los casos de prueba configurados por actividad y ejercicio:
```bash
./ripley testcase list [--activity <actividad>]
```

#### `testcase check`
Audita que no existan entradas `.in` sin sus correspondientes salidas `.out` esperadas:
```bash
./ripley testcase check [--activity <actividad>]
```

---

### 4.5 Fuzzing y Generación de Casos de Prueba (`testcase fuzz`)
Genera casos de borde aleatorios (`INT_MAX`, `INT_MIN`, cadenas de caracteres vacías o gigantes, números negativos) y calcula las salidas `.out` esperadas ejecutando la solución modelo docente:

```bash
./ripley testcase fuzz \
  --activity "entrega-1_1228009" \
  --exercise "ejercicio1" \
  --reference-source "./practicas/entrega-1/ejercicios/ejercicio1/solucion_modelo.c" \
  --count 10
```

---

### 4.6 Evaluación Integral de Entregas (`evaluate`)
Orquesta la compilación modular por mapeo, cálculo de diff semántico AST, análisis de estilo, linters, pruebas de ejecución dinámica, sanitizadores UBSan/ASan y auditoría de memoria con Valgrind:

```bash
./ripley evaluate --activity "entrega-1_1228009" [--parallel/--no-parallel] [--check-plagiarism]
```

**Opciones:**
- `--activity`, `-a`: Slug de la actividad a evaluar.
- `--parallel / --no-parallel`: Ejecuta la evaluación en paralelo utilizando todos los núcleos del CPU.
- `--check-plagiarism`: Dispara el análisis cruzado de plagio tras finalizar la evaluación individual.

---

### 4.7 Análisis de Plagio y Similitud (`plagiarism`)
Calcula coeficientes de similitud estructural (Jaccard y Contención) entre todas las entregas mediante tokenización AST de C y algoritmo **Winnowing**:

```bash
./ripley plagiarism \
  --activity "entrega-1_1228009" \
  --threshold 0.70 \
  --output "plagiarism_report.md"
```

**Opciones:**
- `--threshold`, `-t`: Umbral de similitud mínima para emitir alerta (ej. `0.70` = 70%).
- `--output`, `-o`: Archivo Markdown donde guardar el informe de coincidencias sospechosas.

---

### 4.8 Linters de Calidad, AST y Buenas Prácticas (`lint`)
Audita el cumplimiento de buenas prácticas en C:

```bash
./ripley lint --file entregas/alumno_1/r1/ejercicio1.c [OPCIONES]
```

**Opciones:**
- `--file`, `-f`: Archivo C a analizar.
- `--magic-numbers / --no-magic-numbers`: Literales numéricos sin nombre fuera de `#define`/`enum`.
- `--clones / --no-clones`: Detección de bloques de código duplicados (copy-paste) dentro del mismo archivo.
- `--naming / --no-naming`: Convenciones de nombres (`snake_case`, constantes en `UPPER_CASE`, prefijo `t_`).
- `--dead-code / --no-dead-code`: Funciones inalcanzables desde `main()` y código posterior a `return`/`exit()`.
- `--doxygen / --no-doxygen`: Verificación de comentarios `@brief`, `@param` y `@return`.
- `--p1-rules / --no-p1-rules`: (Por defecto activo) Audita el catálogo oficial de reglas de estilo de Programación I bajo la nomenclatura hexadecimal `0xXXXXh`:
  - `0x0001h`: Identificadores descriptivos: variables de menos de 5 letras se listan como "A mejorar", y variables de 1 sola letra se marcan para revisión manual (diferenciando las convencionales de bucles como `i`, `j`, `k` de identificadores crípticos no descriptivos).
  - `0x0002h`: Una declaración de variable por línea.

  - `0x0003h`: Inicialización obligatoria de variables locales.
  - `0x0004h`: Un espacio antes y después de operadores binarios.
  - `0x0005h`: Indentación estricta de 4 espacios.
  - `0x0006h`: Asterisco de punteros junto al identificador (`int *ptr`).
  - `0x0007h`: Variables y argumentos en `snake_case` minúsculas.
  - `0x0008h`: Constantes en `MAYUSCULAS_SNAKE_CASE`.
  - `0x0009h`: Límite máximo de 79 caracteres por línea.
  - `0x1001h`: Llaves obligatorias `{}` en estructuras de control.
  - `0x1002h`: Prohibición de `continue` y control de `break`.
  - `0x1003h`: `for` para conteo y `while` para condiciones lógicas.
  - `0x1005h`: Evitar condiciones ambiguas por truthiness (comparar contra `NULL` o `0`).
  - `0x1006h`: Prohibición estricta de `goto`.
  - `0x1007h`: Prohibición del operador ternario `?:`.
  - `0x1008h`: Cláusula `default:` obligatoria en `switch`.
  - `0x2004h`: Prohibición de variables globales mutables.
  - `0x3001h`: Verificación obligatoria de `malloc` / `calloc` contra `NULL`.
  - `0x3002h`: Asignación de `NULL` al puntero tras `free()`.
  - `0x3003h`: No mezclar asignación y comparación en la misma línea `if`.
  - `0x3004h`: Definición de `struct` con `typedef` y sufijo `_t` / `t_`.
  - `0x5001h`: Prohibición de Arreglos de Longitud Variable (VLAs).
  - `0x5006h`: Prohibición de `gets()` y `scanf("%s")` desprotegido.
- `--advanced / --no-advanced`: Habilita linters profundos de AST (comparaciones de floats, *const-correctness*, *IWYU*, *deep free*, punteros salvajes del stack, sobre-ingeniería XOR).

  3. *Const-Correctness:* Punteros de solo lectura no calificados con `const`.
  4. *Efectos Colaterales en Cortocircuito:* `if (a && b++)`.
  5. *Deep Free Verifier:* `free(nodo)` sin liberar campos puntero anidados.
  6. *Punteros Nulos en `<string.h>`:* `strlen(s)` sin validar `if (s != NULL)`.
  7. *Variable Shadowing:* Variables locales que ocultan parámetros.
  8. *Dangling Stack Pointer Return:* `return &local_var;` (severidad `ERROR`).
  9. *Sobre-Ingeniería:* Intercambios XOR (`a ^= b`) y ternarios triplemente anidados.
  10. *Orden de Evaluación de Argumentos:* Modificación y lectura simultánea en parámetros `f(i++, i++)`.
  11. *Escritura en `.rodata`:* `char *s = "hola"; s[0] = 'X';`.
  12. *Saltos Hacia Atrás con `goto`:* Saltos a etiquetas previas (*spaghetti loops*).

---

### 4.9 Auditoría de Funciones Puras (`pure-audit`)
Verifica estáticamente y mediante GCC con inyección de atributos que las funciones cumplan con los contratos `__attribute__((pure))` o `__attribute__((const))`:

```bash
./ripley pure-audit --file programa.c --mode const [--verify-compiler]
```

**Opciones:**
- `--file`, `-f`: Archivo fuente en C.
- `--mode`, `-m`: `pure` (sin efectos secundarios ni mutaciones de memoria global) o `const` (depende únicamente de sus argumentos escalares y no lee punteros ni memoria global).
- `--verify-compiler`: Inyecta el atributo en una copia temporal y compila con GCC bajo `-O2 -Werror`.

---

### 4.10 Simulador de Fragmentación de Memoria Heap (`heap-simulate`)
Simula asignaciones y liberaciones de memoria en un montículo con coalescencia contigua automática para diagnosticar fragmentación externa:

```bash
./ripley heap-simulate \
  --capacity 2048 \
  --allocations "128,512,64,256,128" \
  --frees "2,4"
```

**Opciones:**
- `--capacity`, `-c`: Capacidad del Heap simulado en bytes.
- `--allocations`, `-a`: Lista de tamaños a asignar separados por comas.
- `--frees`, `-f`: Índices 1-based de las asignaciones que se liberan.

---

### 4.11 Emulación de Memoria Embebida Restringida (`embedded-test`)
Ejecuta el binario compilado bajo límites estrictos de memoria física (`RLIMIT_AS` y `RLIMIT_DATA`) para verificar sistemas con recursos ultra reducidos (microcontroladores o RTOS):

```bash
./ripley embedded-test --binary ./binario_alumno --limit-kb 64 --stdin "10 20"
```

**Opciones:**
- `--binary`, `-b`: Ruta al ejecutable compilado.
- `--limit-kb`, `-l`: Límite máximo de memoria en Kilobytes (por defecto: `64` KB).
- `--stdin`: Datos provistos por la entrada estándar.

---

### 4.12 Diagramas de Flujo Tradicionales ISO/ANSI (`flowchart`)
Genera diagramas de flujo con la simbología estándar (óvalos de inicio/fin, paralelogramos de E/S, rombos de decisión y rectángulos de asignación):

```bash
./ripley flowchart --file programa.c --format mermaid [--output diagrama.md]
```

**Opciones:**
- `--file`, `-f`: Archivo C con las funciones a diagramar.
- `--function`: Nombre de la función específica a graficar (si se omite, grafica `main()`).
- `--format`: `mermaid` (renderizable en Markdown) o `dot` (Graphviz).
- `--output`, `-o`: Guarda el resultado en un archivo en lugar de imprimirlo por pantalla.

---

### 4.13 Árboles de Llamadas Call Graph (`callgraph`)
Genera el grafo de dependencias e invocaciones entre funciones del programa:

```bash
./ripley callgraph --file programa.c --format dot --stdlib [--output callgraph.dot]
```

**Opciones:**
- `--file`, `-f`: Archivo fuente en C.
- `--format`: `mermaid` o `dot`.
- `--stdlib`: Incluye las invocaciones a funciones de la biblioteca estándar (`printf`, `malloc`, `free`, etc.).

---

### 4.14 Visualizador de Estructuras Dinámicas en Memoria (`memory-visualize`)
Extrae las definiciones de `struct` y genera la topología de memoria y enlaces de punteros (listas enlazadas, árboles binarios, grafos):

```bash
./ripley memory-visualize --file estructuras.c --format mermaid
```

---

### 4.15 Generador de Mocks en C (`mock generate`)
Genera automáticamente stubs y arneses mock (`mock_<modulo>.h` y `.c`) a partir de un header C para pruebas unitarias docentes:

```bash
./ripley mock generate --header modulo.h --output-dir tests/mocks/
```

Genera:
- `mock_<fn>_call_count`: Contador de llamadas a cada función simulada.
- `mock_<fn>_set_return(...)`: Inyector de valores de retorno simulados.
- `reset_all_mocks()`: Reseteo de contadores para aislamiento entre tests.

---

### 4.16 Testing Basado en Propiedades (`property-test`)
Valida invariantes formales en funciones C ejecutando iteraciones con datos pseudoaleatorios y reportando contraejemplos mínimos:

```bash
./ripley property-test \
  --source algoritmos.c \
  --function ordenar_arreglo \
  --property SORT_INVARIANT \
  --iterations 500
```

**Propiedades soportadas:**
- `IDEMPOTENCE`: $f(f(x)) == f(x)$
- `COMMUTATIVITY`: $f(a, b) == f(b, a)$
- `SORT_INVARIANT`: Arreglo ordenado ascendentemente preservando la frecuencia de elementos.

---

### 4.17 Auditoría de Documentación Doxygen (`doxygen`)
Verifica la presencia y consistencia de etiquetas de documentación técnica:

```bash
./ripley doxygen --file funciones.c
```

---

### 4.18 Gestión de Plantillas Jinja2 (`template`)

#### `template init`
Crea plantillas Markdown por defecto (`header.jinja2.md`, `version_section.jinja2.md`, `footer.jinja2.md`):
```bash
./ripley template init [--path templates/] [--force]
```

#### `template check`
Valida la sintaxis de las plantillas y el uso obligatorio de variables en formato `snake_case`:
```bash
./ripley template check [--path templates/]
```

---

### 4.19 Exportación a Moodle y Tablero Docente (`export`)
Consolida los resultados de evaluación en archivos listos para entrega:

```bash
./ripley export --activity "entrega-1_1228009"
```

Genera:
1. `moodle_grades.csv`: Archivo CSV con notas numéricas compatible con la planilla de calificaciones de Moodle.
2. `retroalimentacion_moodle.zip`: Archivo ZIP que contiene los informes de retroalimentación individuales `<alumno>.md` listos para carga masiva.
3. `dashboard.md`: Resumen consolidado para los docentes con métricas de aprobación, errores comunes de compilación y fallas recurrentes de memoria.

---

## 5. Diagnósticos Especializados y Sanitizadores

Ripley incluye interceptores pedagógicos para los errores más complejos en C:

| Diagnóstico | Causa Raíz Detectada | Sugerencia Didáctica Emitida |
| :--- | :--- | :--- |
| **Stack Overflow** | Recursión sin caso base o arreglos locales masivos. | Revisa la condición de corte o traslada el buffer al Heap (`malloc`). |
| **Stdin Deadlock** | El programa pide más datos por teclado (`scanf`) de los que provee el test. | Verifica la cantidad de lecturas o revisa si hay bucles de lectura infinitos. |
| **Use-After-Free** | Lectura o escritura sobre puntero liberado con `free()`. | Asigna `ptr = NULL;` inmediatamente tras liberar la memoria. |
| **Double Free** | Múltiples llamadas a `free()` sobre la misma dirección. | Asegúrate de que cada bloque dinámico tenga un único dueño responsable de liberarlo. |
| **UBSan: Integer Overflow** | Desbordamiento en operaciones aritméticas con signo. | Utiliza tipos más amplios (`int64_t`) o valida los límites antes de operar. |
| **UBSan: Unaligned Access** | Puntero casteado a un tipo con requisito de alineación mayor. | Evita casteos arbitrarios de punteros que violen la alineación de la CPU. |
| **Sign Conversion** | Comparación o asignación implícita entre `int` con signo y `size_t`. | Utiliza tipos coherentes o casteo explícito tras validar que el valor sea positivo. |
| **Variables no Inicializadas** | Lectura de basura en variables del stack (`-Wuninitialized`). | Inicializa siempre las variables locales al declararlas (ej. `int total = 0;`). |
| **Dangling Stack Pointer** | Retorno de dirección de variable local `return &x;`. | Las variables del stack desaparecen al salir de la función; usa el Heap (`malloc`). |

---

## 6. Estructura del Archivo de Configuración `ripley.toml`

```toml
[compiler]
enabled = true
executable = "gcc"
flags = [
    "-Wall",
    "-Wextra",
    "-pedantic",
    "-std=c11",
    "-fsanitize=address,undefined",
    "-Wuninitialized",
    "-Wsign-conversion"
]

[limits]
timeout_segundos = 5.0
limite_memoria_mb = 128
max_tamano_ejecutable_mb = 10

[style]
enabled = true
brace_style = "allman"          # "allman" (llaves en nueva línea) o "k&r"
require_braces = true           # Exigir llaves en if/while de una sola línea
indent_style = "spaces"         # "spaces" o "tabs"
indent_size = 4
no_trailing_whitespace = true
max_blank_lines = 2

[p1_rules]
enabled = true                  # Catálogo oficial de Programación I (0x0001h a 0x3004h)

[linters]
enabled = false                 # Linters especializados adicionales
dead_code = true
magic_numbers = true
internal_clones = true
naming = true

[ast_auditors]
enabled = false                 # Auditores de AST y sintaxis profunda
const_correctness = true
short_circuit = true
deep_free = true
string_null = true
variable_shadowing = true
dangling_stack_pointer = true
overengineering = true
evaluation_order = true
string_literal_write = true
backward_goto = true

[flowchart]
enabled = false                 # Generador de diagramas de flujo
format = "mermaid"              # "mermaid" o "dot"

[memory_visualizer]
enabled = false                 # Diagramas de topología y estructuras en memoria
format = "mermaid"              # "mermaid" o "dot"

[callgraph]
enabled = false                 # Grafo de llamadas y detección de recursión
format = "mermaid"              # "mermaid" o "dot"
include_stdlib = false

[property_testing]
enabled = false                 # Property-Based Testing
properties = ["idempotence", "commutativity", "sort_invariant"]

[pure_functions]
enabled = false                 # Análisis de pureza y efectos de lado
functions = []                  # Funciones a verificar (vacío = todas)

[restrictions]
enabled = false                 # Restricciones de código prohibido / requerido
forbidden_constructs = []       # ej. ["goto", "global_vars", "float"]
required_constructs = []        # ej. ["while", "struct", "pointers"]

[doxygen]
enabled = false                 # Auditoría de documentación técnica Doxygen
require_brief = true
require_params = true
require_return = true

[cppcheck]
enabled = true
ejecutable = "cppcheck"
parametros = [
    "--enable=all",
    "--inline-suppr",
    "--suppress=missingIncludeSystem",
    "--suppress=staticFunction"
]

[valgrind]
enabled = true
flags = ["--leak-check=full", "--show-leak-kinds=all", "--track-origins=yes"]
tolerar_fugas_en_error = true   # No penaliza fugas si el programa abortó por error

[security]
enabled = true
forbidden_calls = ["system", "fork", "execv", "popen"]
forbidden_headers = ["unistd.h", "sys/socket.h"]

[rubric]
peso_compilacion = 0.30
peso_linter = 0.20
peso_estilo = 0.10
peso_pruebas = 0.40

# Herramientas de Línea de Comandos Arbitrarias (Custom Tools)
# Variables disponibles: {source}, {binary}, {folder}, {filename}, {stem}
# Etapas soportadas: "source" (por archivo C), "binary" (por ejecutable), "folder" (por revisión)

[[custom_tools]]
name = "clang-tidy"
command = "clang-tidy {source} -- -std=c11"
enabled = false
stage = "source"
fail_on_error = false

[[custom_tools]]
name = "flawfinder"
command = "flawfinder --quiet {source}"
enabled = false
stage = "source"
fail_on_error = false
```

---


## 8. Guía del Estudiante: verificación temprana con `ripley-check`

Ripley se separa en dos superficies de uso. La suite docente (`ripley`) requiere la
infraestructura completa; el estudiante solo necesita `ripley-check`, que comparte el
mismo catálogo de reglas pero nunca accede a datos de Moodle, plagio ni notas.

### 8.1 Instalación

```bash
# Opción A: paquete pip (requiere typer y rich, ya incluidos)
pipx install ripley

# Opción B: zipapp autocontenido sin instalación (requiere typer+rich en el sistema)
python scripts/build_zipapp.py            # genera dist/ripley_check.pyz
./dist/ripley_check.pyz --help
```

Herramientas externas opcionales (gcc recomendado; valgrind, frama-c, qemu,
bwrap... se detectan automáticamente y sus checks se marcan como OMITIDOS si faltan).

### 8.2 Diagnóstico del entorno

```bash
ripley-check doctor        # qué herramientas hay y qué checks se omitirán
ripley-check checks list   # catálogo completo con scope y requisitos
```

### 8.3 Verificación contra la práctica oficial

El docente publica un paquete `.ripkg` con los checks habilitados y los testcases
públicos de la práctica:

```bash
ripley-check run --practica entrega-2.ripkg mi_solucion.c
```

El comando compila con los flags oficiales de la práctica, ejecuta los testcases
públicos contra las salidas esperadas y aplica exactamente el subconjunto de
verificaciones declarado por el docente. El resultado es orientativo: la nota
siempre proviene de la evaluación docente.

### 8.4 Análisis individual sin paquete

Todos los analizadores funcionan de forma independiente sobre archivos locales:
`lint`, `padding-audit`, `contract-check`, `stack-audit`, `coverage-fuzz`,
`complexity-profile`, `benchmark`, `flowchart`, `callgraph`, `doxygen`, etc.
Ver `ripley-check --help`.

---

## 9. Referencias Adicionales

- 🛠️ [Guía Completa de Configuración de Herramientas Externas para C (`HERRAMIENTAS_EXTERNAS.md`)](file:///home/mrtin/dev/p1/ripley/HERRAMIENTAS_EXTERNAS.md)
- 📌 [Pautas Oficiales de Programación I (Reglas P1: 0x0001h - 0x5006h)](file:///home/mrtin/dev/p1/ripley/practicas/entrega-2_1236012/pautas_evaluacion.md)



