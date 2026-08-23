#include <stdio.h>
#include <string.h>

struct registro {
    char inicial;
    int saldo;
};

/* Caso 1: goto hacia atrás (bucle desestructurado) */
int con_goto(void) {
    int i = 0;
inicio:
    i++;
    if (i < 10) {
        goto inicio;
    }
    return i;
}

/* Caso 2: API obsoleta + escritura de literal .rodata */
void con_deprecated(char *copia) {
    char *lit = "hola";
    lit[0] = 'H';
    gets(copia);
}

/* Caso 3: bucle sin variable de control mutada */
int bucle_infinito(void) {
    int x = 5;
    while (x > 0) {
        printf("%d\n", x);
    }
    return 0;
}

/* Caso 4: struct con padding enviada a archivo sin memset */
void vuelca_registro(void) {
    struct registro r;
    FILE *f = fopen("salida.bin", "wb");
    fwrite(&r, sizeof(r), 1, f);
    fclose(f);
}
