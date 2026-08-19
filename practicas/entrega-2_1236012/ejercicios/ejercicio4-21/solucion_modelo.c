/*
Ejercicio 4.21 – Validación de Entrada
Leé un número entre 1 y 100. Si está fuera de rango, pedí nuevamente hasta que sea válido.
-----------------
Cátedra Programación I
INGCOM-UNRN-P1
*/

#include <stdio.h>
#include <stdbool.h>

int main(void)
{
    int numero_ingresado = 0;
    bool es_valido = false;

    while (!es_valido)
    {
        printf("Ingrese un número entre 1 y 100: ");
        if (scanf("%d", &numero_ingresado) == 1)
        {
            if (numero_ingresado >= 1 && numero_ingresado <= 100)
            {
                es_valido = true;
            }
            else
            {
                printf("Valor fuera de rango. Reintente.\n");
            }
        }
    }

    printf("Número válido ingresado: %d\n", numero_ingresado);
    return 0;
}
