# Manual del Docente

> Audiencia: docente/cátedra que configura prácticas, evalúa entregas y publica notas.
> Para verificación temprana del lado del alumno, ver [`estudiante.md`](estudiante.md).

## 1. Instalación

```bash
pipx install ripley          # provee el comando `ripley`
# entorno de desarrollo:
uv sync --extra dev && uv run pytest
```

Herramientas externas opcionales por funcionalidad — tabla completa en
[`../referencia/herramientas-externas.md`](../referencia/herramientas-externas.md).
Verificación del entorno: `ripley-check doctor` (sí, el comando estudiantil sirve
también para diagnosticar la máquina del docente).

## 2. Estructura del workspace

```
<workspace>/
├── practicas/
│   └── entrega-2_1236012/
│       ├── ripley.toml        # config de la práctica (checks, límites, rúbrica)
│       ├── consigna/ · pautas/
│       ├── testcases/         # .in/.out/.argv por ejercicio
│       ├── ejercicios/<slug>/solucion_modelo.c
│       └── entregas.zip?      # descarga cruda de Moodle antes de ingest
├── entregas/
│   └── entrega-2_1236012/
│       └── <alumno_slug>/     # .metadata.db + fuentes versionadas
├── templates/                 # plantillas Jinja2 de informes
└── .ripley/toolchain_snapshot.json
```

## 3. Ciclo completo paso a paso

### 3.1 Crear la práctica

```bash
ripley practica init --name "Práctica 2 - Punteros" --id 1236012
ripley testcase skeleton --exercise ej1      # esqueletos .in/.out/.argv
ripley testcase fuzz ejercicios/ej1 \        # edge cases con solución modelo como oráculo
    --reference ejercicios/ej1/solucion_modelo.c -n 6
ripley testcase map                          # mapeo interactivo fuentes↔testcases
```

Editá `practicas/<slug>/ripley.toml`: habilitá checks ([`ast_auditors`], `[padding]`,
`[restrictions]`, `[makefile]`, `[graphics]`…), límites, rúbrica. Referencia completa de
todas las claves y defaults: [`../referencia/configuracion.md`](../referencia/configuracion.md).

### 3.2 Empaquetar para los estudiantes

```bash
ripley practica pack entrega-2_1236012 -o distribuir/entrega-2.ripkg [--sign-key HUELLA_GPG]
```

El `.ripkg` lleva **solo** los checks habilitados de tu config + testcases públicos.
Publicalo en el campus; el alumno lo verifica localmente (ver manual estudiante).

### 3.3 Ingesta de Moodle

```bash
ripley ingest descargas_moodle/*.zip --workspace .
```

Aplana carpetas, filtra extensiones, hash SHA-256 y crea `entregas/<actividad>/<alumno>/.metadata.db`.

### 3.4 Evaluación

```bash
ripley evaluate --activity entrega-2_1236012 --workspace .
```

Por cada alumno compila (ASan/UBSan con fallback), corre testcases + valgrind + cppcheck,
aplica los auditores AST habilitados vía el registro unificado, genera informe `.md` por alumno
y calcula nota preliminar según `[rubric]`. Fallos de compilación quedan traducidos a lenguaje
natural dentro del informe.

### 3.5 Plagio (opcional)

```bash
ripley plagiarism --activity entrega-2_1236012   # Winnowing + Jaccard entre pares
```

Con sospechas: mové la entrega a `sospechosa` en el tablero de auditoría (§5).

### 3.6 Exportación

```bash
ripley export --activity entrega-2_1236012     # CSV Moodle + ZIP feedback + dashboard cohorte
ripley export-report entregas/*/informe.md -f pdf   # HTML/PDF autocontenido sin dependencias
```

## 4. Paquetes de práctica avanzados

| Necesidad | Cómo |
|---|---|
| TP gráfico (SDL2/Raylib) | `ribley practica graphics-capture sol_modelo.out -o golden.png` → `graphics-eval app.out -g golden.png` |
| Makefile estudiantil | `[makefile] enabled=true` + `expected_binary="app"`; el runner estudiantil usa `make` primero |
| Firmar el paquete | `pack … --sign-key GPG`; el alumno valida con `run --verify-signature` |

## 5. Flujo de auditoría docente

Estados por `(actividad, alumno)` con bitácora append-only:

```
ingresada → evaluada → en_revision → calificada → publicada → apelada → en_revision…
                │           │
                ├─▶ sospechosa ─→ en_revision
                └─▶ observada ──(reentrega)──▶ ingresada
```

```bash
ripley audit board entrega-2_1236012                       # tablero por estado
ripley audit transition entrega-2_1236012 lopez_99 en_revision -a profe2
ripley audit transition entrega-2_1236012 diaz_77 sospechosa --force -n "similitud 87%"
ripley audit history entrega-2_1236012 lopez_99            # bitácora completa
ripley audit publish  entrega-2_1236012                    # calificadas → publicada
```

Reglas: solo transiciones declaradas (`--force` queda marcado FORZADA); cada cambio registra
actor/nota/timestamp en la `.metadata.db` del alumno; solo `publicada` admite apelación.

## 6. Plugins de cátedra

Creá `<workspace>/plugins/mi_regla.py` con funciones hook (`pre_checks(ctx)`, `post_report(ctx)`…)
para inyectar observaciones propias o anotar resultados. Listado: `ripley-check plugins list`.
Escape hatch global: `RIPLEY_DISABLE_PLUGINS=1`.

## 7. Exámenes presenciales

Diseño completo (bloqueo de red nftables/bwrap, timer sellado HMAC, sobres `.rexam`,
recolección al tablero): [`../planes/exam-lockout.md`](../planes/exam-lockout.md).

## 8. Solución de problemas

| Síntoma | Causa probable | Acción |
|---|---|---|
| `evaluate` marca todo ERROR en runtime | binario ASan + límite de datos viejo | ya corregido (`RLIMIT_DATA` opt-in); actualizá ripley |
| Valgrind nunca corre | binario ausente | instalalo; `doctor` lo lista |
| Tablero vacío | workspace incorrecto | `audit board` recorre `<ws>/entregas/<act>/<alumno>/` |
| Export CSV vacío | no hay evaluaciones guardadas | corré `evaluate` primero |
| Sobres `.rexam` rechazados | HMAC inválido | revisá que el bundle usado sea el mismo del examen; estado pasa a `sospechosa` automáticamente |
