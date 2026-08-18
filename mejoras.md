# Registro de Potenciales Mejoras para Ripley

Listado de 30 mejoras técnicas, arquitectónicas y pedagógicas para evolucionar la herramienta, con su estado actual de implementación.

---

### 1. Detección de Plagio y Similitud de Código (Anti-Cheating) — `[IMPLEMENTADO]`
- **Descripción:** Motor de similitud estructural basado en normalización de AST y algoritmo Winnowing ($k$-gramas y ventanas de hashing) para comparar entregas entre pares de estudiantes.
- **Ubicación:** [`src/ripley/plagiarism.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/plagiarism.py) | Comando CLI: `./ripley plagiarism --activity <slug>` y `./ripley evaluate --check-plagiarism`.
- **Pruebas:** [`tests/unit/test_plagiarism.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_plagiarism.py).

### 2. Soporte para Makefiles Estudiantiles y Compilación Modular — `[PENDIENTE]`
- **Descripción:** Detectar si el estudiante incluyó su propio `Makefile` y permitir una estrategia de compilación delegada bajo límites estrictos de sandboxing y timeout.
- **Impacto:** Permite evaluar proyectos más complejos con múltiples unidades de traducción organizadas por el alumno.

### 3. Análisis de Complejidad Ciclomática y Métricas Halstead — `[PENDIENTE]`
- **Descripción:** Integrar métricas de complejidad cognitiva y ciclomática de McCabe (mediante librerías como `lizard` o inspectores AST internos).
- **Impacto:** Permite penalizar funciones excesivamente largas, anidadas o incomprensibles en la rúbrica de estilo.

### 4. Generación Automatizada de Casos de Prueba de Borde (Fuzzing) — `[IMPLEMENTADO]`
- **Descripción:** Generador de casos de prueba con valores numéricos de borde (`INT_MAX`, `INT_MIN`, `0`, `-1`), cadenas extremas y mutación de entradas semilla, calculando salidas esperadas automáticas con la solución modelo docente.
- **Ubicación:** [`src/ripley/fuzzing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/fuzzing.py) | Comando CLI: `./ripley testcase fuzz --activity <slug> --exercise <ex>`.
- **Pruebas:** [`tests/unit/test_fuzzing.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_fuzzing.py).

### 5. Aislamiento Estricto mediante Contenedores Efímeros OCI / cgroups v2 — `[PENDIENTE]`
- **Descripción:** Ejecutar la compilación y pruebas dentro de micro-contenedores sin privilegios (usando `bubblewrap`, `cgroups v2` y namespaces de Linux, o contenedores efímeros Docker/Podman).
- **Impacto:** Garantiza aislamiento total del filesystem del host, consumo de red nulo y límites de memoria insoslayables.

