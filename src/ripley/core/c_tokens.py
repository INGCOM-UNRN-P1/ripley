"""C source tokenization shared by plagiarism detection, semantic diffing and linters."""

import re
from typing import List, Tuple

from ripley.core.security import strip_c_comments_and_strings

C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while", "_Bool", "_Complex", "_Imaginary"
}


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
