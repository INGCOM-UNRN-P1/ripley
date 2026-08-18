# Ripley - Registro de Funcionalidades y Mejoras

---

## 1. Funcionalidades Implementadas (24)

Las siguientes 24 funcionalidades ya fueron completamente implementadas, integradas a la arquitectura CLI/evaluador y validadas con `76/76` pruebas unitarias e integradas:

1. **Detección de Plagio y Similitud de Código (Anti-Cheating)**
   - *Detalle:* Tokenización AST, algoritmo Winnowing ($k$-gramas y ventanas deslizantes) y cálculo de similitud Jaccard en la cohorte.
   - *Ubicación:* [`src/ripley/plagiarism.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/plagiarism.py) | CLI: `./ripley plagiarism`, `./ripley evaluate --check-plagiarism`.
   - *Tests:* [`tests/unit/test_plagiarism.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_plagiarism.py).

2. **Generación Automatizada de Casos de Prueba de Borde (Fuzzing)**
   - *Detalle:* Generación de valores extremos numéricos, mutaciones de semillas y cálculo de `.out` automático con la solución modelo docente.
   - *Ubicación:* [`src/ripley/fuzzing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/fuzzing.py) | CLI: `./ripley testcase fuzz`.
   - *Tests:* [`tests/unit/test_fuzzing.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_fuzzing.py).

