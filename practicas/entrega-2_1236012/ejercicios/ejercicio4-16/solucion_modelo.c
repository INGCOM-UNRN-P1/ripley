/*
Ejercicio 4.16 – Suma de N Números
Leé un número N y calculá la suma de los primeros N números naturales.
-----------------
Cátedra Programación I
INGCOM-UNRN-P1
*/

#include <stdio.h>

int main(void)
{
    int numero_limite = 0;
    int suma_acumulada = 0;

    printf("Ingrese un número natural N: ");
    if (scanf("%d", &numero_limite) != 1 || numero_limite <= 0)
    {
        printf("Número inválido.\n");
        return 1;
    }

    for (int i = 1; i <= numero_limite; i++)
    {
        suma_acumulada += i;
    }

    printf("La suma de los primeros %d números naturales es: %d\n", numero_limite, suma_acumulada);
    return 0;
}
