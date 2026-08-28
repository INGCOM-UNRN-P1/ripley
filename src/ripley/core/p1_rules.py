"""Comprehensive style and quality rule definitions following Programación I apunte."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple

from ripley.core.security import strip_c_comments_and_strings
from ripley.core.semantic_diff import CFunctionAST, extract_c_functions


@dataclass
class P1Rule:
    code: str  # ej. "0x0004h"
    category: str  # ej. "Sintaxis Básica y Nomenclatura"
    title: str  # ej. "Un espacio antes y después de cada operador binario"
    description: str
    severity: str  # "ESTILO" | "ADVERTENCIA" | "ERROR"
    incorrect_example: str = ""
    correct_example: str = ""
    rationale: str = ""


P1_RULES_CATALOG: Dict[str, P1Rule] = {
    # 0x00XXh: Sintaxis Básica y Nomenclatura
    "0x0000h": P1Rule(
        code="0x0000h",
        category="Sintaxis y Nomenclatura",
        title="La claridad y prolijidad son de máxima importancia",
        description="Escribir código limpio, legible y auto-explicativo con estructura consistente.",
        severity="ESTILO",
    ),
    "0x0001h": P1Rule(
        code="0x0001h",
        category="Sintaxis y Nomenclatura",
        title="Los identificadores deben ser descriptivos (Variables < 5 letras y revisión de 1 letra)",
        description="Los nombres de variables deben reflejar con precisión su propósito (identificadores < 5 letras a mejorar, y 1 letra requiere revisión manual salvo i, j, k).",
        severity="ESTILO",
    ),
    "0x0002h": P1Rule(
        code="0x0002h",
        category="Sintaxis y Nomenclatura",
        title="Una declaración de variable por línea",
        description="Declarar cada variable en una línea separada para facilitar comentarios y legibilidad.",
        severity="ESTILO",
    ),
    "0x0003h": P1Rule(
        code="0x0003h",
        category="Sintaxis y Nomenclatura",
        title="Siempre debés inicializar las variables a un valor conocido",
        description="Inicializar las variables locales al declararlas para evitar valores residuales del stack.",
        severity="ADVERTENCIA",
    ),
    "0x0004h": P1Rule(
        code="0x0004h",
        category="Sintaxis y Nomenclatura",
        title="Un espacio antes y después de cada operador binario",
        description="Colocar un espacio antes y después de operadores binarios (+, -, *, /, =, ==, !=, &&, ||).",
        severity="ESTILO",
    ),
    "0x0005h": P1Rule(
        code="0x0005h",
        category="Sintaxis y Nomenclatura",
        title="Cada bloque debe tener una indentación de cuatro espacios",
        description="La indentación debe ser exactamente de cuatro espacios respecto al contenedor.",
        severity="ESTILO",
    ),
    "0x0006h": P1Rule(
        code="0x0006h",
        category="Sintaxis y Nomenclatura",
        title="El asterisco de los punteros debe declararse junto al identificador",
        description="Declarar el asterisco junto al nombre de la variable (int *ptr) y no junto al tipo (int* ptr).",
        severity="ESTILO",
    ),
    "0x0007h": P1Rule(
        code="0x0007h",
        category="Sintaxis y Nomenclatura",
        title="Argumentos y variables locales deben usar snake_case en minúsculas",
        description="Utilizar minúsculas con guiones bajos (snake_case) para variables y argumentos.",
        severity="ESTILO",
    ),
    "0x0008h": P1Rule(
        code="0x0008h",
        category="Sintaxis y Nomenclatura",
        title="Las constantes deben nombrarse en MAYUSCULAS_SNAKE_CASE",
        description="Las constantes (#define y const) deben escribirse enteramente en MAYUSCULAS_SNAKE_CASE.",
        severity="ESTILO",
    ),
    "0x0009h": P1Rule(
        code="0x0009h",
        category="Sintaxis y Nomenclatura",
        title="Las líneas de código no deben exceder los 79 caracteres",
        description="Limitar la longitud de línea a un máximo de 79 caracteres para evitar desplazamiento horizontal.",
        severity="ESTILO",
    ),
    "0x000Ah": P1Rule(
        code="0x000Ah",
        category="Sintaxis y Nomenclatura",
        title="Escribí comentarios que expliquen el 'porqué', no el 'qué'",
        description="Los comentarios deben justificar decisiones de diseño complejas y no repetir lo evidente.",
        severity="ESTILO",
    ),
    "0x000Bh": P1Rule(
        code="0x000Bh",
        category="Sintaxis y Nomenclatura",
        title="Las llaves deben ubicarse en líneas independientes según el estilo Allman",
        description="Ubicar las llaves de apertura y cierre en líneas separadas alineadas con la instrucción de control.",
        severity="ESTILO",
    ),

    # 0x10XXh: Estructuras de Control y Lazos
    "0x1001h": P1Rule(
        code="0x1001h",
        category="Estructuras de Control",
        title="Todas las estructuras de control deben utilizar llaves",
        description="Las sentencias if, else, for, while deben incluir siempre llaves {}, incluso para una sola línea.",
        severity="ESTILO",
    ),
    "0x1002h": P1Rule(
        code="0x1002h",
        category="Estructuras de Control",
        title="Evitá continue y break descontrolado; preferí banderas lógicas",
        description="El uso de continue está estrictamente prohibido y break debe reservarse para simplificaciones claras.",
        severity="ADVERTENCIA",
    ),
    "0x1003h": P1Rule(
        code="0x1003h",
        category="Estructuras de Control",
        title="Utilizá for para conteo definido y while para lazos lógicos",
        description="No forzar lecturas interactivas o condiciones indefinidas dentro del encabezado for.",
        severity="ESTILO",
    ),
    "0x1004h": P1Rule(
        code="0x1004h",
        category="Estructuras de Control",
        title="Las condiciones complejas deben ser simplificadas o comentadas",
        description="Dividir expresiones booleanas complejas con variables intermedias explicativas.",
        severity="ESTILO",
    ),
    "0x1005h": P1Rule(
        code="0x1005h",
        category="Estructuras de Control",
        title="Evitá condiciones ambiguas basadas en truthiness",
        description="Comparar explícitamente contra NULL o contra 0 en lugar de confiar en conversiones booleanas implícitas.",
        severity="ESTILO",
    ),
    "0x1006h": P1Rule(
        code="0x1006h",
        category="Estructuras de Control",
        title="No utilizar la instrucción goto",
        description="La instrucción goto está prohibida en la materia; utilizá estructuras de control estándar.",
        severity="ERROR",
    ),
    "0x1007h": P1Rule(
        code="0x1007h",
        category="Estructuras de Control",
        title="No utilizar el operador condicional (ternario) ?:",
        description="El operador ternario complica la lectura; utilizá if-else estructurado.",
        severity="ESTILO",
    ),
    "0x1008h": P1Rule(
        code="0x1008h",
        category="Estructuras de Control",
        title="Toda instrucción switch debe incluir un caso default",
        description="Incluir siempre default: al final de un bloque switch para manejar estados no previstos.",
        severity="ADVERTENCIA",
    ),

    # 0x20XXh: Funciones y Modularización
    "0x2001h": P1Rule(
        code="0x2001h",
        category="Funciones y Modularización",
        title="Usar cláusulas de guarda para evitar anidación profunda",
        description="Validar precondiciones y salir tempranamente para evitar código en flecha.",
        severity="ESTILO",
    ),
    "0x2002h": P1Rule(
        code="0x2002h",
        category="Funciones y Modularización",
        title="Las funciones auxiliares no deben contener printf o scanf",
        description="Separar la lógica computacional del código de entrada/salida por consola.",
        severity="ADVERTENCIA",
    ),
    "0x2003h": P1Rule(
        code="0x2003h",
        category="Funciones y Modularización",
        title="Todas las funciones deben incluir documentación completa",
        description="Documentar funciones con @brief, @param y @return en formato Doxygen.",
        severity="ESTILO",
    ),
    "0x2004h": P1Rule(
        code="0x2004h",
        category="Funciones y Modularización",
        title="No se permite el uso de variables globales mutables",
        description="Las variables globales introducen acoplamiento oculto y dificultan el testeo.",
        severity="ERROR",
    ),
    "0x2005h": P1Rule(
        code="0x2005h",
        category="Funciones y Modularización",
        title="Cada función debe tener una única responsabilidad",
        description="Evitar funciones extensas (>50 líneas) que realicen múltiples tareas disímiles.",
        severity="ESTILO",
    ),
    "0x2006h": P1Rule(
        code="0x2006h",
        category="Funciones y Modularización",
        title="Una aserción por cada función de prueba",
        description="Modularizar las pruebas unitarias enfocando cada test en un caso atómico.",
        severity="ESTILO",
    ),
    "0x2007h": P1Rule(
        code="0x2007h",
        category="Funciones y Modularización",
        title="Mantené el alcance de las variables al mínimo posible",
        description="Declarar las variables en el bloque más interno donde sean utilizadas.",
        severity="ESTILO",
    ),
    "0x2008h": P1Rule(
        code="0x2008h",
        category="Funciones y Modularización",
        title="Los valores de retorno deben definirse como constantes o enum",
        description="Reemplazar códigos de retorno numéricos mágicos por constantes descriptivas o enum.",
        severity="ESTILO",
    ),
    "0x2009h": P1Rule(
        code="0x2009h",
        category="Funciones y Modularización",
        title="Los ejercicios deben ser resueltos mediante funciones",
        description="No colocar toda la lógica del problema dentro de la función main().",
        severity="ADVERTENCIA",
    ),
    "0x200Ah": P1Rule(
        code="0x200Ah",
        category="Funciones y Modularización",
        title="Nombres de funciones deben usar snake_case en minúsculas",
        description="Los identificadores de función deben estar en snake_case.",
        severity="ESTILO",
    ),

    # 0x30XXh: Punteros y Gestión de Memoria
    "0x3001h": P1Rule(
        code="0x3001h",
        category="Punteros y Memoria",
        title="Siempre verificá la asignación exitosa de memoria dinámica",
        description="Comprobar siempre if (ptr == NULL) tras llamar a malloc, calloc o realloc.",
        severity="ERROR",
    ),
    "0x3002h": P1Rule(
        code="0x3002h",
        category="Punteros y Memoria",
        title="Asigná NULL al puntero tras free() para evitar punteros colgantes",
        description="Hacer ptr = NULL inmediatamente tras free(ptr);.",
        severity="ADVERTENCIA",
    ),
    "0x3003h": P1Rule(
        code="0x3003h",
        category="Punteros y Memoria",
        title="No mezcles asignación y comparación en una sola línea",
        description="Separar la asignación ptr = malloc(...) de la comparación if (ptr == NULL).",
        severity="ESTILO",
    ),
    "0x3004h": P1Rule(
        code="0x3004h",
        category="Punteros y Memoria",
        title="Utilizá typedef para definir tipos de estructuras con sufijo _t o t_",
        description="Definir alias de tipos con typedef struct ... t_nombre o nombre_t.",
        severity="ESTILO",
    ),
    "0x3005h": P1Rule(
        code="0x3005h",
        category="Punteros y Memoria",
        title="Minimizá el uso de múltiples niveles de indirección (***ptr)",
        description="Evitar punteros triples o niveles de indirección innecesariamente complejos.",
        severity="ADVERTENCIA",
    ),
    "0x3006h": P1Rule(
        code="0x3006h",
        category="Punteros y Memoria",
        title="Documentá la propiedad de los recursos al utilizar punteros",
        description="Indicar explícitamente en el contrato qué módulo es responsable de liberar la memoria.",
        severity="ESTILO",
    ),
    "0x3007h": P1Rule(
        code="0x3007h",
        category="Punteros y Memoria",
        title="Argumentos puntero de solo lectura deben ser const",
        description="Calificar con const los punteros cuyos datos apuntados no son modificados por la función.",
        severity="ESTILO",
    ),
    "0x3008h": P1Rule(
        code="0x3008h",
        category="Punteros y Memoria",
        title="Punteros nulos deben ser inicializados y comparados con NULL",
        description="Usar explícitamente NULL en lugar del literal 0 para punteros.",
        severity="ESTILO",
    ),
    "0x3009h": P1Rule(
        code="0x3009h",
        category="Punteros y Memoria",
        title="Documentá explícitamente los casos en que una función puede retornar NULL",
        description="Aclarar en la documentación si el retorno NULL indica error o fin de iteración.",
        severity="ESTILO",
    ),
    "0x300Ah": P1Rule(
        code="0x300Ah",
        category="Punteros y Memoria",
        title="Utilizá cast explícito al convertir tipos de punteros",
        description="Evitar casteos implícitos incompatibles entre diferentes tipos de datos.",
        severity="ADVERTENCIA",
    ),
    "0x300Bh": P1Rule(
        code="0x300Bh",
        category="Punteros y Memoria",
        title="Usá siempre sizeof en asignaciones dinámicas (prefiriendo sizeof(*ptr))",
        description="Evitar tamaños fijos calculados a mano en malloc/calloc.",
        severity="ADVERTENCIA",
    ),
    "0x300Ch": P1Rule(
        code="0x300Ch",
        category="Punteros y Memoria",
        title="Verificá siempre los límites de los arreglos antes de acceder a sus elementos",
        description="Validar índices de arreglos para evitar desbordamientos de búfer (out-of-bounds).",
        severity="ERROR",
    ),
    "0x300Dh": P1Rule(
        code="0x300Dh",
        category="Punteros y Memoria",
        title="Utilizá enum en lugar de números mágicos",
        description="Definir enumeraciones descriptivas para estados y constantes de dominio.",
        severity="ESTILO",
    ),
    "0x300Eh": P1Rule(
        code="0x300Eh",
        category="Punteros y Memoria",
        title="Documentá el comportamiento de las funciones ante punteros nulos",
        description="Especificar si una función tolera parámetros NULL o aborta con aserción.",
        severity="ESTILO",
    ),
    "0x300Fh": P1Rule(
        code="0x300Fh",
        category="Punteros y Memoria",
        title="Liberá la memoria en el orden inverso a su asignación (deep free)",
        description="Liberar los miembros dinámicos antes de liberar la estructura contenedora.",
        severity="ADVERTENCIA",
    ),
    "0x3010h": P1Rule(
        code="0x3010h",
        category="Punteros y Memoria",
        title="Variables de tamaños o índices deben ser de tipo size_t",
        description="Utilizar size_t en lugar de int con signo para longitudes e iteradores de arreglos.",
        severity="ESTILO",
    ),
    "0x3011h": P1Rule(
        code="0x3011h",
        category="Punteros y Memoria",
        title="Si una función recibe un puntero genérico de solo lectura, usar const void*",
        description="Firmar funciones con const void* cuando no se modifiquen los bytes leídos.",
        severity="ESTILO",
    ),
    "0x0035h": P1Rule(
        code="0x0035h",
        category="Punteros y Memoria",
        title="Diseñá los Tipos de Datos Abstractos utilizando punteros opacos",
        description="Ocultar los detalles de implementación de structs en archivos .h mediante punteros incompletos.",
        severity="ESTILO",
    ),
    "0x0036h": P1Rule(
        code="0x0036h",
        category="Punteros y Memoria",
        title="Asigná NULL al puntero tras liberar un recurso opaco",
        description="Asignar NULL al puntero en el cliente tras destruir un TDA para prevenir accesos inválidos.",
        severity="ADVERTENCIA",
    ),

    # 0x40XXh: Gestión de Archivos y Errores
    "0x4001h": P1Rule(
        code="0x4001h",
        category="Archivos y Errores",
        title="Manejá correctamente la apertura y cierre de archivos",
        description="Validar if (archivo == NULL) tras fopen y asegurar el cierre con fclose.",
        severity="ADVERTENCIA",
    ),
    "0x4002h": P1Rule(
        code="0x4002h",
        category="Archivos y Errores",
        title="Validá los retornos de lectura y escritura de archivos",
        description="Verificar los valores de retorno de fread, fwrite, fgets, fscanf.",
        severity="ADVERTENCIA",
    ),
    "0x4003h": P1Rule(
        code="0x4003h",
        category="Archivos y Errores",
        title="Utilizá errno, perror y strerror para reportar fallos",
        description="Diagnosticar fallos de archivos mediante perror o strerror(errno).",
        severity="ESTILO",
    ),
    "0x4004h": P1Rule(
        code="0x4004h",
        category="Archivos y Errores",
        title="Asegurá la simetría de recursos al abrir y cerrar archivos",
        description="Abrir y cerrar descriptores de archivos dentro del mismo nivel de abstracción funcional.",
        severity="ADVERTENCIA",
    ),
    "0x4005h": P1Rule(
        code="0x4005h",
        category="Archivos y Errores",
        title="Evitá offsets fijos codificados a mano sin validar dimensiones",
        description="Comprobar el tamaño real del archivo antes de posicionar punteros con fseek.",
        severity="ADVERTENCIA",
    ),

    # 0x50XXh: Compilación y Buenas Prácticas
    "0x5001h": P1Rule(
        code="0x5001h",
        category="Buenas Prácticas",
        title="Arreglos estáticos con tamaño fijo en compilación (prohibido VLA)",
        description="Los arreglos de longitud variable (int arr[n]) están prohibidos; usar constantes o malloc.",
        severity="ERROR",
    ),
    "0x5002h": P1Rule(
        code="0x5002h",
        category="Buenas Prácticas",
        title="Desarrollá y compilá siempre con todas las advertencias activadas",
        description="Compilar con -Wall -Wextra -Werror -pedantic para detectar anomalías tempranas.",
        severity="ADVERTENCIA",
    ),
    "0x5003h": P1Rule(
        code="0x5003h",
        category="Buenas Prácticas",
        title="Utilizá guardas de inclusión en archivos de cabecera (.h)",
        description="Incluir #ifndef MODULO_H / #define MODULO_H / #endif en headers.",
        severity="ESTILO",
    ),
    "0x5004h": P1Rule(
        code="0x5004h",
        category="Buenas Prácticas",
        title="Todas las operaciones con cadenas deben ser seguras",
        description="Utilizar snprintf o strncpy en lugar de strcpy/strcat sin límite de tamaño.",
        severity="ADVERTENCIA",
    ),
    "0x5005h": P1Rule(
        code="0x5005h",
        category="Buenas Prácticas",
        title="Organizá la estructura de tus archivos .c de forma estándar",
        description="Estructurar los archivos con includes, defines, typedefs, prototipos y funciones.",
        severity="ESTILO",
    ),
    "0x5006h": P1Rule(
        code="0x5006h",
        category="Buenas Prácticas",
        title="Preferí fgets sobre gets y scanf para leer cadenas",
        description="La función gets() está prohibida y scanf(\"%s\") no valida desbordamientos.",
        severity="ERROR",
    ),
}


@dataclass
class P1RuleObservation:
    rule_code: str
    filename: str
    line: int
    severity: str
    title: str
    message: str
    suggestion: str


class P1RuleChecker:
    """Evaluador exhaustivo de las reglas de estilo y buenas prácticas de Programación I."""

    def analyze(self, code: str, filename: str = "archivo.c") -> List[P1RuleObservation]:
        observations: List[P1RuleObservation] = []
        raw_lines = code.splitlines()
        clean = strip_c_comments_and_strings(code)
        clean_lines = clean.splitlines()
        functions = extract_c_functions(code)

        # --------------------------------------------------------------------
        # 0. 0x0001h: Variables cortas (< 5 letras: "A mejorar" / 1 letra: "Revisión manual")
        # --------------------------------------------------------------------
        var_decl_pattern = re.compile(
            r"\b(?:int|char|float|double|size_t|ssize_t|long|short|unsigned|signed|uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t|bool|FILE|struct\s+[a-zA-Z0-9_]+|[a-zA-Z0-9_]+_t|t_[a-zA-Z0-9_]+)\s+(?P<decl>[^;{}()]+);",
            re.MULTILINE,
        )
        for m in var_decl_pattern.finditer(clean):
            decl_str = m.group("decl")
            line_num = clean[: m.start()].count("\n") + 1
            items = decl_str.split(",")
            for item in items:
                item_clean = re.sub(r"=.*$", "", item).strip()
                item_clean = re.sub(r"\[.*\]", "", item_clean).strip()
                var_match = re.search(r"[*]*\s*([a-zA-Z_][a-zA-Z0-9_]*)$", item_clean)
                if var_match:
                    vname = var_match.group(1)
                    if vname in ("main", "setUp", "tearDown"):
                        continue
                    if len(vname) < 5:
                        if len(vname) == 1:
                            if vname.lower() in ("i", "j", "k"):
                                observations.append(
                                    P1RuleObservation(
                                        rule_code="0x0001h",
                                        filename=filename,
                                        line=line_num,
                                        severity="ESTILO",
                                        title=P1_RULES_CATALOG["0x0001h"].title,
                                        message=f"Variable de 1 letra: `{vname}` (Aceptable para contadores `i`, `j`, `k`, pero requiere revisión manual de contexto).",
                                        suggestion="Conservar únicamente como contador o índice local de bucle; no emplear para datos de dominio (Regla 0x0001h).",
                                    )
                                )
                            else:
                                observations.append(
                                    P1RuleObservation(
                                        rule_code="0x0001h",
                                        filename=filename,
                                        line=line_num,
                                        severity="ADVERTENCIA",
                                        title=P1_RULES_CATALOG["0x0001h"].title,
                                        message=f"Variable de 1 letra no descriptiva: `{vname}` (Requiere revisión manual obligatoria).",
                                        suggestion=f"Renombrá la variable `{vname}` por un identificador representativo del dominio (Regla 0x0001h).",
                                    )
                                )
                        else:
                            observations.append(
                                P1RuleObservation(
                                    rule_code="0x0001h",
                                    filename=filename,
                                    line=line_num,
                                    severity="ESTILO",
                                    title=P1_RULES_CATALOG["0x0001h"].title,
                                    message=f"Nombre de variable corto ({len(vname)} letras): `{vname}` (A mejorar).",
                                    suggestion=f"Se recomienda utilizar identificadores más descriptivos y expresivos que expliciten el propósito de la variable (Regla 0x0001h).",
                                )
                            )

        # --------------------------------------------------------------------
        # 1. 0x0002h: Una declaración de variable por línea
        # --------------------------------------------------------------------

        multi_decl_regex = re.compile(
            r"^[ \t]*(?:int|char|float|double|size_t|long|short)\s+([a-zA-Z_][a-zA-Z0-9_]*\s*(?:=\s*[^,;]+)?\s*,\s*)+[a-zA-Z_][a-zA-Z0-9_]*",
            re.MULTILINE,
        )
        for m in multi_decl_regex.finditer(clean):
            line_num = clean[: m.start()].count("\n") + 1
            observations.append(
                P1RuleObservation(
                    rule_code="0x0002h",
                    filename=filename,
                    line=line_num,
                    severity=P1_RULES_CATALOG["0x0002h"].severity,
                    title=P1_RULES_CATALOG["0x0002h"].title,
                    message="Múltiples declaraciones de variables en la misma línea.",
                    suggestion="Declarar cada variable en su propia línea (ej. `int a;\\nint b;`).",
                )
            )

        # --------------------------------------------------------------------
        # 2. 0x0004h: Espacio antes y después de operadores binarios
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            for op in ("==", "!=", "<=", ">=", "&&", r"\|\|"):
                clean_op = op.replace("\\", "")
                if re.search(rf"[a-zA-Z0-9_]{op}[a-zA-Z0-9_]", line):
                    observations.append(
                        P1RuleObservation(
                            rule_code="0x0004h",
                            filename=filename,
                            line=idx,
                            severity=P1_RULES_CATALOG["0x0004h"].severity,
                            title=P1_RULES_CATALOG["0x0004h"].title,
                            message=f"Falta espacio alrededor del operador binario `{clean_op}`.",
                            suggestion=f"Colocá un espacio antes y después: `x {clean_op} y`.",
                        )
                    )

        # --------------------------------------------------------------------
        # 3. 0x0006h: Asterisco de punteros junto al identificador (int *p vs int* p)
        # --------------------------------------------------------------------
        star_type_regex = re.compile(r"\b(?:int|char|float|double|void|size_t)\*\s+[a-zA-Z_][a-zA-Z0-9_]*\b")
        for idx, line in enumerate(clean_lines, start=1):
            if star_type_regex.search(line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x0006h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x0006h"].severity,
                        title=P1_RULES_CATALOG["0x0006h"].title,
                        message="El asterisco de puntero está pegado al tipo (`tipo* ptr`) en lugar del identificador.",
                        suggestion="Escribí `tipo *ptr` para mantener la convención estándar de la cátedra.",
                    )
                )

        # --------------------------------------------------------------------
        # 4. 0x0007h / 0x0008h: Nomenclatura camelCase en variables vs MAYUSCULAS en constantes
        # --------------------------------------------------------------------
        camel_var_regex = re.compile(r"\b(?:int|char|float|double|size_t)\s+(?P<v>[a-z]+[A-Z][a-zA-Z0-9]*)\b")
        for idx, line in enumerate(clean_lines, start=1):
            m = camel_var_regex.search(line)
            if m:
                vname = m.group("v")
                observations.append(
                    P1RuleObservation(
                        rule_code="0x0007h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x0007h"].severity,
                        title=P1_RULES_CATALOG["0x0007h"].title,
                        message=f"La variable `{vname}` usa camelCase en lugar de snake_case.",
                        suggestion=f"Renombrala en minúsculas separadas por guión bajo (ej. `{self._to_snake(vname)}`).",
                    )
                )

        # --------------------------------------------------------------------
        # 5. 0x0009h: Longitud de línea > 79 caracteres
        # --------------------------------------------------------------------
        for idx, line in enumerate(raw_lines, start=1):
            if len(line) > 79:
                observations.append(
                    P1RuleObservation(
                        rule_code="0x0009h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x0009h"].severity,
                        title=P1_RULES_CATALOG["0x0009h"].title,
                        message=f"La línea excede los 79 caracteres ({len(line)} columnas).",
                        suggestion="Dividí la instrucción o cadena en múltiples líneas para respetar el estándar de 80 columnas.",
                    )
                )

        # --------------------------------------------------------------------
        # 6. 0x1001h: Todas las estructuras de control deben utilizar llaves
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            s_line = line.strip()
            for kw in ("if", "for", "while"):
                match = re.search(rf"\b{kw}\s*\([^\)]*\)\s*([^{{;]+);", s_line)
                if match and not s_line.endswith("{") and not match.group(1).startswith("//"):
                    observations.append(
                        P1RuleObservation(
                            rule_code="0x1001h",
                            filename=filename,
                            line=idx,
                            severity=P1_RULES_CATALOG["0x1001h"].severity,
                            title=P1_RULES_CATALOG["0x1001h"].title,
                            message=f"Estructura de control `{kw}` en una sola línea sin llaves {{}}.",
                            suggestion="Envolvé siempre el cuerpo de la estructura con llaves `{ ... }` en líneas propias.",
                        )
                    )

        # --------------------------------------------------------------------
        # 7. 0x1002h: Prohibición de continue
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            if re.search(r"\bcontinue\s*;", line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x1002h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x1002h"].severity,
                        title=P1_RULES_CATALOG["0x1002h"].title,
                        message="Uso prohibido de la sentencia `continue`.",
                        suggestion="Reestructurá el lazo utilizando una condición lógica o bandera booleana.",
                    )
                )

        # --------------------------------------------------------------------
        # 8. 0x1006h: Prohibición de goto
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            if re.search(r"\bgoto\s+[a-zA-Z_][a-zA-Z0-9_]*\s*;", line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x1006h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x1006h"].severity,
                        title=P1_RULES_CATALOG["0x1006h"].title,
                        message="Uso prohibido de la instrucción `goto`.",
                        suggestion="Reemplazá `goto` por estructuras de control estructuradas estándar (`while`, `for`, `if`).",
                    )
                )

        # --------------------------------------------------------------------
        # 9. 0x1007h: Prohibición del operador ternario ?:
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            if "?" in line and ":" in line and not line.strip().startswith("//") and not line.strip().startswith("case "):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x1007h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x1007h"].severity,
                        title=P1_RULES_CATALOG["0x1007h"].title,
                        message="Uso desaconsejado del operador condicional ternario `?:`.",
                        suggestion="Reemplazá el operador ternario por un bloque estructurado `if / else`.",
                    )
                )

        # --------------------------------------------------------------------
        # 10. 0x1008h: Switch debe incluir default
        # --------------------------------------------------------------------
        switch_matches = re.finditer(r"\bswitch\s*\([^\)]*\)\s*\{(?P<body>[^}]*)\}", clean)
        for sm in switch_matches:
            s_body = sm.group("body")
            if "default:" not in s_body:
                line_num = clean[: sm.start()].count("\n") + 1
                observations.append(
                    P1RuleObservation(
                        rule_code="0x1008h",
                        filename=filename,
                        line=line_num,
                        severity=P1_RULES_CATALOG["0x1008h"].severity,
                        title=P1_RULES_CATALOG["0x1008h"].title,
                        message="Bloque `switch` sin cláusula `default:` obligatoria.",
                        suggestion="Agregá `default:` al final del `switch` para manejar estados imprevistos.",
                    )
                )

        # --------------------------------------------------------------------
        # 11. 0x2004h: Prohibición de variables globales mutables
        # --------------------------------------------------------------------
        global_var_regex = re.compile(
            r"^[ \t]*(?!const\b)(?:int|char|float|double|size_t)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=\s*[^;]+)?;",
            re.MULTILINE,
        )
        # Extraer variables que están fuera de funciones y fuera de structs/unions/enums
        in_fn_ranges = [(f.start_line, f.start_line + f.raw_body.count("\n")) for f in functions.values()]
        struct_ranges = [
            (clean[: sm.start()].count("\n") + 1, clean[: sm.end()].count("\n") + 1)
            for sm in re.finditer(r"\b(?:struct|union|enum)\b[^{};]*\{[^}]*\}", clean, re.DOTALL)
        ]
        for m in global_var_regex.finditer(clean):
            line_num = clean[: m.start()].count("\n") + 1
            inside_any_fn = any(start <= line_num <= end for start, end in in_fn_ranges)
            inside_any_struct = any(start <= line_num <= end for start, end in struct_ranges)
            if not inside_any_fn and not inside_any_struct:
                observations.append(
                    P1RuleObservation(
                        rule_code="0x2004h",
                        filename=filename,
                        line=line_num,
                        severity=P1_RULES_CATALOG["0x2004h"].severity,
                        title=P1_RULES_CATALOG["0x2004h"].title,
                        message="Declaración de variable global mutable.",
                        suggestion="Eliminá la variable global; pasá el estado explícitamente mediante parámetros de función.",
                    )
                )

        # --------------------------------------------------------------------
        # 12. 0x3001h: Verificación obligatoria de retorno de malloc/calloc
        # --------------------------------------------------------------------
        for fname, fobj in functions.items():
            alloc_calls = re.findall(r"(?P<var>[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?(?:malloc|calloc|realloc)\s*\(", fobj.raw_body)
            for v in alloc_calls:
                # Comprobar si en el cuerpo se valida if (v == NULL) o if (!v)
                if not re.search(rf"\bif\s*\(\s*(?:{v}\s*==\s*NULL|!{v}|NULL\s*==\s*{v})\b", fobj.raw_body):
                    observations.append(
                        P1RuleObservation(
                            rule_code="0x3001h",
                            filename=filename,
                            line=fobj.start_line,
                            severity=P1_RULES_CATALOG["0x3001h"].severity,
                            title=P1_RULES_CATALOG["0x3001h"].title,
                            message=f"Asignación dinámica de `{v}` sin verificación inmediata contra `NULL`.",
                            suggestion=f"Agregá `if ({v} == NULL) {{ /* manejo de error */ }}` antes de usar el puntero.",
                        )
                    )

        # --------------------------------------------------------------------
        # 13. 0x3003h: No mezclar asignación y comparación en if
        # --------------------------------------------------------------------
        assign_in_cond = re.compile(r"\bif\s*\(\s*\([a-zA-Z0-9_* ]+\s*=\s*(?:malloc|calloc|realloc|fopen)\s*\(")
        for idx, line in enumerate(clean_lines, start=1):
            if assign_in_cond.search(line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x3003h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x3003h"].severity,
                        title=P1_RULES_CATALOG["0x3003h"].title,
                        message="Asignación y comparación combinadas en una sola línea dentro del `if`.",
                        suggestion="Separá la asignación en la línea anterior y evaluá la condición en una sentencia limpia.",
                    )
                )

        # --------------------------------------------------------------------
        # 14. 0x3004h: Structs con typedef y sufijo _t / prefijo t_
        # --------------------------------------------------------------------
        bare_struct_regex = re.compile(r"^[ \t]*struct\s+(?P<sname>[a-zA-Z0-9_]+)\s*\{", re.MULTILINE)
        for m in bare_struct_regex.finditer(clean):
            sname = m.group("sname")
            line_num = clean[: m.start()].count("\n") + 1
            if not sname.endswith("_t") and not sname.startswith("t_"):
                # Comprobar si está dentro de un typedef
                typedef_check = clean[max(0, m.start() - 15) : m.start()]
                if "typedef" not in typedef_check:
                    observations.append(
                        P1RuleObservation(
                            rule_code="0x3004h",
                            filename=filename,
                            line=line_num,
                            severity=P1_RULES_CATALOG["0x3004h"].severity,
                            title=P1_RULES_CATALOG["0x3004h"].title,
                            message=f"Estructura `{sname}` declarada sin `typedef` ni sufijo `_t` / prefijo `t_`.",
                            suggestion=f"Definila como `typedef struct {{ ... }} {sname}_t;`.",
                        )
                    )

        # --------------------------------------------------------------------
        # 15. 0x5001h: Prohibición de VLAs (Arreglos de longitud variable)
        # --------------------------------------------------------------------
        vla_regex = re.compile(r"\b(?:int|char|float|double)\s+[a-zA-Z_][a-zA-Z0-9_]*\[\s*(?![0-9A-Z_]+\s*\])[a-z_][a-zA-Z0-9_]*\s*\]\s*;")
        for idx, line in enumerate(clean_lines, start=1):
            if vla_regex.search(line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x5001h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x5001h"].severity,
                        title=P1_RULES_CATALOG["0x5001h"].title,
                        message="Uso de Arreglo de Longitud Variable (VLA).",
                        suggestion="Los VLAs están prohibidos. Utilizá una constante `#define TAM 100` o asignación dinámica con `malloc`.",
                    )
                )

        # --------------------------------------------------------------------
        # 16. 0x5006h: Preferir fgets sobre gets y scanf("%s")
        # --------------------------------------------------------------------
        for idx, line in enumerate(clean_lines, start=1):
            if re.search(r"\bgets\s*\(", line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x5006h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x5006h"].severity,
                        title=P1_RULES_CATALOG["0x5006h"].title,
                        message="Uso de la función obsoleta e insegura `gets()`.",
                        suggestion="Reemplazá `gets()` por `fgets(buffer, sizeof(buffer), stdin)`.",
                    )
                )
            elif re.search(r'\bscanf\s*\(\s*"%s"', line):
                observations.append(
                    P1RuleObservation(
                        rule_code="0x5006h",
                        filename=filename,
                        line=idx,
                        severity=P1_RULES_CATALOG["0x5006h"].severity,
                        title=P1_RULES_CATALOG["0x5006h"].title,
                        message="Uso de `scanf(\"%s\")` desprotegido contra desbordamiento de búfer.",
                        suggestion="Utilizá `fgets` o especificá un ancho máximo como `scanf(\"%99s\", buffer)`.",
                    )
                )

        return filter_suppressed_observations(observations, code)

    def _to_snake(self, name: str) -> str:
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def extract_suppressions(code: str) -> Tuple[Set[str], Dict[int, Set[str]], List[Tuple[int, int, Set[str]]]]:
    """Extrae reglas suprimidas a nivel de archivo, línea o bloque.
    
    Formatos soportados:
      // ripley:disable=0x1001h,0x1002h
      // ripley:disable-line=0x1001h
      // ripley:disable-next-line=0x1001h
      /* ripley:disable=0x1001h */ ... /* ripley:enable=0x1001h */
    """
    file_suppressions: Set[str] = set()
    line_suppressions: Dict[int, Set[str]] = {}
    range_suppressions: List[Tuple[int, int, Set[str]]] = []

    active_ranges: Dict[str, int] = {}
    lines = code.splitlines()

    for idx, line in enumerate(lines, start=1):
        # Directiva de línea o archivo: ripley:disable(=|:)([0-9a-zA-Zx, ]+)
        m_disable = re.findall(r"ripley:disable(?:-line)?\s*[=:]\s*([0-9a-zA-Zx_,\s]+)", line, re.IGNORECASE)
        for group in m_disable:
            codes = {c.strip().lower() for c in group.split(",") if c.strip()}
            if idx <= 5 and re.match(r"^\s*(?://|/\*)\s*ripley:disable", line, re.IGNORECASE):
                file_suppressions.update(codes)
            line_suppressions.setdefault(idx, set()).update(codes)

        m_next = re.findall(r"ripley:disable-next-line\s*[=:]\s*([0-9a-zA-Zx_,\s]+)", line, re.IGNORECASE)
        for group in m_next:
            codes = {c.strip().lower() for c in group.split(",") if c.strip()}
            line_suppressions.setdefault(idx + 1, set()).update(codes)

        m_range_start = re.findall(r"/\*\s*ripley:disable\s*[=:]\s*([0-9a-zA-Zx_,\s]+)\s*\*/", line, re.IGNORECASE)
        for group in m_range_start:
            codes = {c.strip().lower() for c in group.split(",") if c.strip()}
            for c in codes:
                active_ranges[c] = idx

        m_range_end = re.findall(r"/\*\s*ripley:enable\s*[=:]\s*([0-9a-zA-Zx_,\s]+)\s*\*/", line, re.IGNORECASE)
        for group in m_range_end:
            codes = {c.strip().lower() for c in group.split(",") if c.strip()}
            for c in codes:
                if c in active_ranges:
                    range_suppressions.append((active_ranges[c], idx, {c}))
                    del active_ranges[c]

    for c, start_line in active_ranges.items():
        range_suppressions.append((start_line, len(lines) + 1, {c}))

    return file_suppressions, line_suppressions, range_suppressions


def filter_suppressed_observations(
    observations: List[P1RuleObservation],
    code: str,
) -> List[P1RuleObservation]:
    """Filtra observaciones anuladas mediante comentarios de supresión directos."""
    if not observations:
        return []

    file_sup, line_sup, range_sup = extract_suppressions(code)
    filtered = []

    for obs in observations:
        code_norm = obs.rule_code.lower()
        if "all" in file_sup or code_norm in file_sup:
            continue
        if obs.line in line_sup and ("all" in line_sup[obs.line] or code_norm in line_sup[obs.line]):
            continue
        in_range = False
        for start_l, end_l, codes in range_sup:
            if start_l <= obs.line <= end_l and ("all" in codes or code_norm in codes):
                in_range = True
                break
        if in_range:
            continue

        filtered.append(obs)

    return filtered

