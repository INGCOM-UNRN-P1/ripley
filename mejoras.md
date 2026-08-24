# Ripley - Registro Modular de Funcionalidades y Mejoras

> **Última revisión:** 2026-08-23 — `263` tests pasando, `3` omitidos por herramientas externas ausentes en el entorno (`pytest`, suite unitaria + integración).

---

## 1. Funcionalidades Implementadas (74)

Las funcionalidades se encuentran modularizadas por capas (`models/core/tools/pipeline/teacher`, ver [`PLAN_MODULARIZACION.md`](PLAN_MODULARIZACION.md)) con suites de pruebas unitarias e integradas:

> Las rutas listadas son las canónicas post-modularización; los módulos planos de la raíz (`src/ripley/<modulo>.py`) son shims de compatibilidad.


### Módulo A: Ingesta, Persistencia y Gestión de Prácticas
1. **Detección de Plagio y Similitud de Código (Anti-Cheating):** Algoritmo Winnowing con tokenización AST de C ($k$-gramas y ventanas deslizantes) y cálculo de similitud Jaccard ([`src/ripley/teacher/plagiarism.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/teacher/plagiarism.py)).
2. **Inicialización y Gestión Integral de Prácticas:** Estructuración automática de consignas, pautas docentes, rúbricas y casos de prueba en `./practicas/<slug>/` ([`src/ripley/teacher/practice.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/teacher/practice.py)).
3. **Mapeo Interactivo de Ejercicios y Testcases:** Vinculación interactiva y heurística de fuentes `.c` con previsualización de código y asignación de roles `[AUXILIAR]` o `[IGNORAR]` ([`src/ripley/teacher/mapping.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/teacher/mapping.py)).
4. **Ingesta Determinista y Normalización UTF-8:** Aplanamiento de carpetas ZIP de Moodle, filtro de extensiones y hashing SHA-256 ([`src/ripley/teacher/ingest.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/teacher/ingest.py)).
5. **Persistencia de Estado Local en SQLite:** Base de datos relacional para seguimiento de entregas, reentregas y notas acumulativas ([`src/ripley/teacher/db.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/teacher/db.py)).
6. **Gestor y Validador de Plantillas Jinja2:** Instanciación y verificación de plantillas de informe con variables `snake_case` ([`src/ripley/teacher/templates.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/teacher/templates.py)).

### Módulo B: Diagnósticos de Ejecución y Sanitizadores de Bajo Nivel
7. **Diagnóstico Especializado de Stack Overflow y Recursión Infinita:** Detección de agotamiento de pila con recomendaciones didácticas ([`src/ripley/tools/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/diagnostics.py)).
8. **Detección de Bloqueos en Stdin (I/O Deadlocks):** Detección de procesos colgados esperando entradas por teclado no provistas por el testcase ([`src/ripley/tools/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/diagnostics.py)).
9. **Detección Estricta de Punteros Colgantes (*Dangling Pointers*):** Captura dinámica de *Use-After-Free* y *Double Free*, y análisis estático post-`free()` ([`src/ripley/tools/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/diagnostics.py)).
10. **Detección de Desbordamientos de Enteros (UBSan):** Reporte de *signed integer overflow*, división por cero y shifts inválidos ([`src/ripley/tools/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/sanitizers.py)).
11. **Análisis de Variables no Asignadas:** Reporte de lectura de variables locales no inicializadas en el stack ([`src/ripley/tools/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/sanitizers.py)).
12. **Detección de Conversiones Implícitas Peligrosas (*Sign Conversion*):** Captura de advertencias de cambio de signo o truncamiento entre `int` y `size_t` ([`src/ripley/tools/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/sanitizers.py)).
13. **Detección de Desalineación de Memoria (*Unaligned Access*):** Captura de accesos a direcciones no alineadas a los múltiplos del tipo en la CPU ([`src/ripley/tools/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/sanitizers.py)).
14. **Detección de Bucles Infinitos por Contador de Instrucciones CPU:** Medición determinista de instrucciones ejecutadas con Callgrind ([`src/ripley/tools/instruction_counter.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/instruction_counter.py)).
15. **Tolerancia Diferenciada de Fugas de Memoria ante Salidas Anormales:** Tolerancia pedagógica para fugas previas a `exit(EXIT_FAILURE)` ([`src/ripley/tools/runner.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/runner.py)).
16. **Emulación de Memoria Restringida para Sistemas Embebidos:** Ejecución bajo límites estrictos de heap/stack (`RLIMIT_AS` y `RLIMIT_DATA`) ([`src/ripley/tools/embedded.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/embedded.py)).

