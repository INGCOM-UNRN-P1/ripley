"""Catálogo de reglas P1 (0xXXXXh) de la cátedra."""

from dataclasses import dataclass
from typing import Dict






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
    "0x0037h": P1Rule(
        code="0x0037h",
        category="Sintaxis y Nomenclatura",
        title="Evitá identificadores genéricos con sufijo numérico (numero1, num_1, etc.)",
        description="Los identificadores genéricos seguidos de un número (como 'numero1', 'num_1', 'var1', 'dato1') denotan una elección pobre de nombres.",
        severity="ADVERTENCIA",
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
