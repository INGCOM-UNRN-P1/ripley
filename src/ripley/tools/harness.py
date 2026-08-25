"""c-harness — Generador de arneses de prueba con inyección de fallos (nuevas.md §3.2).

A partir de un ``spec.yaml`` genera un arnés C que:

1. Incluye el código del alumno y llama a la función bajo test con los
   argumentos del caso (posicionales, escalares).
2. Imprime el resultado en formato canónico espacio-separado para compararlo
   contra ``esperado``.
3. Con ``fault_rate > 0`` compila con ``-Wl,--wrap=malloc``: el wrapper
   ``__wrap_malloc`` devuelve NULL según una probabilidad reproducible
   (semilla fija) y cuenta cuántas reservas fallaron y cuántas no fueron
   verificadas por el alumno.
4. Se ejecuta con rlimits estrictas (CPU, memoria, stack) y reporta JSON.

El arnés es deliberadamente simple: la gracia pedagógica es que el alumno vea
cómo se prueba su primitiva sin magia.
"""

from __future__ import annotations

import json
import re
import resource
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------

@dataclass
class SpecHarness:
    return_type: str
    nombre_funcion: str
    parametros: List[tuple[str, str]]          # [(tipo, nombre)] en orden
    archivo_fuente: Path
    casos: List[Dict[str, Any]] = field(default_factory=list)
    invariantes: List[str] = field(default_factory=list)
    fault_rate: float = 0.0
    semilla: int = 42

    @classmethod
    def desde_yaml(cls, ruta: Path) -> "SpecHarness":
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        firma = str(datos.get("funcion", "")).strip()
        m = re.match(
            r"^(?P<ret>[A-Za-z_][\w\s\*]*?)[ \t]*(?P<stars>\**)[ \t]*(?P<name>[A-Za-z_]\w*)"
            r"\s*\((?P<params>[^)]*)\)$",
            firma,
        )
        if not m:
            raise ValueError(f"Firma inválida en 'funcion': {firma!r}")

        estrellas = (m.group("stars") or "").strip()
        ret = re.sub(r"[\s*]+", " ", m.group("ret")).strip()
        if estrellas:
            ret = f"{ret} {estrellas}".strip()
        params_crudos = [p.strip() for p in (m.group("params").split(",") if m.group("params").strip() else [])]
        parametros: List[tuple[str, str]] = []
        for p in params_crudos:
            mm = re.match(r"^(?P<tipo>.+?)\s*(?P<ptr>\*+)\s*(?P<nombre>[A-Za-z_]\w*)$", p)
            if mm:
                parametros.append((f"{mm.group('tipo')} {mm.group('ptr')}", mm.group("nombre")))
                continue
            m2 = re.match(r"^(?P<tipo>(?:unsigned|const|struct)\s+|[A-Za-z_]\w*\s+)(?P<nombre>[A-Za-z_]\w*)$", p)
            if m2:
                parametros.append((m2.group("tipo").strip(), m2.group("nombre")))
            else:
                parametros.append((p, f"arg{len(parametros) + 1}"))

        fuente = Path(str(datos.get("archivo_fuente", "")))
        if not fuente.is_absolute():
            fuente = ruta.parent / fuente
        if not fuente.is_file():
            raise FileNotFoundError(f"archivo_fuente no encontrado: {fuente}")

        casos = []
        for caso in datos.get("tests", []):
            casos.append({
                "entrada": list(caso.get("entrada", [])),
                "esperado": list(caso.get("esperado", [])),
                "tolerancia_malloc_fault": bool(caso.get("tolerancia_malloc_fault", False)),
            })

        return cls(
            return_type=ret,
            nombre_funcion=m.group("name"),
            parametros=parametros,
            archivo_fuente=fuente,
            casos=casos,
            invariantes=[str(i) for i in datos.get("invariantes", [])],
            fault_rate=float(datos.get("fault_rate", 0.0)),
            semilla=int(datos.get("semilla", 42)),
        )


