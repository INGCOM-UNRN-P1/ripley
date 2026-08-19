/*
Ejercicio 4.38 – Tabla de Multiplicar Completa
Mostrá tabla de multiplicar del 1 al 10 (todas las tablas).
-----------------
Cátedra Programación I
INGCOM-UNRN-P1
*/

#include <stdio.h>

int main(void)
{
    printf("Tabla de Multiplicar del 1 al 10:\n");
    for (int fila = 1; fila <= 10; fila++)
    {
        for (int columna = 1; columna <= 10; columna++)
        {
            printf("%4d", fila * columna);
        }
        printf("\n");
    }

    return 0;
}
