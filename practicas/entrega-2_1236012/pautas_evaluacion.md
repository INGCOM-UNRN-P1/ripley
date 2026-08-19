# Pautas de Evaluación - Entrega #2

## 1. Criterios de Corrección y Desglose de Calificación
La evaluación cuantitativa preliminar se calcula en una escala de 0 a 10 con los siguientes pesos:

- **Compilación sin errores ni advertencias (gcc -Wall -Wextra):** 25%
- **Pruebas de Entrada/Salida y Casos de Borde:** 35%
- **Análisis Estático y Reglas de Calidad (Cppcheck):** 25%
- **Cumplimiento de Estilo y Formato de Código:** 15%

## 2. Aspectos Clave a Evaluar
1. **Manejo de Recursos y Memoria:** Todo bloque solicitado con `malloc` debe ser liberado con `free`. No deben registrarse fugas ni lecturas inválidas en Valgrind.
2. **Estilo de Código C:**
   - Estilo de llaves consistente (Allman/K&R).
   - Uso obligatorio de llaves `{}` en todas las estructuras de control.
   - Sangría uniforme (4 espacios) sin tabulaciones mezcladas.
   - Espaciado adecuado en operadores y palabras clave.
3. **Seguridad y Modularidad:**
   - Prohibido el uso de llamadas al sistema no autorizadas (`system()`, `fork()`, `popen()`).
   - Modularización en funciones con responsabilidades acotadas.
