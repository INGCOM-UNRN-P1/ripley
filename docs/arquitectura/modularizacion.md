# Plan de Modularización de Ripley — Verificación Temprana del Lado del Estudiante

> Estado: IMPLEMENTADO (F1–F5 completadas) — 2026-08-23
> Motivación: permitir que el estudiante verifique su entrega **antes** de subirla, en su propia computadora, sin instalar el flujo docente completo ni ejecutar verificaciones que no aplican a la práctica.

---

## 1. Objetivos

1. **Verificación temprana:** el estudiante compila, linkea y analiza su entrega localmente con *las mismas reglas* que usará el docente.
2. **Distribución mínima:** instalar solo un CLI liviano (`ripley-check`), no la suite docente (Moodle, plagio, notas, dashboards).
3. **Verificaciones por práctica:** cada práctica declara qué checks aplican; el resto ni se anuncia ni se ejecuta ("partes que no tienen sentido").
4. **Paridad garantizada:** una sola implementación de cada regla compartida por ambos lados; prohibido duplicar lógica.
5. **Evaluación autoritativa intacta:** lo que el estudiante ve es orientativo; la nota se calcula solo del lado docente.

## 2. Principios de diseño

- **Núcleo analítico puro:** los analizadores estáticos viven en una capa sin `subprocess`, sin red y sin estado global → testeable y embebible en cualquier distribución.
- **Registro unificado de checks:** cada verificación se declara con metadatos:
  ```python
  @dataclass(frozen=True)
  class CheckSpec:
      check_id: str            # "ast.backward_goto"
      scope: str               # "student" | "teacher" | "both"
      layer: str               # "static" | "dynamic" | "prover"
      requires_tools: tuple    # ("gcc",) | () | ("valgrind", "qemu-aarch64")
      config_section: str      # clave en ripley.toml
      runner: Callable
  ```
- **Manifiesto de práctica como filtro:** el docente empaqueta la configuración habilitada; el CLI estudiantil ejecuta exactamente ese subconjunto.
- **Degradación elegante formalizada:** ya existe (valgrind/frama-c/qemu opcionales); se formaliza con una matriz de disponibilidad consultable (`ripley-check doctor`).

## 3. Arquitectura destino (4 capas + 2 CLIs)

```
src/ripley/
├── models/          # LinterObservation, TestResultDetail, contratos de datos compartidos
├── core/            # Analizadores ESTÁTICOS puros (solo stdlib)
│                    #   security, style, linters, ast_auditors, p1_rules,
│                    #   restrictions, doxygen, padding_audit,
│                    #   semantic_diff, diffing, callgraph, flowchart,
│                    #   memory_visualizer, mocks, heap_simulator,
│                    #   c_tokens (ex-tokenizer de plagiarism),
│                    #   acsl (parser de formal_contracts)
├── tools/           # Wrappers de PROCESOS EXTERNOS (gcc/valgrind/qemu/bwrap...)
│                    #   compiler, runner, sanitizers, diagnostics,
│                    #   instruction_counter, stack_usage, benchmark,
│                    #   complexity_profiler, coverage_fuzzing, cross_arch,
│                    #   sandbox, socket_faults, embedded, property_testing,
│                    #   pure_functions, fuzzing, frama_c (runner WP),
│                    #   toolchain, testcases
├── pipeline/        # Registro de checks + orquestación neutra
│                    #   registry.py, availability.py, runner_check.py
├── teacher/         # Flujo DOCENTE exclusivo
│                    #   ingest, mapping, db, evaluate (rubrica/notas),
│                    #   reporter, templates, exporter, plagiarism,
│                    #   practice (autoría/sync)
└── cli/
    ├── app_teacher.py   → comando `ripley`
    └── app_student.py   → comando `ripley-check`
```

### Distribuciones (paquetes separados, monorepo)

| Distribución | Contenido | Dependencias duras | Usuario |
|---|---|---|---|
| `ripley-core` | models + core + pipeline + schema de config | stdlib | librería base |
| `ripley-check` | core + tools + CLI estudiantil | typer, rich (+ extras opcionales) | estudiante |
| `ripley` | todo (teacher incluido) | jinja2, python-slugify, tomli-w | docente |

Extras opcionales de `ripley-check`: `[fuzz]`(gcov), `[formal]`(frama-c), `[cross]`(qemu+cross-gcc), `[sandbox]`(bwrap).

**Opción cero-instalación:** generar además un `zipapp` (o script PEP 723) autocontenido de `ripley-check` descargable desde el campus; ideal para laboratorios sin permisos de instalación.

## 4. Clasificación de los módulos actuales (validada contra el grafo de imports)

Hechos del grafo actual que condicionan el re-layout:

- `security.strip_c_comments_and_strings` tiene **14 importadores** → utilidad fundacional de `core`.
- `semantic_diff.extract_c_functions` / `CFunctionAST` tienen **10** → `core`.
- `plagiarism.tokenize_c_code` es usado por `linters` y `semantic_diff` → el **tokenizador** migra a `core/c_tokens`; la comparación entre alumnos queda en `teacher/plagiarism`.
- `LinterObservation` vive hoy dentro de `linters` pero lo consumen `ast_auditors`/`padding_audit` → migra a `models`.

