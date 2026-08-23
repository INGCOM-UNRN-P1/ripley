"""Unit tests for Doxygen documentation auditor."""

from ripley.core.doxygen import DoxygenAuditor


def test_doxygen_auditor_detects_missing_docs():
    code = """
    int suma_sin_doc(int a, int b) {
        return a + b;
    }

    /**
     * @brief Calcula el producto de dos enteros.
     * @param x Primer factor.
     * @param y Segundo factor.
     * @return Producto de x e y.
     */
    int producto_con_doc(int x, int y) {
        return x * y;
    }
    """
    auditor = DoxygenAuditor()
    obs = auditor.audit_code(code, "test.c")

    assert len(obs) == 1
    assert obs[0].function_name == "suma_sin_doc"
    assert any("@brief" in m for m in obs[0].missing_items)
    assert any("@param a" in m for m in obs[0].missing_items)
    assert any("@return" in m for m in obs[0].missing_items)
