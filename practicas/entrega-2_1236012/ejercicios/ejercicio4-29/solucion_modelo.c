/*
Ejercicio 4.29 – Números Perfectos
Encontrá todos los números perfectos hasta N.
-----------------
Cátedra Programación I
INGCOM-UNRN-P1
*/

#include <stdio.h>

int main(void)
{
    int numero_limite = 0;

    printf("Ingrese el límite N para buscar números perfectos: ");
    if (scanf("%d", &numero_limite) != 1 || numero_limite < 2)
    {
        return 1;
    }

    printf("Números perfectos hasta %d:\n", numero_limite);
    for (int evaluado = 2; evaluado <= numero_limite; evaluado++)
    {
        int suma_divisores = 0;
        for (int divisor = 1; divisor <= evaluado / 2; divisor++)
        {
            if (evaluado % divisor == 0)
            {
                suma_divisores += divisor;
            }
        }

        if (suma_divisores == evaluado)
        {
            printf("%d ", evaluado);
        }
    }
    printf("\n");

    return 0;
}