3. **Diff Semántico Basado en AST**
   - *Detalle:* Comparación estructural de funciones C ($r_N$ vs $r_{N-1}$), clasificando altas, bajas, modificaciones lógicas y cambios puramente cosméticos.
   - *Ubicación:* [`src/ripley/semantic_diff.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/semantic_diff.py) y [`src/ripley/diffing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diffing.py).
   - *Tests:* [`tests/unit/test_semantic_diff.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_semantic_diff.py).

4. **Diagnóstico Especializado de Stack Overflow y Recursión Infinita**
   - *Detalle:* Detección de agotamiento de pila y recursiones sin caso base con recomendaciones pedagógicas adaptativas.
   - *Ubicación:* [`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py).
   - *Tests:* [`tests/unit/test_diagnostics.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_diagnostics.py).

5. **Verificación de Restricciones del Enunciado (Blacklist/Whitelist de AST)**
   - *Detalle:* Control de construcciones prohibidas (`for`, `while`, `goto`, cabeceras como `<string.h>`) o requisitos obligatorios (`struct`, `malloc`, recursión).
   - *Ubicación:* [`src/ripley/restrictions.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/restrictions.py).
   - *Tests:* [`tests/unit/test_restrictions.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_restrictions.py).

6. **Comparación Flexible de Salidas (Regex y Normalización Fuzzy)**
   - *Detalle:* Soporte para directivas `REGEX:` en `.out` y comparación flexible tolerante a diferencias de espaciado, puntuación y mayúsculas.
   - *Ubicación:* [`src/ripley/runner.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/runner.py).
   - *Tests:* [`tests/unit/test_runner.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_runner.py).

7. **Detección Estricta de Punteros Colgantes (*Dangling Pointers*)**
   - *Detalle:* Identificación dinámica de eventos *Use-After-Free* y *Double Free*, y análisis estático de reuso de punteros tras `free()`.
   - *Ubicación:* [`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py).
   - *Tests:* [`tests/unit/test_diagnostics.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_diagnostics.py).

8. **Detección de Bloqueos en Stdin (I/O Deadlocks)**
   - *Detalle:* Diagnóstico de procesos suspendidos esperando datos por teclado de los provistos por el caso de prueba.
   - *Ubicación:* [`src/ripley/diagnostics.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/diagnostics.py).
   - *Tests:* [`tests/unit/test_diagnostics.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_diagnostics.py).

9. **Inicialización y Gestión Integral de Prácticas**
   - *Detalle:* Estructuración automática de consignas, pautas docentes, rúbricas y casos de prueba en `./practicas/<slug>/`.
   - *Ubicación:* [`src/ripley/practice.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/practice.py) | CLI: `./ripley practice init`, `./ripley practice list`, `./ripley practice sync`.
   - *Tests:* [`tests/unit/test_practice.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_practice.py).

10. **Generación de Diagramas de Flujo Tradicionales (ISO/ANSI)**
    - *Detalle:* Creación de diagramas de flujo con formas geométricas estándar (óvalos de inicio/fin, paralelogramos de I/O, rombos de decisión y rectángulos de proceso).
    - *Ubicación:* [`src/ripley/flowchart.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/flowchart.py) | CLI: `./ripley flowchart --file <path.c>`.
    - *Tests:* [`tests/unit/test_flowchart.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_flowchart.py).

11. **Generación de Árboles de Llamadas (Call Graphs)**
    - *Detalle:* Extracción de relaciones de invocación entre funciones C, funciones recursivas y llamadas a librerías estándar en Mermaid y Graphviz DOT.
    - *Ubicación:* [`src/ripley/callgraph.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/callgraph.py) | CLI: `./ripley callgraph --file <path.c>`.
    - *Tests:* [`tests/unit/test_callgraph.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_callgraph.py).

12. **Detección de Desbordamientos de Enteros con UBSan**
    - *Detalle:* Diagnóstico pedagógico de desbordamientos aritméticos con signo, división por cero y shifts inválidos con UndefinedBehaviorSanitizer.
    - *Ubicación:* [`src/ripley/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/sanitizers.py).
    - *Tests:* [`tests/unit/test_sanitizers.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_sanitizers.py).

13. **Análisis de Variables no Asignadas**
    - *Detalle:* Reporte exacto de lectura de variables locales no inicializadas con basura de memoria en el stack.
    - *Ubicación:* [`src/ripley/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/sanitizers.py).
    - *Tests:* [`tests/unit/test_sanitizers.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_sanitizers.py).

14. **Detector de Números Mágicos**
    - *Detalle:* Linter de estilo que alerta sobre literales numéricos sin nombre en el código, sugiriendo el uso de constantes simbólicas o enums.
    - *Ubicación:* [`src/ripley/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/linters.py) | CLI: `./ripley lint --magic-numbers`.
    - *Tests:* [`tests/unit/test_linters.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_linters.py).

15. **Testing Basado en Propiedades (Property-Based Testing en C)**
    - *Detalle:* Generador y ejecutor de arneses C para validar invariantes formales (idempotencia, conmutatividad, multiconjunto ordenado).
    - *Ubicación:* [`src/ripley/property_testing.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/property_testing.py) | CLI: `./ripley property-test`.
    - *Tests:* [`tests/unit/test_property_testing.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_property_testing.py).

16. **Detector de Duplicación Interna de Código (Copy-Paste Detector)**
    - *Detalle:* Detección de bloques de tokens duplicados entre funciones dentro de la misma entrega del estudiante.
    - *Ubicación:* [`src/ripley/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/linters.py) | CLI: `./ripley lint --clones`.
    - *Tests:* [`tests/unit/test_linters.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_linters.py).

17. **Linter de Convenciones de Nombres Configurable**
    - *Detalle:* Fiscalización de nomenclatura requerida para funciones, variables (`snake_case`), constantes (`UPPER_CASE`) y tipos (`t_nodo`).
    - *Ubicación:* [`src/ripley/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/linters.py) | CLI: `./ripley lint --naming`.
    - *Tests:* [`tests/unit/test_linters.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_linters.py).

18. **Auditoría de Documentación Doxygen**
    - *Detalle:* Verificación de completitud de bloques de documentación Doxygen/Javadoc (`@brief`, `@param`, `@return`).
    - *Ubicación:* [`src/ripley/doxygen.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/doxygen.py) | CLI: `./ripley doxygen --file <path.c>`.
    - *Tests:* [`tests/unit/test_doxygen.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_doxygen.py).

19. **Generador Automático de Arneses de Prueba Mock**
    - *Detalle:* Generación automática de stubs y mocks en C con registro de invocaciones (`call_count`) y valores de retorno configurables.
    - *Ubicación:* [`src/ripley/mocks.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/mocks.py) | CLI: `./ripley mock generate --header <path.h>`.
    - *Tests:* [`tests/unit/test_mocks.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_mocks.py).

20. **Detección de Bucles Infinitos por Contador de Instrucciones CPU**
    - *Detalle:* Medición determinista de instrucciones ejecutadas con Callgrind para detectar loops infinitos inmune a variaciones de carga.
    - *Ubicación:* [`src/ripley/instruction_counter.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/instruction_counter.py).
    - *Tests:* [`tests/unit/test_instruction_counter.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_instruction_counter.py).

21. **Tolerancia Diferenciada de Fugas de Memoria ante Salidas Anormales**
    - *Detalle:* Configuración de tolerancia pedagógica para fugas previas a `exit(EXIT_FAILURE)` o terminación con código de error.
    - *Ubicación:* [`src/ripley/runner.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/runner.py) y [`src/ripley/config.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/config.py).

22. **Detección de Código Muerto y Funciones Jamás Invocadas**
    - *Detalle:* Análisis de accesibilidad en el call graph partiendo de `main()`, alertando sobre funciones inalcanzables.
    - *Ubicación:* [`src/ripley/callgraph.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/callgraph.py) y [`src/ripley/linters.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/linters.py) | CLI: `./ripley lint --dead-code`.
    - *Tests:* [`tests/unit/test_dead_code.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_dead_code.py).

