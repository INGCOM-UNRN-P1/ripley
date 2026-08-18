# Ripley - Registro de Funcionalidades y Mejoras

---

## 1. Funcionalidades Implementadas (9)

Las siguientes funcionalidades ya fueron desarrolladas, integradas al evaluador/CLI y validadas con suites de pruebas unitarias e integradas:

1. **Detección de Plagio y Similitud de Código (Anti-Cheating)**
   - *Detalle:* Normalización de tokens AST, algoritmo Winnowing ($k$-gramas y ventanas deslizantes) y cálculo de similitud Jaccard entre pares de entregas de la cohorte.
   - *Ubicación:* [`src/ripley/plagiarism.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/plagiarism.py) | CLI: `./ripley plagiarism`, `./ripley evaluate --check-plagiarism`.
   - *Tests:* [`tests/unit/test_plagiarism.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_plagiarism.py).

2. **Generación Automatizada de Casos de Prueba de Borde (Fuzzing)**
   - *Detalle:* Generador de casos extremos numéricos (`INT_MAX`, `INT_MIN`, `0`), cadenas límite y mutaciones, calculando salidas esperadas automáticas con la solución modelo docente.
   - *Ubicación:* [`src/ripley/fuzzing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/fuzzing.py) | CLI: `./ripley testcase fuzz`.
   - *Tests:* [`tests/unit/test_fuzzing.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_fuzzing.py).

