# include <stdio.h>

// Descomentar cuando esté lista la implementación en ASM.
// extern int process_value(float value);

int mock_process_value(double value) {
    return (int) value + 1;
}

int get_value_processed(double value) {
    return mock_process_value(value);
    // Cuando ASM esté listo, cambiar por:
    // return process_value(value);
}