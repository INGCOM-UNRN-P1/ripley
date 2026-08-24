# Ripley

**CLI para procesar, compilar, verificar y calificar entregas masivas de C** — con verificación
temprana del lado del estudiante y flujo de auditoría docente.

[![CI](https://github.com/anomalyco/ripley/actions/workflows/ci.yml/badge.svg)](../../actions)
`74 funcionalidades · 263 tests · Python ≥ 3.11`

## Dos herramientas, un mismo catálogo de reglas

| | Docente | Estudiante |
|---|---|---|
| Comando | `ripley` | `ripley-check` |
| Ingesta Moodle + evaluación + notas | ✔ | — |
| Auditoría con estados (borrador→publicada) | ✔ | — |
| Plagio (Winnowing) · export CSV/dashboard | ✔ | — |
| Compilar, lintear, correr testcases públicos | ✔ | ✔ |
| Watch TDD · traductor GCC · glosario accesible | ✔ | ✔ |

El estudiante recibe un paquete **`.ripkg`** firmado por el docente con los checks habilitados:
`ripley-check run --practica entrega-2.ripkg src/*.c` ejecuta exactamente ese subconjunto.
Lo que falta en su máquina aparece como **OMITIDO con motivo**, nunca como aprobado.

## Instalación

```bash
pipx install ripley                 # ambos comandos
# estudiante sin instalación:
python scripts/build_zipapp.py && ./dist/ripley_check.pyz doctor
```

Requiere Python ≥ 3.11 y gcc. Valgrind/cppcheck/gcov/frama-c/qemu/bwrap/Xvfb son opcionales
por funcionalidad ([matriz completa](docs/referencia/herramientas-externas.md)).

## 30 segundos de demostración

```bash
# docente: empaqueta la práctica
ripley practica pack entrega-2_1236012 -o entrega-2.ripkg

# estudiante: verifica antes de entregar
ripley-check run --practica entrega-2.ripkg solucion.c
ripley-check watch --practica entrega-2.ripkg src/     # live TDD al guardar
```

## Documentación

Toda la documentación vive en [`docs/`](docs/index.md):

- 📘 [Manual del docente](docs/manual/docente.md)
- 📗 [Manual del estudiante](docs/manual/estudiante.md)
- ⚙️ [Configuración `ripley.toml`](docs/referencia/configuracion.md)
- 🏛️ [Arquitectura](docs/arquitectura/overview.md) · [Desarrollo](docs/desarrollo.md)
- 📋 [Registro de mejoras (74)](docs/referencia/mejoras.md) · [Especificación original](docs/referencia/especificacion-original.md)

## Desarrollo

```bash
uv sync --extra dev && uv run pytest    # suite verde esperada (skips ambientales permitidos)
```
Guía de contribución y recetas (agregar checks, comandos, plugins): [`docs/desarrollo.md`](docs/desarrollo.md).
