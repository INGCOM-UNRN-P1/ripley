/*
Ejercicio 1.2 – Secuencia Ascendente
Mostrar una secuencia de números enteros desde n hasta antes de m.
-----------------
Docente Cátedra
catedra_p1
*/

#include <stdio.h>

int main(void)
{
    int n = 0;
    int m = 0;

    if (scanf("%d %d", &n, &m) == 2)
    {
        for (int i = n; i < m; i++)
        {
            printf("%d\n", i);
        }
    }

    return 0;
}
