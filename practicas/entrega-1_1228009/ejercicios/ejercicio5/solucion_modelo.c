/*
Ejercicio 1.5 – Contador de Dígitos
Calcular la cantidad de dígitos que componen un número entero.
-----------------
Docente Cátedra
catedra_p1
*/

#include <stdio.h>

int main(void)
{
    long long numero = 0;
    int digitos = 0;

    if (scanf("%lld", &numero) == 1)
    {
        if (numero < 0)
        {
            numero = -numero;
        }

        if (numero == 0)
        {
            digitos = 1;
        }
        else
        {
            while (numero > 0)
            {
                digitos++;
                numero = numero / 10;
            }
        }

        printf("%d\n", digitos);
    }

    return 0;
}