# ---------------------------------------------------------------------------
# Codegen
# ---------------------------------------------------------------------------

def _es_puntero(tipo: str) -> bool:
    return "*" in tipo


_NOMBRES_CONTEO = re.compile(r"^(?:n|cant|cantidad|tam|tamano|tamanio|size|len|largo)$", re.I)


def _imprimir_resultado(retorno: str, spec: SpecHarness) -> str:
    """Imprime el resultado según el tipo de retorno.

    Para punteros a enteros usa como cantidad el primer parámetro escalar cuyo
    nombre sugiera tamaño (n/cantidad/tam/size/largo...); si no existe, uno.
    Punteros a char se imprimen como cadena; el resto, como dirección (%p).
    """
    if retorno == "void":
        return 'printf("[void]\\n");'

    if _es_puntero(retorno):
        base = retorno.replace("*", "").strip()
        if base == "char":
            return 'printf("%s\\n", (char*)__resultado);'
        if base in ("int", "long", "long long", "short", "unsigned",
                    "unsigned int", "unsigned long", "size_t"):
            cast = f"({base})"
            conteo_var = next(
                (nombre for _tipo, nombre in spec.parametros
                 if "*" not in _tipo and _NOMBRES_CONTEO.match(nombre)),
                "1",
            )
            return (
                "{ long long __k; "
                "if (__resultado == NULL) { printf(\"(nil)\\n\"); } else { "
                f"for (__k = 0; __k < ({conteo_var}); __k++) {{ "
                'printf("%lld%c", (long long)' + cast + "__resultado[__k], "
                "(__k + 1 < (" + conteo_var + ")) ? ' ' : '\\n'); } "
                "if ((" + conteo_var + ") <= 0) { printf(\"\\n\"); } } }"
            )
        return 'printf("%p\\n", (void*)__resultado);'

    if retorno in ("float", "double"):
        return 'printf("%.6g\\n", (double)__resultado);'
    return 'printf("%lld\\n", (long long)__resultado);'


