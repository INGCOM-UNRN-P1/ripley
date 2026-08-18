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
   Toda la lógica configurable debe residir en un archivo TOML:
   - Compilador (`gcc`), flags (`-Wall -Wextra -pedantic -std=c11 -fsanitize=address,undefined`).
   - Límites de recursos (`timeout_segundos = 5`, `limite_memoria_mb = 128`, `max_tamaño_ejecutable_mb = 10`).
   - Ruta al directorio de plantillas Jinja2 (ej. `ruta_plantillas = "templates/"`).
   - **Configuración de Linter y Reglas Personalizadas (`cppcheck`):**
     - Ruta al ejecutable de Cppcheck (ej. `cppcheck` del sistema o binario local `./cppcheck`).
     - Parámetros adicionales y reglas (ej. `--enable=all`, `--inline-suppr`).
     - Soporte para scripts de reglas/addons personalizados en Python (ej. `reglas_python = ["tools/cppcheck_rules.py"]` o `--rule-file` / `--addon`).
   - **Análisis de Estilo y Formato Personalizable (`[style]`):**
     - Reglas personalizables para evaluar el estilo de código C:
       - **Estilo de llaves (`brace_style`):** `K&R`, `Allman` / `BSD` o `attach`/`break` (ej. si la llave de apertura `{` debe ir en la misma línea o en línea nueva tras `if`/`while`/`for`/funciones).
       - **Obligatoriedad de llaves (`require_braces`):** Forzar el uso de llaves `{}` en bloques condicionales e iterativos aun si consisten en una sola línea (ej. `if (c) stmt;` prohibido).
       - **Indentación y Espacios (`indent_style`):** Espacios vs Tabs y tamaño estricto de sangría (ej. 4 espacios).
       - **Espaciado alrededor de operadores y paréntesis (`spacing`):** Validar espacios antes/después de operadores binarios, comas y palabras clave (ej. `if (` vs `if(`).
       - **Espacios finales y líneas en blanco (`formatting`):** Detectar espacios en blanco al final de línea (*trailing whitespace*) y número máximo de líneas en blanco consecutivas.
     - Implementación flexible: Soporte para reglas escritas en Python (módulo interno de inspección AST/Regex) o integración con herramientas de formato externas (ej. `clang-format` con archivo `.clang-format` personalizable).
   - Comandos y flags de `valgrind`.
   - Pesos para la rúbrica de calificación (ej. `peso_compilacion = 0.25`, `peso_linter = 0.25`, `peso_estilo = 0.15`, `peso_pruebas = 0.35`).
2. **Persistencia de Estado (`.metadata.db` / SQLite):**
   Guardar el estado global de estudiantes, hashes de archivos, versiones procesadas, resultados de pruebas y notas en una base de datos local SQLite para consultas ultrarrápidas.

---

### 3. Estructura de Directorios y Versionado Incremental

```text
workspace/
├── ripley.toml                                 # Archivo de configuración global
├── templates/                                  # Plantillas base Jinja2 para la generación de informes
│   ├── header.jinja2.md
│   ├── version_section.jinja2.md
│   └── footer.jinja2.md
├── tests/                                      # Casos de prueba agrupados por actividad slugificada
│   └── <actividad_slugificada>/                 # ej. entrega-1_1228009/
│       ├── ejercicio1/
│       │   ├── caso1.in / caso1.out / caso1.argv
│       │   └── caso2.in / caso2.out
│       └── ejercicio2/
│           └── caso1.in / caso1.out / caso1.argv
└── <actividad_slugificada>/                     # ej. entrega-1_1228009/
    ├── dashboard.md                            # Reporte consolidado de la cohorte
    ├── moodle_grades.csv                       # CSV para importar calificaciones en Moodle
    ├── retroalimentacion_moodle.zip            # ZIP listo para subir retroalimentación a Moodle
    └── <estudiante_slugificado>/               # ej. yucra-agustin-daniel_1848964/
        ├── <estudiante_slugificado>_<actividad_slugificada>.md   # Informe acumulativo
        ├── .metadata.db                        # Base de datos SQLite o estado local
        ├── r1/                                 # Primera versión procesada
        │   ├── ejercicio1.c
        │   └── ejercicio2.c
        └── r2/                                 # Reentrega (si hubo cambios)
            ├── ejercicio1.c
            └── ejercicio2.c
```

