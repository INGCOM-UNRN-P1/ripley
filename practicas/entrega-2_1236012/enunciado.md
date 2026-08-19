# Entrega #2: Estructuras de Control y Lazos
**Identificador:** `1236012` | **Fecha de Publicación:** 19/08/2026

## 1. Descripción y Objetivos
Completá los siguientes enunciados, creando un archivo fuente `.c` por cada uno.

Para esta entrega, no es necesario usar funciones y para ser considerada 'completa' debe contener como mínimo **tres ejercicios resueltos**, que serán revisados. Se pueden implementar tantos ejercicios del Repositorio de Enunciados como deseen.

### Plantilla de Encabezado Obligatoria
```c
/*
Ejercicio X.X – Nombre del Ejercicio
Consigna detallada del ejercicio.
-----------------
Nombre y Apellido
Usuario Github
*/
```

---

## 2. Cuestiones de Estilo Aplicables (Reglas de Cátedra P1)
- **Inicialización de Variables:** De acuerdo con la **Regla 0x0003h**, siempre se deben inicializar las variables a un valor conocido en su declaración.
- **Uso de Llaves:** Toda estructura de control debe utilizar llaves (`{}`) según la **Regla 0x1001h** (estilo Allman recomendado).
- **Prohibición de `break` y `continue`:** Según la **Regla 0x1002h**, se encuentra restringido el uso descontrolado de `break` y `continue`. En su lugar, se deben estructurar lazos controlados mediante banderas lógicas booleanas (`stdbool.h`).
- **Lazos e Iteraciones:** Según la **Regla 0x1003h**, se debe preferir el uso de lazos `for` para iteraciones con rango o contador definido, y `while` para lazos controlados por condiciones lógicas.

---

## 3. Ejercicios Incluidos

1. **[Ejercicio 4.16 - Suma de N Números](./ejercicios/ejercicio4-16/enunciado.md) ⭐☆☆☆☆**
   Leé un número $N$ y calculá la suma de los primeros $N$ números naturales.
2. **[Ejercicio 4.19 - Números Pares en Rango](./ejercicios/ejercicio4-19/enunciado.md) ⭐⭐☆☆☆**
   Mostrá todos los números pares entre dos valores ingresados.
3. **[Ejercicio 4.21 - Validación de Entrada](./ejercicios/ejercicio4-21/enunciado.md) ⭐⭐⭐☆☆**
   Leé un número entre 1 y 100. Si está fuera de rango, pedí nuevamente hasta que sea válido.
4. **[Ejercicio 4.24 - Secuencia de Fibonacci](./ejercicios/ejercicio4-24/enunciado.md) ⭐⭐⭐☆☆**
   Generá los primeros $N$ números de Fibonacci de forma iterativa ($t_0 = 0, t_1 = 1, t_n = t_{n-1} + t_{n-2}$).
5. **[Ejercicio 4.29 - Números Perfectos](./ejercicios/ejercicio4-29/enunciado.md) ⭐⭐⭐⭐☆**
   Encontrá todos los números perfectos hasta $N$. Un número es perfecto si la suma de sus divisores propios es igual al número.
6. **[Ejercicio 4.37 - Rombo](./ejercicios/ejercicio4-37/enunciado.md) ⭐⭐⭐⭐⭐**
   Dibujá un rombo de asteriscos con ancho/altura ingresado por el usuario.
7. **[Ejercicio 4.38 - Tabla de Multiplicar Completa](./ejercicios/ejercicio4-38/enunciado.md) ⭐⭐⭐⭐☆**
   Mostrá la tabla de multiplicar pitagórica completa del 1 al 10 (todas las tablas).

---

## 4. Pautas de Entrega
- Subir los archivos fuente `.c` individuales a la plataforma Moodle.
- El código debe compilar limpiamente con `gcc -Wall -Wextra -pedantic -std=c11`.
- Respetar la nomenclatura de variables y los lineamientos de buenas prácticas.
