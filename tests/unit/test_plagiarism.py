"""Unit tests for plagiarism and code similarity detection."""

from pathlib import Path
from ripley.plagiarism import (
    PlagiarismDetector,
    compute_winnowing_fingerprints,
    tokenize_c_code,
)


def test_tokenize_and_fingerprints():
    code1 = """
    #include <stdio.h>
    int main() {
        int variable_uno = 10;
        int variable_dos = 20;
        printf("%d\\n", variable_uno + variable_dos);
        return 0;
    }
    """
    # Renombrado de variables y cambio de formato
    code2 = """
    #include <stdio.h>
    int main()
    {
        int x = 10;
        int y = 20;
        printf("%d\\n", x + y);
        return 0;
    }
    """
    tokens1 = tokenize_c_code(code1)
    tokens2 = tokenize_c_code(code2)

    # Las secuencias de tipos de tokens deben ser idénticas a pesar del renombrado
    assert [t[0] for t in tokens1] == [t[0] for t in tokens2]

    fps1 = compute_winnowing_fingerprints(tokens1, k=6, w=3)
    fps2 = compute_winnowing_fingerprints(tokens2, k=6, w=3)
    assert len(fps1 & fps2) == len(fps1)


def test_plagiarism_detector_detects_copied_code(tmp_path):
    ws = tmp_path
    act_slug = "entrega-1_1228009"
    act_dir = ws / act_slug
    act_dir.mkdir(parents=True, exist_ok=True)

    # Estudiante 1
    s1_r1 = act_dir / "alumno-a_111" / "r1"
    s1_r1.mkdir(parents=True, exist_ok=True)
    (s1_r1 / "ej1.c").write_text(
        """
        #include <stdio.h>
        int calcular(int a, int b) {
            int resultado = 0;
            for (int i = 0; i < a; i++) {
                resultado += b * 2 + i;
            }
            return resultado;
        }
        int main() {
            printf("%d\\n", calcular(10, 5));
            return 0;
        }
        """,
        encoding="utf-8",
    )

    # Estudiante 2 (Copia con renombrado de variables)
    s2_r1 = act_dir / "alumno-b_222" / "r1"
    s2_r1.mkdir(parents=True, exist_ok=True)
    (s2_r1 / "ej1.c").write_text(
        """
        #include <stdio.h>
        int calcular(int x, int y) {
            int res = 0;
            for (int j = 0; j < x; j++) {
                res += y * 2 + j;
            }
            return res;
        }
        int main() {
            printf("%d\\n", calcular(10, 5));
            return 0;
        }
        """,
        encoding="utf-8",
    )

    # Estudiante 3 (Código completamente diferente)
    s3_r1 = act_dir / "alumno-c_333" / "r1"
    s3_r1.mkdir(parents=True, exist_ok=True)
    (s3_r1 / "ej1.c").write_text(
        """
        #include <stdio.h>
        int main() {
            char buffer[64];
            fgets(buffer, sizeof(buffer), stdin);
            puts(buffer);
            return 0;
        }
        """,
        encoding="utf-8",
    )

    detector = PlagiarismDetector(k=6, w=3, threshold=0.75)
    matches = detector.analyze_activity(act_dir)

    assert len(matches) == 1
    match = matches[0]
    assert "alumno-a_111" in (match.student_a, match.student_b)
    assert "alumno-b_222" in (match.student_a, match.student_b)
    assert match.similarity_pct >= 75.0

    report = detector.generate_report(act_slug, matches)
    assert "alumno-a_111" in report
    assert "alumno-b_222" in report