---

### 4. Requisitos Funcionales y Comandos CLI

El proyecto estará gestionado con `uv` en un subdirectorio (`ripley/`) e invocado mediante un script Bash wrapper (`./ripley ...`). Debe incluir barra de progreso e indicadores visuales ricos en consola usando `rich.progress`.

#### A. Subcomando `ingest`
- Recibe el ZIP descargado de Moodle. Parsea el nombre con Regex y genera carpetas slugificadas.
- Soporta la opción `--dry-run` para simular la descompresión y estandarización sin escribir en disco.
- Realiza conversión UTF-8, aplanamiento de carpetas, segregación de archivos no válidos y verificación SHA-256.

#### B. Subcomando `template` (Gestión y Creación de Plantillas Base)
- **Inicialización de Plantillas (`template init` / `template skeleton`):** Genera o restaura las plantillas Jinja2 por defecto (`header.jinja2.md`, `version_section.jinja2.md`, `footer.jinja2.md`) en el directorio especificado por `ripley.toml` (o por defecto `templates/`). Permite la bandera `--force` para sobrescribir plantillas existentes.
  - Ejemplo de uso: `./ripley template init` o `./ripley template init --path custom_templates/ --force`
- **Listado y Verificación (`template list` / `template check`):**
  - Lista las plantillas disponibles en la carpeta configurada e indica si falta alguna de las 3 requeridas.
  - Valida la sintaxis de las plantillas Jinja2 y la presencia de las variables críticas `snake_case` obligatorias (ej. `numero_version`, `resultados_compilacion`, `nota_preliminar`).

#### C. Subcomando `testcase` (Gestión y Esqueletos de Pruebas)
- **Generación de Esqueletos (`testcase skeleton`):** Genera automáticamente la estructura de directorios y archivos plantilla vacíos o de ejemplo (`caso1.in`, `caso1.out`, opcionalmente `caso1.argv`) para una actividad y ejercicios dados.
  - Ejemplo de uso: `./ripley testcase skeleton --activity entrega-1_1228009 --exercise ejercicio1 --cases 3 --with-argv`
- **Listado y Validación (`testcase list` / `testcase check`):**
  - Lista los casos de prueba asociados a cada ejercicio en `workspace/tests/<actividad_slugificada>/`.
  - Verifica la presencia e integridad de parejas `.in` / `.out` e indica si existen `.argv` asociados.

#### D. Subcomando `evaluate`
- Soporta procesamiento concurrente/paralelo mediante `multiprocessing` o `concurrent.futures`.
- **Diff Inteligente:** Compara $r_N$ contra $r_{N-1}$ generando un `unified diff`, ofreciendo banderas para ignorar cambios en comentarios o líneas en blanco.
- **Escaneo Preventivo de Llamadas al Sistema:** Valida mediante expresiones regulares/AST que el código C no incluya librerías o llamadas peligrosas (`system()`, `fork()`, `#include <unistd.h>`).
- **Compilación e Inspección con Límites de Recursos:**
  - Compila con `gcc` empleando flags de sanitización (`-fsanitize=address,undefined`).
  - Aplica límites de CPU (timeout), memoria (128 MB) y tamaño de ejecutable utilizando el módulo `resource` de Unix o subprocesos aislados.
  - *Opción de Sandboxing:* Permite ejecuciones opcionales dentro de contenedores efímeros (Docker/Podman/bubblewrap) si la configuración lo requiere.
- **Análisis de Estilo y Formato de Código:**
  - Inspecciona los archivos `.c` evaluando las reglas personalizadas configuradas en `ripley.toml` (estilo de llaves, sangría/espacios, obligación de llaves en bloques, espaciado de operadores).
  - Emite un reporte detallado con líneas y observaciones específicas de desvíos de estilo.
- **Evaluación Dinámica (Test Cases I/O y Argumentos CLI):**
  - Busca los casos de prueba en `workspace/tests/<actividad_slugificada>/`.
  - Si existe un archivo `.argv` asociado al caso de prueba (ej. `caso1.argv`), lee su contenido y pasa los argumentos de línea de comandos correspondientes al binario durante su ejecución.
  - Ejecuta el binario suministrando la entrada del archivo `.in` vía `stdin` y compara la salida (`stdout`) contra la salida esperada (`.out`), ignorando espacios o saltos de línea finales.
