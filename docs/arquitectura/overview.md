# Arquitectura de Ripley

> Última actualización: 2026-08-23 · 74 funcionalidades · 263 tests · suite verde.

## 1. Visión general

Ripley resuelve dos problemas complementarios con **un solo catálogo de reglas**:

1. **Docente**: ingesta masiva de Moodle, evaluación reproducible, calificación con auditoría y exportación.
2. **Estudiante**: verificar la entrega *antes* de subirla, con exactamente las mismas reglas que usará el docente.

La separación se logra por capas + dos CLIs sobre un registro unificado de checks:

```
┌─────────────────────────────────────────────────────────────┐
│  cli/                                                       │
│    app_teacher.py (ripley)        app_student.py (ripley-check)│
│         └────────────┬───────────────────┘                     │
│  teacher/            │   pipeline/            tools/           │
│  ingest, mapping,    │   registry (CheckSpec) compiler, runner│
│  db, evaluate,       │   availability         sanitizers      │
│  reporter, exporter, │   bundle (.ripkg)      stack_usage     │
│  plagiarism, pack,   │   plugins (hooks)      coverage_fuzz…  │
│  audit               │   student_runner                       │
│         ▲            │         │                               │
│         └── core/ ◀──┴─────────┘                              │
│  analizadores estáticos puros (style, linters, ast_auditors,  │
│  p1_rules, restrictions, doxygen, padding, semantic_diff,     │
│  diffing, callgraph, flowchart, memory_visualizer, mocks,     │
│  heap_simulator, acsl, c_tokens, gcc_translator, glossary,    │
│  security, memory_animation)                                  │
│                                                               │
│  models/ → LinterObservation y contratos compartidos          │
└─────────────────────────────────────────────────────────────┘
```

**Reglas de dependencia** (verificadas por `tests/unit/test_layer_boundaries.py` con AST):

- `core` no importa `tools`, `pipeline` ni `teacher`; `tools` nunca importa `teacher`;
  la zona estudiante nunca importa `teacher` ni sus deps duras (jinja2/slugify/tomli_w).
- Los módulos planos de la raíz (`src/ripley/<mod>.py`) son **shims** de compatibilidad.

## 2. Registro unificado de checks

Cada verificación vive una sola vez, declarada como `CheckSpec`
(`pipeline/registry.py`, catálogo en `pipeline/checks.py`):

| Campo | Significado |
|---|---|
| `check_id` | Identificador estable (`ast.backward_goto`) |
| `layer` | `static` (análisis puro) / `dynamic` (procesos externos) |
| `scope` | `student` / `teacher` / `both` — qué CLI lo muestra |
| `config_section`+`toggle` | Clave de `ripley.toml` que lo habilita |
| `requires_tools` | Ejecutables externos necesarios (`valgrind`, `qemu-aarch64`…) |
| `runner` | Firma uniforme `fn(code, filename) -> [LinterObservation]` para los estáticos |

Consecuencias prácticas:

- Agregar un check nuevo = registrarlo **en un solo lugar**; aparece en
  `evaluate` (docente), `ripley-check checks list`, `doctor` y el runner estudiantil.
- `teacher/pack.py` deriva el manifiesto `.ripkg` filtrando ese registro con la config
  de la práctica → el estudiante ejecuta **exactamente** el subconjunto habilitado.
- Herramientas ausentes ⇒ check listado como **OMITIDO (motivo)** vía
  `pipeline/availability.py`; jamás silenciosamente aprobado.

## 3. Formatos de paquete

| Formato | Dirección | Contenido | Integridad |
|---|---|---|---|
| `.ripkg` | docente → estudiante | manifiesto TOML (checks on, flags gcc), testcases públicos, consigna-hash | SHA-256 por archivo + firma GPG detached opcional (`pipeline/bundle.py`) |
| `.rexam` *(plan)* | estudiante → docente | fuentes + bitácora de eventos sellada con HMAC de sesión | ver [`planes/exam-lockout.md`](../planes/exam-lockout.md) |

Ambos comparten escritor/lector seguro (validación de rutas, tamper-detection).

## 4. Flujo de auditoría docente

Máquina de estados por `(actividad, alumno)` persistida en la `.metadata.db`
de cada alumno (convención existente de ingest/evaluate/export):

```
ingresada → evaluada → en_revision → calificada → publicada
                │           │                          │
                ├──▶ sospechosa ◀──────┐              ▼
                │           └──→ en_revision       apelada → en_revision
                └── observada ──(reentrega)──▶ ingresada
```

- Solo transiciones declaradas; `--force` salta pero queda marcado FORZADA.
- Bitácora **append-only**: actor, nota, timestamp (`audit_events`).
- `ripley audit publish` mueve masivamente solo las `calificadas`.
- Detalle: [`manual/docente.md` §5](../manual/docente.md).

## 5. Plugins

`<workspace>/plugins/*.py` cargados alfabéticamente; un plugin participa declarando funciones
con el nombre del hook: `session_start`, `pre_compile`, `post_compile`, `pre_checks`,
`post_checks`, `pre_report`, `post_report`, `session_end` (+ `pre_commit_git` para shims git).
Fail-open contado, `strict` disponible, escape hatch `RIPLEY_DISABLE_PLUGINS=1`.
El runner estudiantil despacha alrededor de compilación/checks; los hallazgos llegan al plugin
vía `ctx.observations`. Git hooks: `ripley-check plugins git-hook install pre-commit`.

## 6. Matriz de herramientas externas

| Herramienta | Obligatoria | Alimenta |
|---|---|---|
| gcc | sí (casi todo) | compilación segura ASan/UBSan, fuzzing, stack-usage |
| valgrind/callgrind | no | fugas, conteo de instrucciones, benchmark energético |
| cppcheck | no | linter externo en evaluate |
| gcov | no | fuzzing guiado por cobertura |
| make | no | builds modulares estudiantiles (`build.makefile`) |
| frama-c | no | demostración WP de contratos ACSL |
| bwrap/unshare | no | sandbox sin root; exam lockout modo A2 |
| qemu-* + cross-gcc | no | matriz ARM64/RISC-V/MIPS-BE |
| Xvfb + ImageMagick | no | TPs gráficos SDL2/Raylib (captura raíz + compare AE) |
| gpg | no | firma de `.ripkg` / verificación |

Detección centralizada: `pipeline/availability.py` (`ripley-check doctor`).

## 7. Números actuales

- 74 funcionalidades documentadas ([registro](../referencia/mejoras.md)).
- 263 tests (unit + integración) · 3 skips ambientales.
- Distribuciones: `ripley` (docente) y `ripley-check` (estudiante) desde un monorepo;
  zipapp cero-instalación vía `scripts/build_zipapp.py`.
