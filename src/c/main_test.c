#include <stdio.h>

extern int process_value(double d1, double d2, double d3, double d4, double d5, double d6, double d7, double d8, double real_value);

int main() {
    double valor_prueba = 42.7;
    int resultado = process_value(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, valor_prueba);
    printf("Resultado final: %d\n", resultado);
    return 0;
}