- **Análisis de Fugas con Valgrind:**
  - Si está activado en `ripley.toml`, ejecuta `valgrind --leak-check=full` para auditar el uso de `malloc`/`free`.
- **Análisis Estático y Reglas Personalizadas (`cppcheck`):**
  - Ejecuta `cppcheck` utilizando la ruta configurable especificada en `ripley.toml` (ej. binario local `./cppcheck` o de sistema).
  - Admite e invoca scripts/addons de Python con reglas de análisis personalizado definidos en la configuración (`--rule-file`, `--addon` o invocación directa de scripts Python de inspección AST).
- **Rúbrica de Calificación:** Calcula una puntuación cuantitativa preliminar (0 a 10) según los pesos definidos en `ripley.toml` (compilación, linter, estilo y casos de prueba).

#### E. Subcomando `export` (Reportería y Docencia)
- **`moodle_grades.csv`:** Exporta un archivo de calificaciones estructurado para ser subido directamente al Libro de Calificaciones de Moodle.
- **`retroalimentacion_moodle.zip`:** Empaqueta todos los informes `.md` (o convertidos) respetando el formato requerido por Moodle para la "Subida masiva de archivos de retroalimentación".
- **`dashboard.md`:** Genera un resumen global para el profesor con métricas de la cohorte (% que compila, cumplimiento de estilo, errores más frecuentes, promedio de nota preliminar).

---

### 5. Generación de Informes Mediante Plantillas (Jinja2)

Toda la generación de informes en Markdown debe usar plantillas en el directorio `templates/` (o el configurado en `ripley.toml`). Todos los tags de las plantillas deben ser simples y seguir strictly la convención `snake_case`.

#### Plantillas Requeridas:
1. `header.jinja2.md`: Encabezado con metadatos del estudiante y de la entrega.
2. `version_section.jinja2.md`: Bloque modular para renderizar diffs, tabla de compilación, análisis de estilo, análisis estático, fugas con Valgrind, resultados de Test Cases y archivos ignorados.
3. `footer.jinja2.md`: Cierre, versión de `ripley`, timestamp y nota final preliminar.

#### Ejemplo de Contenido en Plantilla (`version_section.jinja2.md`):

```markdown
<!-- VERSIÓN (Cargado desde plantilla: version_section.jinja2.md) -->
## Versión {{ numero_version }} - {{ fecha_hora }}

### Resumen de Cambios y Archivos
- **Archivos nuevos:** {{ archivos_nuevos }}
- **Archivos modificados:** {{ archivos_modificados }}
- **Archivos sin cambios:** {{ archivos_sin_cambios }}
- **Archivos ignorados/no permitidos:** {{ archivos_ignorados }}

{% if diff_unificado %}
```diff
{{ diff_unificado }}
```
{% endif %}

### Compilación, Estilo y Análisis Estático

| Archivo | Estado Compilación | Evaluación de Estilo | Valgrind (Fugas) | Cppcheck / Rules |
| ----- | ----- | ----- | ----- | ----- |
{% for item in resultados_compilacion %}
| `{{ item.nombre_archivo }}` | {{ item.estado }} | {{ item.estado_estilo }} | {{ item.estado_valgrind }} | {{ item.estado_cppcheck }} |
{% endfor %}

#### Observaciones de Estilo y Formato
{% for observacion in observaciones_estilo %}
- **`{{ observacion.archivo }}` (Línea {{ observacion.linea }}):** {{ observacion.mensaje }}
{% else %}
_No se detectaron faltas de estilo según las reglas configuradas._
{% endfor %}

#### Logs de Compilación y Linter
```text
{{ logs_detallados_compilacion }}
```

### Pruebas de Entrada/Salida (Test Cases)

| Ejercicio | Caso de Prueba | Argumentos CLI | Resultado | Tiempo Exec. |
| ----- | ----- | ----- | ----- | ----- |
{% for test in resultados_pruebas %}
| `{{ test.ejercicio }}` | {{ test.nombre_caso }} | `{{ test.argumentos_cli }}` | {{ test.resultado }} | {{ test.tiempo_ms }} ms |
{% endfor %}

### Nota Preliminar Estimada: {{ nota_preliminar }} / 10
_Desglose: Compilación ({{ nota_compilacion }}), Estilo ({{ nota_estilo }}), Linter ({{ nota_linter }}), Test Cases ({{ nota_pruebas }})_
```

