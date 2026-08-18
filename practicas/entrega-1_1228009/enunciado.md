# Práctica 1: Primeros Programas en C
**Identificador:** `entrega-1_1228009` (Moodle ID: `1228009`) | **Materia:** Programación I

---

## 1. Descripción General y Objetivos

Completá los siguientes enunciados creando un archivo `.c` por cada uno.

Para esta entrega inicial, **no es obligatorio modularizar en funciones separadas** (pueden resolverse directamente dentro de `main()`). Para ser considerada **completa**, la entrega debe contener como **mínimo tres (3) ejercicios resueltos** que serán revisados formalmente. Sin embargo, podés implementar todos los ejercicios que desees del repositorio.

---

## 2. Plantilla Obligatoria de Archivo

Cada archivo entregado debe comenzar con el bloque de encabezado institucional:

```c
/*
Ejercicio 1.X – Nombre del Ejercicio
Breve descripción de la consigna del ejercicio.
-----------------
Nombre y Apellido: Tu Nombre
Usuario Github: tu_usuario
*/

#include <stdio.h>

int main(void)
{
    // Código de resolución
    return 0;
}
```

---

## 3. Cuestiones de Estilo Aplicables (Reglas Oficiales de Cátedra)

- **Inicialización de Variables ([Regla `0x0003h`](https://algoritmica.org/reglas/0_sintaxis.html#0x0003h)):** Siempre debés inicializar las variables a un valor conocido en su declaración (ej. `int contador = 0;`).
- **Uso Obligatorio de Llaves ([Regla `0x1001h`](https://algoritmica.org/reglas/1_control.html#0x1001h)):** Toda estructura de control (`if`, `else`, `for`, `while`, `do`) debe utilizar llaves `{}` en líneas propias, incluso para bloques de una sola sentencia.
- **Selección Apropiada de Lazos ([Regla `0x1003h`](https://algoritmica.org/reglas/1_control.html#0x1003h)):** Preferí el uso del lazo `for` para iteraciones con rango o contador definido, y `while` para lazos controlados por condiciones puramente lógicas o eventos interactivos.

---

## 4. Catálogo de Ejercicios

| # | Ejercicio | Dificultad | Enunciado |
|---|---|---|---|
| 1 | **¡Hola mundo!** | ⭐☆☆☆☆ | [Ver consigna](./ejercicios/ejercicio1/enunciado.md) |
| 2 | **Secuencia Ascendente** | ⭐☆☆☆☆ | [Ver consigna](./ejercicios/ejercicio2/enunciado.md) |
| 3 | **Par o Impar** | ⭐⭐☆☆☆ | [Ver consigna](./ejercicios/ejercicio3/enunciado.md) |
| 4 | **Invertir un Número Entero** | ⭐⭐☆☆☆ | [Ver consigna](./ejercicios/ejercicio4/enunciado.md) |
| 5 | **Contador de Dígitos** | ⭐⭐⭐☆☆ | [Ver consigna](./ejercicios/ejercicio5/enunciado.md) |
| 6 | **Vocales y Consonantes** | ⭐⭐⭐☆☆ | [Ver consigna](./ejercicios/ejercicio6/enunciado.md) |
| 7 | **Conversor de Calificaciones** | ⭐⭐⭐⭐☆ | [Ver consigna](./ejercicios/ejercicio7/enunciado.md) |

---

## 5. Pautas de Entrega y Compilación

- Subí los archivos fuente `.c` correspondientes a la actividad en el campus virtual Moodle.
- El código debe compilar limpiamente con `gcc -Wall -Wextra -pedantic -std=c11`.
- No comprimas en formatos no estándar ni subas ejecutables binarios.
- Consultá las [Pautas de Evaluación](./pautas_evaluacion.md) para conocer el desglose de calificación.
