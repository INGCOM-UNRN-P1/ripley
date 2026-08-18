"""Unit tests for Ripley templates manager."""

from ripley.templates import (
    check_templates,
    init_templates,
    list_templates,
)


def test_init_templates_creates_all_files(tmp_path):
    target_dir = tmp_path / "templates"
    created = init_templates(target_dir=target_dir)
    assert len(created) == 3
    assert (target_dir / "header.jinja2.md").exists()
    assert (target_dir / "version_section.jinja2.md").exists()
    assert (target_dir / "footer.jinja2.md").exists()

    # Re-init sin force no debe sobrescribir
    created_again = init_templates(target_dir=target_dir, force=False)
    assert len(created_again) == 0

    # Re-init con force debe sobrescribir
    created_force = init_templates(target_dir=target_dir, force=True)
    assert len(created_force) == 3


def test_list_templates(tmp_path):
    target_dir = tmp_path / "templates"
    status = list_templates(target_dir)
    assert not all(status.values())

    init_templates(target_dir=target_dir)
    status_after = list_templates(target_dir)
    assert all(status_after.values())


def test_check_templates_valid(tmp_path):
    target_dir = tmp_path / "templates"
    init_templates(target_dir=target_dir)
    is_valid, errors = check_templates(target_dir)
    assert is_valid is True
    assert len(errors) == 0


def test_check_templates_missing_required_variable(tmp_path):
    target_dir = tmp_path / "templates"
    init_templates(target_dir=target_dir)

    # Corromper version_section.jinja2.md eliminando numero_version
    version_file = target_dir / "version_section.jinja2.md"
    version_file.write_text(
        "{{ resultados_compilacion }} {{ nota_preliminar }}", encoding="utf-8"
    )

    is_valid, errors = check_templates(target_dir)
    assert is_valid is False
    assert any("numero_version" in err for err in errors)


def test_check_templates_invalid_syntax(tmp_path):
    target_dir = tmp_path / "templates"
    init_templates(target_dir=target_dir)

    # Sintaxis Jinja2 rota
    header_file = target_dir / "header.jinja2.md"
    header_file.write_text("{{ estudiante_nombre %}", encoding="utf-8")

    is_valid, errors = check_templates(target_dir)
    assert is_valid is False
    assert any("Error de sintaxis" in err for err in errors)