3. **Diff Semántico Basado en AST**
   - *Detalle:* Extracción y comparación estructural de funciones C ($r_N$ vs $r_{N-1}$), discriminando altas, bajas y cambios lógicos de modificaciones puramente cosméticas.
   - *Ubicación:* [`src/ripley/semantic_diff.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/semantic_diff.py) y [`src/ripley/diffing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diffing.py).
   - *Tests:* [`tests/unit/test_semantic_diff.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_semantic_diff.py).

4. **Diagnóstico Especializado de Stack Overflow y Recursión Infinita**
   - *Detalle:* Identificación dinámica de agotamiento de stack y recursión sin caso base con sugerencias didácticas adaptativas.
   - *Ubicación:* [`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py).
   - *Tests:* [`tests/unit/test_diagnostics.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_diagnostics.py).

5. **Verificación de Restricciones del Enunciado (Blacklist/Whitelist de AST)**
   - *Detalle:* Fiscalización de estructuras prohibidas (`for`, `while`, `goto`), librerías vetadas (`<string.h>`), funciones no autorizadas (`qsort`), o exigencia obligatoria de recursión, `struct` o `malloc`.
   - *Ubicación:* [`src/ripley/restrictions.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/restrictions.py).
   - *Tests:* [`tests/unit/test_restrictions.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_restrictions.py).

6. **Comparación Flexible de Salidas (Regex y Normalización Fuzzy)**
   - *Detalle:* Directivas `REGEX:` en archivos `.out` y tolerancia fuzzy a diferencias de mayúsculas/minúsculas, signos de puntuación y espaciado redundante.
   - *Ubicación:* [`src/ripley/runner.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/runner.py).
   - *Tests:* [`tests/unit/test_runner.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_runner.py).

7. **Detección Estricta de Punteros Colgantes (*Dangling Pointers*)**
   - *Detalle:* Captura dinámica de eventos *Use-After-Free* y *Double Free*, junto a análisis estático de reuso de punteros tras `free()`.
   - *Ubicación:* [`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py).
   - *Tests:* [`tests/unit/test_diagnostics.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_diagnostics.py).

8. **Detección de Bloqueos en Stdin (I/O Deadlocks)**
   - *Detalle:* Detección de procesos colgados esperando más datos por teclado (`scanf`/`getchar`/`fgets`) de los provistos por el caso de prueba.
   - *Ubicación:* [`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py).
   - *Tests:* [`tests/unit/test_diagnostics.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_diagnostics.py).

9. **Inicialización y Gestión Integral de Prácticas**
   - *Detalle:* Estructuración automática de consignas, pautas docentes, rúbricas, soluciones modelo y casos de prueba en `./practicas/<slug_practica>/`.
   - *Ubicación:* [`src/ripley/practice.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/practice.py) | CLI: `./ripley practice init`, `./ripley practice list`, `./ripley practice sync`.
   - *Tests:* [`tests/unit/test_practice.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_practice.py).

---

## 2. 30 Nuevas Propuestas de Mejora

### 1. Auditoría de Concurrencia y Detección de Data Races con ThreadSanitizer (TSan)
- **Descripción:** Integrar compilación y ejecución con `-fsanitize=thread` en ejercicios de hilos (`pthreads`), detectando condiciones de carrera y deadlocks entre mutexes.
- **Impacto:** Permite evaluar trabajos prácticos de concurrencia y sincronización en materias avanzadas.

### 2. Inyección de Fallas en Memoria Dinámica (*Fault-Injection Malloc*)
- **Descripción:** Simular fallos forzados de `malloc()` (haciendo que retorne `NULL` en el $k$-ésimo intento) mediante interposición de librerías (`LD_PRELOAD`).
- **Impacto:** Verifica si el estudiante programó el manejo robusto de errores ante falta de memoria o si asume que `malloc` siempre tiene éxito.

### 3. Detección de Fugas de Descriptores de Archivos (`FILE *` y `fopen`/`fclose` Leaks)
- **Descripción:** Auditar que todos los archivos abiertos con `fopen()` sean cerrados con `fclose()` antes del retorno de la función o finalización del programa.
- **Impacto:** Evita agotamiento de file descriptors en ejercicios de persistencia y manejo de archivos en C.

### 4. Sistema de Pistas Progresivas (*Progressive Hints*)
- **Descripción:** Generar pistas pedagógicas graduadas cuando el alumno falla consecutivamente un caso de prueba (Nivel 1: Concepto teórico, Nivel 2: Caso análogo simplificado, Nivel 3: Traza paso a paso).
- **Impacto:** Guía al estudiante sin revelar la solución directa.

### 5. Generación de Diagramas de Flujo y Callgraphs (Graphviz/DOT)
- **Descripción:** Crear automáticamente representaciones visuales del grafo de llamadas de las funciones del alumno para incrustar en los reportes Markdown.
- **Impacto:** Facilita la comprensión de la arquitectura del código entregado.

### 6. Auditoría de Conmutación de Compiladores (Clang vs GCC Cross-Check)
- **Descripción:** Compilar el código simultáneamente con GCC y Clang bajo `-Wall -Wextra -Werror` para validar estricta portabilidad y conformidad con ISO C11/C17.
- **Impacto:** Detecta comportamientos no estándar o dependientes de extensiones específicas del compilador.

### 7. Integración con Git y GitHub Classroom / GitLab CI
- **Descripción:** Subcomandos `ripley git clone-all` y `ripley git push-feedback` para gestionar actividades basadas en repositorios Git remotos.
- **Impacto:** Amplía el alcance de Ripley más allá de los archivos ZIP descargados de Moodle.

### 8. Detección de Desbordamientos de Enteros con UBSan (`-fsanitize=undefined`)
- **Descripción:** Instrumentar binarios con el UndefinedBehaviorSanitizer para reportar desbordamientos aritméticos con signo, corrimientos de bits inválidos y división por cero.
- **Impacto:** Identifica bugs sutiles de comportamiento indefinido que pasan desapercibidos en ejecuciones estándar.

### 9. Análisis de Inicialización de Variables no Asignadas (MemorySanitizer / GCC Warnings)
- **Descripción:** Reportar con precisión de línea el uso de variables locales no inicializadas antes de su primera lectura.
- **Impacto:** Previene lectura de datos basura en la memoria del stack.

### 10. Detección de Números Mágicos y Constantes Literales sin Nombre
- **Descripción:** Regla de análisis estático que penaliza el uso de literales numéricos directos en el cuerpo de las funciones en lugar de `#define` o `enum`.
- **Impacto:** Refuerza buenas prácticas de legibilidad y mantenibilidad del código.

### 11. Testing Basado en Propiedades (*Property-Based Testing* en C)
- **Descripción:** Generar automáticamente miles de combinaciones de entradas para validar invariantes lógicas formales (ej. `ordenar(A)` preserva los mismos elementos y los deja en orden no decreciente).
- **Impacto:** Descubre casos de falla que los testcases manuales no contemplan.

### 12. Detección de Duplicación Interna de Código (*Copy-Paste Detector*)
- **Descripción:** Alertar al estudiante si duplicó bloques idénticos o cuasi-idénticos de más de 8 líneas en distintas partes de su entrega.
- **Impacto:** Fomenta la modularización y reutilización de código en funciones auxiliares.

### 13. Interfaz de Terminal Interactiva (TUI con Textual)
- **Descripción:** Subcomando `ripley tui` con explorador de archivos, visualizador interactivo de diffs y panel de notas en consola.
- **Impacto:** Experiencia fluida para el docente que prefiere trabajar 100% en la terminal.

### 14. Modo de Evaluación Ciega / Anónima (*Blind Grading*)
- **Descripción:** Enmascarar nombres, correos y legajos de los estudiantes por identificadores aleatorios durante la revisión docente.
- **Impacto:** Elimina sesgos inconscientes en la corrección manual.

### 15. Sistema de Anotaciones Docentes en Línea
- **Descripción:** Permitir insertar comentarios docentes en líneas específicas del código mediante directivas Markdown (`<!-- feedback: ... -->`) que se preservan entre reevaluaciones.
- **Impacto:** Combina corrección automática con observaciones pedagógicas manuales.

### 16. Linter de Convenciones de Nombres Configurable
- **Descripción:** Fiscalizar el estilo de nomenclatura requerido (snake_case, camelCase, prefijos para tipos como `t_nodo` o constantes en `MAYUSCULAS`).
- **Impacto:** Asegura coherencia estilística en toda la cohorte.

### 17. Simulación de Entrada Lenta (*Rate-Limited Stdin Stream*)
- **Descripción:** Alimentar la entrada estándar con pausas byte a byte para auditar que los buffers de lectura del alumno manejen fragmentación de paquetes.
- **Impacto:** Valida el manejo correcto de `fgets` y buffers en programas de comunicación.

### 18. Detección de Vulnerabilidades de Formato en Funciones `printf` / `scanf`
- **Descripción:** Auditar llamadas inseguras como `printf(cadena_usuario)` en lugar de `printf("%s", cadena_usuario)`.
- **Impacto:** Previene vulnerabilidades de inyección y sobreescritura de memoria.

### 19. Exportación de Métricas en Formato OpenTelemetry / Prometheus
- **Descripción:** Exponer métricas de rendimiento, tiempos de compilación y tasas de error de la cohorte hacia sistemas de monitoreo y analítica académica.
- **Impacto:** Monitorea la infraestructura docente en correcciones masivas de miles de entregas.

### 20. Auditoría de Documentación Doxygen / HeaderDoc
- **Descripción:** Verificar la presencia y completitud de comentarios de documentación en prototipos (`@param`, `@return`, `@brief`).
- **Impacto:** Promueve el hábito de documentar interfaces en C.

### 21. Tolerancia Diferenciada de Fugas de Memoria ante Salidas Anormales
- **Descripción:** Configurar si una fuga de memoria previa a `exit(EXIT_FAILURE)` ante una entrada inválida debe ser tolerada o penalizada con menor peso que en el camino de éxito.
- **Impacto:** Flexibiliza la rúbrica ante situaciones de error irrecuperable.

### 22. Detección de Bucles Infinitos por Contador de Instrucciones de CPU (Callgrind / Perf)
- **Descripción:** Medir la cantidad absoluta de instrucciones de CPU ejecutadas en lugar de depender únicamente del tiempo transcurrido (*wall-clock time*).
- **Impacto:** Inmune a retrasos o congelamientos causados por sobrecarga en el servidor del docente.

### 23. Rúbrica Matricial Criterio por Criterio (Rúbrica Cualitativa)
- **Descripción:** Desglosar la evaluación en matrices con niveles de desempeño (Excelente, Bueno, Regular, Insuficiente) con descriptores pedagógicos asociados.
- **Impacto:** Alineación con normativas institucionales de evaluación por competencias.

### 24. Detección de Conversiones Implícitas Peligrosas (*Sign Conversion*)
- **Descripción:** Auditar advertencias de conversión de tipos (`-Wsign-conversion`, `-Wconversion`) que causan desbordamientos o comparaciones erróneas entre `int` y `size_t`.
- **Impacto:** Enseña el uso riguroso del sistema de tipos en C.

### 25. Generador Automático de Arneses de Prueba Mock (CMock / FFF)
- **Descripción:** Crear stubs y mocks automáticos para aislar funciones bajo prueba sin depender de la implementación real de otros módulos.
- **Impacto:** Permite pruebas unitarias desacopladas por función.

### 26. Conversor de Enunciados a Preguntas Moodle XML / Quiz
- **Descripción:** Exportar los enunciados y casos de prueba generados en Ripley directamente al formato de importación XML de Moodle.
- **Impacto:** Sincronización bidireccional entre la herramienta CLI y las evaluaciones del aula virtual.

### 27. Detección de Desalineación de Memoria (*Unaligned Pointer Access*)
- **Descripción:** Capturar accesos a memoria no alineada con `-fsanitize=alignment` en estructuras empaquetadas o casting de punteros incompatibles.
- **Impacto:** Evita fallos sutiles al portar código a diferentes arquitecturas de CPU.

### 28. Generador de Informes Comparativos de Cohorte (*Cohort Benchmark Report*)
- **Descripción:** Generar un reporte estadístico global con histogramas de notas, errores más frecuentes y tiempos promedio de resolución de la cursada.
- **Impacto:** Otorga a la cátedra un diagnóstico integral del rendimiento académico.

### 29. Detección de Código Muerto y Funciones Jamás Invocadas
- **Descripción:** Identificar funciones o bloques de código presentes en la entrega que no son alcanzados por ningún flujo de ejecución posible.
- **Impacto:** Limpia entregas con código sobrante o pruebas intermedias olvidadas.

### 30. Soporte para Encriptación y Protección de Casos de Prueba Ocultos
- **Descripción:** Permitir empaquetar casos de prueba privados encriptados con clave docente para evitar que los estudiantes vean las pruebas ocultas antes de tiempo.
- **Impacto:** Seguridad pedagógica en exámenes y parciales prácticos en vivo.

---

## 3. Roadmap de Propuestas Previas Pendientes

- Soporte para Makefiles estudiantiles y compilación modular.
- Análisis de complejidad ciclomática (McCabe) y métricas Halstead.
- Aislamiento estricto con contenedores efímeros OCI / cgroups v2.
- Auditoría de memoria liviana alternativa a Valgrind (ASan + LSan).
- Pruebas unitarias nativas en C (Criterion / Unity).
- Retroalimentación pedagógica adaptativa con LLMs locales (`ollama`).
- Dashboard web local interactivo (`ripley serve`).
- Sincronización directa con API REST de Moodle (`ripley moodle pull/push`).
- Modo Live TDD / Watch para el estudiante (`ripley watch`).
- Arquitectura extensible multi-lenguaje (C++, Python, Rust, Java).
- Traductor pedagógico de errores de GCC a lenguaje natural.
- Medición de cobertura de código (`gcov` / `lcov`).
- Benchmarking de complejidad temporal empírica ($O(N)$ vs $O(N^2)$).
- Exportación a PDF y HTML enriquecido.
- Firma criptográfica e inmutabilidad con GPG/Ed25519.
- Sistema de plugins y hooks de ciclo de vida en `plugins/`.
- Base de datos compartida PostgreSQL / SQLite en red.
- Soporte para entregas grupales y co-autoría en Moodle.
- Flujo de trabajo con estados de auditoría docente.
- Métricas longitudinales de evolución y aprendizaje ($r_1 \to r_2 \to r_3$).
- Soporte para pruebas con terminales virtuales (PTY / Expect).