23. **Detección de Conversiones Implícitas Peligrosas (*Sign Conversion*)**
    - *Detalle:* Captura de advertencias `-Wsign-conversion` y `-Wconversion` entre tipos con y sin signo o con pérdida de precisión.
    - *Ubicación:* [`src/ripley/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/sanitizers.py).
    - *Tests:* [`tests/unit/test_sanitizers.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_sanitizers.py).

24. **Detección de Desalineación de Memoria (*Unaligned Pointer Access*)**
    - *Detalle:* Captura de accesos a memoria no alineada con `-fsanitize=alignment` en estructuras o casteo incorrecto de punteros.
    - *Ubicación:* [`src/ripley/sanitizers.py`](file:///home/mrtin/dev/p1/ripley/src/ripley/sanitizers.py).
    - *Tests:* [`tests/unit/test_sanitizers.py`](file:///home/mrtin/dev/p1/ripley/tests/unit/test_sanitizers.py).

---

## 2. 30 Nuevas Propuestas de Mejora

### 1. Auditoría de Desbordamiento de Buffer en Stack con Canaries (`-fstack-protector-all`)
- **Descripción:** Compilar con instrumentación de canaries de pila e interceptar llamadas a `__stack_chk_fail`, identificando qué arreglo o variable local desbordó el marco de ejecución.
- **Impacto:** Diagnósticos comprensibles para estudiantes que pisan la dirección de retorno en el stack.

### 2. Testing de Mutación para Evaluación de Casos de Prueba Docentes (*Mutation Testing*)
- **Descripción:** Inyectar mutantes automáticos (modificar operadores relacionales, alterar constantes, omitir llamadas) en la solución modelo para evaluar si la suite de tests docentes es capaz de atrapar todos los bugs.
- **Impacto:** Garantiza que los casos de prueba de la cátedra no tengan puntos ciegos.

### 3. Detección de Comparaciones Peligrosas en Números de Punto Flotante
- **Descripción:** Regla de análisis estático que penaliza comparaciones directas `a == b` o `a != b` en variables `float`/`double`, sugiriendo el uso de márgenes de tolerancia (`fabs(a - b) < EPSILON`).
- **Impacto:** Enseña los límites de precisión del estándar IEEE 754.

### 4. Pruebas Interactivas Bidireccionales con Terminales Virtuales (Pexpect / PTY)
- **Descripción:** Soportar scripts de prueba que interactúen paso a paso con programas que presentan menús o prompts secuenciales por consola.
- **Impacto:** Permite evaluar trabajos prácticos interactivos sin requerir archivos de entrada monolíticos.

### 5. Medición de Cobertura de Ramas y Decisiones MC/DC (`gcov` / `lcov`)
- **Descripción:** Calcular el porcentaje de líneas, ramas e instrucciones lógicas ejecutadas en el código del estudiante por cada caso de prueba.
- **Impacto:** Revela qué partes del código del alumno quedaron sin ejercitar durante la corrección.

### 6. Emulación de Memoria Restringida para Sistemas Embebidos
- **Descripción:** Limitar el tamaño máximo de heap disponible (ej. 32 KB con `setrlimit(RLIMIT_AS)`) para evaluar ejercicios de optimización de memoria.
- **Impacto:** Útil para cátedras con orientación a sistemas embebidos y microcontroladores.

### 7. Visualizador Gráfico de Estructuras Dinámicas en Memoria (Graphviz)
- **Descripción:** Instrumentar el código para generar diagramas visuales (PNG/SVG) del estado de listas enlazadas, árboles binarios y grafos paso a paso.
- **Impacto:** Facilita la comprensión visual del comportamiento de punteros en estructuras recursivas.

### 8. Detector y Optimizador de Recursión de Cola (*Tail Call Optimization Checker*)
- **Descripción:** Auditar si las funciones recursivas cumplen la forma de recursión de cola pura y validar si el compilador genera un bucle iterativo sin consumo de stack.
- **Impacto:** Refuerza conceptos avanzados de diseño de algoritmos recursivos.

### 9. Detección de Inclusiones Innecesarias (*Include What You Use - IWYU*)
- **Descripción:** Identificar directivas `#include` de cabeceras estándar o locales cuyos tipos y funciones jamás son utilizados en el código fuente.
- **Impacto:** Limpia dependencias superfluas y acelera tiempos de compilación.

### 10. Auditoría de Calificación `const` en Parámetros (*Const-Correctness*)
- **Descripción:** Validar que los punteros que actúan como parámetros de solo lectura estén explícitamente declarados como `const tipo *`.
- **Impacto:** Enseña buenas prácticas de diseño de contratos en interfaces C.

### 11. Simulación de Interrupciones por Señales Asíncronas (`SIGINT` / `SIGALRM`)
- **Descripción:** Enviar señales del sistema operativo durante operaciones bloqueantes (`read`, `sleep`) para evaluar si el código maneja adecuadamente el error `EINTR`.
- **Impacto:** Fundamental para trabajos prácticos de programación de sistemas y POSIX.

### 12. Generación Automática de Preguntas Conceptuales Adaptativas
- **Descripción:** Generar micro-cuestionarios personalizados basados en los errores específicos cometidos por el estudiante en su entrega.
- **Impacto:** Transforma el reporte de corrección en una herramienta de aprendizaje activo.

### 13. Fiscalización de Códigos de Salida Estándar (`EXIT_SUCCESS` / `EXIT_FAILURE`)
- **Descripción:** Verificar que el programa retorne códigos de salida conformes a `<stdlib.h>` y no números negativos o arbitrarios.
- **Impacto:** Garantiza compatibilidad con scripts de integración y pipelines Unix.

### 14. Detección de Evaluaciones de Cortocircuito Peligrosas con Efectos Colaterales
- **Descripción:** Alertar sobre expresiones como `if (valido && leer_dato(&x))` o `if (i++ && b)` donde los efectos colaterales dependen de la evaluación booleana.
- **Impacto:** Evita bugs no deterministas difíciles de depurar.

### 15. Calificación Distribuida Masiva en Paralelo (Celery / Redis / Ray)
- **Descripción:** Orquestar la evaluación de miles de entregas simultáneamente en un clúster distribuido de nodos evaluadores.
- **Impacto:** Reduce drásticamente los tiempos de procesamiento en cátedras masivas.

### 16. Verificación de Liberación de Estructuras Anidadas (*Deep Free Verifier*)
- **Descripción:** Auditar que las funciones de destrucción de estructuras liberen tanto los campos internos como el nodo contenedor sin dejar bloques huérfanos.
- **Impacto:** Elimina fugas de memoria en tipos de datos abstractos complejos.

### 17. Auditoría de Macros sin Paréntesis Protectores
- **Descripción:** Detectar macros `#define MULT(a, b) a * b` que carecen de paréntesis de protección contra precedencia de operadores.
- **Impacto:** Previene errores de evaluación al pasar expresiones como argumentos.

### 18. Historial de Depuración con Time-Travel Debugging (GDB / RR Wrapper)
- **Descripción:** Grabar trazas de ejecución de casos fallidos y permitir reproducir el avance y retroceso del estado de memoria paso a paso.
- **Impacto:** Acelera la identificación de fallas complejas durante las tutorías docentes.

### 19. Sistema de Insignias y Gamificación Didáctica
- **Descripción:** Otorgar insignias pedagógicas en el reporte de evaluación ("Cero Fugas de Memoria", "Código Limpio", "Maestro de Punteros").
- **Impacto:** Aumenta la motivación y compromiso de los estudiantes con las buenas prácticas.

### 20. Auditoría de Punteros Nulos en Funciones de Cadenas (`<string.h>`)
- **Descripción:** Advertir sobre llamadas a `strlen`, `strcmp` o `strcpy` con variables no validadas contra `NULL`.
- **Impacto:** Previene caídas por *Null Pointer Dereference* en funciones de biblioteca estándar.

### 21. Detección de Sombras de Variables (*Variable Shadowing*)
- **Descripción:** Alertar cuando una variable declarada dentro de un bloque interno o parámetro oculta una variable de ámbito superior.
- **Impacto:** Evita confusiones de alcance y accesos a datos erróneos.

### 22. Auditoría del Retorno de Funciones de Entrada (`scanf` return check)
- **Descripción:** Fiscalizar que el código verifique el valor retornado por `scanf` o `sscanf` antes de utilizar las variables leídas.
- **Impacto:** Previene el uso de variables con valores indefinidos ante entradas corruptas.

### 23. Pruebas de Estrés y Rendimiento con Cargas Rápidas
- **Descripción:** Ejecutar miles de operaciones en ráfaga para verificar la estabilidad y el consumo de recursos bajo alta demanda.
- **Impacto:** Evalúa la eficiencia de algoritmos y estructuras de datos.

### 24. Detector de Castings Inseguros a través de `void*`
- **Descripción:** Auditar conversiones peligrosas de `void*` a tipos de estructuras incompatibles sin campos de discriminación de tipo.
- **Impacto:** Enseña el uso seguro de polimorfismo genérico en C.

### 25. Generador de Resúmenes en Audio con Síntesis de Voz (TTS para Accesibilidad)
- **Descripción:** Sintetizar resúmenes de audio con las observaciones y notas para estudiantes con necesidades de accesibilidad visual.
- **Impacto:** Inclusión educativa y accesibilidad universal.

### 26. Detección de Retorno de Direcciones de Variables del Stack
- **Descripción:** Alertar cuando una función retorna un puntero a una variable local automática que se destruye al salir del ámbito.
- **Impacto:** Previene comportamientos indefinidos por punteros a marcos de pila desasignados.

### 27. Detector de Sobre-Ingeniería y Optimizaciones Prematuras Ilegibles
- **Descripción:** Comparar complejidad ciclomática frente a volumen de código para sugerir simplificaciones en código excesivamente intrincado.
- **Impacto:** Promueve la simplicidad y claridad conceptual sobre trucos crípticos.

### 28. Auditoría de Código Ensamblador Generado (`gcc -S` / Objdump)
- **Descripción:** Analizar las instrucciones en ensamblador generadas para comprobar si el compilador aplicó vectorización o optimizaciones solicitadas.
- **Impacto:** Didáctica de arquitectura de computadoras y compiladores.

### 29. Servidor LSP Embebido para Diagnósticos en Tiempo Real en VS Code
- **Descripción:** Implementar un servidor de Language Server Protocol dentro de Ripley para mostrar advertencias directamente en el editor del alumno.
- **Impacto:** Retroalimentación instantánea mientras el estudiante programa.

### 30. Auditoría Forense de Metadatos y Tiempos de Modificación
- **Descripción:** Analizar marcas de tiempo POSIX e historial de modificaciones para identificar patrones temporales anómalos en las entregas.
- **Impacto:** Soporte analítico para la gestión de prórrogas y honestidad académica.

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
- Benchmarking de complejidad temporal empírica ($O(N)$ vs $O(N^2)$).
- Exportación a PDF y HTML enriquecido.
- Firma criptográfica e inmutabilidad con GPG/Ed25519.
- Sistema de plugins y hooks de ciclo de vida en `plugins/`.
- Base de datos compartida PostgreSQL / SQLite en red.
- Soporte para entregas grupales y co-autoría en Moodle.
- Flujo de trabajo con estados de auditoría docente.
- Métricas longitudinales de evolución y aprendizaje ($r_1 \to r_2 \to r_3$).