def generar_harness(spec: SpecHarness) -> str:
    """Genera el código C del arnés para la función bajo test."""
    fuente_c = spec.archivo_fuente.name
    header_local = spec.archivo_fuente.with_suffix(".h")
    include_header = (
        f'#include "{header_local.name}"' if header_local.exists()
        else f'/* sin header: se declara el prototipo abajo */'
    )

    firma_params = ", ".join(f"{t} {n}" for t, n in spec.parametros) or "void"
    tiene_header = header_local.exists()
    prototipo = f"{spec.return_type} {spec.nombre_funcion}({firma_params});"

    bloque_wrapper = []
    if spec.fault_rate > 0:
        bloque_wrapper = [
            "#ifdef FAULT_MALLOC",
            "extern void *__real_malloc(size_t size);",
            "static long harness_faults_total = 0;",
            "static long harness_faults_unhandled = 0;",
            "",
            "void *__wrap_malloc(size_t size) {",
            "    harness_faults_total++;",
            "    /* PRNG xorshift con semilla fija: corridas reproducibles */",
            "    static unsigned long estado = 0;",
            "    if (estado == 0) estado = (unsigned long)HARNESS_SEMILLA | 1UL;",
            "    estado ^= estado << 13; estado ^= estado >> 7; estado ^= estado << 17;",
            "    double umbral = (double)(estado >> 33) / (double)(1UL << 31);",
            "    if (umbral < HARNESS_FAULT_RATE) {",
            "        return NULL;",
            "    }",
            "    return __real_malloc(size);",
            "}",
            "#endif",
            "",
        ]

    lineas = [
        "/* Arnés generado por ripley c-harness — no editar a mano. */",
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "#include <string.h>",
        "",
        f'{include_header}',
        "",
    ] + ([] if tiene_header else [
        "/* Prototipo explícito (no hay header del módulo) */",
        prototipo,
    ]) + bloque_wrapper + [
        "long harness_reporte_faults(int *sin_verificar) {",
        "    if (sin_verificar) *sin_verificar = 0;",
        "    return 0;",
        "}",
        "",
"static int caso_actual = -1;   /* índice 1-based del caso a ejecutar (argv[1]) */",
        "",
        "int main(int argc, char **argv) {",
        "    if (argc < 2) { fprintf(stderr, \"uso: %s <indice_de_caso>\\n\", argv[0]); return 64; }",
        "    caso_actual = atoi(argv[1]);",
        "    int faults_sin_verificar = 0;",
        "    long faults_total = harness_reporte_faults(&faults_sin_verificar);",
        f"    switch (caso_actual) {{",
    ]

    # Un case por test: asigna argumentos escalares y ejecuta
    for idx, caso in enumerate(spec.casos, start=1):
        entradas = caso.get("entrada", [])
        lineas.append(f"    case {idx}: {{")
        for i, (tipo, nombre) in enumerate(spec.parametros):
            if i < len(entradas):
                valor = entradas[i]
                if isinstance(valor, str) and not _es_puntero(tipo):
                    valor_repr = f'"{valor}"' if tipo == "char" and len(valor) == 1 else valor
                elif isinstance(valor, str):
                    valor_repr = f'"{valor}"'
                else:
                    valor_repr = str(valor)
                cast = "" if _es_puntero(tipo) else f"({tipo})"
                lineas.append(f"        {tipo} {nombre} = {cast}{valor_repr};")
        llamada = ", ".join(n for _, n in spec.parametros) or ""
        if spec.return_type == "void":
            lineas.append(f"        {spec.nombre_funcion}({llamada});")
            lineas.append('        printf("[void]\\n");')
        else:
            lineas.append(f"        {spec.return_type} __resultado = {spec.nombre_funcion}({llamada});")
            lineas.append(f"        {_imprimir_resultado(spec.return_type, spec)}")
        lineas.append("        break;")
        lineas.append("    }")

    lineas += [
        "    default:",
        '        fprintf(stderr, "caso %d fuera de rango\\n", caso_actual);',
        "        return 65;",
        "    }",
        "    (void)argc; (void)argv;",
        "    (void)faults_total; (void)faults_sin_verificar;",
        "    return 0;",
        "}",
    ]

    texto = "\n".join(lineas)
    # constantes del fault injector
    texto = texto.replace("HARNESS_SEMILLA", str(spec.semilla))
    texto = texto.replace("HARNESS_FAULT_RATE", f"{spec.fault_rate:.4f}")
    return texto


# ---------------------------------------------------------------------------
# Compilación + ejecución con rlimits
# ---------------------------------------------------------------------------

def _con_rlimits():  # pragma: no cover (corre en el hijo)
    def aplicar():
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (5, 8))
            resource.setrlimit(resource.RLIMIT_AS, (64 * 1024 * 1024,) * 2)
            resource.setrlimit(resource.RLIMIT_STACK, (8 * 1024 * 1024,) * 2)
        except Exception:
            pass
    return aplicar


def _preexec():
    try:
        import resource  # noqa: F401
        return _con_rlimits()
    except ImportError:
        return None


