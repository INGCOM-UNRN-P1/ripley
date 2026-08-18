# Potenciales Mejoras para Ripley

Listado de 30 mejoras técnicas, arquitectónicas y pedagógicas para evolucionar la herramienta.

---

### 1. Detección de Plagio y Similitud de Código (Anti-Cheating)
- **Descripción:** Implementar un motor interno de detección de similitud basado en comparación de árboles de sintaxis abstracta (AST) y $n$-gramas de tokens (algoritmo Winnowing, similar a MOSS/JPlag).
- **Impacto:** Detecta copias entre entregas de la cohorte incluso si cambiaron nombres de variables, funciones o comentarios.

### 2. Soporte para Makefiles Estudiantiles y Compilación Modular
- **Descripción:** Detectar si el estudiante incluyó su propio `Makefile` y permitir una estrategia de compilación delegada bajo límites estrictos de sandboxing y timeout.
- **Impacto:** Permite evaluar proyectos más complejos con múltiples unidades de traducción organizadas por el alumno.

### 3. Análisis de Complejidad Ciclomática y Métricas Halstead
- **Descripción:** Integrar métricas de complejidad cognitiva y ciclomática de McCabe (mediante librerías como `lizard` o inspectores AST internos).
- **Impacto:** Permite penalizar funciones excesivamente largas, anidadas o incomprensibles en la rúbrica de estilo.

### 4. Generación Automatizada de Casos de Prueba de Borde (Fuzzing)
- **Descripción:** Incorporar un subcomando `testcase fuzz` que utilice técnicas de mutación de entradas o integración con libFuzzer/AFL para generar casos extremos (valores límite, desbordamientos, strings vacíos).
- **Impacto:** Aumenta la robustez de las pruebas docentes sin requerir diseño manual de cada caso de borde.

### 5. Aislamiento Estricto mediante Contenedores Efímeros OCI / cgroups v2
- **Descripción:** Ejecutar la compilación y pruebas dentro de micro-contenedores sin privilegios (usando `bubblewrap`, `cgroups v2` y namespaces de Linux, o contenedores efímeros Docker/Podman).
- **Impacto:** Garantiza aislamiento total del filesystem del host, consumo de red nulo y límites de memoria insoslayables.

### 6. Diff Semántico Basado en AST
- **Descripción:** Implementar comparación de revisiones ($r_N$ vs $r_{N-1}$) a nivel estructural de AST en C, ignorando reformateos cosméticos o cambios de nombres de identificadores.
- **Impacto:** Identifica con precisión si la reentrega introdujo cambios lógicos reales o solo modificaciones superficiales.

### 7. Auditoría de Memoria Liviana Alternativa a Valgrind
- **Descripción:** Complementar la sobrecarga de Valgrind con instrumentación dinámica liviana mediante `AddressSanitizer` + `LeakSanitizer` (`-fsanitize=address,leak`) o sondas eBPF.
- **Impacto:** Reduce drásticamente el tiempo de ejecución en lotes grandes de cientos de alumnos.

### 8. Soporte para Pruebas Unitarias Nativas en C (CUnit / Criterion / Unity)
- **Descripción:** Permitir suites de pruebas que no dependan únicamente de capturar `stdin`/`stdout`, sino que linkeen un arnés de pruebas contra funciones individuales del estudiante.
- **Impacto:** Posibilita evaluar librerías y tipos abstractos de datos (TADs) sin requerir una función `main()` por parte del alumno.

### 9. Generador de Retroalimentación Pedagógica Adaptativa con LLMs Locales
- **Descripción:** Integrar un hook configurable para enviar logs de compilación, desvíos de estilo y fallos de tests a un modelo de lenguaje (local vía `ollama` o API) para generar sugerencias didácticas personalizadas.
- **Impacto:** Brinda explicaciones conceptuales claras y adaptadas al nivel de un alumno de Programación I.

### 10. Dashboard Web Local Interactivo (FastAPI + React/Vite)
- **Descripción:** Agregar el comando `ripley serve` para levantar una interfaz web local de visualización, filtrado por estados, comparación de diffs lado a lado y ajuste manual de notas.
- **Impacto:** Agiliza la revisión y auditoría docente frente a la visualización estática de Markdown y terminal.

### 11. Sincronización Directa con la API REST de Moodle
- **Descripción:** Implementar subcomandos `ripley moodle pull` y `ripley moodle push` utilizando los webservices de Moodle con tokens de docente.
- **Impacto:** Elimina la necesidad de descargar y subir manualmente archivos ZIP o planillas CSV al aula virtual.

### 12. Modo Watch / Live TDD para Uso del Estudiante
- **Descripción:** Permitir la ejecución de `ripley watch` en el directorio de trabajo para reejecutar pruebas y verificaciones de estilo cada vez que se guarda un archivo `.c`.
- **Impacto:** Transforma a Ripley en un arnés de desarrollo y autoevaluación para los alumnos antes de entregar.

### 13. Arquitectura Extensible Multi-Lenguaje (C++, Python, Rust, Java)
- **Descripción:** Desacoplar los evaluadores de C en adaptadores modulares para soportar otros lenguajes de programación comunes en la carrera.
- **Impacto:** Reutilización de la infraestructura de Ripley en materias correlativas (Algoritmos y Estructuras de Datos, POO).

### 14. Diagnóstico Especializado de Stack Overflow y Recursión Infinita
- **Descripción:** Detectar y diferenciar fallos de segmentación provocados por agotamiento del stack frente a desreferencias de punteros nulos o fuera de rango.
- **Impacto:** Proporciona retroalimentación precisa sobre llamadas recursivas sin caso base.

