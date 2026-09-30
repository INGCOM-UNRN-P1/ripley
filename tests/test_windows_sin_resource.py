"""En Windows no existe el módulo `resource` (N-ECO-10).

ripley.core.compiler lo importaba sin protección: en el Python de Windows (el nativo o el de MSYS2
UCRT64 que trae entorno) no se podían importar compiler, runner ni pipeline.student_runner, así que
los comandos que ejecutan los programas del estudiante se caían. Se simula quitando el módulo.
"""

from __future__ import annotations

import subprocess
import sys

import ripley.core.compiler as compiler


def test_los_modulos_que_ejecutan_programas_importan_sin_resource():
    programa = ("import sys\n"
                "sys.modules['resource'] = None  # como en Windows\n"
                "import ripley.core.compiler, ripley.core.runner, ripley.pipeline.student_runner\n"
                "import ripley.core.sanitizers, ripley.core.ub_sentinel, ripley.core.property_testing\n")
    proc = subprocess.run([sys.executable, "-c", programa], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr


def test_sin_resource_no_hay_preexec_fn(monkeypatch):
    # subprocess rechaza preexec_fn en Windows: los límites quedan en el timeout.
    monkeypatch.setattr(compiler, "resource", None)
    assert compiler.limites_para_subprocess(64, 2) is None
    compiler.set_process_limits(64, 2)  # no hace nada ni falla


def test_con_resource_aplica_los_limites():
    assert callable(compiler.limites_para_subprocess(64, 2))
