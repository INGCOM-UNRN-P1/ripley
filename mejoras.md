# Ripley - Registro Modular de Funcionalidades y Mejoras

> **Última revisión:** 2026-08-23 — `149/149` tests pasando al 100% (`pytest`, suite unitaria + integración).

---

## 1. Funcionalidades Implementadas (65)

Las funcionalidades se encuentran modularizadas e implementadas con suites de pruebas unitarias e integradas (`102/102` tests pasando al 100%):


### Módulo A: Ingesta, Persistencia y Gestión de Prácticas
1. **Detección de Plagio y Similitud de Código (Anti-Cheating):** Algoritmo Winnowing con tokenización AST de C ($k$-gramas y ventanas deslizantes) y cálculo de similitud Jaccard ([`src/ripley/plagiarism.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/plagiarism.py)).
2. **Inicialización y Gestión Integral de Prácticas:** Estructuración automática de consignas, pautas docentes, rúbricas y casos de prueba en `./practicas/<slug>/` ([`src/ripley/practice.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/practice.py)).
3. **Mapeo Interactivo de Ejercicios y Testcases:** Vinculación interactiva y heurística de fuentes `.c` con previsualización de código y asignación de roles `[AUXILIAR]` o `[IGNORAR]` ([`src/ripley/mapping.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/mapping.py)).
4. **Ingesta Determinista y Normalización UTF-8:** Aplanamiento de carpetas ZIP de Moodle, filtro de extensiones y hashing SHA-256 ([`src/ripley/ingest.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ingest.py)).
5. **Persistencia de Estado Local en SQLite:** Base de datos relacional para seguimiento de entregas, reentregas y notas acumulativas ([`src/ripley/db.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/db.py)).
6. **Gestor y Validador de Plantillas Jinja2:** Instanciación y verificación de plantillas de informe con variables `snake_case` ([`src/ripley/templates.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/templates.py)).

### Módulo B: Diagnósticos de Ejecución y Sanitizadores de Bajo Nivel
7. **Diagnóstico Especializado de Stack Overflow y Recursión Infinita:** Detección de agotamiento de pila con recomendaciones didácticas ([`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py)).
8. **Detección de Bloqueos en Stdin (I/O Deadlocks):** Detección de procesos colgados esperando entradas por teclado no provistas por el testcase ([`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py)).
9. **Detección Estricta de Punteros Colgantes (*Dangling Pointers*):** Captura dinámica de *Use-After-Free* y *Double Free*, y análisis estático post-`free()` ([`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py)).
10. **Detección de Desbordamientos de Enteros (UBSan):** Reporte de *signed integer overflow*, división por cero y shifts inválidos ([`src/ripley/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/sanitizers.py)).
11. **Análisis de Variables no Asignadas:** Reporte de lectura de variables locales no inicializadas en el stack ([`src/ripley/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/sanitizers.py)).
12. **Detección de Conversiones Implícitas Peligrosas (*Sign Conversion*):** Captura de advertencias de cambio de signo o truncamiento entre `int` y `size_t` ([`src/ripley/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/sanitizers.py)).
13. **Detección de Desalineación de Memoria (*Unaligned Access*):** Captura de accesos a direcciones no alineadas a los múltiplos del tipo en la CPU ([`src/ripley/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/sanitizers.py)).
14. **Detección de Bucles Infinitos por Contador de Instrucciones CPU:** Medición determinista de instrucciones ejecutadas con Callgrind ([`src/ripley/instruction_counter.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/instruction_counter.py)).
15. **Tolerancia Diferenciada de Fugas de Memoria ante Salidas Anormales:** Tolerancia pedagógica para fugas previas a `exit(EXIT_FAILURE)` ([`src/ripley/runner.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/runner.py)).
16. **Emulación de Memoria Restringida para Sistemas Embebidos:** Ejecución bajo límites estrictos de heap/stack (`RLIMIT_AS` y `RLIMIT_DATA`) ([`src/ripley/embedded.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/embedded.py)).

