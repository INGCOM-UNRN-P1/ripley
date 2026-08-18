/*
Ejercicio 1.7 – Conversor de Calificaciones
Convertir calificación decimal a letra y porcentaje equivalente.
-----------------
Docente Cátedra
catedra_p1
*/

#include <stdio.h>

int main(void)
{
    float nota = 0.0f;

    if (scanf("%f", &nota) == 1)
    {
        char letra = 'F';
        int porcentaje = (int)(nota * 10.0f + 0.5f);

        if (nota >= 9.0f)
        {
            letra = 'A';
        }
        else if (nota >= 8.0f)
        {
            letra = 'B';
        }
        else if (nota >= 7.0f)
        {
            letra = 'C';
        }
        else if (nota >= 6.0f)
        {
            letra = 'D';
        }
        else
        {
            letra = 'F';
        }

        printf("%c (%d%%)\n", letra, porcentaje);
    }

    return 0;
}
