# Manual del Estudiante

> Audiencia: Estudiante de Programación I que quiere verificar su código, entender errores de compilación y entregar **bien a la primera**.
> Ripley utiliza exactamente el mismo motor y reglas que los docentes: lo que ves localmente es lo que se evalúa.

---

## 1. Opciones de Ejecución

### Opción A: Binario Autónomo (`ripley.pyz`)
No requiere instalar dependencias adicionales. Descargá el archivo `ripley.pyz` y ejecutalo directamente:

```bash
# Otorgar permisos de ejecución (Linux/macOS)
chmod +x ripley.pyz

# Ejecutar verificación pedagógica
./ripley.pyz check solucion.c

# Diagnóstico de herramientas locales
./ripley.pyz doctor
```

### Opción B: Instalación en Entorno Python
Si estás en el entorno virtual de la cátedra:

```bash
ripley check solucion.c
```

---

## 2. Comandos Principales

### 2.1 Verificación Integral (`ripley check`)
Analiza en un solo paso las reglas P1 de la cátedra, convenciones de nomenclatura, números mágicos, compilación protegida con AddressSanitizer y ejecución de testcases:

```bash
# Verificación de un archivo específico
ripley check ejercicio1.c

# Verificación del proyecto completo con salida estricta
ripley check . --strict
```

### 2.2 Modo Live TDD (`ripley watch`)
Recompila y verifica automáticamente cada vez que guardás un archivo `.c` o `.h`:

```bash
ripley watch src/
```

### 2.3 Traductor de Errores GCC (`ripley explain`)
Cuando el compilador o enlazador arroja mensajes confusos:

```bash
gcc -Wall main.c 2> errores.log
ripley explain errores.log

# O directamente desde la tubería:
gcc -Wall main.c 2>&1 | ripley explain -
```

---

## 3. Análisis Específicos y Herramientas Avanzadas

| Comando | Descripción |
|---|---|
| `ripley lint -f archivo.c` | Auditoría de reglas P1 (0xXXXXh), código muerto, números mágicos y convenciones. |
| `ripley padding-audit *.c` | Detección de structs con padding enviados a archivos/sockets sin inicializar. |
| `ripley contract-check archivo.c` | Verificación de pre/postcondiciones formales en contratos ACSL. |
| `ripley stack-audit *.c` | Medición de consumo de stack y variables de longitud variable (VLA). |
| `ripley complexity-profile bin.out` | Análisis empírico de complejidad asintótica $O(N)$ vs $O(N^2)$. |
| `ripley benchmark bin.out` | Medición de tiempos de ejecución y ciclos de CPU. |
| `ripley flowchart archivo.c` | Generación de diagramas de flujo en formato Mermaid / SVG. |
| `ripley glossary --list` | Glosario interactivo accesible sobre conceptos de memoria, punteros y heap. |

---

## 4. Códigos de Diagnóstico P1 Comunes

| Código | Significado | Sugerencia |
|---|---|---|
| `0x0001h` | Bucle infinito potencial | Revisá las condiciones de corte del `while` / `for`. |
| `0x0002h` | Uso de `goto` hacia atrás | Reemplazá el salto por estructuras de control estructuradas. |
| `0x3004h` | Struct sin `typedef` o sufijo `_t` | Definila como `typedef struct { ... } nombre_t;`. |
| `0x5006h` | Uso de función insegura (`gets`) | Reemplazá por `fgets(buffer, sizeof(buffer), stdin)`. |
| `0x7001h` | Falta calificador `const` | Declarar punteros de solo lectura como `const tipo *`. |
| `0x8001h` | Include innecesario (IWYU) | Eliminá directivas `#include` cuyos símbolos no se usen. |