### Módulo C: Linters de Calidad, AST y Buenas Prácticas
17. **Verificación de Restricciones del Enunciado (Blacklist/Whitelist AST):** Control de palabras clave prohibidas (`goto`, `while`, `<string.h>`) o requeridas (`struct`, `malloc`) ([`src/ripley/restrictions.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/restrictions.py)).
18. **Detector de Números Mágicos:** Alerta sobre literales numéricos sin nombre fuera de `#define`/`enum` ([`src/ripley/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/linters.py)).
19. **Detector de Duplicación Interna de Código (Copy-Paste Detector):** Detección de bloques de tokens duplicados dentro de la misma entrega ([`src/ripley/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/linters.py)).
20. **Linter de Convenciones de Nombres Configurable:** Validación de nomenclatura para variables, funciones (`snake_case`), constantes (`UPPER_CASE`) y tipos (`t_nodo`) ([`src/ripley/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/linters.py)).
21. **Detección de Código Muerto y Funciones Jamás Invocadas:** Identificación de funciones inalcanzables desde `main()` y código posterior a `return`/`exit()` ([`src/ripley/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/linters.py)).
22. **Detección de Comparaciones Peligrosas en Punto Flotante:** Alerta de comparaciones directas `==` o `!=` en `float`/`double` ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
23. **Detección de Inclusiones Innecesarias (*IWYU*):** Identificación de cabeceras `#include` cuyos tipos y funciones no se usan ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
24. **Auditoría de Calificación `const` en Parámetros (*Const-Correctness*):** Validación de parámetros puntero de solo lectura ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
25. **Detección de Cortocircuitos Peligrosos con Efectos Colaterales:** Alerta de `++`, `--` o asignaciones dentro de `&&` o `||` ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
26. **Verificación de Liberación de Estructuras Anidadas (*Deep Free*):** Control de liberación de campos dinámicos antes de `free(nodo)` ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
27. **Auditoría de Punteros Nulos en `<string.h>`:** Fiscalización de llamadas a `strlen`/`strcmp`/`strcpy` sin validación previa contra `NULL` ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
28. **Detección de Sombras de Variables (*Variable Shadowing*):** Alerta cuando una variable local oculta a un parámetro de la función ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
29. **Detección de Retorno de Direcciones del Stack (*Dangling Stack Pointer*):** Detección de `return &var_local;` (severidad `ERROR`) ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
30. **Detector de Sobre-Ingeniería:** Alerta sobre trucos de intercambio XOR y ternarios triplemente anidados ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
31. **Auditoría de Documentación Doxygen:** Verificación de bloques `@brief`, `@param` y `@return` en funciones ([`src/ripley/doxygen.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/doxygen.py)).

### Módulo D: Visualización, Diff Semántico y Testing Avanzado
32. **Diagramas de Flujo Tradicionales (ISO/ANSI 5807):** Generación de diagramas con óvalos, paralelogramos, rombos y rectángulos en Mermaid y DOT ([`src/ripley/flowchart.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/flowchart.py)).
33. **Árboles de Llamadas (Call Graphs):** Extracción de relaciones entre funciones, recursiones y bibliotecas estándar ([`src/ripley/callgraph.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/callgraph.py)).
34. **Visualizador Gráfico de Estructuras Dinámicas en Memoria:** Representación de topología de nodos y enlaces en DOT y Mermaid ([`src/ripley/memory_visualizer.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/memory_visualizer.py)).
35. **Testing Basado en Propiedades (Property-Based Testing en C):** Validación automática de invariantes formales (idempotencia, conmutatividad, multiconjunto ordenado) ([`src/ripley/property_testing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/property_testing.py)).

### Módulo E: Compilación, Estilo, Seguridad e Infraestructura de Análisis
36. **Compilación Segura con Sanitizadores y Fallback:** GCC con `-fsanitize=address,undefined`, límites `RLIMIT_CPU`/`RLIMIT_FSIZE` y reintento automático ante falta de `libasan` ([`src/ripley/compiler.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/compiler.py)).
37. **Análisis de Estilo y Formato Configurable:** Verificación de llaves (Allman/K&R), indentación, espaciado de operadores/keywords y líneas en blanco según `ripley.toml` ([`src/ripley/style.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/style.py)).
38. **Escáner Preventivo de Vulnerabilidades en C:** Detección de patrones inseguros (`gets`, `sprintf`, desbordes de buffer) sobre fuente pre-limpia de comentarios y literales ([`src/ripley/security.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/security.py)).
39. **Gestor Integral de Casos de Prueba:** Generación de esqueletos `.in/.out/.argv`, listado, verificación de integridad y descubrimiento por ejercicio ([`src/ripley/testcases.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/testcases.py)).
40. **Reglas Didácticas del Seminario Programación I:** Fiscalización específica del apunte P1 (declaraciones múltiples, VLA, variables cortas, asignaciones en condiciones) ([`src/ripley/p1_rules.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/p1_rules.py)).
41. **Runner Dinámico con Diagnóstico Didáctico:** Ejecución de casos I/O con argumentos CLI, timeouts y clasificación pedagógica de fallos ([`src/ripley/runner.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/runner.py)).

### Módulo F: Diffing, Fuzzing, Simulación y Exportación
42. **Diff Unificado entre Reentregas:** Comparación incremental de fuentes normalizadas para informes de evolución ([`src/ripley/diffing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diffing.py)).
43. **Diff Semántico basado en AST de C:** Extracción de firmas y cuerpos de funciones para comparar cambios estructurales entre versiones ([`src/ripley/semantic_diff.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/semantic_diff.py)).
44. **Fuzzing Automático de Entradas y Edge Cases:** Mutación aleatoria controlada de entradas para descubrir crashes no cubiertos por testcases fijos ([`src/ripley/fuzzing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/fuzzing.py)).
45. **Simulador de Fragmentación de Memoria Heap:** Simulación de patrones malloc/free con cálculo de fragmentación externa e internal (✔ propuesta 10 del registro anterior) ([`src/ripley/heap_simulator.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/heap_simulator.py), CLI `heap-simulate`).
46. **Auditoría de Funciones Puras y `const`:** Validación de `__attribute__((pure))`/`((const))` contra efectos secundarios reales, verificada por compilación (✔ propuesta 18) ([`src/ripley/pure_functions.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/pure_functions.py), CLI `pure-audit`).
47. **Generador de Mocks y Stubs para Unit Testing en C:** Creación de harness con sustitutos de funciones dependientes a partir del AST ([`src/ripley/mocks.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/mocks.py), CLI `mock generate`).
48. **Exportación de Notas y Feedback a Moodle:** CSV compatible con importación masiva más paquete ZIP de retroalimentación individual desde la base SQLite ([`src/ripley/exporter.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/exporter.py), CLI `export`).
49. **Dashboard de Cohorte y Evolución Longitudinal:** Métricas agregadas por actividad y alumno (notas, intentos, errores recurrentes) generadas como cuadro de mando (✔ propuesta 24) ([`src/ripley/exporter.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/exporter.py), CLI `export`).

### Módulo G: Auditores Semánticos Avanzados (AST)
50. **Detector de Dependencia de Orden de Evaluación de Argumentos:** Captura `f(i++, i++)` y llamadas múltiples con posibles efectos (`f(g(), h())`) vía whitelist de funciones puras (✔ propuesta 3) ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
51. **Auditoría de Modificación de Cadenas Literales en `.rodata`:** Escrituras directas, familia completa strcpy/str…/memcpy/memset y aliases del puntero; documenta el trap en runtime y `-Wwrite-strings` (✔ propuesta 4) ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
52. **Control de Saltos Hacia Atrás con `goto`:** Penalización de saltos regresivos que emulan bucles desestructurados (✔ propuesta 5) ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
53. **Demostrador Heurístico de Terminación de Bucles:** Variables de condición sin mutar en cuerpo/incremento de `while`, `do-while` y `for` (incluye `for (;;)`); advertencia de bucle infinito (✔ propuesta 14) ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
54. **Auditoría de Enums como Máscaras de Bits:** Detecta operadores `&`, `|`, `^`, `~` sobre enumeradores que no son potencias de dos (✔ propuesta 15) ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).
55. **Detector de Funciones Obsoletas y Desaconsejadas (Deprecated C API):** Alerta sobre `gets`, `strcpy`, `sprintf`, `strtok`, `atoi`, `asctime`, etc., con reemplazos seguros sugeridos (✔ propuesta 17) ([`src/ripley/ast_auditors.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/ast_auditors.py)).

### Módulo H: Entornos Seguros, Rendimiento y Verificación Formal
56. **Compilación Cruzada Multi-Arquitectura (QEMU):** Matriz x86_64 (nativo), ARM64, RISC-V y MIPS big-endian con comparación de salidas contra el nativo; degrada con mensaje si falta toolchain (✔ propuesta 1) ([`src/ripley/cross_arch.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/cross_arch.py), CLI `cross-test`).
57. **Aislamiento con Espacios de Nombres Linux:** Ejecución sin root vía bubblewrap (`--unshare-all`) o `unshare --user` con detección por sondeo y fallback reportado (✔ propuesta 2) ([`src/ripley/sandbox.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/sandbox.py), CLI `sandbox-test`).
58. **Instantáneas de Toolchains Herméticas:** Captura y verificación JSON de versiones de GCC, target, libc, kernel y hash de flags para reproducibilidad temporal (✔ propuesta 6) ([`src/ripley/toolchain.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/toolchain.py), CLI `toolchain-snapshot --verify`).
59. **Fuzzing Guiado por Cobertura (gcov):** Compila con `--coverage`, muta entradas y prioriza las que descubren líneas nuevas; detecta crashes y arma corpus incremental sin requerir AFL++/LibFuzzer (✔ propuesta 7) ([`src/ripley/coverage_fuzzing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/coverage_fuzzing.py), CLI `coverage-fuzz`).
60. **Analizador Empírico de Complejidad Asintótica:** Perfila tiempos con $N$ creciente y clasifica O(1)/O(√N)/O(N)/O(N log N)/O(N²)/O(N³) mediante regresión log-log con $R^2$ (✔ propuesta 8) ([`src/ripley/complexity_profiler.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/complexity_profiler.py), CLI `complexity-profile`).
61. **Auditoría de Consumo de Stack Máximo (`-fstack-usage`):** Parseo de archivos `.su` con umbral configurable y flag de asignaciones dinámicas (VLA/alloca) (✔ propuesta 9) ([`src/ripley/stack_usage.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/stack_usage.py), CLI `stack-audit`).
62. **Inyección de Fallas en Sockets (LD_PRELOAD):** Shim C generado en runtime que interpone `socket/connect/send/recv/close`, inyecta `ECONNRESET` a partir de la N-ésima operación y audita fugas de descriptores (✔ propuesta 11) ([`src/ripley/socket_faults.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/socket_faults.py), CLI `socket-fault`).
63. **Benchmarking de Consumo Energético y Ciclos:** Tiempo de pared multi-corrida + conteo Callgrind con modelo energético estimado (dinámico por instrucción + estático) para materias de arquitectura (✔ propuesta 12) ([`src/ripley/benchmark.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/benchmark.py), CLI `benchmark`).
64. **Verificación Formal Ligera (Frama-C / ACSL):** Inventario estático de contratos `requires/ensures/assigns` adjuntos a funciones, métrica de cobertura documental y wrapper del demostrador WP cuando Frama-C está instalado (✔ propuesta 13) ([`src/ripley/formal_contracts.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/formal_contracts.py), CLI `contract-check`).
65. **Verificador de Inicialización de Struct Padding (*Padding Zeroing*):** Cálculo del layout C estándar (huecos y relleno final) y alerta cuando structs con padding se envían a archivos/sockets sin `memset` previo (✔ propuesta 16) ([`src/ripley/padding_audit.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/padding_audit.py), CLI `padding-audit`, integrado en `evaluate` vía `[padding] enabled`).

---

## 2. Propuestas de Mejora Pendientes (11)

> **Propuestas ya implementadas** y migradas a la Sección 1: **1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 24** (ítems 56-65, 50-52, 45, 53-55, 46 y 49 respectivamente). Los Módulos 1, 2 y 3 del registro original están completados.

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
19. **Generador de Animaciones de Memoria Paso a Paso (SVG Interactivo / GIF):** Crear representaciones animadas del estado de memoria (Stack, Heap, Punteros) durante la ejecución de casos fallidos.
20. **Recomendador de Lecturas y Ejercicios de Refuerzo:** Vincular cada error detectado con secciones específicas de la bibliografía de la materia.
21. **Modo Tutor Socrático Interactivo en Terminal (`ripley tutor`):** Asistente CLI que guía al estudiante a depurar su código mediante preguntas orientadoras sin revelar la solución.
22. **Métrica de Complejidad Cognitiva de SonarQube:** Medir la dificultad de lectura del código penalizando anidamientos profundos y estructuras intrincadas.
23. **Glosario Visual de Conceptos de Bajo Nivel:** Recursos gráficos y diagramas explicativos adaptados para estudiantes con necesidades de accesibilidad.
24. ~~**Informes de Evolución Longitudinal del Aprendizaje**~~ → **Implementada** (Sección 1, ítem 49).

### Módulo 5: Infraestructura, Integración y Ecosistema Docente
25. **Sincronización Webhook en Tiempo Real con Moodle:** Recepción de eventos push de Moodle para evaluar entregas en menos de 10 segundos tras su envío.
26. **Exportación a Formato Estándar SARIF (OASIS SARIF):** Exportar diagnósticos para visualización en GitHub Code Scanning y GitLab SAST.
27. **Servicio Centralizado de Analítica Académica (Grafana / Prometheus):** Exponer métricas de rendimiento y errores recurrentes de toda la cursada hacia paneles de monitoreo.
28. **Evaluación de Trabajos Prácticos Gráficos (SDL2 / Raylib en Framebuffer Virtual):** Ejecutar prácticas multimedia con `Xvfb` y comparar capturas de pantalla de la ventana contra salidas esperadas.
29. **Auditoría de Co-Autoría y Firmas Criptográficas Git:** Analizar firmas GPG/SSH e historial de commits para fiscalizar la participación equitativa en entregas grupales.
30. **Modo Evaluación Presencial con Bloqueo de Red (Exam Lockout Mode):** Configuración de entorno de examen presencial que bloquea accesos no autorizados a la red y periféricos.

---

## 3. Roadmap de Propuestas Previas Pendientes

> Ver además: [`PLAN_MODULARIZACION.md`](PLAN_MODULARIZACION.md) — **implementado**: capas models/core/tools/pipeline/teacher, CLIs separados `ripley` (docente) y `ripley-check` (estudiante), paquetes de práctica `.ripkg` firmables y zipapp cero-instalación.

- Soporte para Makefiles estudiantiles y compilación modular.
- Dashboard web local interactivo (`ripley serve`).
- Sincronización directa con API REST de Moodle (`ripley moodle pull/push`).
- Modo Live TDD / Watch para el estudiante (`ripley watch`).
- Arquitectura extensible multi-lenguaje (C++, Python, Rust, Java).
- Traductor pedagógico de errores de GCC a lenguaje natural.
- Exportación a PDF y HTML enriquecido.
- Firma criptográfica e inmutabilidad con GPG/Ed25519.
- Sistema de plugins y hooks de ciclo de vida en `plugins/`.
- Base de datos compartida PostgreSQL / SQLite en red.
- Flujo de trabajo con estados de auditoría docente.