### 6. Diff Semántico Basado en AST — `[IMPLEMENTADO]`
- **Descripción:** Comparación estructural de revisiones ($r_N$ vs $r_{N-1}$) que identifica altas/bajas de funciones y modificaciones lógicas discriminándolas de cambios puramente cosméticos (renombrado de variables, espaciado, comentarios).
- **Ubicación:** [`src/ripley/semantic_diff.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/semantic_diff.py) e integrado en [`src/ripley/diffing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diffing.py).
- **Pruebas:** [`tests/unit/test_semantic_diff.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_semantic_diff.py).

### 7. Auditoría de Memoria Liviana Alternativa a Valgrind — `[PENDIENTE]`
- **Descripción:** Complementar la sobrecarga de Valgrind con instrumentación dinámica liviana mediante `AddressSanitizer` + `LeakSanitizer` (`-fsanitize=address,leak`) o sondas eBPF.
- **Impacto:** Reduce drásticamente el tiempo de ejecución en lotes grandes de cientos de alumnos.

### 8. Soporte para Pruebas Unitarias Nativas en C (CUnit / Criterion / Unity) — `[PENDIENTE]`
- **Descripción:** Permitir suites de pruebas que no dependan únicamente de capturar `stdin`/`stdout`, sino que linkeen un arnés de pruebas contra funciones individuales del estudiante.
- **Impacto:** Posibilita evaluar librerías y tipos abstractos de datos (TADs) sin requerir una función `main()` por parte del alumno.

### 9. Generador de Retroalimentación Pedagógica Adaptativa con LLMs Locales — `[PENDIENTE]`
- **Descripción:** Integrar un hook configurable para enviar logs de compilación, desvíos de estilo y fallos de tests a un modelo de lenguaje (local vía `ollama` o API) para generar sugerencias didácticas personalizadas.
- **Impacto:** Brinda explicaciones conceptuales claras y adaptadas al nivel de un alumno de Programación I.

### 10. Dashboard Web Local Interactivo (FastAPI + React/Vite) — `[PENDIENTE]`
- **Descripción:** Agregar el comando `ripley serve` para levantar una interfaz web local de visualización, filtrado por estados, comparación de diffs lado a lado y ajuste manual de notas.
- **Impacto:** Agiliza la revisión y auditoría docente frente a la visualización estática de Markdown y terminal.

### 11. Sincronización Directa con la API REST de Moodle — `[PENDIENTE]`
- **Descripción:** Implementar subcomandos `ripley moodle pull` y `ripley moodle push` utilizando los webservices de Moodle con tokens de docente.
- **Impacto:** Elimina la necesidad de descargar y subir manualmente archivos ZIP o planillas CSV al aula virtual.

### 12. Modo Watch / Live TDD para Uso del Estudiante — `[PENDIENTE]`
- **Descripción:** Permitir la ejecución de `ripley watch` en el directorio de trabajo para reejecutar pruebas y verificaciones de estilo cada vez que se guarda un archivo `.c`.
- **Impacto:** Transforma a Ripley en un arnés de desarrollo y autoevaluación para los alumnos antes de entregar.

### 13. Arquitectura Extensible Multi-Lenguaje (C++, Python, Rust, Java) — `[PENDIENTE]`
- **Descripción:** Desacoplar los evaluadores de C en adaptadores modulares para soportar otros lenguajes de programación comunes en la carrera.
- **Impacto:** Reutilización de la infraestructura de Ripley en materias correlativas (Algoritmos y Estructuras de Datos, POO).

### 14. Diagnóstico Especializado de Stack Overflow y Recursión Infinita — `[IMPLEMENTADO]`
- **Descripción:** Diagnóstico específico que diferencia fallos de segmentación por recursión sin caso base / desbordamiento de stack frente a desreferencias nulas estándar, suministrando explicaciones didácticas orientadas a estudiantes.
- **Ubicación:** [`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py).
- **Pruebas:** [`tests/unit/test_diagnostics.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_diagnostics.py).

### 15. Traductor Pedagógico de Errores de GCC — `[PENDIENTE]`
- **Descripción:** Parsear las advertencias y errores crípticos del compilador (`-Wall`, `-Wextra`, `-pedantic`) y traducirlos a explicaciones en español claro con ejemplos didácticos.
- **Impacto:** Disminuye la frustración de alumnos iniciales ante mensajes técnicos del compilador.

### 16. Verificación de Restricciones del Enunciado (Blacklist/Whitelist de AST) — `[IMPLEMENTADO]`
- **Descripción:** Validador que fiscaliza consignas pedagógicas como prohibición de estructuras (`for`, `while`, `do`, `goto`), cabeceras no autorizadas (`<string.h>`), funciones vetadas (`qsort`, `strcpy`), o exigencia obligatoria de recursión, `struct` o memoria dinámica.
- **Ubicación:** [`src/ripley/restrictions.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/restrictions.py).
- **Pruebas:** [`tests/unit/test_restrictions.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_restrictions.py).

### 17. Medición de Cobertura de Código de los Testcases (gcov / lcov) — `[PENDIENTE]`
- **Descripción:** Instrumentar el código con `--coverage` para determinar qué porcentaje de las ramas y líneas del código del alumno fue ejecutado por los casos de prueba docentes.
- **Impacto:** Identifica casos de prueba insuficientes o código muerto dentro de la solución del estudiante.

### 18. Benchmarking y Análisis de Complejidad Temporal Empírica — `[PENDIENTE]`
- **Descripción:** Ejecutar binarios con entradas escalonadas de tamaño $N$ para estimar la cota de complejidad temporal ($O(N)$, $O(N \log N)$, $O(N^2)$).
- **Impacto:** Permite evaluar la eficiencia algorítmica y detectar soluciones que excedan la complejidad esperada.

### 19. Exportación a PDF y HTML Enriquecido — `[PENDIENTE]`
- **Descripción:** Incorporar un conversor de Markdown a documentos PDF y HTML autocontenidos con soporte para tipografía cuidada y resaltado de sintaxis.
- **Impacto:** Facilita la impresión de actas o el envío directo de retroalimentación por correo electrónico.

### 20. Firma Criptográfica e Inmutabilidad de Evaluaciones — `[PENDIENTE]`
- **Descripción:** Firmar digitalmente los reportes y hashes de cada versión $r_N$ mediante claves GPG/Ed25519 del docente.
- **Impacto:** Garantiza la integridad inalterable de las calificaciones y fechas ante reclamos académicos.

### 21. Sistema de Plugins y Hooks de Ciclo de Vida — `[PENDIENTE]`
- **Descripción:** Proveer puntos de extensión (`pre_ingest`, `post_compile`, `custom_linter`, `post_evaluate`) cargados dinámicamente desde un directorio `plugins/`.
- **Impacto:** Permite a cada cátedra inyectar reglas y comprobaciones a medida sin modificar el núcleo de Ripley.

### 22. Base de Datos Centralizada para Trabajo en Equipo Docente — `[PENDIENTE]`
- **Descripción:** Soportar motores PostgreSQL o SQLite compartida mediante red para que varios ayudantes califiquen y agreguen observaciones concurrentemente.
- **Impacto:** Escalabilidad en materias masivas con comisiones de cientos de estudiantes.

### 23. Comparación Flexible de Salidas (Regex y Normalización Fuzzy) — `[IMPLEMENTADO]`
- **Descripción:** Soporte para directivas `REGEX:` en archivos `.out` de testcases y normalización fuzzy (tolerancia a diferencias de mayúsculas/minúsculas, signos de puntuación y espaciado).
- **Ubicación:** [`src/ripley/runner.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/runner.py).
- **Pruebas:** [`tests/unit/test_runner.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_runner.py).

### 24. Detección Estricta de Punteros Colgantes (*Dangling Pointers*) — `[IMPLEMENTADO]`
- **Descripción:** Detección dinámica de eventos *Use-After-Free* y *Double Free*, complementada con análisis estático de reuso de punteros tras `free(ptr)`.
- **Ubicación:** [`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py).
- **Pruebas:** [`tests/unit/test_diagnostics.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_diagnostics.py).

### 25. Soporte para Entregas Grupales y Co-autoría — `[PENDIENTE]`
- **Descripción:** Permitir la vinculación de múltiples alumnos a un único repositorio/entrega con replicación automática de notas en la planilla Moodle.
- **Impacto:** Soporta trabajos prácticos integradores grupales sin pasos manuales.

### 26. Flujo de Trabajo con Estados de Auditoría Docente — `[PENDIENTE]`
- **Descripción:** Implementar un ciclo de vida con estados explícitos (`Ingestado`, `Auto-Evaluado`, `Revisión Manual Pendiente`, `Aprobado`, `Publicado`).
- **Impacto:** Otorga visibilidad del progreso de corrección del equipo docente.

### 27. Detección de Bloqueos en Stdin (I/O Deadlocks) — `[IMPLEMENTADO]`
- **Descripción:** Diagnóstico pedagógico que discrimina bloqueos por lecturas incompletas en `stdin` (`scanf`/`getchar` esperando más datos de los provistos) frente a bucles infinitos de CPU.
- **Ubicación:** [`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py).
- **Pruebas:** [`tests/unit/test_diagnostics.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_diagnostics.py).

### 28. Validador de Consistencia Docente y Gestión de Prácticas — `[IMPLEMENTADO]`
- **Descripción:** Estructuración y generación automática de prácticas en `./practicas/<slug_practica>/` con enunciados, pautas pedagógicas, soluciones modelo docentes y sincronización de testcases.
- **Ubicación:** [`src/ripley/practice.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/practice.py) | Comando CLI: `./ripley practice init`, `./ripley practice list`, `./ripley practice sync`.
- **Pruebas:** [`tests/unit/test_practice.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_practice.py).

### 29. Métricas Longitudinales de Aprendizaje y Evolución — `[PENDIENTE]`
- **Descripción:** Computar la tasa de corrección de errores entre versiones consecutivas ($r_1 \to r_2 \to r_3$) y generar gráficos de persistencia de fallas en la cohorte.
- **Impacto:** Brinda datos analíticos a los profesores sobre los conceptos que presentan mayor dificultad pedagógica.

### 30. Soporte para Pruebas con Pseudo-Terminales (PTY / Expect) — `[PENDIENTE]`
- **Descripción:** Ejecutar programas que requieren interacción en tiempo real mediante terminales virtuales PTY (ej. menús interactivos o lectura carácter a carácter con `termios`).
- **Impacto:** Permite evaluar ejercicios de interacción continua y juegos de consola en C.
