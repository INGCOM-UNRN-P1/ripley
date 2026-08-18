# Ripley - Registro Modular de Funcionalidades y Mejoras

---

## 1. Funcionalidades Implementadas (35)

Las 35 funcionalidades se encuentran modularizadas e implementadas con suites de pruebas unitarias e integradas (`87/87` tests pasando al 100%):

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

---

## 2. 30 Nuevas Propuestas de Mejora (Modularizadas)

### Módulo 1: Compilación, Aislamiento y Entornos Seguros
1. **Soporte para Compilación Cruzada Multi-Arquitectura (x86_64, ARM64, RISC-V con QEMU):** Compilar y ejecutar los binarios de los alumnos en emuladores QEMU para validar portabilidad y orden de bytes (*endianness*).
2. **Aislamiento Basado en Espacios de Nombres Linux (Bubblewrap / Unshare):** Ejecutar pruebas dentro de un sandbox estricto sin privilegios de root (PID, Mount, Network e IPC namespaces).
3. **Detector de Dependencia de Orden de Evaluación de Argumentos:** Capturar llamadas como `f(i++, i++)` o `f(g(), h())` donde el estándar C deja el orden de evaluación indefinido (*unspecified behavior*).
4. **Auditoría de Modificación de Cadenas Literales en `.rodata`:** Proteger páginas de solo lectura para atrapar en tiempo de ejecución cualquier intento de modificar literales de texto (`char *s = "hola"; s[0] = 'H';`).
5. **Control de Saltos Hacia Atrás con `goto`:** Regla que penaliza saltos hacia atrás con `goto` que simulan bucles desestructurados (*spaghetti code*).
6. **Generador de Instantáneas de Toolchains Herméticas:** Empaquetar versiones fijas de GCC y bibliotecas estándar para garantizar evaluaciones 100% reproducibles en el tiempo.

### Módulo 2: Testing Dinámico, Rendimiento y Fuzzing Avanzado
7. **Fuzzing Guiado por Cobertura (Coverage-Guided Fuzzing con LibFuzzer / AFL++):** Mutación de entradas que prioriza la exploración de nuevas ramas no alcanzadas del código del alumno.
8. **Analizador Empírico de Complejidad Asintótica ($O(N)$ vs $O(N^2)$ Profiler):** Ejecutar algoritmos con entradas exponenciales ($N = 10, 100, 1000, 10000$) y ajustar curvas de regresión no lineal.
9. **Auditoría de Consumo de Stack Máximo (`-fstack-usage`):** Medir los bytes pico utilizados en la pila para alertar sobre arreglos locales desmedidos (`int buffer[1000000];`).
10. **Simulador de Fragmentación de Memoria Heap:** Simular patrones de asignación y liberación aleatorios para evaluar la eficiencia del heap del alumno.
11. **Inyección de Fallas en Descriptores de Red y Sockets:** Simular conexiones caídas o timeouts para verificar si el código cierra adecuadamente los sockets.
12. **Benchmarking de Consumo Energético y Ciclos de Instrucción:** Estimar la eficiencia energética del código para materias de arquitectura de computadoras.

### Módulo 3: Análisis Semántico y Verificación Formal
13. **Verificación Formal Ligera con Frama-C / ACSL:** Demostración automática de contratos de funciones con precondiciones (`/*@ requires n > 0 */`) y postcondiciones (`/*@ ensures \result >= 0 */`).
14. **Demostrador de Terminación de Bucles (*Termination Proof*):** Analizar si las variables de control dentro de un bucle `while` o `for` son invariantes, deduciendo si el bucle es infinito.
15. **Auditoría de Uso de Enums como Máscaras de Bits:** Detectar operaciones a nivel de bits (`&`, `|`) sobre `enums` que no fueron declarados como potencias de dos.
16. **Verificador de Inicialización de Relleno de Estructuras (*Struct Padding Zeroing*):** Detectar si estructuras enviadas a archivos o sockets contienen bytes de relleno (*padding*) sin inicializar.
17. **Detector de Funciones Obsoletas y Desaconsejadas (Deprecated C API Linter):** Alertar sobre funciones como `gets`, `tmpnam`, `asctime` o `strtok` sugiriendo sus reemplazos seguros (`fgets`, `mkstemp`, `strtok_r`).
18. **Análisis de Efectos Secundarios en Funciones Puras (`__attribute__((pure))`):** Validar que funciones que retornan valores basados únicamente en sus parámetros no alteren estado global.

### Módulo 4: Didáctica, Feedback Personalizado y Accesibilidad
19. **Generador de Animaciones de Memoria Paso a Paso (SVG Interactivo / GIF):** Crear representaciones animadas del estado de memoria (Stack, Heap, Punteros) durante la ejecución de casos fallidos.
20. **Recomendador de Lecturas y Ejercicios de Refuerzo:** Vincular cada error detectado con secciones específicas de la bibliografía de la materia.
21. **Modo Tutor Socrático Interactivo en Terminal (`ripley tutor`):** Asistente CLI que guía al estudiante a depurar su código mediante preguntas orientadoras sin revelar la solución.
22. **Métrica de Complejidad Cognitiva de SonarQube:** Medir la dificultad de lectura del código penalizando anidamientos profundos y estructuras intrincadas.
23. **Glosario Visual de Conceptos de Bajo Nivel:** Recursos gráficos y diagramas explicativos adaptados para estudiantes con necesidades de accesibilidad.
24. **Informes de Evolución Longitudinal del Aprendizaje:** Cuadro de mando que muestra la evolución de cada alumno a lo largo de las distintas entregas del cuatrimestre.

### Módulo 5: Infraestructura, Integración y Ecosistema Docente
25. **Sincronización Webhook en Tiempo Real con Moodle:** Recepción de eventos push de Moodle para evaluar entregas en menos de 10 segundos tras su envío.
26. **Exportación a Formato Estándar SARIF (OASIS SARIF):** Exportar diagnósticos para visualización en GitHub Code Scanning y GitLab SAST.
27. **Servicio Centralizado de Analítica Académica (Grafana / Prometheus):** Exponer métricas de rendimiento y errores recurrentes de toda la cursada hacia paneles de monitoreo.
28. **Evaluación de Trabajos Prácticos Gráficos (SDL2 / Raylib en Framebuffer Virtual):** Ejecutar prácticas multimedia con `Xvfb` y comparar capturas de pantalla de la ventana contra salidas esperadas.
29. **Auditoría de Co-Autoría y Firmas Criptográficas Git:** Analizar firmas GPG/SSH e historial de commits para fiscalizar la participación equitativa en entregas grupales.
30. **Modo Evaluación Presencial con Bloqueo de Red (Exam Lockout Mode):** Configuración de entorno de examen presencial que bloquea accesos no autorizados a la red y periféricos.

---

## 3. Roadmap de Propuestas Previas Pendientes

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
