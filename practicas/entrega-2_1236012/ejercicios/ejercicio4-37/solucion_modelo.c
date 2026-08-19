/*
Ejercicio 4.37 – Rombo
Dibujá un rombo de asteriscos
-----------------
Cátedra Programación I
INGCOM-UNRN-P1
*/

#include <stdio.h>

int main(void)
{
    int ancho_maximo = 0;

    printf("Ingrese el ancho máximo del rombo (número impar): ");
    if (scanf("%d", &ancho_maximo) != 1 || ancho_maximo <= 0)
    {
        return 1;
    }

    if (ancho_maximo % 2 == 0)
    {
        ancho_maximo += 1;
    }

    // Parte superior
    for (int fila = 1; fila <= ancho_maximo; fila += 2)
    {
        for (int espacios = 0; espacios < (ancho_maximo - fila) / 2; espacios++)
        {
            printf(" ");
        }
        for (int asteriscos = 0; asteriscos < fila; asteriscos++)
        {
            printf("*");
        }
        printf("\n");
    }

    // Parte inferior
    for (int fila = ancho_maximo - 2; fila >= 1; fila -= 2)
    {
        for (int espacios = 0; espacios < (ancho_maximo - fila) / 2; espacios++)
        {
            printf(" ");
        }
        for (int asteriscos = 0; asteriscos < fila; asteriscos++)
        {
            printf("*");
        }
        printf("\n");
    }

    return 0;
}
