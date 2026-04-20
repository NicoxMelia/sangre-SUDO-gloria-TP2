# Trabajo Práctico N°2 — Cálculos en Ensamblador con Capas Python/C

## Descripción General

El sistema implementa un pipeline de cuatro capas para obtener, procesar y visualizar el **Índice de Gini** de cualquier país desde la API REST del Banco Mundial:

1. **Python (`api.py`)** — consulta la API REST, filtra y normaliza datos, y orquesta el procesamiento.
2. **C (`receiver.c`)** — actúa como puente entre Python y el ensamblador.
3. **Ensamblador x86-64 (`calc.asm`)** — realiza el cálculo numérico efectivo usando el stack.
4. **Flask + HTML/CSS (`view.py` + templates)** — expone una UI web para explorar los datos procesados.

---

## Arquitectura y Flujo de Datos

```
┌─────────────────────────────────────────────────────┐
│  CAPA 0 — Flask UI (src/python/view.py)             │
│  • Servidor HTTP en puerto 5000                     │
│  • GET /?country=X → render index.html             │
│  • Llama a api.build_view_data()                    │
└────────────────────┬────────────────────────────────┘
                     │ Python function call
┌────────────────────▼────────────────────────────────┐
│  CAPA 1 — Python (src/python/api.py)                │
│  • HTTP GET → API REST Banco Mundial (todos los     │
│    países 2011-2020)                                │
│  • Filtra, normaliza y procesa via ctypes           │
│  • Expone build_view_data(country) al servidor      │
└────────────────────┬────────────────────────────────┘
                     │ ctypes → lib.get_value_processed(double)
┌────────────────────▼────────────────────────────────┐
│  CAPA 2 — C (src/c/receiver.c)                      │
│  • get_value_processed(double value)                │
│  • Llama a process_value() con 9 parámetros         │
│    (8 dummies para agotar XMM0–XMM7)               │
└────────────────────┬────────────────────────────────┘
                     │ call → process_value (stack)
┌────────────────────▼────────────────────────────────┐
│  CAPA 3 — Ensamblador (src/asm/calc.asm)            │
│  • Lee el 9.º parámetro desde [rbp+16]              │
│  • Trunca double → int (cvttsd2si)                  │
│  • Suma 1 y retorna en eax                          │
└─────────────────────────────────────────────────────┘
```

---

## Capa 1 — Python: Consulta REST y Orquestación

**Archivo:** `src/python/api.py`

El módulo consulta el endpoint público del Banco Mundial para obtener los coeficientes de Gini de **todos los países** entre 2011 y 2020. Ofrece funciones de filtrado, normalización y construcción del contexto para la UI Flask. La ruta a `libgini.so` se resuelve de forma dinámica para funcionar tanto desde la terminal como desde el servidor web.

```python
import os
import ctypes
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
LIB_PATH = os.path.join(ROOT_DIR, "libgini.so")

lib = ctypes.CDLL(LIB_PATH)
lib.get_value_processed.argtypes = [ctypes.c_double]
lib.get_value_processed.restype = ctypes.c_int

API_URL = (
    "https://api.worldbank.org/v2/en/country/all/indicator/"
    "SI.POV.GINI?format=json&date=2011:2020&per_page=32500&page=1"
)


def get_data_from_api(url=API_URL):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, list) and len(payload) > 1:
        return payload[1]
    return []


def filter_data_by_country(data, country):
    items_filtered = []
    for item in data:
        if item.get("country", {}).get("value") == country:
            items_filtered.append(item)
    return items_filtered


def get_gini_data(data):
    gini_data = []
    for item in data:
        value = item.get("value")
        if value is not None:
            gini_index = int(lib.get_value_processed(float(value)))
        else:
            gini_index = None
        gini_data.append(gini_index)
    return gini_data


def add_processed_values(data):
    processed_values = get_gini_data(data)
    for item, processed in zip(data, processed_values):
        item["processed_value"] = processed
    return data


def normalize_data(data):
    items = []
    for item in data:
        if not item or not item.get("country") or not item.get("indicator"):
            continue
        items.append(
            {
                "year": item.get("date"),
                "value": item.get("processed_value"),
                "country": item.get("country", {}).get("value"),
                "iso3": item.get("countryiso3code") or "-",
                "indicator": item.get("indicator", {}).get("value"),
            }
        )
    return items


def format_value(value):
    if value is None:
        return "Unknown"
    return value


def build_view_data(selected_country=""):
    data = add_processed_values(get_data_from_api())
    rows = normalize_data(data)
    rows = sorted(rows, key=lambda item: int(item.get("year") or 0), reverse=True)

    countries = sorted({item["country"] for item in rows if item["country"]})

    if selected_country:
        filtered_data = filter_data_by_country(data, selected_country)
        filtered_rows = normalize_data(filtered_data)
        filtered_rows = sorted(
            filtered_rows, key=lambda item: int(item.get("year") or 0), reverse=True
        )
        status_text = f"Showing results for {selected_country}."
    else:
        filtered_rows = rows
        status_text = "Showing results for all countries."

    for item in filtered_rows:
        item["display_value"] = format_value(item.get("value"))

    return {
        "countries": countries,
        "selected_country": selected_country,
        "rows": filtered_rows,
        "total_count": len(rows),
        "filtered_count": len(filtered_rows),
        "status_text": status_text,
    }


if __name__ == "__main__":
    sample = build_view_data("Argentina")
    print(sample["rows"][:3])
```