| Módulo actual | Destino | Nota |
|---|---|---|
| security, style, linters, ast_auditors, p1_rules, restrictions, doxygen, padding_audit | core | estáticos puros |
| semantic_diff, diffing, callgraph, flowchart, memory_visualizer, mocks, heap_simulator | core | sin subprocess |
| formal_contracts | core(acsl) + tools(frama_c) | dividir parser y prover |
| plagiarism | teacher + core(c_tokens) | corpus = dato docente |
| compiler, runner, sanitizers, diagnostics, instruction_counter, stack_usage, benchmark, complexity_profiler, coverage_fuzzing, fuzzing, property_testing, pure_functions, embedded, testcases, toolchain | tools | ambos lados según manifiesto |
| cross_arch, sandbox, socket_faults | tools (extras) | requieren binarios externos |
| ingest, mapping, db, evaluate*, reporter, templates, exporter, practice | teacher | *evaluate delega observaciones al pipeline |
| config | pipeline/schema compartido | mismo TOML para ambos lados |
| cli.py | cli/app_teacher.py + cli/app_student.py | split por comandos |

## 5. Manifiesto de práctica (`.ripkg`)

Nuevo formato de paquete que resuelve "ejecutar solo lo que aplica":

```console
# Docente (una vez por práctica):
ripley practica pack practicas/entrega-2_1236012 -o entrega-2.ripkg

# Estudiante:
ripley-check run --practica entrega-2.ripkg src/*.c
```

Contenido del `.ripkg` (zip firmable):
- `manifest.toml` — checks habilitados con parámetros (derivado del `ripley.toml` de la práctica, filtrado a `scope != teacher`), versión mínima de herramienta, hash de consigna y de la solución modelo (sin incluirla).
- `testcases_publicos/` — casos visibles para el estudiante (los ocultos quedan solo del lado docente).
- Firma GPG/Ed25519 (conecta con ítem existente del roadmap) → el CLI verifica origen e integridad.

Regla de oro: **si un check no figura en el manifiesto, `ripley-check` ni lo menciona**; si figura pero falta la herramienta externa, aparece en el informe como `OMITIDO (motivo)` — nunca como aprobado.

## 6. Flujo del estudiante

1. Instalar una sola vez: `pipx install ripley-check` (o descargar zipapp).
2. Descargar `entrega-N.ripkg` del campus.
3. `ripley-check doctor` → qué checks correrán y qué herramientas faltan.
4. `ripley-check lint src/` · `ripley-check test src/` · `ripley-check run --practica ...`
5. Informe local con los mismos códigos de observación que el informe docente (`[AST:BackwardGoto]`, etc.) para que el feedback sea consistente.

## 7. Fases de implementación

| Fase | Alcance | Criterio de salida |
|---|---|---|
| **F0** ✅ | Auditoría de imports (hecha), clasificar módulos, decidir nombres finales | Este documento aprobado |
| **F1** ✅ | Re-layout físico (`core/tools/teacher/models`) manteniendo imports compatibles vía shims; suite verde sin cambios funcionales | `pytest` verde + test de frontera que impide imports teacher→student |
| **F2** ✅ | `pipeline/registry.py` + `availability.py`; migrar `evaluate` a consumir el registro; comandos `doctor` y `checks list` | Un check nuevo se registra en UN lugar y aparece en ambos CLIs |
| **F3** ✅* | CLI dividido (`ripley` / `ripley-check`) + CI con job "entorno estudiante mínimo" | Entrypoints separados; doctor reporta omisiones explícitas. *La distribución multi-paquete queda como empaquetado posterior: hoy `ripley-check` se consume vía entrypoint o zipapp |
| **F4** ✅ | Formato `.ripkg` + `practica pack` + firma GPG opcional + `ripley-check run` | Flujo pack→run verificado end-to-end con detección de manipulación |
| **F5** ✅ | Zipapp cero-instalación + MANUAL dividido + tests de paridad dorada | Paridad registro↔analizadores directos en CI |

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Divergencia de reglas entre lados | Núcleo único + tests de paridad con fixtures doradas en F5 |
| El estudiante "juega" con el checker local | Resultado siempre orientativo; nota solo del lado docente; testcases ocultos nunca viajan |
| Fricción de instalación | Deps mínimas (typer/rich), extras opcionales, zipapp sin instalación |
| Romper configs TOML existentes | Schema compartido + loader tolerante; shims durante F1-F2 |
| Entornos de laboratorio restrictivos (userns bloqueado) | Matriz de disponibilidad explícita; sandbox cae a fallback reportado |

## 9. Métricas de éxito

- Tiempo hasta primer feedback del estudiante < 30 s en notebook promedio.
- Tamaño de `ripley-check` instalado < 15 MB sin extras.
- 0 imports cruzados teacher→student (verificado por CI con `import-linter`).
- 100% de checks del manifiesto ejecutados u omitidos-con-motivo en el informe estudiantil.
