"""El compilador interno funciona con el toolchain de Windows (N-ECO-10).

MinGW (MSYS2 UCRT64) no trae los sanitizers y avisa «cannot find -lasan» (no «libasan»), y escribe el
binario con .exe: el reintento sin -fsanitize no se activaba y la compilación se daba por fallida
aunque el .exe existiera. Se imita a MinGW con un compilador falso.
"""

import os
import stat
import sys
from pathlib import Path

import pytest

import ripley.core.compiler as compiler
from ripley.config import CompilerConfig, LimitsConfig, SandboxConfig

MINGW_FALSO = """import sys
from pathlib import Path
args = sys.argv[1:]
if any(a.startswith("-fsanitize=") for a in args):
    sys.stderr.write("D:/a/_temp/msys64/ucrt64/bin/ld.exe: cannot find -lasan: No such file or directory\\n")
    sys.exit(1)
salida = Path(args[args.index("-o") + 1])
Path(str(salida) + ".exe").write_bytes(b"MZ")
"""


@pytest.mark.skipif(os.name == "nt", reason="el compilador falso es un script con shebang")
def test_compila_sin_sanitizers_y_devuelve_el_exe(tmp_path, monkeypatch):
    falso = tmp_path / "gcc-mingw"
    falso.write_text(f"#!{sys.executable}\n{MINGW_FALSO}", encoding="utf-8")
    falso.chmod(falso.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(compiler, "ES_WINDOWS", True)
    c = compiler.Compiler(
        CompilerConfig(executable=str(falso), flags=["-std=c11", "-fsanitize=address,undefined"]),
        LimitsConfig(timeout_segundos=15), SandboxConfig(enabled=False))
    (tmp_path / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    res = c.compile([tmp_path / "main.c"], tmp_path / "student_bin")
    assert res.success, res.stderr
    assert res.binary_path == tmp_path / "student_bin.exe"
