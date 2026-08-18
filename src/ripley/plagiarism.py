"""Plagiarism and code similarity detector using AST-level tokenization and Winnowing algorithm."""

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple

from ripley.security import strip_c_comments_and_strings

C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while", "_Bool", "_Complex", "_Imaginary"
}


@dataclass
class SimilarityMatch:
    student_a: str
    student_b: str
    similarity_pct: float
    shared_fingerprints_count: int
    total_fingerprints_a: int
    total_fingerprints_b: int
    common_files: List[str] = field(default_factory=list)


def tokenize_c_code(code: str) -> List[Tuple[str, int]]:
    """Tokeniza código C normalizando identificadores y constantes para detección de estructura."""
    clean = strip_c_comments_and_strings(code)
    tokens: List[Tuple[str, int]] = []

    # Regex para tokens en C
    token_pattern = re.compile(
        r"(?P<KEYWORD>\b(?:" + "|".join(C_KEYWORDS) + r")\b)|"
        r"(?P<NUMBER>\b\d+\b)|"
        r"(?P<IDENT>[a-zA-Z_][a-zA-Z0-9_]*)|"
        r"(?P<OP>==|!=|<=|>=|&&|\|\||\+\+|--|->|[+\-*/%=<>&|^~!?:])|"
        r"(?P<PUNCT>[{}();,\[\]])"
    )

    for line_num, line in enumerate(clean.splitlines(), start=1):
        for m in token_pattern.finditer(line):
            kind = m.lastgroup
            val = m.group(0)
            if kind == "KEYWORD":
                tokens.append((f"K_{val}", line_num))
            elif kind == "IDENT":
                tokens.append(("IDENT", line_num))
            elif kind == "NUMBER":
                tokens.append(("NUM", line_num))
            elif kind == "OP":
                tokens.append((f"OP_{val}", line_num))
            elif kind == "PUNCT":
                tokens.append((f"P_{val}", line_num))

    return tokens


def compute_winnowing_fingerprints(
    tokens: List[Tuple[str, int]],
    k: int = 8,
    w: int = 4,
) -> Set[int]:
    """Calcula las huellas digitales (fingerprints) usando el algoritmo Winnowing."""
    if len(tokens) < k:
        # Si el código es muy corto, hasheamos lo que haya
        seq = "".join(t[0] for t in tokens)
        return {int(hashlib.md5(seq.encode("utf-8")).hexdigest()[:8], 16)}

    # 1. Calcular hashes de k-gramas
    k_gram_hashes: List[int] = []
    for i in range(len(tokens) - k + 1):
        k_gram_str = "".join(t[0] for t in tokens[i : i + k])
        h = int(hashlib.md5(k_gram_str.encode("utf-8")).hexdigest()[:8], 16)
        k_gram_hashes.append(h)

    # 2. Algoritmo Winnowing con ventana w
    fingerprints: Set[int] = set()
    if len(k_gram_hashes) < w:
        return set(k_gram_hashes)

    for i in range(len(k_gram_hashes) - w + 1):
        window = k_gram_hashes[i : i + w]
        min_hash = min(window)
        fingerprints.add(min_hash)

    return fingerprints


class PlagiarismDetector:
    """Detecta similitudes y sospechas de plagio entre entregas de una actividad."""

    def __init__(self, k: int = 8, w: int = 4, threshold: float = 0.70) -> None:
        self.k = k
        self.w = w
        self.threshold = threshold

    def extract_student_fingerprints(self, student_dir: Path | str) -> Tuple[Set[int], List[str]]:
        s_dir = Path(student_dir)
        # Buscar última revisión rN
        rev_dirs = [d for d in s_dir.iterdir() if d.is_dir() and re.match(r"^r\d+$", d.name)]
        if not rev_dirs:
            return set(), []

        latest_rev = sorted(rev_dirs, key=lambda d: int(d.name[1:]))[-1]
        all_fingerprints: Set[int] = set()
        c_files: List[str] = []

        for c_file in sorted(latest_rev.glob("*.c")):
            c_files.append(c_file.name)
            try:
                code = c_file.read_text(encoding="utf-8", errors="replace")
                tokens = tokenize_c_code(code)
                fps = compute_winnowing_fingerprints(tokens, k=self.k, w=self.w)
                all_fingerprints.update(fps)
            except Exception:
                continue

        return all_fingerprints, c_files

    def analyze_activity(
        self,
        activity_dir: Path | str,
        threshold: Optional[float] = None,
    ) -> List[SimilarityMatch]:
        thresh = threshold if threshold is not None else self.threshold
        act_path = Path(activity_dir)
        if not act_path.exists():
            return []

        student_dirs = [
            d for d in sorted(act_path.iterdir())
            if d.is_dir() and not d.name.startswith(".") and d.name not in ("tests", "templates")
        ]

        student_fps: Dict[str, Set[int]] = {}
        student_files: Dict[str, List[str]] = {}

        for s_dir in student_dirs:
            fps, files = self.extract_student_fingerprints(s_dir)
            if fps:
                student_fps[s_dir.name] = fps
                student_files[s_dir.name] = files

        matches: List[SimilarityMatch] = []
        students = list(student_fps.keys())

        for i in range(len(students)):
            for j in range(i + 1, len(students)):
                s_a = students[i]
                s_b = students[j]

                fps_a = student_fps[s_a]
                fps_b = student_fps[s_b]

                if not fps_a or not fps_b:
                    continue

                intersection = len(fps_a & fps_b)
                union = len(fps_a | fps_b)

                # Coeficiente de Jaccard y Contención
                jaccard = intersection / union if union > 0 else 0.0
                containment = intersection / min(len(fps_a), len(fps_b)) if min(len(fps_a), len(fps_b)) > 0 else 0.0
                similarity_score = max(jaccard, containment)

                if similarity_score >= thresh:
                    common_f = sorted(set(student_files[s_a]) & set(student_files[s_b]))
                    matches.append(
                        SimilarityMatch(
                            student_a=s_a,
                            student_b=s_b,
                            similarity_pct=round(similarity_score * 100.0, 1),
                            shared_fingerprints_count=intersection,
                            total_fingerprints_a=len(fps_a),
                            total_fingerprints_b=len(fps_b),
                            common_files=common_f,
                        )
                    )

        return sorted(matches, key=lambda m: m.similarity_pct, reverse=True)

    def generate_report(self, activity_slug: str, matches: List[SimilarityMatch]) -> str:
        lines = [
            f"# Reporte de Detección de Similitud y Plagio - {activity_slug}",
            f"**Umbral configurado:** {int(self.threshold * 100)}%",
            f"**Total de pares sospechosos detectados:** {len(matches)}",
            "",
        ]

        if not matches:
            lines.append("✓ No se detectaron pares de estudiantes con similitud superior al umbral establecido.")
        else:
            lines.extend(
                [
                    "| Estudiante A | Estudiante B | Similitud (%) | Huellas Compartidas | Archivos Comunes |",
                    "| ------------ | ------------ | ------------- | ------------------- | ---------------- |",
                ]
            )
            for m in matches:
                lines.append(
                    f"| `{m.student_a}` | `{m.student_b}` | **{m.similarity_pct:.1f}%** | {m.shared_fingerprints_count} | {', '.join(m.common_files) or '-'} |"
                )

        return "\n".join(lines) + "\n"
