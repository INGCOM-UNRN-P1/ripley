"""Deep verification tests for Makefile-based projects."""

import os
import shutil

import pytest

from ripley.core import makefile
from ripley.core.makefile import (
    MakefileAnalyzer,
    render_ripley_mk,
    suggest_sources,
    verify_project,
)


def _tools() -> bool:
    return shutil.which("gcc") is not None and shutil.which("make") is not None


GOOD_MAKEFILE = """\
CC = gcc
CFLAGS = -Wall -std=c11

.PHONY: all clean test

all: app

app: main.o util.o
\t$(CC) $(CFLAGS) main.o util.o -o app

main.o: main.c util.h
\t$(CC) $(CFLAGS) -c main.c

util.o: util.c util.h
\t$(CC) $(CFLAGS) -c util.c

test: app
\t@./app --selftest

clean:
\trm -f *.o app
"""

BROKEN_DEPS_MAKEFILE = """\
CC = gcc
.PHONY: all clean

all: app
app: main.o util.o
\t$(CC) main.o util.o -o app
main.o: main.c
\t$(CC) -c main.c
util.o: util.c
\t$(CC) -c util.c
clean:
\trm -f *.o app
"""


@pytest.fixture()
def good_project(tmp_path):
    (tmp_path / "util.h").write_text("int duplica(int);\n", encoding="utf-8")
    (tmp_path / "util.c").write_text('#include "util.h"\nint duplica(int x){return 2*x;}\n', encoding="utf-8")
    (tmp_path / "main.c").write_text(
        '#include <stdio.h>\n#include "util.h"\n'
        'int main(int argc, char **argv){ if(argc>1 && argv[1][0]==\'-\') return 0;'
        ' printf("%d\\n", duplica(21)); return 0; }\n',
        encoding="utf-8",
    )
    (tmp_path / "Makefile").write_text(GOOD_MAKEFILE, encoding="utf-8")
    return tmp_path


@pytest.mark.skipif(not _tools(), reason="gcc/make no disponibles")
def test_good_project_passes_full_verification(good_project):
    rep = verify_project(good_project)
    assert rep.build_ok and rep.binary_path is not None
    if os.name == "nt":  # el objetivo `app` genera app.exe: no se puede verificar (y no es un error)
        assert rep.idempotent is None and "app.exe" in rep.message, rep.message
    else:
        assert rep.idempotent is True, rep.message
    assert rep.missing_header_deps == []
    assert rep.orphan_sources == []
    assert rep.clean_ok is True
    assert rep.test_ok is True
    assert rep.ok


@pytest.mark.skipif(os.name == "nt", reason="con el objetivo `app` (app.exe) make -q pide reconstruir siempre")
@pytest.mark.skipif(not _tools(), reason="gcc/make no disponibles")
def test_missing_header_dependency_detected(good_project):
    (good_project / "Makefile").write_text(BROKEN_DEPS_MAKEFILE, encoding="utf-8")
    rep = verify_project(good_project, run_test_target=False)
    assert rep.build_ok                      # compila igual…
    assert rep.idempotent is True            # …y al día
    # tocar util.h NO dispara rebuild → dependencia faltante
    assert "util.h" in rep.missing_header_deps
    assert not rep.ok


@pytest.mark.skipif(not _tools(), reason="gcc/make no disponibles")
def test_orphan_sources_detected(good_project):
    (good_project / "huérfano.c").write_text("int huerfana(void){return 1;}\n", encoding="utf-8")
    rep = verify_project(good_project)
    assert any("huérfano.c" in o for o in rep.orphan_sources)


def test_render_ripley_mk_contains_targets_and_tabs():
    mk = render_ripley_mk(["main.c", "util.c"], practica="entrega-2")
    for objetivo in ("ripley-verify:", "ripley-lint:", "ripley-watch:", ".PHONY:"):
        assert objetivo in mk
    assert "PRACTICA ?= entrega-2" in mk
    assert "--practica entrega-2" in mk
    receta = [l for l in mk.splitlines() if l.startswith("\t")][0]
    assert receta.startswith("\t")           # recetas con TAB real


def test_suggest_sources_sorted_relative(tmp_path):
    (tmp_path / "b.c").write_text("int b;\n")
    sub = tmp_path / "lib"; sub.mkdir()
    (sub / "a.c").write_text("int a;\n")
    assert suggest_sources(tmp_path) == ["b.c", "lib/a.c"]


def test_analyzer_still_flags_bad_makefile():
    obs = MakefileAnalyzer().analyze("app:\n   gcc x.c\n")
    assert any(o.severity == "ERROR" for o in obs)


@pytest.mark.skipif(not _tools(), reason="gcc/make no disponibles")
def test_en_windows_el_objetivo_sin_exe_no_es_un_rebuild_innecesario(good_project, monkeypatch):
    """En Windows gcc escribe app.exe aunque el Makefile diga `-o app`: make -q pide reconstruir
    siempre y ripley informaba «re-build innecesario (deps redundantes)», un falso positivo para
    cualquier estudiante con mingw32-make. Además os.access(X_OK) vale para todo archivo y el
    Makefile contaba como artefacto que `make clean` no borraba (N-ECO-10). Se simula con un
    Makefile que escribe app.exe, como gcc en Windows."""
    monkeypatch.setattr(makefile, "_EN_WINDOWS", True)
    (good_project / "Makefile").write_text(
        GOOD_MAKEFILE.replace("-o app", "-o app.exe").replace("rm -f *.o app", "rm -f *.o app.exe")
        .replace("./app --selftest", "./app.exe --selftest"),  # el sh de MSYS encuentra app.exe como ./app
        encoding="utf-8")
    rep = verify_project(good_project)
    assert rep.build_ok and rep.binary_path is not None and rep.binary_path.name == "app.exe"
    assert rep.idempotent is None
    assert "re-build innecesario" not in rep.message and "app.exe" in rep.message
    assert rep.missing_header_deps == []
    assert rep.clean_ok is True and not (good_project / "app.exe").exists()
    assert rep.ok


@pytest.mark.skipif(not _tools(), reason="gcc/make no disponibles")
def test_un_rebuild_innecesario_real_se_sigue_informando_en_windows(good_project, monkeypatch):
    """El caso de app.exe no tapa un Makefile que de verdad reconstruye siempre."""
    monkeypatch.setattr(makefile, "_EN_WINDOWS", True)
    (good_project / "Makefile").write_text(
        GOOD_MAKEFILE.replace("-o app", "-o app.exe").replace("all: app\n", "all: app.exe siempre\n")
        .replace("app: main.o", "app.exe: main.o").replace(".PHONY: all clean test", ".PHONY: all clean test siempre")
        + "\nsiempre:\n\t@true\n",
        encoding="utf-8")
    rep = verify_project(good_project, run_test_target=False)
    assert rep.build_ok
    assert rep.idempotent is False and "re-build innecesario" in rep.message
