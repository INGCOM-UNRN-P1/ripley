/*
Ejercicio 1.4 – Invertir un Número Entero
Invertir los dígitos de un número entero ingresado por el usuario.
-----------------
Docente Cátedra
catedra_p1
*/

#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int numero = 0;
    int invertido = 0;
    int signo = 1;

    if (scanf("%d", &numero) == 1)
    {
        if (numero < 0)
        {
            signo = -1;
            numero = -numero;
        }

        while (numero > 0)
        {
            invertido = (invertido * 10) + (numero % 10);
            numero = numero / 10;
        }

        printf("%d\n", invertido * signo);
    }

    return 0;
}