## Capa 2 — C: Puente hacia el Ensamblador

**Archivo:** `src/c/receiver.c`

El archivo C expone la función pública `get_value_processed` hacia Python y es quien invoca la rutina de ensamblador. La estrategia de los 8 parámetros dummy es deliberada: agota los registros vectoriales `XMM0–XMM7` de la ABI System V AMD64, obligando a que el noveno argumento (el valor real) se pase **por el stack**, lo cual es exactamente lo que se quiere demostrar.

```c
#include <stdio.h>

/*
 * Declaración de la rutina de ensamblador.
 * Los 8 primeros parámetros son floats/doubles dummy para agotar
 * los registros XMM0–XMM7; el noveno es el valor real de Gini.
 */
extern int process_value(
    float value1, float value2, float value3, float value4,
    float value5, float value6, float value7, float value8,
    double value9
);

/* Función pública llamada desde Python vía ctypes. */
int get_value_processed(double value) {
    return process_value(
        0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 0.0,
        value          /* <-- noveno argumento → va al stack */
    );
}
```

**Archivo de prueba:** `src/c/main_test.c`

Permite ejecutar la rutina ASM de forma aislada (sin Python) para depuración con GDB.

```c
#include <stdio.h>

extern int process_value(
    double d1, double d2, double d3, double d4,
    double d5, double d6, double d7, double d8,
    double real_value
);

int main() {
    double valor_prueba = 42.7;
    int resultado = process_value(
        0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 0.0,
        valor_prueba
    );
    printf("Resultado final: %d\n", resultado);   /* Espera: 43 */
    return 0;
}
```

---

## Capa 3 — Ensamblador x86-64: Cálculo con Stack

**Archivo:** `src/asm/calc.asm`

### Convención de llamado (System V AMD64 ABI)

| Parámetro | Tipo | Ubicación |
|---|---|---|
| value1 … value8 | float/double | XMM0 – XMM7 (registros vectoriales) |
| **value9 (Gini)** | **double** | **Stack — [rbp + 16]** |
| Retorno (int) | int | Registro `eax` |

### Mapa del stack al entrar a `process_value`

```
       Dirección más alta
       ┌──────────────────┐
       │  ... parámetros  │  (value8, value7, …)
       ├──────────────────┤
rbp+16 │  value9 (double) │  ← el valor real de Gini
       ├──────────────────┤
rbp+8  │  dirección ret.  │  (empujada por CALL)
       ├──────────────────┤
rbp    │  rbp anterior    │  (guardado por PUSH RBP)
       └──────────────────┘
       Dirección más baja (tope del stack)
```

### Código ensamblador comentado

```nasm
bits 64

global process_value        ; Hace visible la función para el enlazador

section .text

process_value:

    ; ── 1. Creación del Stack Frame ──────────────────────────
    push rbp                ; Guarda el puntero base del llamador (C)
    mov  rbp, rsp           ; Establece el propio frame pointer

    ; ── 2. LECTURA DEL PARÁMETRO DESDE LA PILA ─────────────────────────
    ; Los primeros 8 argumentos flotantes ya ocuparon XMM0–XMM7.
    ; El 9.º (value9, el Gini real) quedó en el stack.
    ; Offset: 8 bytes (old rbp) + 8 bytes (return addr) = 16
    movsd xmm0, qword [rbp + 16]   ; Carga el double de 8 bytes en XMM0

    ; ── 3. CÁLCULO Y CONVERSIÓN ────────────────────────────────────────
    ; cvttsd2si: Convert with Truncation Scalar Double-precision to
    ;            Signed Integer — trunca (no redondea) hacia cero.
    cvttsd2si eax, xmm0            ; double → int, resultado en EAX
    add eax, 1                     ; Aplica la conversión solicitada (+1)

    ; ── 4. Restauración y Retorno ───────────────────────────
    pop rbp                        ; Restaura el frame pointer del llamador
    ret                            ; Retorna; el resultado entero está en EAX

    ; Marca el stack como no ejecutable (hardening de seguridad ELF)
    section .note.GNU-stack noalloc noexec nowrite progbits
```

