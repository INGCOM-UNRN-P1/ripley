# Diseño de Especificación Técnica: Delegación Completa de Verificaciones en Herramientas Secundarias como Plugins

- **Fecha:** 2026-09-01
- **Herramienta:** `ripley`
- **Estado:** Aprobado

---

## 1. Contexto y Objetivos

`ripley` está diseñado para operar como un **microkernel orquestador desacoplado** de evaluación pedagógica para la cátedra de Programación 1. Su función es coordinar el ciclo de vida de auditoría del código C entregado por los estudiantes, publicar diagnósticos en tiempo real vía Language Server Protocol (LSP) y generar reportes unificados (Rich, JSON, SARIF, Markdown).

Para evitar que `ripley` actúe como un monolito sobredimensionado con implementaciones duplicadas de compiladores, linters y sandboxes, se establece el siguiente mandato arquitectónico:

> **Mandato:** `ripley` debe delegar **el 100 % de las verificaciones** a las herramientas secundarias especializadas del ecosistema (`daedalus`, `nostromo`, `gaff`, `spunkmeyer`, `kaneda`, `wierzbowski`, `zhora`, `brett`, `motoko`, etc.) a través de un bus de plugins unificado.

---

## 2. Mapeo de Responsabilidades Delegadas

| Herramienta | Entrypoint (`ripley.plugins`) | Comando CLI | Responsabilidad de Verificación Delegada |
| :--- | :--- | :--- | :--- |
| **`daedalus`** | `compiler` | `daedalus` | Compilación C bajo flags cátedra, AddressSanitizer/UBSan y traducción pedagógica de diagnósticos GCC/Clang/ld. |
| **`nostromo`** | `sandbox` | `nostromo` | Ejecución aislada en sandbox Bubblewrap y validación de casos de prueba `.in`/`.out`. |
| **`gaff`** | `style` | `gaff` | Auditoría de convenciones de estilo (Allman, indentación, espacios, llaves, nombres). |
| **`spunkmeyer`** | `antipatterns` | `spunkmeyer` | Detección de vicios de programación (`while(!feof)`, casts en `malloc`, etc.). |
| **`kaneda`** | `security` | `kaneda` | Análisis de seguridad de llamadas al sistema, buffer overflows y APIs prohibidas. |
| **`wierzbowski`** | `headers_audit` | `wierzbowski` | Auditoría de inclusión de encabezados y dependencias directas (IWYU). |
| **`zhora`** | `macro_security` | `zhora` | Auditoría de seguridad y paréntesis en macros y directivas del preprocesador. |
| **`brett`** | `padding` | `brett` | Análisis de alineación, tamaño de structs y bytes de padding desperdiciados. |
| **`motoko`** | `tda_encapsulation` | `motoko` | Verificación de opacidad y encapsulamiento de Tipos de Datos Abstractos (TDA). |
| **`dietrich` / `crowe`** | `portability` | `dietrich` / `crowe` | Detección de asunciones de arquitectura y portabilidad (ancho de tipos, endianness). |
| **`giger`** | `callgraph` | `giger` | Callgraph, Control Flow Graph (CFG), ciclos de recursión y funciones no invocadas. |
| **`callahan`** | `formal_contracts` | `callahan` | Verificación formal de contratos y pre/postcondiciones ACSL con Frama-C. |

---

## 3. Protocolo del Adaptador Híbrido (`SatellitePluginAdapter`)

El mecanismo de descubrimiento y despacho se implementa en `src/ripley/core/entrypoints.py` garantizando compatibilidad tanto en entornos donde los paquetes comparten el mismo virtualenv de Python como en aquellos donde se instalan como herramientas de sistema o binarios aislados (`uv tool` en PATH).

### 3.1. Algoritmo de Resolución de Disponibilidad

1. **Prioridad 1 — Carga en RAM (In-Memory Entrypoint):**
   - Se consulta el grupo `ripley.plugins` mediante `importlib.metadata.entry_points(group="ripley.plugins")`.
   - Si el plugin está presente e importable, se instancia y se invoca su método `.execute(workspace, config)` o `.run(context)`.
