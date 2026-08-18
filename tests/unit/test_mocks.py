"""Unit tests for Mock generator."""

from pathlib import Path
from ripley.mocks import MockGenerator


def test_mock_generator_creates_headers_and_sources(tmp_path):
    header_c = tmp_path / "sensor.h"
    header_c.write_text(
        """
        int leer_temperatura(int sensor_id);
        void activar_alarma(void);
        """,
        encoding="utf-8",
    )

    gen = MockGenerator()
    h_file, c_file = gen.generate_files(header_c, tmp_path)

    assert h_file.exists()
    assert c_file.exists()

    h_text = h_file.read_text(encoding="utf-8")
    c_text = c_file.read_text(encoding="utf-8")

    # Header assertions
    assert "mock_leer_temperatura_call_count" in h_text
    assert "mock_leer_temperatura_set_return" in h_text
    assert "reset_all_mocks" in h_text

    # Source assertions
    assert "int mock_leer_temperatura_call_count = 0;" in c_text
    assert "void reset_all_mocks(void)" in c_text
    assert "int leer_temperatura(int sensor_id)" in c_text
