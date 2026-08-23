"""Unit tests for Frama-C/ACSL contract parsing and prover wrapper."""

import shutil

from ripley.formal_contracts import FormalContractAnalyzer


def test_extracts_complete_contracts():
    code = """
    /*@ requires n > 0;
        ensures \\result >= 0;
      */
    int absoluto(int n) {
        return n < 0 ? -n : n;
    }

    int sin_contrato(int x) {
        return x + 1;
    }
    """
    analyzer = FormalContractAnalyzer()
    inventory = analyzer.extract_contracts(code, "test.c")
    assert inventory.total_functions == 2
    assert len(inventory.contracts) == 1
    contrato = inventory.contracts[0]
    assert contrato.function_name == "absoluto"
    assert contrato.requires == ["n > 0"]
    assert contrato.ensures == ["\\result >= 0"]
    assert contrato.is_complete
    assert inventory.functions_without_contract == ["sin_contrato"]


def test_distinguishes_doxygen_from_acsl():
    code = """
    /**
     * @brief requires atención: esto es doxygen, no ACSL.
     */
    int documentada(int a) { return a; }

    /*@ ensures \\result == 1; */
    int con_acsl(int a) { return 1; }
    """
    analyzer = FormalContractAnalyzer()
    inventory = analyzer.extract_contracts(code, "test.c")
    assert inventory.total_functions == 2
    assert [c.function_name for c in inventory.contracts] == ["con_acsl"]
    assert inventory.functions_without_contract == ["documentada"]


def test_contract_coverage_report():
    code = """
    /*@ requires \\true; */
    int solo_requires(int a) { return a; }

    int oculta(int b) { return b; }
    """
    analyzer = FormalContractAnalyzer()
    coverage = analyzer.audit_contract_coverage(code, "test.c")
    assert coverage["total_functions"] == 2
    assert coverage["documented"] == 1
    assert coverage["coverage_pct"] == 50.0
    assert coverage["incomplete_contracts"] == ["solo_requires"]
    assert coverage["undocumented_functions"] == ["oculta"]


def test_frama_c_unavailable_degrades_gracefully(tmp_path):
    if shutil.which("frama-c"):
        pytest_skip = True  # Entorno con frama-c: se prueba el camino real en integración.
    src = tmp_path / "mini.c"
    src.write_text("int f(int a){ return a; }\n", encoding="utf-8")
    analyzer = FormalContractAnalyzer()
    result = analyzer.run_frama_c(src)
    if shutil.which("frama-c"):
        assert result.available
    else:
        assert not result.available
        assert "no está instalado" in result.message
