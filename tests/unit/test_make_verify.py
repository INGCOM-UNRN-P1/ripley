"""Deep verification tests for Makefile-based projects."""

import shutil

import pytest

from ripley.tools.makefile import (
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
    assert rep.idempotent is True, rep.message
    assert rep.missing_header_deps == []
    assert rep.orphan_sources == []
    assert rep.clean_ok is True
    assert rep.test_ok is True
    assert rep.ok


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