2. **Prioridad 2 — Fallback a Subproceso CLI:**
   - Si el paquete Python no está en el entorno actual pero el comando ejecutable está en el `PATH` del sistema (`shutil.which(cmd)`), Ripley invoca al subproceso con el flag `--json` (o equivalente estructurado) y captura `stdout`.
3. **Prioridad 3 — Herramienta Ausente:**
   - Si no se encuentra ni como entrypoint ni en `PATH`, el plugin se declara no disponible (`is_available = False`). Ripley registra un diagnóstico informativo formal:
     - `codigo`: `MISSING_TOOL_<NOMBRE>`
     - `severidad`: `ADVERTENCIA` (se eleva a `ERROR` bajo `--strict`)
     - `mensaje`: `"La herramienta secundaria '<nombre>' no está disponible en el entorno ni en PATH. Se omitieron sus verificaciones."`
     - `sugerencia`: `"Instalá la herramienta mediante 'uv tool install <nombre>'."`

### 3.2. Esquema Normalizado de Hallazgos

Cualquiera sea la vía de ejecución (RAM o CLI), el resultado se adapta a la estructura canónica de Ripley:

```json
{
  "rule_code": "0x300Ah",
  "rule_name": "Cast innecesario en malloc",
  "severity": "ADVERTENCIA",
  "file": "main.c",
  "line": 12,
  "column": 5,
  "message": "En C no es necesario castear el retorno de malloc.",
  "suggestion": "Eliminá el cast explícito '(int *)'.",
  "source_plugin": "spunkmeyer"
}
```

---

## 4. Reestructuración de `core/engine.py`

El pipeline central `analyze_target()` se reestructura para eliminar toda ejecución directa de linters internos redundantes:

1. **Compilación:** Delega exclusivamente en el plugin `compiler` (`daedalus`). Si no está disponible, registra la falla y diagnósticos de herramienta ausente sin ejecutar invocaciones directas a `gcc`.
2. **Sandbox y Pruebas:** Delega exclusivamente en el plugin `sandbox` (`nostromo`). Si no está disponible y existen testcases, emite la advertencia correspondiente y marca los tests como omitidos.
3. **Auditoría Estática:** Invoca la colección de plugins satélites registrados (`style`, `antipatterns`, `security`, `headers_audit`, `macro_security`, `padding`, `tda_encapsulation`, etc.).
4. **Desduplicación Jerárquica:** Agrupa y unifica observaciones sobre la misma tupla `(archivo, linea, codigo_normalizado)` para evitar duplicaciones entre analizadores solapados.

---

## 5. Resiliencia y Aislamiento de Fallos

- **Fail-Open Controlado:** Si un plugin secundario lanza una excepción no controlada, agota el timeout de subproceso o emite JSON malformado, Ripley captura el error, registra un hallazgo `PLUGIN_ERROR_<NOMBRE>` con severidad `ERROR` y continúa despachando el resto de las herramientas.
- **Modo Estricto (`--strict`):** Cualquier plugin ausente o con error en ejecución marca el resultado global de la corrida como fallido (`passed = False`).

---

## 6. Plan de Testing y Verificación

1. **`tests/unit/test_entrypoints.py`:**
   - Pruebas unitarias de ejecución in-memory (`.execute()` y `.run()`).
   - Pruebas unitarias de fallback a subproceso CLI con simulación de JSON en `stdout`.
   - Pruebas unitarias de detección de herramientas ausentes y generación de `MISSING_TOOL_*`.
   - Pruebas unitarias de captura y resiliencia ante excepciones internas en plugins.
2. **`tests/unit/test_engine.py`:**
   - Prueba de integración del pipeline completo delegando en `daedalus`, `nostromo` y plugins satélites.
   - Prueba de desduplicación jerárquica de hallazgos concurrentes.
   - Prueba del comportamiento ante flags `--strict`.
3. **`tests/unit/test_style.py`:**
   - Corrección y desacoplamiento de las pruebas de estilo mediante fixtures de delegación en `gaff`.
4. **Regresión:** Ejecución del 100 % de la suite de `pytest` (295+ tests) en estado verde.
