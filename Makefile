ASM_DIR := src/asm
C_DIR := src/c
PY_DIR := src/python

ASM_SRC := $(ASM_DIR)/calc.asm
C_SRC := $(C_DIR)/receiver.c

ASM_OBJ := converter.o
SO_LIB := libgini.so

.PHONY: all clean run

all: $(SO_LIB)

# ----- BLOQUE ASM (activar cuando calc.asm tenga process_value) -----
# $(ASM_OBJ): $(ASM_SRC)
# 	nasm -f elf64 $(ASM_SRC) -o $(ASM_OBJ)

# Modo actual: solo C (usa mock_process_value definido en receiver.c)
$(SO_LIB): $(C_SRC)
	gcc -shared -fPIC $(C_SRC) -o $(SO_LIB)

# Cuando ASM esté listo, usar este target en lugar del anterior:
# $(SO_LIB): $(C_SRC) $(ASM_OBJ)
# 	gcc -shared -fPIC $(C_SRC) $(ASM_OBJ) -o $(SO_LIB)

run: $(SO_LIB)
	python3 $(PY_DIR)/api.py

clean:
	rm -f $(ASM_OBJ) $(SO_LIB)