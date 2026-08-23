"""Unit tests for student Makefile auditing and modular builds."""

import shutil

import pytest

from ripley.tools.makefile import MakefileAnalyzer, make_build


def _gcc_make() -> bool:
    return shutil.which("gcc") is not None and shutil.which("make") is not None


GOOD_MAKEFILE = """
CC = gcc
CFLAGS = -Wall -std=c11

.PHONY: all clean

all: app

app: main.o util.o
\t$(CC) $(CFLAGS) main.o util.o -o app

clean:
\trm -f *.o app
"""

BAD_MAKEFILE = """
app:
   gcc main.c -o app
"""


def test_good_makefile_passes_clean():
    obs = MakefileAnalyzer().analyze(GOOD_MAKEFILE)
    assert obs == []


def test_spaces_instead_of_tabs_is_error():
    obs = MakefileAnalyzer().analyze(BAD_MAKEFILE)
    assert any(o.severity == "ERROR" and "missing separator" in o.message for o in obs)


def test_missing_targets_and_phony_detected():
    text = "app:\n\tgcc main.c -o app\n"
    obs = MakefileAnalyzer().analyze(text)
    msgs = " ".join(o.message for o in obs)
    assert "all" in msgs
    assert "clean" in msgs
    assert ".PHONY" in msgs
    assert any("hardcodeado" in o.message or "hardcodeado" in o.suggestion for o in obs)


def test_first_target_must_be_all():
    all_segundo = (
        "CC = gcc\n"
        ".PHONY: all clean app\n"
        "app:\n"
        "\t@echo hola\n"
        "all: app\n"
        "clean:\n"
        "\t@echo limpio\n"
    )
    obs = MakefileAnalyzer().analyze(all_segundo)
    assert any("primer objetivo" in o.message for o in obs)

    obs_good = MakefileAnalyzer().analyze(GOOD_MAKEFILE)
    assert not any("primer objetivo" in o.message for o in obs_good)


@pytest.mark.skipif(not _gcc_make(), reason="gcc/make no disponibles")
def test_make_build_discovers_binary(tmp_path):
    (tmp_path / "main.c").write_text('#include <stdio.h>\nint main(void){puts("mk");return 0;}\n')
    (tmp_path / "Makefile").write_text(
        "CC=gcc\n.PHONY: all clean\nall: app\napp: main.c\n\t$(CC) main.c -o app\nclean:\n\trm -f app\n",
        encoding="utf-8",
    )
    result = make_build(tmp_path, timeout_sec=30)
    assert result.success
    assert result.binary_path is not None and result.binary_path.name == "app"


@pytest.mark.skipif(not _gcc_make(), reason="gcc/make no disponibles")
def test_make_build_failure_translates_errors(tmp_path):
    (tmp_path / "main.c").write_text("int main(void){ return x; }\n")
    (tmp_path / "Makefile").write_text(
        "all: app\napp: main.c\n\tgcc main.c -o app\n",
        encoding="utf-8",
    )
    result = make_build(tmp_path, timeout_sec=30)
    assert not result.success
    assert "x" in result.human_errors and "declarado" in result.human_errors


@pytest.mark.skipif(not _gcc_make(), reason="gcc/make no disponibles")
def test_make_build_without_makefile_reports_cleanly(tmp_path):
    result = make_build(tmp_path)
    assert not result.success
    assert "Sin Makefile" in result.message