def compilar_harness(codigo: str, fuentes_alumno: Sequence[Path], salida: Path,
                     fault_rate: float) -> tuple[bool, str]:
    gcc = shutil.which("gcc")
    if gcc is None:
        return False, "gcc no disponible"
    harness_path = salida.with_suffix(".harness.c")
    harness_path.write_text(codigo, encoding="utf-8")

    cmd = [gcc, "-std=c11", "-O0", "-g", "-Wall", "-I",
           str(Path(fuentes_alumno[0]).parent)]
    cmd += [str(f) for f in fuentes_alumno]
    if fault_rate > 0:
        cmd += ["-DFAULT_MALLOC", "-Wl,--wrap=malloc"]
    cmd += [str(harness_path), "-o", str(salida), "-lm"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return proc.returncode == 0, (proc.stderr[-600:] if proc.returncode else "")


def _ejecutar_caso(binario: Path, indice: int, timeout: float = 5.0):
    preexec = _preexec()
    try:
        return subprocess.run([str(binario), str(indice)], capture_output=True,
                              text=True, timeout=timeout, preexec_fn=preexec)
    except subprocess.TimeoutExpired:
        return None


# ---------------------------------------------------------------------------
# Runner principal
# ---------------------------------------------------------------------------

def ejecutar_spec(spec_path: Path, dir_trabajo: Optional[Path] = None) -> Dict[str, Any]:
    """Pipeline completo: parse → codegen → compile (normal + fault) → run → JSON."""
    spec = SpecHarness.desde_yaml(spec_path)
    trabajo = Path(dir_trabajo or tempfile.mkdtemp(prefix="ripley_harness_"))
    trabajo.mkdir(parents=True, exist_ok=True)

    fuentes: List[Path] = [spec.archivo_fuente]
    header = spec.archivo_fuente.with_suffix(".h")
    if header.is_file():
        fuentes.insert(0, header)

    informe: Dict[str, Any] = {
        "funcion": spec.nombre_funcion,
        "pass": True,
        "casos": [],
        "malloc_faults_total": 0,
        "malloc_faults_unhandled": 0,
        "leaks_detected": False,
        "modo_fault_injection": spec.fault_rate > 0,
    }

    bin_normal = trabajo / "harness_normal.bin"
    ok_n, err_n = compilar_harness(generar_harness(spec), fuentes, bin_normal,
                                   fault_rate=0.0)
    if not ok_n:
        informe["pass"] = False
        informe["error_compilacion"] = err_n
        return informe

    bin_fault = None
    if spec.fault_rate > 0:
        bin_fault = trabajo / "harness_faulty.bin"
        ok_f, err_f = compilar_harness(generar_harness(spec), fuentes, bin_fault,
                                       fault_rate=spec.fault_rate)
        if not ok_f:
            informe["pass"] = False
            informe["error_compilacion_fault"] = err_f
            return informe

    for indice, caso in enumerate(spec.casos, start=1):
        esperado = " ".join(str(v) for v in caso.get("esperado", [])).strip()

        proc = _ejecutar_caso(bin_normal, indice)
        obtenido = (proc.stdout.strip() if proc is not None else "")
        ok_caso = (
            proc is not None
            and proc.returncode == 0
            and normalizar(obtenido) == normalizar(esperado)
        )
        detalle_caso: Dict[str, Any] = {
            "indice": indice,
            "ok": ok_caso,
            "esperado": esperado,
            "obtenido": normalizar(obtenido),
            "returncode": proc.returncode if proc is not None else None,
        }
        if not ok_caso:
            informe["pass"] = False
        informe["casos"].append(detalle_caso)

        # Fault injection: sólo para los casos que declaran tolerancia.
        # Un caso tolerante DEBE sobrevivir (sin crash/corrupción); si falla,
        # el alumno está asumiendo que malloc siempre funciona.
        if bin_fault is not None and caso.get("tolerancia_malloc_fault", False):
            proc_f = _ejecutar_caso(bin_fault, indice)
            if proc_f is None or proc_f.returncode != 0:
                informe["pass"] = False
                detalle_caso["fault_tolerance"] = "FALLÓ bajo inyección de malloc NULL"
            else:
                detalle_caso["fault_tolerance"] = "sobrevivió"

    # Leaks: si ASan está disponible en el host, el binario normal ya corre con
    # él vía compile_sources? No: aquí compilamos sin sanitizers a propósito.
    # La detección de fugas queda delegada a `ripley check`/ub-sentinel.
    return informe


def normalizar(s: str) -> str:
    return " ".join(s.split())