### 15. Traductor Pedagógico de Errores de GCC
- **Descripción:** Parsear las advertencias y errores crípticos del compilador (`-Wall`, `-Wextra`, `-pedantic`) y traducirlos a explicaciones en español claro con ejemplos didácticos.
- **Impacto:** Disminuye la frustración de alumnos iniciales ante mensajes técnicos del compilador.

### 16. Verificación de Restricciones del Enunciado (Blacklist/Whitelist de AST)
- **Descripción:** Configurar reglas por ejercicio para validar restricciones de código (ej. "prohibido usar bucles `for`/`while`", "prohibido usar librerías de `string.h`", "forzar uso de punteros").
- **Impacto:** Automatiza el control de consignas pedagógicas que los compiladores tradicionales no auditan.

### 17. Medición de Cobertura de Código de los Testcases (gcov / lcov)
- **Descripción:** Instrumentar el código con `--coverage` para determinar qué porcentaje de las ramas y líneas del código del alumno fue ejecutado por los casos de prueba docentes.
- **Impacto:** Identifica casos de prueba insuficientes o código muerto dentro de la solución del estudiante.

### 18. Benchmarking y Análisis de Complejidad Temporal Empírica
- **Descripción:** Ejecutar binarios con entradas escalonadas de tamaño $N$ para estimar la cota de complejidad temporal ($O(N)$, $O(N \log N)$, $O(N^2)$).
- **Impacto:** Permite evaluar la eficiencia algorítmica y detectar soluciones que excedan la complejidad esperada.

### 19. Exportación a PDF y HTML Enriquecido
- **Descripción:** Incorporar un conversor de Markdown a documentos PDF y HTML autocontenidos con soporte para tipografía cuidada y resaltado de sintaxis.
- **Impacto:** Facilita la impresión de actas o el envío directo de retroalimentación por correo electrónico.

### 20. Firma Criptográfica e Inmutabilidad de Evaluaciones
- **Descripción:** Firmar digitalmente los reportes y hashes de cada versión $r_N$ mediante claves GPG/Ed25519 del docente.
- **Impacto:** Garantiza la integridad inalterable de las calificaciones y fechas ante reclamos académicos.

### 21. Sistema de Plugins y Hooks de Ciclo de Vida
- **Descripción:** Proveer puntos de extensión (`pre_ingest`, `post_compile`, `custom_linter`, `post_evaluate`) cargados dinámicamente desde un directorio `plugins/`.
- **Impacto:** Permite a cada cátedra inyectar reglas y comprobaciones a medida sin modificar el núcleo de Ripley.

### 22. Base de Datos Centralizada para Trabajo en Equipo Docente
- **Descripción:** Soportar motores PostgreSQL o SQLite compartida mediante red para que varios ayudantes califiquen y agreguen observaciones concurrentemente.
- **Impacto:** Escalabilidad en materias masivas con comisiones de cientos de estudiantes.

### 23. Comparación Flexible de Salidas (Regex y Normalización Fuzzy)
- **Descripción:** Permitir que los archivos `.out` contengan patrones regex o directivas de tolerancia a puntuación y mayúsculas/minúsculas.
- **Impacto:** Evita desaprobar casos de prueba por variaciones menores en textos informativos de la salida.

### 24. Detección Estricta de Punteros Colgantes (*Dangling Pointers*)
- **Descripción:** Validar estáticamente o mediante sanitizadores que los punteros liberados con `free()` sean asignados a `NULL` o salgan de ámbito de inmediato.
- **Impacto:** Refuerza las buenas prácticas de manejo de memoria dinámica en C.

### 25. Soporte para Entregas Grupales y Co-autoría
- **Descripción:** Permitir la vinculación de múltiples alumnos a un único repositorio/entrega con replicación automática de notas en la planilla Moodle.
- **Impacto:** Soporta trabajos prácticos integradores grupales sin pasos manuales.

### 26. Flujo de Trabajo con Estados de Auditoría Docente
- **Descripción:** Implementar un ciclo de vida con estados explícitos (`Ingestado`, `Auto-Evaluado`, `Revisión Manual Pendiente`, `Aprobado`, `Publicado`).
- **Impacto:** Otorga visibilidad del progreso de corrección del equipo docente.

### 27. Detección de Bloqueos en Stdin (I/O Deadlocks)
- **Descripción:** Monitorizar el consumo de `stdin` para reportar específicamente si el programa del estudiante quedó esperando más lecturas que las provistas por el caso de prueba.
- **Impacto:** Proporciona un diagnóstico claro cuando `scanf` o `getchar` no terminan de consumir datos.

### 28. Validador de Consistencia Docente (Solución Modelo Fixture)
- **Descripción:** Comando `testcase verify --solution <path>` para contrastar la suite de pruebas contra el código de referencia del docente antes de iniciar la evaluación.
- **Impacto:** Garantiza que los casos de prueba sean coherentes y que la solución oficial obtenga 10/10.

### 29. Métricas Longitudinales de Aprendizaje y Evolución
- **Descripción:** Computar la tasa de corrección de errores entre versiones consecutivas ($r_1 \to r_2 \to r_3$) y generar gráficos de persistencia de fallas en la cohorte.
- **Impacto:** Brinda datos analíticos a los profesores sobre los conceptos que presentan mayor dificultad pedagógica.

### 30. Soporte para Pruebas con Pseudo-Terminales (PTY / Expect)
- **Descripción:** Ejecutar programas que requieren interacción en tiempo real mediante terminales virtuales PTY (ej. menús interactivos o lectura carácter a carácter con `termios`).
- **Impacto:** Permite evaluar ejercicios de interacción continua y juegos de consola en C.
