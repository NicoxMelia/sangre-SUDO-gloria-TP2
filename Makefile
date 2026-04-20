ASM_DIR := src/asm
C_DIR := src/c
PY_DIR := src/python

ASM_SRC := $(ASM_DIR)/calc.asm
C_SRC := $(C_DIR)/receiver.c
C_TEST_SRC := $(C_DIR)/main_test.c

ASM_OBJ := converter.o
SO_LIB := libgini.so
GDB_EXEC := programa_gdb

.PHONY: all clean run debug run-debug run_flask

all: $(SO_LIB)

# ----- BLOQUE ASM -----
# Se agregó la bandera -g para la depuración en GDB
$(ASM_OBJ): $(ASM_SRC)
	nasm -f elf64 -g $(ASM_SRC) -o $(ASM_OBJ)

# Construcción de la librería compartida para Python
$(SO_LIB): $(C_SRC) $(ASM_OBJ)
	gcc -shared -fPIC $(C_SRC) $(ASM_OBJ) -o $(SO_LIB)

# ----- BLOQUE DEBUGGING -----
# Compila el archivo de prueba en C junto con el objeto ASM
debug: $(ASM_OBJ)
	gcc -g $(C_TEST_SRC) $(ASM_OBJ) -o $(GDB_EXEC)

# Compila para debug y abre GDB automáticamente
run-debug: debug
	gdb ./$(GDB_EXEC)

run: $(SO_LIB)
	python3 $(PY_DIR)/api.py

run_flask: $(SO_LIB)
	python3 $(PY_DIR)/view.py

# Se agregó la eliminación del ejecutable de prueba
clean:
	rm -f $(ASM_OBJ) $(SO_LIB) $(GDB_EXEC)