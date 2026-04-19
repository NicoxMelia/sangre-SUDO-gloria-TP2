# include <stdio.h>

// Descomentar cuando esté lista la implementación en ASM.
extern int process_value(float value1,float value2,float value3,float value4,float value5,float value6,float value7,float value8, double value9);

//int mock_process_value(double value) {
 //   return (int) value + 1;
//}

int get_value_processed(double value) {
    //return mock_process_value(value);
    // Cuando ASM esté listo, cambiar por:
    return process_value(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, value);
}