# Manual del Estudiante

> Audiencia: estudiante de Programación I que quiere entregar **bien a la primera**.
> Ripley usa exactamente las mismas reglas que tu docente: lo que ves acá es lo que él ve.

## 1. Instalación (una sola vez)

```bash
# Opción A: pip
pipx install ripley            # provee `ripley-check`

# Opción B: zipapp sin instalación (necesita typer+rich en el sistema)
python scripts/build_zipapp.py # genera dist/ripley_check.pyz
./dist/ripley_check.pyz --help
```

Requisito duro: **gcc**. Opcionales (valgrind, cppcheck, gcov…) se detectan solos.

```bash
ripley-check doctor        # ¿qué checks podré correr? ¿qué me falta?
```

Todo lo ausente aparece como **OMITIDO (motivo)** en los reportes — nunca como aprobado.

## 2. Flujo con el paquete de la práctica

Tu docente publica un `entrega-N.ripkg` (checks habilitados + testcases públicos + flags oficiales).

```bash
ripley-check run --practica entrega-N.ripkg src/*.c
```

Salida típica:

```text
Verificación temprana — entrega-2_1236012
  Compilación       : OK
  Testcases públicos: 3/3
  ast.backward_goto: 1 hallazgos (0 ERROR)
    · main.c:14 Salto hacia atrás con `goto inicio;` …
  [dim]Omitidos por falta de herramientas: core.struct_padding…[/dim]

⚠ Revisá los puntos anteriores antes de entregar.
```

Reglas de oro:
- `ERROR` o testcase fallido ⇒ **no entregues todavía** (`run` sale con exit code 1).
- `OMITIDO` = tu máquina no tiene esa herramienta; el docente sí la correrá.
- El resultado es orientativo: la nota definitiva siempre es la evaluación docente.

## 3. Live TDD mientras programás

```bash
ripley-check watch --practica entrega-N.ripkg src/
```

Al cada guardado recompila con los flags oficiales, corre los testcases públicos y muestra
errores de GCC traducidos. Ctrl+C para salir. Sin paquete también funciona (solo compila).

## 4. Cuando GCC te grita

```bash
gcc main.c -o app 2> errores.log
ripley-check explain errores.log          # o: gcc … |& ripley-check explain -
```

Traducción pedagógica (~25 reglas): qué significa, por qué pasa y cómo arreglarlo —
en español, conservando el mensaje original.

## 5. Análisis suelto (sin paquete)

| Comando | Qué hace |
|---|---|
| `lint -f archivo.c` | números mágicos, duplicación, nombres, código muerto, reglas P1 (0xXXXXh) |
| `make-audit . [--build]` | calidad del Makefile + build modular vía make |
| `padding-audit *.c` | structs con padding enviados a archivos/sockets sin memset |
| `contract-check fuente.c` | contratos ACSL `requires/ensures` (+ Frama-C si está) |
| `stack-audit *.c -t 1024` | consumo de stack por función (-fstack-usage), VLA |
| `coverage-fuzz fuente.c` | fuzzing guiado por cobertura: busca inputs que rompen tu programa |
| `complexity-profile app.out` | ¿tu algoritmo es O(N) u O(N²)? regresión log-log empírica |
| `benchmark app.out` | tiempo, instrucciones y energía estimada |
| `property-test` · `pure-audit` · `mock generate` | testing avanzado en C |
| `flowchart` · `callgraph` · `memory-visualize` · `doxygen` | documentación y visualización |

## 6. Glosario visual accesible

```bash
ripley-check glossary --list
ripley-check glossary puntero heap dangling-pointer \
    --theme high-contrast --large-text -o glosario.html
```

11 conceptos con diagramas SVG: temas alto contraste / colorblind-safe, texto ampliable,
`<title>/<desc>` para lectores de pantalla y descripción larga visible bajo cada figura.
Un solo archivo HTML autocontenido.

## 7. Animaciones de memoria

¿Falla un caso de heap? Generá la animación paso a paso:

```bash
ripley-check memory-animate --ops "malloc:32:nodo1,malloc:64:nodo2,free:nodo1" -o mem.svg --gif mem.gif
```

Muestra cuándo un puntero queda **DANGLING**, marca fugas y rechaza double-free.

## 8. Verificación automática en tus commits

```bash
cd tu-repo-git
ripley-check plugins git-hook install pre-commit
git commit -m "…"   # compila stageados + 5 checks rápidos; ERROR bloquea el commit
```

Plugins propios: carpeta `plugins/` con funciones hook (`pre_compile(ctx)`, `post_checks(ctx)`…).
Desactivar todo: `RIPLEY_DISABLE_PLUGINS=1`. Quitar shim: `plugins git-hook uninstall pre-commit`.

## 9. Solución de problemas

| Síntoma | Qué significa | Qué hacer |
|---|---|---|
| `run` dice OMITIDO valgrind | no lo tenés instalado | instalalo o ignorá: el docente lo correrá allá |
| Compila acá pero falla en `run` | flags distintas a las tuyas | usá siempre `run/watch`; no compiles "a mano" para decidir |
| ASan aborta al arrancar en WSL1 | WSL1 no soporta ASan completo | usá WSL2 o Linux nativo |
| bwrap no disponible | notebook sin bubblewrap | normal: sandbox cae a fallback reportado |
| El commit git se bloquea | pre-commit encontró ERROR | corregí; `--strict` además bloquea por advertencias |