---

### 6. Estrategia de Testing y Calidad de Código (QA)

Para garantizar la fiabilidad de `ripley`, el proyecto debe incluir una suite de pruebas automatizada con `pytest` en un subdirectorio `tests/`:

1. **Pruebas Unitarias (`tests/unit/`):**
   - **Parsing de Moodle:** Validación de expresiones regulares con nombres de ZIP reales y no válidos.
   - **Normalización de Encoding:** Verificación de conversión correcta de archivos codificados en `ISO-8859-1`, `Windows-1252` y `UTF-8`.
   - **Aplanamiento y Filtro:** Test para verificar que carpetas anidadas extraen solo archivos `.c`/`.h` y mueven otros a ignorados.
   - **Gestor de Plantillas (`template init` / `check`):** Verificación de creación de plantillas Jinja2 por defecto, detección de plantillas faltantes y validación de sintaxis de variables `snake_case`.
   - **Generación de Esqueletos de Tests:** Test de comandos `testcase skeleton` comprobando la creación de carpetas y archivos `.in`/`.out`/`.argv`.
   - **Verificación de Reglas de Estilo:** Tests unitarios del analizador de estilo evaluando casos de violación de llaves (K&R vs Allman), omitir llaves en `if` de una línea, espaciado e indentación.
   - **Generación de Diff:** Test sobre cadenas de texto con y sin ignorar comentarios/espacios.
   - **Parseo de Argumentos CLI (`.argv`):** Validación de lectura correcta de argumentos en línea de comandos para pasárselos al ejecutable.
   - **Invocación de Cppcheck con Reglas Personalizadas:** Test unitario verificando el montaje de argumentos para binarios locales (`./cppcheck`) y ejecución de reglas Python/addons.
   - **Renderizado Jinja2:** Validación de que los contextos en `snake_case` rellenan adecuadamente las plantillas.

2. **Pruebas de Integración y Mocks (`tests/integration/`):**
   - **Invocación de Subprocesos:** Mocks de `gcc`, `cppcheck` (con sus reglas custom) y `valgrind` mediante `pytest-mock` para probar el parseo de salidas sin depender de ejecutables del sistema.
   - **Flujo Completo de Ingesta, Generación de Tests y Evaluación:** Creación de archivos ZIP sintéticos en memoria (`io.BytesIO` / `zipfile`) con entregas válidas e inválidas, verificando la creación de la estructura `r1/`, `r2/`, `.metadata.db` e informes finales.
   - **Timeouts y Límites de Memoria:** Simulación de programas C con bucles infinitos para verificar la interrupción correcta por timeout.

---

### 7. Planificación de Tareas y Roadmap de Implementación

Para asegurar una construcción modular y 100% completa (sin código omitido ni placeholders `TODO`), la implementación se estructurará en 6 fases secuenciales:

#### Fase 1: Configuración del Entorno y Estructura CLI
- Configurar `pyproject.toml` con `uv` y dependencias (`typer`, `rich`, `jinja2`, `python-slugify`, `tomli_w` / `tomllib`).
- Crear el script wrapper Bash `./ripley`.
- Implementar la carga y validación de `ripley.toml` (incluyendo ejecutable de `cppcheck`, reglas custom en Python y sección de estilo `[style]`).
- Implementar el subcomando `template` (`template init`, `template list`, `template check`) para instanciar y validar plantillas base Jinja2.

#### Fase 2: Módulo de Ingesta, Sanitización y Persistencia
- Implementar expresiones regulares para parseo de nombre del ZIP de Moodle.
- Crear funciones de descompresión, detección/conversión de encodings, aplanamiento de rutas y hashing SHA-256.
- Diseñar la base de datos SQLite (`.metadata.db`) y modelos de datos.
- Implementar el comando `ingest` (incluyendo `--dry-run`).

#### Fase 3: Motor de Compilación Segura, Aislamiento y Analizador de Estilo
- Crear el ejecutor de subprocesos con restricciones (`resource.setrlimit`, timeouts y flags de sanitización gcc).
- Implementar el escaneo preventivo de código C (detección de `system`, `fork`, etc.).
- Desarrollar el analizador de reglas de estilo personalizables (llaves, indentación, espacios, llaves obligatorias).
- Añadir el soporte para ejecución en sandbox (Docker/Podman/bubblewrap).