### Instrucciones clave

| Instrucción | Significado |
|---|---|
| `push rbp` | Guarda el frame pointer del llamador en el stack |
| `mov rbp, rsp` | Congela la base del frame actual |
| `movsd xmm0, qword [rbp+16]` | Lee 8 bytes (double) desde el stack |
| `cvttsd2si eax, xmm0` | Convierte double → entero con truncamiento |
| `add eax, 1` | Cálculo de conversión: índice + 1 |
| `pop rbp` | Restaura el frame pointer original |
| `ret` | Retorna al llamador; `eax` contiene el resultado |

---

## Capa 0 — Flask: Servidor Web y UI

### Servidor Flask

**Archivo:** `src/python/view.py`

Expone la aplicación web en el puerto 5000. La ruta `GET /` acepta el parámetro `country` para filtrar resultados y delega toda la lógica de datos a `api.build_view_data()`.

```python
import os
import requests
from flask import Flask, jsonify, render_template, request
import api

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "..", "templates"),
    static_folder=os.path.join(BASE_DIR, "..", "static"),
)


@app.get("/")
def index():
    selected_country = request.args.get("country", "")
    context = api.build_view_data(selected_country)
    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

### Template HTML

**Archivo:** `src/templates/index.html`

Renderizado en el servidor (Jinja2). Permite filtrar por país via un `<select>` que hace submit automático al cambiar. Muestra una tabla con columnas: Año, Índice Gini (procesado), País, ISO3 e Indicador.

```html
<!doctype html>
<html lang="en">
  <head>
    <title>Gini Index Explorer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet" />
    <link rel="stylesheet" href="/static/css/styles.css" />
  </head>
  <body>
    <!-- Hero card con título y chip de cobertura 2011-2020 -->
    <header class="py-5">
      <div class="container">
        <div class="hero-card">
          <div class="hero-text">
            <p class="eyebrow">World Bank Data</p>
            <h1 class="display-5 fw-semibold">Gini Index Explorer</h1>
          </div>
          <div class="hero-chip">
            <span class="chip-title">Coverage</span>
            <span class="chip-value">2011 - 2020</span>
          </div>
        </div>
      </div>
    </header>

    <main class="pb-5">
      <div class="container">
        <!-- Filtro por país -->
        <div class="controls-card">
          <form method="get">
            <select name="country" class="form-select" onchange="this.form.submit()">
              <option value="">All countries</option>
              {% for country in countries %}
                <option value="{{ country }}" {% if country == selected_country %}selected{% endif %}>
                  {{ country }}
                </option>
              {% endfor %}
            </select>
          </form>
        </div>

        <!-- Tabla de datos -->
        <div class="data-card mt-4">
          <p class="text-muted">{{ status_text }}</p>
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Year</th><th>Gini Index</th><th>Country</th>
                <th>ISO3</th><th>Indicator</th>
              </tr>
            </thead>
            <tbody>
              {% for item in rows %}
                <tr>
                  <td>{{ item.year }}</td>
                  <td>{{ item.display_value }}</td>
                  <td>{{ item.country }}</td>
                  <td>{{ item.iso3 }}</td>
                  <td>{{ item.indicator }}</td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  </body>
</html>
```

**Puntos clave del template:**
- El `<select>` usa `onchange="this.form.submit()"` para recargar la página sin JavaScript adicional.
- Los valores `None` del API se muestran como `Unknown` (via `format_value` en `api.py`).
- El renderizado es **server-side**: no hay fetch asíncrono, todo lo resuelve Flask en el `GET /`.

### Estilos CSS

**Archivo:** `src/static/css/styles.css`

Diseño con variables CSS, gradiente radial de fondo, cards con sombra y animación de entrada (`float-in`). Usa la fuente `Space Grotesk` de Google Fonts.

```css
:root {
  --bg-start: #edf3ff;
  --bg-end: #fef6f0;
  --card: #ffffff;
  --ink: #1f1f28;
  --muted: #6b7280;
  --accent: #1d4ed8;
  --accent-soft: rgba(29, 78, 216, 0.1);
  --shadow: 0 20px 50px rgba(15, 23, 42, 0.12);
}

body {
  font-family: "Space Grotesk", system-ui, -apple-system, sans-serif;
  background: radial-gradient(circle at top left, rgba(29, 78, 216, 0.12), transparent 45%),
    radial-gradient(circle at 60% 20%, rgba(251, 146, 60, 0.18), transparent 40%),
    linear-gradient(140deg, var(--bg-start), var(--bg-end));
  min-height: 100vh;
}

