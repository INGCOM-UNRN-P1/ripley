"""ripley no sugiere instalar herramientas del ecosistema por nombre (N-RIPLEY-10, N-ECO-02).

Varios nombres (sebastian, gaff, ripley…) están tomados en PyPI por proyectos ajenos: `uv tool install
sebastian` o `pipx install ripley` instalan código de terceros. El mensaje de herramienta ausente y la
cabecera del ripley.mk que se genera para el alumno indican instalar desde git.
"""

import re
from pathlib import Path

from ripley.core.entrypoints import SatellitePluginAdapter
from ripley.core.makefile import render_ripley_mk

POR_NOMBRE = re.compile(r"(?:uv\s+tool\s+install|pipx\s+install|pip3?\s+install)\s+['\"]?(?!git\+)[\w-]+(?![\w./-])")


def test_herramienta_ausente_sugiere_instalar_desde_git(tmp_path):
    adapter = SatellitePluginAdapter(name="sebastian", tool_name="sebastian", cli_command="sebastian",
                                     entry_point=None, instance=None)
    sugerencia = adapter._handle_missing_tool(Path(tmp_path))["observaciones"][0]["suggestion"]
    assert "git+https://github.com/INGCOM-UNRN-P1/sebastian" in sugerencia
    assert not POR_NOMBRE.search(sugerencia), sugerencia


def test_ripley_mk_no_indica_instalar_por_nombre():
    cabecera = render_ripley_mk(["main.c"])[:400]
    assert not POR_NOMBRE.search(cabecera), cabecera
    assert "git+https://github.com/INGCOM-UNRN-P1/ripley" in cabecera
