# Ripley — Documentación

> CLI para procesar, compilar, verificar y calificar entregas masivas de C (Moodle o paquetes locales), con verificación temprana del lado del estudiante y flujo de auditoría docente.
> **Estado:** 74 funcionalidades · 263 tests · Python ≥ 3.11.

## Guía de lectura

| Soy… | Empezá por |
|---|---|
| **Estudiante** que quiere verificar su entrega antes de subirla | [`manual/estudiante.md`](manual/estudiante.md) |
| **Docente** que configura prácticas, evalúa y publica notas | [`manual/docente.md`](manual/docente.md) |
| **Desarrollador** que quiere extender Ripley | [`desarrollo.md`](desarrollo.md) |

## Mapa completo

### Manuales de uso
- [Manual del docente](manual/docente.md) — workspace, ciclo completo (pack → ingest → evaluate → audit → export), exámenes, plugins.
- [Manual del estudiante](manual/estudiante.md) — instalación mínima (`ripley-check`), verificación temprana con `.ripkg`, watch TDD, glosario accesible, git hooks.

### Referencia
- [Configuración `ripley.toml`](referencia/configuracion.md) — todas las secciones con valores por defecto reales.
- [Herramientas externas](referencia/herramientas-externas.md) — qué instala cada distribución y qué se degrada elegantemente.
- [Registro de mejoras](referencia/mejoras.md) — 74 funcionalidades implementadas + propuestas pendientes.
- [Especificación original](referencia/especificacion-original.md) — el documento fundacional del proyecto.

### Arquitectura
- [Visión general](arquitectura/overview.md) — capas `models/core/tools/pipeline/teacher`, CLIs separados, registro unificado de checks, formatos `.ripkg`/`.rexam`.
- [Plan de modularización](arquitectura/modularizacion.md) — cómo se llegó a esa estructura (fases F0–F5).

### Planes
- [Exam Lockout Mode](planes/exam-lockout.md) — diseño de evaluación presencial con bloqueo de red (propuesta #30).

## Instalación express

```bash
# Docente: suite completa
pipx install ripley            # comando: ripley

# Estudiante: solo verificación
pipx install ripley            # comando: ripley-check
# …o sin instalación:
python scripts/build_zipapp.py && ./dist/ripley_check.pyz --help
```

Las herramientas externas (gcc obligatorio; valgrind, cppcheck, gcov, frama-c, qemu, bwrap opcionales)
se detectan solas: lo ausente aparece como **OMITIDO con motivo**, nunca como aprobado. Detalle en
[`referencia/herramientas-externas.md`](referencia/herramientas-externas.md).