.hero-card, .controls-card, .data-card {
  background: var(--card);
  border-radius: 20px;
  padding: 24px 28px;
  box-shadow: var(--shadow);
}

.hero-card { animation: float-in 700ms ease-out; }

@keyframes float-in {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

---

## Sistema de Compilación (Makefile)

```makefile
ASM_DIR := src/asm
C_DIR   := src/c
PY_DIR  := src/python

ASM_SRC    := $(ASM_DIR)/calc.asm
C_SRC      := $(C_DIR)/receiver.c
C_TEST_SRC := $(C_DIR)/main_test.c

ASM_OBJ  := converter.o
SO_LIB   := libgini.so
GDB_EXEC := programa_gdb

.PHONY: all clean run debug run-debug run_flask

all: $(SO_LIB)

# Ensambla el .asm en un objeto ELF64 con símbolos de debug
$(ASM_OBJ): $(ASM_SRC)
	nasm -f elf64 -g $(ASM_SRC) -o $(ASM_OBJ)

# Enlaza el objeto ASM con el wrapper C para generar la librería compartida
$(SO_LIB): $(C_SRC) $(ASM_OBJ)
	gcc -shared -fPIC $(C_SRC) $(ASM_OBJ) -o $(SO_LIB)

# Compila el ejecutable de prueba para uso con GDB
debug: $(ASM_OBJ)
	gcc -g $(C_TEST_SRC) $(ASM_OBJ) -o $(GDB_EXEC)

# Construye en modo debug y abre GDB automáticamente
run-debug: debug
	gdb ./$(GDB_EXEC)

# Compila y ejecuta el sistema completo (Python + C + ASM) en modo CLI
run: $(SO_LIB)
	python3 $(PY_DIR)/api.py

# Compila y levanta el servidor Flask con la UI web
run_flask: $(SO_LIB)
	python3 $(PY_DIR)/view.py

clean:
	rm -f $(ASM_OBJ) $(SO_LIB) $(GDB_EXEC)
```

### Targets disponibles

| Target | Descripción |
|---|---|
| `make` / `make all` | Compila `libgini.so` |
| `make run` | Compila y ejecuta el pipeline en modo CLI |
| `make run_flask` | Compila y levanta el servidor Flask en `localhost:5000` |
| `make debug` | Compila el binario de prueba para GDB |
| `make run-debug` | Compila y abre GDB automáticamente |
| `make clean` | Elimina artefactos compilados |

### Cadena de compilación

```
src/asm/calc.asm
    │
    │  nasm -f elf64 -g
    ▼
converter.o  ──┐
               │  gcc -shared -fPIC
src/c/receiver.c ──┤
               │
               ▼
          libgini.so
               │
               │  ctypes.CDLL (en tiempo de ejecución)
               ▼
        src/python/api.py  ←── src/python/view.py (Flask)
                                        │
                                 HTTP GET /?country=X
                                        ▼
                               src/templates/index.html
```

---

## Ejemplo de Ejecución

### Modo CLI

```
$ make run
python3 src/python/api.py
[{'year': '2019', 'value': 43, 'country': 'Argentina', ...}, ...]
```

### Modo UI Web

```
$ make run_flask
python3 src/python/view.py
 * Running on http://0.0.0.0:5000
```

Luego abrir `http://localhost:5000` en el navegador. El `<select>` filtra por país y recarga la tabla automáticamente.

Para depuración con GDB:

```
$ make run-debug
gdb ./programa_gdb
(gdb) break process_value
(gdb) run
(gdb) info registers xmm0
(gdb) stepi
```

---

## Convenciones de Llamado Demostradas

El trabajo demuestra el uso correcto de las convenciones de llamado **System V AMD64 ABI**:

1. **Paso de parámetros por registros:** Los primeros 8 argumentos flotantes se pasan en `XMM0–XMM7`. Se usan 8 parámetros dummy para agotar deliberadamente estos registros.

2. **Paso de parámetros por stack:** Al agotarse `XMM0–XMM7`, el noveno argumento (el valor real) se coloca en el stack, accesible desde `[rbp + 16]`.

3. **Prólogo y epílogo estándar:** `push rbp` / `mov rbp, rsp` al entrar; `pop rbp` / `ret` al salir.

4. **Retorno de resultado:** El entero calculado se devuelve en el registro `eax`, que C y Python leen automáticamente como valor de retorno.

5. **Stack no ejecutable:** La sección `.note.GNU-stack` marca la pila como no ejecutable, cumpliendo con las buenas prácticas de seguridad ELF64.

---
