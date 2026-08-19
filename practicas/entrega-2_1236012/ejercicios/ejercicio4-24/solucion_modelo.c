/*
Ejercicio 4.24 – Secuencia de Fibonacci
Generá los primeros N números de Fibonacci de forma iterativa.
-----------------
Cátedra Programación I
INGCOM-UNRN-P1
*/

#include <stdio.h>

int main(void)
{
    int cantidad_terminos = 0;
    long termino_anterior = 0;
    long termino_actual = 1;
    long termino_siguiente = 0;

    printf("Ingrese la cantidad de términos N: ");
    if (scanf("%d", &cantidad_terminos) != 1 || cantidad_terminos <= 0)
    {
        return 1;
    }

    printf("Secuencia de Fibonacci (%d términos):\n", cantidad_terminos);
    for (int indice = 0; indice < cantidad_terminos; indice++)
    {
        printf("%ld ", termino_anterior);
        termino_siguiente = termino_anterior + termino_actual;
        termino_anterior = termino_actual;
        termino_actual = termino_siguiente;
    }
    printf("\n");

    return 0;
}
