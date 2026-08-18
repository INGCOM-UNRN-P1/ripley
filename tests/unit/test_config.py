"""Unit tests for Ripley configuration loader and validation."""

import pytest
from ripley.config import RipleyConfig, load_config


def test_load_default_config(tmp_path):
    # Sin archivo, retorna config por defecto válida
    cfg = load_config(tmp_path / "non_existent.toml")
    assert cfg.compiler.executable == "gcc"
    assert cfg.limits.timeout_segundos == 5
    assert cfg.limits.limite_memoria_mb == 128
    assert cfg.style.brace_style == "allman"
    assert cfg.style.require_braces is True
    assert cfg.rubric.peso_compilacion == 0.25


def test_load_custom_toml(tmp_path):
    toml_file = tmp_path / "custom.toml"
    toml_file.write_text(
        """
[compiler]
executable = "clang"
flags = ["-O2", "-Wall"]

[limits]
timeout_segundos = 10
limite_memoria_mb = 256
max_tamano_ejecutable_mb = 20

[style]
brace_style = "k&r"
require_braces = false
indent_style = "tabs"
indent_size = 8

[rubric]
peso_compilacion = 0.30
peso_linter = 0.20
peso_estilo = 0.10
peso_pruebas = 0.40
        """,
        encoding="utf-8",
    )
    cfg = load_config(toml_file)
    assert cfg.compiler.executable == "clang"
    assert cfg.compiler.flags == ["-O2", "-Wall"]
    assert cfg.limits.timeout_segundos == 10
    assert cfg.limits.limite_memoria_mb == 256
    assert cfg.style.brace_style == "k&r"
    assert cfg.style.indent_style == "tabs"
    assert cfg.rubric.peso_pruebas == 0.40


def test_rubric_weights_validation():
    cfg = RipleyConfig()
    cfg.rubric.peso_compilacion = 0.50
    cfg.rubric.peso_linter = 0.50
    cfg.rubric.peso_estilo = 0.50  # Total = 1.50
    with pytest.raises(ValueError, match="La suma de los pesos de la rúbrica"):
        cfg.validate()


def test_invalid_style_and_limits():
    cfg = RipleyConfig()
    cfg.style.brace_style = "invalid_style"
    with pytest.raises(ValueError, match="brace_style inválido"):
        cfg.validate()

    cfg = RipleyConfig()
    cfg.limits.timeout_segundos = -1
    with pytest.raises(ValueError, match="timeout_segundos debe ser mayor a 0"):
        cfg.validate()