#### Fase 4: Gestión de Pruebas (Testcases), Evaluación Dinámica, Valgrind y Linters
- Implementar el subcomando `testcase` (`skeleton`, `list`, `check`) para crear esqueletos de casos de prueba (`.in`, `.out`, `.argv`) en `workspace/tests/<actividad_slugificada>/`.
- Implementar el ejecutor de Test Cases leyendo desde `workspace/tests/<actividad_slugificada>/` y comparando `.in` / `.out` con normalización de espacios, soportando argumentos opcionales desde archivos `.argv`.
- Integrar la auditoría de memoria con `valgrind` y la ejecución de `cppcheck` soportando rutas personalizadas (`./cppcheck`) y reglas/addons en Python.
- Crear el calculador de notas preliminares según la rúbrica de `ripley.toml`.

#### Fase 5: Versionado Incremental, Diffing y Motor de Plantillas
- Desarrollar la lógica de comparación $r_N$ vs $r_{N-1}$ (diff unificado).
- Integrar el renderizado con las plantillas Jinja2 en `templates/` utilizando variables `snake_case`.
- Implementar la actualización del archivo acumulativo `<estudiante>_<actividad>.md`.

#### Fase 6: Módulo de Exportación y Reportería Moodle
- Implementar la generación de `moodle_grades.csv`.
- Implementar la compresión masiva para `retroalimentacion_moodle.zip`.
- Crear el generador del dashboard consolidado `dashboard.md`.
- Escribir la suite completa de pruebas unitarias e integración en `pytest`.

---

### 8. Entregables Requeridos

1. **Estructura completa del proyecto:** Módulos Python completados en el directorio `ripley/`, carpetas `templates/`, `tests/` y script wrapper Bash.
2. **`pyproject.toml`:** Configuración de dependencias gestionadas por `uv`.
3. **`ripley.toml` por defecto:** Configuración inicial con flags de GCC, timeouts, ruta/parámetros/reglas Python de `cppcheck`, sección de reglas de estilo personalizables (`[style]`), ruta de plantillas Jinja2, opciones de Valgrind, pesos de rúbrica y reglas de sanitización.
4. **Código Python Modular e Íntegro:**
   - Módulo de parsing de rutas, normalización de encoding (UTF-8) y aplanamiento de entregas.
   - Módulo de base de datos local SQLite y cálculo de hashes SHA-256.
   - Módulo gestor de plantillas Jinja2 (`template init` / `list` / `check`).
   - Módulo gestor de casos de prueba y generación de esqueletos (`testcase skeleton` / `list`).
   - Módulo de ejecutor seguro (`subprocess` con `resource`/`ulimit`, timeouts, sanitizadores y soporte de sandbox).
   - Módulo de inspección de estilo y reglas de formato personalizables (llaves, espaciado, sangría, llaves obligatorias).
   - Módulo de pruebas dinámicas (I/O Testing & CLI Arguments) buscando en `workspace/tests/<actividad_slugificada>/` (soporte para `.in`, `.out` y `.argv`), auditoría de memoria con Valgrind y linter `cppcheck` configurable con reglas Python.
   - Módulo de diffing inteligente (con opción de ignorar espacios/comentarios).
   - Módulo de renderizado Jinja2 en `snake_case`.
   - Módulo exportador a Moodle (`moodle_grades.csv`, ZIP de retroalimentación y `dashboard.md`).
5. **Suite de Pruebas Automáticas (`pytest`):** Pruebas unitarias y de integración para validar la ingesta, gestión de plantillas base, esqueletos de pruebas, linter de estilo, invocaciones de `cppcheck` personalizado, seguridad y generación de informes.
6. **Script Bash (`ripley`):** Script ejecutable `+x` que redirija todos los comandos a `uv run main.py ...`.
7. **Ejemplo de Uso:** Comandos CLI completos para probar:
   - `./ripley template init`
   - `./ripley ingest --dry-run entrega1.zip`
   - `./ripley ingest entrega1.zip`
   - `./ripley testcase skeleton --activity entrega-1_1228009 --exercise ejercicio1 --cases 2 --with-argv`
   - `./ripley evaluate --activity entrega-1_1228009`
   - `./ripley export --activity entrega-1_1228009`

