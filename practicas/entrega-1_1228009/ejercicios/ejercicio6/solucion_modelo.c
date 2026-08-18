/*
Ejercicio 1.6 – Vocales y Consonantes
Determinar la categoría de un carácter ingresado.
-----------------
Docente Cátedra
catedra_p1
*/

#include <ctype.h>
#include <stdio.h>

int main(void)
{
    char c = '\0';

    if (scanf("%c", &c) == 1)
    {
        char low = (char)tolower((unsigned char)c);

        if (low == 'a' || low == 'e' || low == 'i' || low == 'o' || low == 'u')
        {
            printf("Vocal\n");
        }
        else if (low >= 'a' && low <= 'z')
        {
            printf("Consonante\n");
        }
        else if (c >= '0' && c <= '9')
        {
            printf("Digito\n");
        }
        else
        {
            printf("Otro\n");
        }
    }

    return 0;
}