### Módulo C: Linters de Calidad, AST y Buenas Prácticas
17. **Verificación de Restricciones del Enunciado (Blacklist/Whitelist AST):** Control de palabras clave prohibidas (`goto`, `while`, `<string.h>`) o requeridas (`struct`, `malloc`) ([`src/ripley/core/restrictions.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/restrictions.py)).
18. **Detector de Números Mágicos:** Alerta sobre literales numéricos sin nombre fuera de `#define`/`enum` ([`src/ripley/core/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/linters.py)).
19. **Detector de Duplicación Interna de Código (Copy-Paste Detector):** Detección de bloques de tokens duplicados dentro de la misma entrega ([`src/ripley/core/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/linters.py)).
20. **Linter de Convenciones de Nombres Configurable:** Validación de nomenclatura para variables, funciones (`snake_case`), constantes (`UPPER_CASE`) y tipos (`t_nodo`) ([`src/ripley/core/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/linters.py)).
21. **Detección de Código Muerto y Funciones Jamás Invocadas:** Identificación de funciones inalcanzables desde `main()` y código posterior a `return`/`exit()` ([`src/ripley/core/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/linters.py)).
22. **Detección de Comparaciones Peligrosas en Punto Flotante:** Alerta de comparaciones directas `==` o `!=` en `float`/`double` ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
23. **Detección de Inclusiones Innecesarias (*IWYU*):** Identificación de cabeceras `#include` cuyos tipos y funciones no se usan ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
24. **Auditoría de Calificación `const` en Parámetros (*Const-Correctness*):** Validación de parámetros puntero de solo lectura ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
25. **Detección de Cortocircuitos Peligrosos con Efectos Colaterales:** Alerta de `++`, `--` o asignaciones dentro de `&&` o `||` ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
26. **Verificación de Liberación de Estructuras Anidadas (*Deep Free*):** Control de liberación de campos dinámicos antes de `free(nodo)` ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
27. **Auditoría de Punteros Nulos en `<string.h>`:** Fiscalización de llamadas a `strlen`/`strcmp`/`strcpy` sin validación previa contra `NULL` ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
28. **Detección de Sombras de Variables (*Variable Shadowing*):** Alerta cuando una variable local oculta a un parámetro de la función ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
29. **Detección de Retorno de Direcciones del Stack (*Dangling Stack Pointer*):** Detección de `return &var_local;` (severidad `ERROR`) ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
30. **Detector de Sobre-Ingeniería:** Alerta sobre trucos de intercambio XOR y ternarios triplemente anidados ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
31. **Auditoría de Documentación Doxygen:** Verificación de bloques `@brief`, `@param` y `@return` en funciones ([`src/ripley/core/doxygen.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/doxygen.py)).

### Módulo D: Visualización, Diff Semántico y Testing Avanzado
32. **Diagramas de Flujo Tradicionales (ISO/ANSI 5807):** Generación de diagramas con óvalos, paralelogramos, rombos y rectángulos en Mermaid y DOT ([`src/ripley/core/flowchart.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/flowchart.py)).
33. **Árboles de Llamadas (Call Graphs):** Extracción de relaciones entre funciones, recursiones y bibliotecas estándar ([`src/ripley/core/callgraph.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/callgraph.py)).
34. **Visualizador Gráfico de Estructuras Dinámicas en Memoria:** Representación de topología de nodos y enlaces en DOT y Mermaid ([`src/ripley/core/memory_visualizer.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/memory_visualizer.py)).
35. **Testing Basado en Propiedades (Property-Based Testing en C):** Validación automática de invariantes formales (idempotencia, conmutatividad, multiconjunto ordenado) ([`src/ripley/tools/property_testing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/property_testing.py)).

### Módulo E: Compilación, Estilo, Seguridad e Infraestructura de Análisis
36. **Compilación Segura con Sanitizadores y Fallback:** GCC con `-fsanitize=address,undefined`, límites `RLIMIT_CPU`/`RLIMIT_FSIZE` y reintento automático ante falta de `libasan` ([`src/ripley/tools/compiler.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/compiler.py)).
37. **Análisis de Estilo y Formato Configurable:** Verificación de llaves (Allman/K&R), indentación, espaciado de operadores/keywords y líneas en blanco según `ripley.toml` ([`src/ripley/core/style.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/style.py)).
38. **Escáner Preventivo de Vulnerabilidades en C:** Detección de patrones inseguros (`gets`, `sprintf`, desbordes de buffer) sobre fuente pre-limpia de comentarios y literales ([`src/ripley/core/security.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/security.py)).
39. **Gestor Integral de Casos de Prueba:** Generación de esqueletos `.in/.out/.argv`, listado, verificación de integridad y descubrimiento por ejercicio ([`src/ripley/tools/testcases.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/testcases.py)).
40. **Reglas Didácticas del Seminario Programación I:** Fiscalización específica del apunte P1 (declaraciones múltiples, VLA, variables cortas, asignaciones en condiciones) ([`src/ripley/core/p1_rules.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/p1_rules.py)).
41. **Runner Dinámico con Diagnóstico Didáctico:** Ejecución de casos I/O con argumentos CLI, timeouts y clasificación pedagógica de fallos ([`src/ripley/tools/runner.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/runner.py)).

### Módulo F: Diffing, Fuzzing, Simulación y Exportación
42. **Diff Unificado entre Reentregas:** Comparación incremental de fuentes normalizadas para informes de evolución ([`src/ripley/core/diffing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/diffing.py)).
43. **Diff Semántico basado en AST de C:** Extracción de firmas y cuerpos de funciones para comparar cambios estructurales entre versiones ([`src/ripley/core/semantic_diff.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/semantic_diff.py)).
44. **Fuzzing Automático de Entradas y Edge Cases:** Mutación aleatoria controlada de entradas para descubrir crashes no cubiertos por testcases fijos ([`src/ripley/tools/fuzzing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/fuzzing.py)).
45. **Simulador de Fragmentación de Memoria Heap:** Simulación de patrones malloc/free con cálculo de fragmentación externa e interna (✔ propuesta 10 del registro anterior) ([`src/ripley/core/heap_simulator.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/heap_simulator.py), CLI `heap-simulate`).
46. **Auditoría de Funciones Puras y `const`:** Validación de `__attribute__((pure))`/`((const))` contra efectos secundarios reales, verificada por compilación (✔ propuesta 18) ([`src/ripley/tools/pure_functions.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/pure_functions.py), CLI `pure-audit`).
47. **Generador de Mocks y Stubs para Unit Testing en C:** Creación de harness con sustitutos de funciones dependientes a partir del AST ([`src/ripley/core/mocks.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/mocks.py), CLI `mock generate`).
48. **Exportación de Notas y Feedback a Moodle:** CSV compatible con importación masiva más paquete ZIP de retroalimentación individual desde la base SQLite ([`src/ripley/teacher/exporter.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/teacher/exporter.py), CLI `export`).
49. **Dashboard de Cohorte y Evolución Longitudinal:** Métricas agregadas por actividad y alumno (notas, intentos, errores recurrentes) generadas como cuadro de mando (✔ propuesta 24) ([`src/ripley/teacher/exporter.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/teacher/exporter.py), CLI `export`).

### Módulo G: Auditores Semánticos Avanzados (AST)
50. **Detector de Dependencia de Orden de Evaluación de Argumentos:** Captura `f(i++, i++)` y llamadas múltiples con posibles efectos (`f(g(), h())`) vía whitelist de funciones puras (✔ propuesta 3) ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
51. **Auditoría de Modificación de Cadenas Literales en `.rodata`:** Escrituras directas, familia completa strcpy/str…/memcpy/memset y aliases del puntero; documenta el trap en runtime y `-Wwrite-strings` (✔ propuesta 4) ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
52. **Control de Saltos Hacia Atrás con `goto`:** Penalización de saltos regresivos que emulan bucles desestructurados (✔ propuesta 5) ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
53. **Demostrador Heurístico de Terminación de Bucles:** Variables de condición sin mutar en cuerpo/incremento de `while`, `do-while` y `for` (incluye `for (;;)`); advertencia de bucle infinito (✔ propuesta 14) ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
54. **Auditoría de Enums como Máscaras de Bits:** Detecta operadores `&`, `|`, `^`, `~` sobre enumeradores que no son potencias de dos (✔ propuesta 15) ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).
55. **Detector de Funciones Obsoletas y Desaconsejadas (Deprecated C API):** Alerta sobre `gets`, `strcpy`, `sprintf`, `strtok`, `atoi`, `asctime`, etc., con reemplazos seguros sugeridos (✔ propuesta 17) ([`src/ripley/core/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/ast_auditors.py)).

### Módulo H: Entornos Seguros, Rendimiento y Verificación Formal
56. **Compilación Cruzada Multi-Arquitectura (QEMU):** Matriz x86_64 (nativo), ARM64, RISC-V y MIPS big-endian con comparación de salidas contra el nativo; degrada con mensaje si falta toolchain (✔ propuesta 1) ([`src/ripley/tools/cross_arch.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/cross_arch.py), CLI `cross-test`).
57. **Aislamiento con Espacios de Nombres Linux:** Ejecución sin root vía bubblewrap (`--unshare-all`) o `unshare --user` con detección por sondeo y fallback reportado (✔ propuesta 2) ([`src/ripley/tools/sandbox.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/sandbox.py), CLI `sandbox-test`).
58. **Instantáneas de Toolchains Herméticas:** Captura y verificación JSON de versiones de GCC, target, libc, kernel y hash de flags para reproducibilidad temporal (✔ propuesta 6) ([`src/ripley/tools/toolchain.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/toolchain.py), CLI `toolchain-snapshot --verify`).
59. **Fuzzing Guiado por Cobertura (gcov):** Compila con `--coverage`, muta entradas y prioriza las que descubren líneas nuevas; detecta crashes y arma corpus incremental sin requerir AFL++/LibFuzzer (✔ propuesta 7) ([`src/ripley/tools/coverage_fuzzing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/coverage_fuzzing.py), CLI `coverage-fuzz`).
60. **Analizador Empírico de Complejidad Asintótica:** Perfila tiempos con $N$ creciente y clasifica O(1)/O(√N)/O(N)/O(N log N)/O(N²)/O(N³) mediante regresión log-log con $R^2$ (✔ propuesta 8) ([`src/ripley/tools/complexity_profiler.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/complexity_profiler.py), CLI `complexity-profile`).
61. **Auditoría de Consumo de Stack Máximo (`-fstack-usage`):** Parseo de archivos `.su` con umbral configurable y flag de asignaciones dinámicas (VLA/alloca) (✔ propuesta 9) ([`src/ripley/tools/stack_usage.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/stack_usage.py), CLI `stack-audit`).
62. **Inyección de Fallas en Sockets (LD_PRELOAD):** Shim C generado en runtime que interpone `socket/connect/send/recv/close`, inyecta `ECONNRESET` a partir de la N-ésima operación y audita fugas de descriptores (✔ propuesta 11) ([`src/ripley/tools/socket_faults.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/socket_faults.py), CLI `socket-fault`).
63. **Benchmarking de Consumo Energético y Ciclos:** Tiempo de pared multi-corrida + conteo Callgrind con modelo energético estimado (dinámico por instrucción + estático) para materias de arquitectura (✔ propuesta 12) ([`src/ripley/tools/benchmark.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/benchmark.py), CLI `benchmark`).
64. **Verificación Formal Ligera (Frama-C / ACSL):** Inventario estático de contratos `requires/ensures/assigns` adjuntos a funciones, métrica de cobertura documental y wrapper del demostrador WP cuando Frama-C está instalado (✔ propuesta 13) ([`src/ripley/tools/formal_contracts.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/formal_contracts.py), CLI `contract-check`).
65. **Verificador de Inicialización de Struct Padding (*Padding Zeroing*):** Cálculo del layout C estándar (huecos y relleno final) y alerta cuando structs con padding se envían a archivos/sockets sin `memset` previo (✔ propuesta 16) ([`src/ripley/core/padding_audit.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/padding_audit.py), CLI `padding-audit`, integrado en `evaluate` vía `[padding] enabled`).


### Módulo J: Experiencia del Estudiante y Diagnóstico Pedagógico
68. **Traductor Pedagógico de Errores de GCC a Lenguaje Natural:** ~25 reglas de diagnóstico (`expected ';'`, `undeclared`, `undefined reference`, formatos printf, linker…) con título, explicación y sugerencia; integrado en fallos de compilación de `ripley-check run` y comando `explain` ([`src/ripley/core/gcc_translator.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/gcc_translator.py), CLI `ripley-check explain`).
69. **Soporte para Makefiles Estudiantiles y Compilación Modular:** Auditoría de calidad del Makefile (objetivo `all` primero, `clean`, `.PHONY`, TABs, CC hardcodeado), build vía `make` con descubrimiento de binario y errores traducidos; se prefiere automáticamente cuando la práctica lo habilita ([`src/ripley/tools/makefile.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/makefile.py), CLI `make-audit`, check `build.makefile`).
70. **Modo Live TDD / Watch:** Vigilancia por polling sin dependencias externas: al guardar recompila con los flags oficiales de la práctica, corre los testcases públicos y muestra diagnósticos traducidos en vivo ([`src/ripley/tools/watcher.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/tools/watcher.py), CLI `ripley-check watch --practica …`).
71. **Glosario Visual Accesible de Conceptos de Bajo Nivel:** 11 conceptos con diagramas SVG puros; `role=img` con `<title>/<desc>` para lectores de pantalla, temas dark/light/**high-contrast**/colorblind-safe (Okabe-Ito), escala tipográfica ampliada y HTML semántico autocontenido sin recursos externos (✔ propuesta 23) ([`src/ripley/core/glossary.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/core/glossary.py), CLI `ripley-check glossary`).
72. **Flujo de Auditoría Docente con Estados:** Máquina de estados por entrega (ingresada → evaluada → en_revision → calificada → publicada, con derivas observada/sospechosa/apelada), transiciones validadas con override `--force` auditado y bitácora append-only (actor/nota/timestamp) en la `.metadata.db` por alumno; tablero agregado, historia completa y publicación masiva (roadmap ✔) ([`src/ripley/teacher/audit.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/teacher/audit.py), CLI `ripley audit board|transition|history|publish`).


### Módulo K: Extensibilidad y Salidas Enriquecidas
73. **Sistema de Plugins y Hooks de Ciclo de Vida:** Descubrimiento de `*.py` en `plugins/` (orden alfabético), 8 hooks de corrida (`session_start/end`, `pre/post_compile`, `pre/post_checks`, `pre/post_report`) más hook especial `pre_commit_git`; contexto mutable con hallazgos, fail-open contado o modo estricto, escape hatch `RIPLEY_DISABLE_PLUGINS`. Integrado en `ripley-check run` y compatible con git: shim ejecutable que preserva hooks previos como `.bak` y bloquea el commit si el circuito rápido detecta errores (roadmap ✔) ([`src/ripley/pipeline/plugins.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/pipeline/plugins.py), CLI `ripley-check plugins list|dispatch|git-hook`).
74. **Exportación a PDF y HTML Enriquecido:** Conversión del subconjunto Markdown de los informes Ripley a HTML estilizado autocontenido (lang=es, sin recursos externos, reglas @media print) y PDF escrito en Python puro (A4, Helvetica/Courier WinAnsi para acentos, paginación automática, tablas monoespaciadas alineadas) sin dependencias externas (roadmap ✔) ([`src/ripley/teacher/report_export.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/teacher/report_export.py), CLI `ripley export-report informe.md --format html|pdf`).

---

## 2. Propuestas de Mejora Pendientes (8)

> **Propuestas ya implementadas** (tachadas abajo) y migradas a la Sección 1: **1–19, 23, 24 y 28** — los Módulos 1, 2 y 3 del registro original están completos, más los ítems 19, 23 y 28 de los Módulos 4/5. Quedan pendientes cuatro entradas históricas del Roadmap (Sección 3): dashboard web, API REST de Moodle, multi-lenguaje y base compartida en red.

### Módulo 1: Compilación, Aislamiento y Entornos Seguros
1. ~~**Soporte para Compilación Cruzada Multi-Arquitectura (x86_64, ARM64, RISC-V con QEMU)**~~ → **Implementada** (Sección 1, ítem 56).
2. ~~**Aislamiento Basado en Espacios de Nombres Linux (Bubblewrap / Unshare)**~~ → **Implementada** (Sección 1, ítem 57).
3. ~~**Detector de Dependencia de Orden de Evaluación de Argumentos**~~ → **Implementada** (Sección 1, ítem 50).
4. ~~**Auditoría de Modificación de Cadenas Literales en `.rodata`**~~ → **Implementada** (Sección 1, ítem 51).
5. ~~**Control de Saltos Hacia Atrás con `goto`**~~ → **Implementada** (Sección 1, ítem 52).
6. ~~**Generador de Instantáneas de Toolchains Herméticas**~~ → **Implementada** (Sección 1, ítem 58).

### Módulo 2: Testing Dinámico, Rendimiento y Fuzzing Avanzado
7. ~~**Fuzzing Guiado por Cobertura (Coverage-Guided Fuzzing con LibFuzzer / AFL++)**~~ → **Implementada con feedback gcov nativo** (Sección 1, ítem 59).
8. ~~**Analizador Empírico de Complejidad Asintótica ($O(N)$ vs $O(N^2)$ Profiler)**~~ → **Implementada** (Sección 1, ítem 60).
9. ~~**Auditoría de Consumo de Stack Máximo (`-fstack-usage`)**~~ → **Implementada** (Sección 1, ítem 61).
10. ~~**Simulador de Fragmentación de Memoria Heap**~~ → **Implementada** (Sección 1, ítem 45).
11. ~~**Inyección de Fallas en Descriptores de Red y Sockets**~~ → **Implementada** (Sección 1, ítem 62).
12. ~~**Benchmarking de Consumo Energético y Ciclos de Instrucción**~~ → **Implementada (modelo estimado)** (Sección 1, ítem 63).

### Módulo 3: Análisis Semántico y Verificación Formal
13. ~~**Verificación Formal Ligera con Frama-C / ACSL**~~ → **Implementada (parser estático + wrapper WP)** (Sección 1, ítem 64).
14. ~~**Demostrador de Terminación de Bucles (*Termination Proof*)**~~ → **Implementada (heurística estática)** (Sección 1, ítem 53).
15. ~~**Auditoría de Uso de Enums como Máscaras de Bits**~~ → **Implementada** (Sección 1, ítem 54).
16. ~~**Verificador de Inicialización de Relleno de Estructuras (*Struct Padding Zeroing*)**~~ → **Implementada** (Sección 1, ítem 65).
17. ~~**Detector de Funciones Obsoletas y Desaconsejadas (Deprecated C API Linter)**~~ → **Implementada** (Sección 1, ítem 55).
18. ~~**Análisis de Efectos Secundarios en Funciones Puras (`__attribute__((pure))`)**~~ → **Implementada** (Sección 1, ítem 46).

### Módulo 4: Didáctica, Feedback Personalizado y Accesibilidad
19. ~~**Generador de Animaciones de Memoria Paso a Paso (SVG Interactivo / GIF)**~~ → **Implementada** (Sección 1, ítem 66).
20. **Recomendador de Lecturas y Ejercicios de Refuerzo:** Vincular cada error detectado con secciones específicas de la bibliografía de la materia.
21. **Modo Tutor Socrático Interactivo en Terminal (`ripley tutor`):** Asistente CLI que guía al estudiante a depurar su código mediante preguntas orientadoras sin revelar la solución.
22. **Métrica de Complejidad Cognitiva de SonarQube:** Medir la dificultad de lectura del código penalizando anidamientos profundos y estructuras intrincadas.
23. ~~**Glosario Visual de Conceptos de Bajo Nivel**~~ → **Implementada** (Sección 1, ítem 71).
24. ~~**Informes de Evolución Longitudinal del Aprendizaje**~~ → **Implementada** (Sección 1, ítem 49).

### Módulo 5: Infraestructura, Integración y Ecosistema Docente
25. **Sincronización Webhook en Tiempo Real con Moodle:** Recepción de eventos push de Moodle para evaluar entregas en menos de 10 segundos tras su envío.
26. **Exportación a Formato Estándar SARIF (OASIS SARIF):** Exportar diagnósticos para visualización en GitHub Code Scanning y GitLab SAST.
27. **Servicio Centralizado de Analítica Académica (Grafana / Prometheus):** Exponer métricas de rendimiento y errores recurrentes de toda la cursada hacia paneles de monitoreo.
28. ~~**Evaluación de Trabajos Prácticos Gráficos (SDL2 / Raylib en Framebuffer Virtual)**~~ → **Implementada** (Sección 1, ítem 67).
29. **Auditoría de Co-Autoría y Firmas Criptográficas Git:** Analizar firmas GPG/SSH e historial de commits para fiscalizar la participación equitativa en entregas grupales.
30. **Modo Evaluación Presencial con Bloqueo de Red (Exam Lockout Mode):** Configuración de entorno de examen presencial que bloquea accesos no autorizados a la red y periféricos → **Diseño aprobado para implementación**: ver [`PLAN_EXAM_LOCKOUT.md`](PLAN_EXAM_LOCKOUT.md) (4 capas: nftables etiquetado/bwrap, sesión con timer monotónico sellado, sobres `.rexam` HMAC, recolección integrada al tablero de auditoría; fases E0–E5).

---

## 3. Roadmap de Propuestas Previas Pendientes

> Ver además: [`PLAN_MODULARIZACION.md`](PLAN_MODULARIZACION.md) — **implementado**: capas models/core/tools/pipeline/teacher, CLIs separados `ripley` (docente) y `ripley-check` (estudiante), paquetes de práctica `.ripkg` firmables y zipapp cero-instalación.

- ~~Soporte para Makefiles estudiantiles y compilación modular.~~ → **Implementado** (Sección 1, ítem 69).
- Dashboard web local interactivo (`ripley serve`).
- Sincronización directa con API REST de Moodle (`ripley moodle pull/push`).
- ~~Modo Live TDD / Watch para el estudiante (`ripley watch`).~~ → **Implementado** (Sección 1, ítem 70).
- Arquitectura extensible multi-lenguaje (C++, Python, Rust, Java).
- ~~Traductor pedagógico de errores de GCC a lenguaje natural.~~ → **Implementado** (Sección 1, ítem 68).
- ~~Exportación a PDF y HTML enriquecido.~~ → **Implementado** (Sección 1, ítem 74).
- Firma criptográfica e inmutabilidad con GPG/Ed25519 → **Implementada para paquetes** (`.ripkg` firmables y verificación SHA-256 + GPG detached, ver [`src/ripley/pipeline/bundle.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/pipeline/bundle.py)); pendiente extender a informes docentes.
- ~~Sistema de plugins y hooks de ciclo de vida en `plugins/`.~~ → **Implementado** (Sección 1, ítem 73), incluye shims para git hooks.
- Base de datos compartida PostgreSQL / SQLite en red.
- ~~Flujo de trabajo con estados de auditoría docente.~~ → **Implementado** (Sección 1, ítem 72).
