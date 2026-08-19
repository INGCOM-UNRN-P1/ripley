/*
Ejercicio 4.19 – Números Pares en Rango
Mostrá todos los números pares entre dos valores ingresados.
-----------------
Cátedra Programación I
INGCOM-UNRN-P1
*/

#include <stdio.h>

int main(void)
{
    int rango_inicio = 0;
    int rango_final = 0;

    printf("Ingrese el valor inicial (A): ");
    if (scanf("%d", &rango_inicio) != 1)
    {
        return 1;
    }

    printf("Ingrese el valor final (B): ");
    if (scanf("%d", &rango_final) != 1)
    {
        return 1;
    }

    if (rango_inicio > rango_final)
    {
        int auxiliar = rango_inicio;
        rango_inicio = rango_final;
        rango_final = auxiliar;
    }

    printf("Números pares en el rango [%d, %d]:\n", rango_inicio, rango_final);
    for (int actual = rango_inicio; actual <= rango_final; actual++)
    {
        if (actual % 2 == 0)
        {
            printf("%d ", actual);
        }
    }
    printf("\n");

    return 0;
}
