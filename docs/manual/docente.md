# Manual del Docente

> Audiencia: Docente o equipo de cátedra que configura prácticas, diseña casos de prueba, evalúa código y gestiona entregas.
> Para la verificación temprana del lado del estudiante, ver [`estudiante.md`](estudiante.md).

---

## 1. División de Roles: Ripley vs. Dredd

En el ecosistema docente actual, las responsabilidades se dividen claramente:

| Componente | Responsabilidad | Herramienta |
|---|---|---|
| **Definición de Prácticas y Testcases** | Creación de esqueletos, generación de entradas por fuzzing y empaquetado `.ripkg`. | **`ripley`** |
| **Motor de Verificación C** | Análisis estático AST, reglas P1 (0xXXXXh), compilación sandbox con ASan y traducción GCC. | **`ripley`** (`check` / `analyze`) |
| **Orquestación Masiva de Moodle** | Ingesta de ZIPs, versionado SHA-256 (`r1`, `r2`), mapeo interactivo (`mappings.json`), CSV y ZIP feedback. | **`dredd`** (`moodle ingest`, `map`, `export`) |
| **Orquestación GitHub Classroom** | Clonación/sincronización, feedback automático en Pull Requests y reparación de ramas. | **`dredd`** (`eval`, `comment`, `pr-fix`) |
| **Detección de Plagio en Cohorte** | Matriz de similitud y reporte Winnowing sobre todas las entregas. | **`dredd`** (`plagiarism`) |
| **Exportación de Informes** | Conversión Markdown a HTML enriquecido o PDF sin dependencias externas. | **`dredd`** (`export-report`) |

---

## 2. Creación y Configuración de Prácticas con Ripley

### 2.1 Inicializar una Práctica
```bash
# Crear estructura en ./practicas/<slug>
ripley practica init --name "Práctica 2 - Punteros y Memoria Dinámica" --id 1236012

# Generar esqueletos de casos de prueba
ripley testcase skeleton --exercise ej1 --cases 4
```

### 2.2 Generar Casos de Prueba con Fuzzing
Podés usar la solución modelo de la cátedra como oráculo para generar automáticamente los casos de prueba de borde y sus salidas esperadas `.out`:

```bash
ripley testcase fuzz --activity entrega-2_1236012 --exercise ej1 \
    --solution practicas/entrega-2_1236012/ejercicios/ej1/solucion_modelo.c --cases 6
```

### 2.3 Empaquetar para Distribución a Estudiantes (`.ripkg`)
Generá el archivo `.ripkg` que contiene los flags oficiales de compilación, checks activos y testcases públicos:

```bash
ripley practica pack entrega-2_1236012 -o entrega-2.ripkg
```

---

## 3. Orquestación y Calificación con Dredd

### 3.1 Flujo Moodle
```bash
# 1. Ingesta y descompresión con normalización UTF-8 y versionado SHA-256
dredd moodle ingest entregas_moodle_tp02.zip

# 2. Mapeo interactivo o heurístico de fuentes a ejercicios
dredd map entrega-2_1236012 -e ej1 -e ej2 --auto

# 3. Detección de plagio en la cohorte
dredd plagiarism entrega-2_1236012 --threshold 0.70

# 4. Exportación de calificaciones y dashboard
dredd export entrega-2_1236012
```

### 3.2 Flujo GitHub Classroom
```bash
# 1. Evaluar repositorios de alumnos y generar reportes Markdown
dredd eval tp02 --all

# 2. Publicar informe como comentario en el Pull Request del alumno
dredd comment tp02 alumno_juan --open

# 3. Reparar Pull Request roto o ausente
dredd pr-fix tp02 alumno_juan
```
