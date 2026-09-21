"""Linters AST de flujo: goto, APIs obsoletas, máscaras enum y terminación de bucles."""

import re
from typing import Dict, List, Optional, Set, Tuple

from ripley.core.linters import LinterObservation
from ripley.core.security import strip_c_comments_and_strings



# ============================================================================
# 12. Control de Saltos Hacia Atrás con goto
# ============================================================================
class BackwardGotoLinter:
    """Detecta saltos hacia atrás con goto que emulan bucles desestructurados (spaghetti code)."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        lines = clean.splitlines()

        # 1. Registrar etiquetas y sus líneas
        labels: Dict[str, int] = {}
        label_regex = re.compile(r"^[ \t]*(?P<label>[a-zA-Z_][a-zA-Z0-9_]*)\s*:", re.MULTILINE)

        for m in label_regex.finditer(clean):
            lbl = m.group("label")
            if lbl not in ("case", "default"):
                line = clean[: m.start()].count("\n") + 1
                labels[lbl] = line

        # 2. Registrar instrucciones goto y comprobar si la etiqueta está antes en el código
        goto_regex = re.compile(r"\bgoto\s+(?P<label>[a-zA-Z_][a-zA-Z0-9_]*)\s*;", re.MULTILINE)

        for m in goto_regex.finditer(clean):
            lbl = m.group("label")
            goto_line = clean[: m.start()].count("\n") + 1
            if lbl in labels:
                target_line = labels[lbl]
                if target_line < goto_line:
                    observations.append(
                        LinterObservation(
                            linter_name="backward_goto",
                            filename=filename,
                            line=goto_line,
                            severity="ADVERTENCIA",
                            message=f"Salto hacia atrás con `goto {lbl};` hacia la línea {target_line} (bucle desestructurado).",
                            suggestion="Los saltos hacia atrás generan código espagueti. Reemplazá el `goto` por estructuras de control estructuradas estándar (`while`, `for`, `do-while`).",
                        )
                    )

        return observations


# ============================================================================
# 13. Detector de Funciones Obsoletas y Desaconsejadas (Deprecated C API)
# ============================================================================
class DeprecatedAPILinter:
    """Alerta sobre funciones de la biblioteca estándar obsoletas o inseguras,
    sugiriendo sus reemplazos modernos."""

    DEPRECATED_FUNCTIONS: Dict[str, Tuple[str, str]] = {
        # función: (reemplazo, justificación)
        "gets": ("fgets", "Imposible limitar el tamaño leído; eliminada del estándar desde C11."),
        "strcpy": ("strncpy / snprintf", "Sin control de desbordamiento del buffer destino."),
        "strcat": ("strncat / snprintf", "Sin control de desbordamiento del buffer destino."),
        "sprintf": ("snprintf", "Sin límite de caracteres escritos; riesgo de desbordamiento."),
        "vsprintf": ("vsnprintf", "Sin límite de caracteres escritos; riesgo de desbordamiento."),
        "strtok": ("strtok_r", "No reentrante: usa estado interno compartido entre llamadas."),
        "tmpnam": ("mkstemp", "Genera condiciones de carrera (TOCTOU) al crear el archivo."),
        "asctime": ("strftime", "Formato fijo, buffer estático compartido y obsoleta en C23."),
        "ctime": ("strftime", "Buffer estático compartido y sin control de zona horaria."),
        "atoi": ("strtol", "No detecta errores de conversión ni desbordes."),
        "atol": ("strtol", "No detecta errores de conversión ni desbordes."),
        "atof": ("strtod", "No detecta errores de conversión ni desbordes."),
        "rewind": ("fseek", "No reporta errores (return void); fseek permite verificar."),
    }

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)
        lines = clean.splitlines()

        # Excluir declaraciones/prototipos y definiciones propias: solo marcar invocaciones.
        call_regex = re.compile(r"\b(?P<fn>[a-zA-Z_][a-zA-Z0-9_]*)\s*\(")

        for line_idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for match in call_regex.finditer(line):
                fn = match.group("fn")
                if fn not in self.DEPRECATED_FUNCTIONS:
                    continue
                replacement, reason = self.DEPRECATED_FUNCTIONS[fn]
                observations.append(
                    LinterObservation(
                        linter_name="deprecated_api",
                        filename=filename,
                        line=line_idx + 1,
                        severity="ADVERTENCIA",
                        message=f"Uso de la función obsoleta `{fn}()`: {reason}",
                        suggestion=f"Reemplazá `{fn}()` por `{replacement}`.",
                    )
                )

        return observations


# ============================================================================
# 14. Auditoría de Enums como Máscaras de Bits
# ============================================================================
class EnumBitmaskLinter:
    """Detecta operaciones a nivel de bits (&, |, ^, ~) aplicadas a constantes
    de enum cuyos valores no son potencias de dos (máscaras de bits mal formadas)."""

    def _parse_enum_values(self, clean: str) -> List[Dict[str, int]]:
        """Extrae los enumeradores de cada bloque enum con su valor efectivo."""
        groups: List[Dict[str, int]] = []
        enum_regex = re.compile(r"\benum\s+(?:[a-zA-Z_][a-zA-Z0-9_]*)?\s*\{(?P<body>[^}]*)\}", re.DOTALL)

        for m in enum_regex.finditer(clean):
            body = m.group("body")
            next_value = 0
            members: Dict[str, int] = {}
            for item in body.split(","):
                item = item.strip()
                if not item:
                    continue
                assign = re.match(r"^(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?P<expr>.+)$", item, re.DOTALL)
                if assign:
                    value = self._eval_const_expr(assign.group("expr"))
                    if value is None:
                        members = {}  # Expresiones no evaluables: descartar grupo.
                        break
                    next_value = value + 1
                    members[assign.group("name")] = value
                else:
                    name_match = re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", item)
                    if not name_match:
                        continue
                    members[item] = next_value
                    next_value += 1
            if members:
                groups.append(members)

        return groups

    def _eval_const_expr(self, expr: str) -> Optional[int]:
        """Evalúa expresiones constantes simples: enteros, hex y shifts `1 << n`."""
        expr = expr.strip().rstrip("}")
        try:
            if re.fullmatch(r"[+-]?0[xX][0-9a-fA-F]+|[+-]?\d+", expr):
                return int(expr, 0)
            shift = re.fullmatch(r"(?P<base>[+-]?\d+)\s*<<\s*(?P<sh>\d+)", expr)
            if shift:
                return int(shift.group("base")) << int(shift.group("sh"))
        except (ValueError, OverflowError):
            pass
        return None

    @staticmethod
    def _is_power_of_two(value: int) -> bool:
        return value > 0 and (value & (value - 1)) == 0

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)

        non_mask_names: Set[str] = set()
        for members in self._parse_enum_values(clean):
            if members and all(self._is_power_of_two(v) or v == 0 for v in members.values()):
                continue  # Grupo válido para máscaras de bits.
            non_mask_names.update(members.keys())

        if not non_mask_names:
            return observations

        names_regex = "|".join(re.escape(n) for n in sorted(non_mask_names))
        bitwise_regex = re.compile(
            rf"(?:\b(?:{names_regex})\b\s*(?P<op1>[&|^]|<<|>>))|((?P<op2>[&|^~]|<<|>>)\s*\b(?:{names_regex})\b)"
        )

        for line_idx, line in enumerate(clean.splitlines()):
            # Ignorar operadores lógicos && y ||
            workline = line.replace("&&", " ").replace("||", " ")
            if bitwise_regex.search(workline):
                observations.append(
                    LinterObservation(
                        linter_name="enum_bitmask",
                        filename=filename,
                        line=line_idx + 1,
                        severity="ADVERTENCIA",
                        message=f"Operación a nivel de bits sobre constantes de enum que no son potencias de dos ({names_regex}).",
                        suggestion='Para usar enums como máscaras de bits, declará los valores como potencias de dos: `FLAG_A = 1 << 0`, `FLAG_B = 1 << 1`, etc.',
                    )
                )

        return observations


# ============================================================================
# 15. Demostrador Heurístico de Terminación de Bucles
# ============================================================================
class LoopTerminationLinter:
    """Analiza si las variables de control de un bucle son modificadas dentro
    del cuerpo o cláusula de incremento; de lo contrario, advierte posible
    bucle infinito."""

    @staticmethod
    def _extract_body_block(code: str, open_brace_idx: int) -> str:
        """Extrae el bloque balanceado de llaves que comienza en open_brace_idx."""
        depth = 0
        for i in range(open_brace_idx, len(code)):
            if code[i] == "{":
                depth += 1
            elif code[i] == "}":
                depth -= 1
                if depth == 0:
                    return code[open_brace_idx : i + 1]
        return code[open_brace_idx:]

    def _is_mutated(self, var: str, block: str) -> bool:
        """Detecta asignaciones, incrementos, lecturas por scanf o paso por referencia."""
        patterns = [
            rf"\b{var}\s*(?:\+\+|--)",
            rf"(?:\+\+|--)\s*{var}\b",
            rf"\b{var}\s*(?:[^=!<>]=)(?!=)",
            rf"\b{var}\s*(?:\+=|-=|\*=|/=|%=|\|=|&=|\^=|<<=|>>=)",
            rf"&\s*{var}\b",
        ]
        if any(re.search(p, block) for p in patterns):
            return True
        # Lectura por biblioteca estándar: scanf("%d", &var), fgets(var, ...), gets(var)
        io_call = re.search(rf"\b(?:scanf|fgets|gets|getchar)\s*\([^;]*\b{var}\b", block)
        return io_call is not None

    def _condition_vars(self, condition: str) -> Set[str]:
        """Identificadores de la condición excluyendo keywords, literales y llamadas."""
        condition = re.sub(r"\b[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)", " ", condition)  # llamadas
        candidates = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", condition)
        reserved = {"sizeof", "NULL", "true", "false", "EOF"}
        return {c for c in candidates if c not in reserved and not c.isupper()}

    def analyze(self, code: str, filename: str = "archivo.c") -> List[LinterObservation]:
        observations: List[LinterObservation] = []
        clean = strip_c_comments_and_strings(code)

        def balanced_paren(start: int) -> Tuple[str, int]:
            """Contenido balanceado entre paréntesis desde 'start' (índice de '(')."""
            depth = 0
            for i in range(start, len(clean)):
                if clean[i] == "(":
                    depth += 1
                elif clean[i] == ")":
                    depth -= 1
                    if depth == 0:
                        return clean[start + 1 : i], i
            return "", len(clean) - 1

        # --- while (...) { ... } ---
        for m in re.finditer(r"\bwhile\s*\(", clean):
            # Omitir la condición de cola de un do-while (ya analizada en su propio pase).
            if clean[: m.start()].rstrip().endswith("}"):
                continue
            cond, close_idx = balanced_paren(m.end() - 1)
            cond_vars = self._condition_vars(cond)
            if not cond_vars:
                continue
            rest = clean[close_idx + 1 :].lstrip()
            body_offset = close_idx + 1 + (len(clean[close_idx + 1 :]) - len(rest))
            if rest.startswith("{"):
                body = self._extract_body_block(clean, body_offset)
            else:
                body = rest.split(";")[0]  # Cuerpo sin llaves: hasta ';'
            non_mutated = [v for v in cond_vars if not self._is_mutated(v, body)]
            if len(non_mutated) == len(cond_vars):
                line = clean[: m.start()].count("\n") + 1
                observations.append(
                    LinterObservation(
                        linter_name="loop_termination",
                        filename=filename,
                        line=line,
                        severity="ADVERTENCIA",
                        message=f"Posible bucle infinito: ninguna variable de la condición `{cond.strip()}` es modificada dentro del cuerpo del `while`.",
                        suggestion="Asegurate de que alguna variable de la condición de corte se actualice dentro del bucle (contador, centinela con lectura, etc.).",
                    )
                )

        # --- do { ... } while (...); ---
        for m in re.finditer(r"\bdo\s*\{", clean):
            body = self._extract_body_block(clean, m.end() - 1)
            tail = clean[m.end() :]
            cond_m = re.search(r"\}\s*while\s*\(", tail)
            if not cond_m:
                continue
            paren_start = m.end() + cond_m.end() - 1
            cond, _ = balanced_paren(paren_start)
            cond_vars = self._condition_vars(cond)
            if cond_vars and all(not self._is_mutated(v, body) for v in cond_vars):
                line = clean[: m.start()].count("\n") + 1
                observations.append(
                    LinterObservation(
                        linter_name="loop_termination",
                        filename=filename,
                        line=line,
                        severity="ADVERTENCIA",
                        message=f"Posible bucle infinito: ninguna variable de la condición `{cond.strip()}` es modificada dentro del cuerpo del `do-while`.",
                        suggestion="Verificá que la condición del `do-while` dependa de una variable actualizada dentro del bloque.",
                    )
                )

        # --- for (init; cond; incr) { ... } ---
        for m in re.finditer(r"\bfor\s*\(", clean):
            header, close_idx = balanced_paren(m.end() - 1)
            parts = self._split_header(header)
            if parts is None:
                continue  # No es un for canónico: omitir.
            _init, cond, incr = parts

            # for(;;): infinito por construcción cuando además no hay break analizable.
            if not cond.strip():
                line = clean[: m.start()].count("\n") + 1
                observations.append(
                    LinterObservation(
                        linter_name="loop_termination",
                        filename=filename,
                        line=line,
                        severity="ADVERTENCIA",
                        message="Bucle `for` sin condición de corte (`for (;;)`): infinito salvo `break` interno.",
                        suggestion="Agregá una condición explícita o documentá el `break` que garantiza la salida.",
                    )
                )
                continue

            rest = clean[close_idx + 1 :].lstrip()
            body_offset = close_idx + 1 + (len(clean[close_idx + 1 :]) - len(rest))
            if rest.startswith("{"):
                body = self._extract_body_block(clean, body_offset)
            else:
                body = rest.split(";")[0]

            def _mutated_in_increment(var: str, incr_text: str) -> bool:
                if not incr_text:
                    return False
                return bool(
                    re.search(rf"\b{var}\s*(?:\+\+|--)", incr_text)
                    or re.search(rf"(?:\+\+|--)\s*{var}\b", incr_text)
                    or re.search(rf"\b{var}\b\s*(?:\+=|-=|\*=|/=|%=)", incr_text)
                    or re.search(rf"(?<![=<>!+\-*/%&|^])\b{var}\s*=(?![=])", incr_text)
                )

            cond_vars = self._condition_vars(cond)

            def _mutated_anywhere(v: str) -> bool:
                return self._is_mutated(v, body) or _mutated_in_increment(v, incr)

            non_mutated = [v for v in cond_vars if not _mutated_anywhere(v)]
            if cond_vars and len(non_mutated) == len(cond_vars):
                line = clean[: m.start()].count("\n") + 1
                observations.append(
                    LinterObservation(
                        linter_name="loop_termination",
                        filename=filename,
                        line=line,
                        severity="ADVERTENCIA",
                        message=f"Posible bucle infinito: ninguna variable de la condición `{cond.strip()}` se actualiza en el cuerpo ni en el incremento del `for`.",
                        suggestion="Mové la actualización de la variable de control al incremento o al cuerpo del bucle.",
                    )
                )

        return observations

    @staticmethod
    def _split_header(header: str) -> Optional[Tuple[str, str, str]]:
        """Divide 'init; cond; incr' respetando paréntesis anidados. None si no hay 2 ';'."""
        parts: List[str] = []
        depth = 0
        current: List[str] = []
        for ch in header:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == ";" and depth == 0:
                parts.append("".join(current))
                current = []
            else:
                current.append(ch)
        parts.append("".join(current))
        if len(parts) != 3:
            return None
        return parts[0], parts[1], parts[2]
