# Referencia — `ripley.toml`

> Valores por defecto reales tomados de `src/ripley/config.py` (RipleyConfig).
> Una práctica sobreescribe lo que necesite en su propio `practicas/<slug>/ripley.toml`;
> el resto hereda estos defaults.

## Secciones y claves

| Sección | Clave | Default | Notas |
|---|---|---|---|
| `[compiler]` | enabled / executable / flags | true · gcc · `-Wall -Wextra -pedantic -std=c11 -fsanitize=address,undefined …` | ASan+UBSan por defecto; fallback automático sin libasan |
| `[limits]` | timeout_segundos / limite_memoria_mb / max_tamano_ejecutable_mb | 5 · 128 · 10 | RLIMIT_CPU siempre; RLIMIT_DATA opt-in (compatibilidad ASan) |
| `[templates]` | ruta_plantillas | templates/ | informes Jinja2 |
| `[cppcheck]` | enabled / ejecutable / parametros | true · cppcheck · `--enable=all --inline-suppr --suppress=missingIncludeSystem --suppress=staticFunction` | requiere binario instalado |
| `[style]` | enabled, brace_style(allman\|k&r), require_braces, indent_style(spaces\|tabs), indent_size(4), spacing_*, no_trailing_whitespace, max_blank_lines(2) | | |
| `[p1_rules]` | enabled | true | reglas 0xXXXXh del apunte P1 |
| `[linters]` | enabled(false) + dead_code/magic_numbers/internal_clones/naming(true), doxygen(false) | | bloque maestro off por defecto |
| `[ast_auditors]` | enabled(**false**) + 13 toggles true: const_correctness, short_circuit, deep_free, string_null, variable_shadowing, dangling_stack_pointer, overengineering, evaluation_order, string_literal_write, backward_goto, deprecated_api, enum_bitmask, loop_termination | | el registro replica 1:1 estos toggles |
| `[flowchart]` / `[callgraph]` / `[memory_visualizer]` | enabled(false) / format(mermaid); callgraph.include_stdlib(false) | | generación de diagramas en evaluate |
| `[property_testing]` | enabled(false) / properties[idempotence, commutativity, sort_invariant] | | |
| `[pure_functions]` | enabled(false) / functions[] | | nombres a auditar como puras/const |
| `[padding]` | enabled | false | structs con padding enviados a I/O sin memset |
| `[makefile]` | enabled(false), prefer_makefile(true), executable(make), target(all), timeout_segundos(30), expected_binary("") | build modular estudiantil. Circuito integral adicional vía CLI: `make-audit --full` y generador `make-integrate` |
| `[graphics]` | enabled(false), screen(1280x720x24), settle_seconds(1.0), max_diff_pixels(100), display_base(90), capture/compare(import/compare) | | TPs SDL2/Raylib bajo Xvfb |
| `[restrictions]` | enabled(false) / forbidden_constructs[] / required_constructs[] | | blacklist/whitelist del enunciado |
| `[doxygen]` | enabled(false) + require_brief/params/return(true) | | |
| `[valgrind]` | enabled(true) / tolerar_fugas_en_error(true) / flags[leak-check=full, show-leak-kinds=all, track-origins=yes, error-exitcode=1] | | requiere valgrind instalado |
| `[rubric]` | peso_compilacion(.25)/peso_linter(.25)/peso_estilo(.15)/peso_pruebas(.35) | validado: suma = 1.0 | |
| `[security]` | enabled(true) / forbidden_calls[system, fork, execv…] / forbidden_headers[unistd.h, sys/socket.h…] | | escáner preventivo |
| `[sandbox]` | enabled(false) / provider(bubblewrap) | | ejecución de pruebas aislada |
| `[[custom_tools]]` | name/command/enabled/stage(source\|binary\|folder)/timeout_segundos | | herramientas arbitrarias; vars `{source} {binary} {folder} {filename} {stem}` |

## Ejemplo mínimo de práctica

```toml
[compiler]
flags = ["-Wall", "-Wextra", "-std=c11", "-fsanitize=address,undefined"]

[limits]
timeout_segundos = 5

[ast_auditors]
enabled = true
backward_goto = true
deprecated_api = true
loop_termination = true

[restrictions]
enabled = true
forbidden_constructs = ["goto", "<string.h>"]
required_constructs  = ["struct", "malloc"]

[rubric]
peso_compilacion = 0.25
peso_linter      = 0.25
peso_estilo      = 0.15
peso_pruebas     = 0.35
```

## Cómo se propaga al estudiante

`ripley practica pack <slug>` lee esta config, consulta el registro unificado de checks
y escribe en el `.ripkg` **solo** los habilitados visibles para estudiante + los flags de
compilador. El alumno corre ese subconjunto exacto con `ripley-check run`.
