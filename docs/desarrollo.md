# Guía de desarrollo

## Entorno

```bash
uv sync --extra dev          # deps + pytest
uv run pytest                # suite completa (263 tests, ~15s)
uv run pytest -m integration # solo integración (algunas requieren Xvfb/valgrind)
```

Markers registrados: `integration`. Suite esperada: verde con skips ambientales
(herramientas ausentes) — nunca roja por falta de herramientas.

## Arquitectura en una página

Ver [`arquitectura/overview.md`](arquitectura/overview.md). Reglas duras:

- Capas: `models ← core ← tools ← pipeline ← teacher`; CLIs al final.
- `tests/unit/test_layer_boundaries.py` escanea imports por AST y falla si se viola
  la dirección o si `jinja2/slugify/tomli_w` aparecen fuera de `teacher/`.
- Shims planos (`src/ripley/<mod>.py`) solo re-exportan; no poner lógica ahí.

## Receta: agregar un check nuevo

1. **Analizador** en `core/` (puro, stdlib): clase con `analyze(code, filename) -> list[LinterObservation]`.
2. **Registrarlo** en `src/ripley/pipeline/checks.py`:
   ```python
   register(CheckSpec(
       check_id="ast.mi_regla",            # estable, namespace.capacidad
       title="…", layer="static", scope="both",
       config_section="ast_auditors",      # sección TOML que lo gobierna
       toggle="mi_regla",                  # clave bool dentro de la sección
       prefix="[AST:MiRegla]",
       runner=MiReglaLinter().analyze,
   ))
   ```
3. Si necesita toggle propio: sumarlo a `AstAuditorsConfig` + loader en `config.py`
   (defaults True como sus pares).
4. **Tests**: unitario del analizador + paridad dorada opcional en `tests/golden/`
   (el registro debe producir lo mismo que la invocación directa).
5. Listo: aparece en `evaluate`, `checks list`, `doctor`, y viaja a los `.ripkg`
   cuando la práctica lo habilita. Dinámicos (requieren binarios): `layer="dynamic"`,
   `requires_tools=(...)`, sin runner uniforme — se ejecutan desde comandos propios.

## Receta: comando CLI nuevo

- Estudiante → `src/ripley/cli/student.py` (**prohibido** importar `ripley.teacher`;
  el boundary test lo hace explotar). Docente → `cli/teacher.py`.
- Grupos Typer nuevos se agregan a `app.add_typer(...)` del módulo correspondiente;
  el `__init__` los fusiona automáticamente a la app plana `ripley`.

## Plugins (código de usuario, no repo)

Hooks disponibles: ver docstring de `pipeline/plugins.py`. Para probar localmente:
carpeta `plugins/ejemplo.py` junto a las fuentes + `ripley-check plugins list`.

## Empaquetado

```bash
python scripts/build_zipapp.py        # dist/ripley_check.pyz + smoke test
uv build                              # wheel/sdist de la distribución completa
```

El zipapp excluye `teacher/` y valida que arranque como ripley-check.

## CI

`.github/workflows/ci.yml`: job **full-suite** (ubuntu + valgrind/cppcheck/bwrap) y job
**student-minimal** con PATH restringido a gcc: fronteras, registro, flujo `.ripkg` y doctor
reportando omisiones. Todo commit debe dejar ambos conceptualmente verdes.

## Convención de commits

Semánticos, en español neutro o inglés técnico consistente:

```
feat(core): … | fix(tools): … | refactor(teacher): …
test(boundaries): … | docs(registry): … | build(ci): …
```

Cuidado con backticks en `-m`: bash ejecuta sustitución de comandos — usar heredoc `git commit -F -`.
