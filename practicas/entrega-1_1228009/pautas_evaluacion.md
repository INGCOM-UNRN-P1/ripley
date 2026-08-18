# Pautas de Evaluación - Práctica 1 (Entrega #1)

## 1. Criterios de Corrección y Desglose de Calificación

La evaluación cuantitativa preliminar se calcula en una escala de 0 a 10 con la siguiente ponderación:

- **Compilación sin errores ni advertencias (gcc -Wall -Wextra -pedantic -std=c11):** 25%
- **Pruebas de Entrada/Salida y Casos de Borde:** 35%
- **Análisis Estático y Calidad de Código (Cppcheck / Linters AST):** 25%
- **Cumplimiento de Estilo y Nomenclatura Oficial:** 15%

---

## 2. Requisitos Mínimos de Aprobación
1. **Completitud:** Para que la entrega sea considerada válida y evaluada, debe contener **al menos tres (3) ejercicios resueltos** de la guía.
2. **Encabezado Institucional:** Cada archivo fuente debe incluir la plantilla de autoría con Nombre, Apellido y Usuario de GitHub.
3. **Reglas de Estilo Obligatorias:**
   - **Regla `0x0003h`:** Toda variable local debe inicializarse explícitamente a un valor conocido en su definición.
   - **Regla `0x1001h`:** Todas las estructuras de control (`if`, `else`, `for`, `while`, `do`) deben utilizar llaves `{}`.
   - **Regla `0x1003h`:** Utilizar `for` para conteos definidos e intervalos, y `while` para lazos condicionales.
   - **Regla `0x0004h`:** Espaciado consistente alrededor de operadores binarios.
   - **Regla `0x0005h`:** Indentación uniforme de 4 espacios por bloque.

---

## 3. Manejo de Errores y Seguridad
- Queda terminantemente prohibido el uso de llamadas al sistema operativo no autorizadas (`system()`, `fork()`, `exec*()`, `popen()`).
- No deben utilizarse funciones inseguras de entrada de datos como `gets()` o `scanf("%s")` desprotegido.
