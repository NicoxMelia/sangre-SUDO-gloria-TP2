bits 64

global process_value
section .text
process_value:
    ; ---------------------------------------------------------
    ; 1. PRÓLOGO (Creación del Stack Frame)
    ; ---------------------------------------------------------
    push rbp               ; Guardamos el puntero base de la función llamadora (C)
    mov rbp, rsp           ; Establecemos nuestro propio puntero base

    ; ---------------------------------------------------------
    ; 2. LECTURA DEL PARÁMETRO DESDE LA PILA
    ; ---------------------------------------------------------
    ; Como C nos enviará el 'double' por la pila (agotando los registros),
    ; el dato se encuentra saltando el rbp viejo (8 bytes) y la
    ; dirección de retorno (8 bytes). Por eso buscamos en 16(rbp).
    movsd xmm0, qword [rbp + 16]   ; Cargamos el double (8 bytes) desde el stack a xmm0

    ; ---------------------------------------------------------
    ; 3. CÁLCULO Y CONVERSIÓN
    ; ---------------------------------------------------------
    ; cvttsd2si: Convert with Truncation Scalar Double to Signed Integer
    ; Convierte el double que está en xmm0 a un entero (int) y lo guarda en eax
    cvttsd2si eax, xmm0
    add eax, 1                  ; Le sumamos 1 al resultado, tal como pide el TP

    ; ---------------------------------------------------------
    ; 4. EPÍLOGO (Destrucción del Stack Frame y Retorno)
    ; ---------------------------------------------------------
    pop rbp                    ; Restauramos el puntero base original de C
    ret                        ; Volvemos al programa en C
    section .note.GNU-stack noalloc noexec nowrite progbits