---
title: "Manual de Referencia: ripley"
subtitle: "Ripley — Linter Pedagógico de Reglas Institucionales 0xXXXXh y Microkernel de Auditoría"
author: "Cátedra de Algoritmos y Programación"
date: "2026-08-31"
---

(manual-ripley)=
# Ripley — Linter Pedagógico de Reglas Institucionales 0xXXXXh y Microkernel de Auditoría

````{abstract}
**Rol en el ecosistema:** Linter central de cátedra que ejecuta el catálogo completo de reglas pedagógicas 0xXXXXh (estilo, modularidad, seguridad, antipatrones) y orquesta plugins desacoplados.
````

---

(manual-ripley-proposito)=
## 1. Propósito y Filosofía Pedagógica

La herramienta **`ripley`** forma parte del ecosistema oficial de software de la cátedra. Su diseño sigue principios pedagógicos rigurosos:

1. **Evidencia Técnica Directa**: Todo diagnóstico se fundamenta en la norma ISO C (C11/C23), en el modelo de memoria del sistema o en convenciones arquitectónicas formales.
2. **Acción Correctiva Concreta**: Cada advertencia incluye la prescripción técnica inmediata para resolver el defecto sin recurrir a conjeturas.
3. **Autonomía del Estudiante**: Facilita la autoevaluación local antes de la entrega final del trabajo práctico.
4. **Objetividad Docente**: Estandariza la corrección automática eliminando discrepancias subjetivas en la evaluación.

---

(manual-ripley-instalacion)=
## 2. Instalación y Diagnóstico del Entorno

````{important}
Asegurate de contar con el compilador GCC/Clang y las librerías del sistema instaladas antes de ejecutar `ripley`.
````

Para comprobar el estado de salud de tu entorno de trabajo y las dependencias auxiliares:

````{code-block} bash
# Comprobación de dependencias del sistema
ripley doctor
````

Si se detecta la falta de alguna utilidad (como `gdb`, `valgrind`, `clang-format` o `typst`), el comando indicará el paquete exacto a instalar según tu distribución GNU/Linux o entorno MSYS2.

---

(manual-ripley-comandos)=
## 3. Referencia Completa de Comandos CLI

A continuación se detallan los subcomandos principales disponibles en `ripley`:

| Sintaxis del Comando | Descripción y Efecto |
| :--- | :--- |
| `ripley check src/ include/` | Ejecuta todas las reglas activas de cátedra sobre el proyecto. |
| `ripley check --rule 0x1001h src/` | Audita una regla específica del catálogo. |
| `ripley explain 0x0001h` | Explica en detalle el fundamento pedagógico de una regla. |
| `ripley list-rules` | Muestra el catálogo completo clasificado por categorías. |
| `ripley doctor` | Verifica dependencias y plugins registrados en el microkernel. |

````{tip}
Podés agregar el flag `--json` a la mayoría de los comandos para exportar resultados en formato estructurado o `--md` para generar reportes Markdown para el informe de entrega.
````

---

(manual-ripley-tutorial)=
## 4. Tutorial Paso a Paso con Ejemplos Reales

### Caso de Estudio

Considerá el siguiente fragmento de código representativo:

````{code-block} c
:linenos:
// Violación de regla institucional 0x1001h (Estructura de control sin bloque de llaves)
void procesar(int a) {
    if (a > 0)
        a++; // Falla 0x1001h: Toda sentencia de control debe tener llaves {}
}
````

### Ejecución de la Herramienta

Ejecutá el análisis desde tu terminal:

````{code-block} bash
ripley check src/ include/
````

### Salida Obtenida en Consola

````{code-block} text
⚠️ REPORTE DE AUDITORÍA RIPLEY (Reglas de Cátedra):
┌──────────────┬─────────┬────────────────────────────────────────────────────────┐
│ Archivo:L:C  │ Regla   │ Descripción del Diagnóstico                            │
├──────────────┼─────────┼────────────────────────────────────────────────────────┤
│ proc.c:3:5   │ 0x1001h │ Estructura de control 'if' sin bloque explícito '{}'.  │
│ proc.c:1:23  │ 0x000Bh │ Llave de apertura en estilo K&R (exigido: Allman).     │
└──────────────┴─────────┴────────────────────────────────────────────────────────┘
💡 Ejecutá 'ripley explain 0x1001h' para ver el ejemplo correcto y fundamento.
````

````{note}
Prestá atención a la explicación pedagógica generada: la herramienta no solo señala la línea del problema, sino que explica la causa raíz y el impacto en memoria o arquitectura.
````

---

(manual-ripley-ejercicios)=
## 5. Ejercicios Prácticos y Desafíos

Practicá el uso avanzado de **`ripley`** resolviendo los siguientes ejercicios:

````{exercise} Desafío 1: Auditoría Integral de Código Estudiantil
Escanear todo el código fuente antes de enviar al autograder.

**Instrucción de ejecución:**
```bash
ripley check src/ include/
```
````

````{solution} Desafío 1
```bash
ripley check src/ include/
# Verificá que la operación concluya exitosamente con código de salida 0.
```
````

````{exercise} Desafío 2: Consulta de Fundamentos Pedagógicos
Consultar por qué está prohibida la sentencia `goto` (0x1006h).

**Instrucción de ejecución:**
```bash
ripley explain 0x1006h
```
````

````{solution} Desafío 2
```bash
ripley explain 0x1006h
# Revisá el archivo generado o el informe en terminal para confirmar la resolución del problema.
```
````

````{exercise} Desafío 3: Verificación con Modo Estricto de Cátedra
Correr auditoría bloqueando commits si existen violaciones institucionales.

**Instrucción de ejecución:**
```bash
ripley check src/ --strict
```
````

````{solution} Desafío 3
```bash
ripley check src/ --strict
# Comprobá que la salida confirme la ausencia de advertencias o errores pendientes.
```
````

---

(manual-ripley-makefile)=
## 6. Integración en el Flujo de Trabajo y Makefile

Para incorporar `ripley` de forma automática a tu flujo de desarrollo, agregá la siguiente regla en el `Makefile` de tu proyecto:

````{code-block} makefile
check-ripley:
	@echo "=== Ejecutando verificación con ripley ==="
	ripley check src/ include/

.PHONY: check-ripley
````

Ejecutá `make check-ripley` antes de cada commit para asegurar que tu código conserve el estado de aprobación.

---

(manual-ripley-arquitectura)=
## 7. Arquitectura Interna y Mecanismo Técnico

La herramienta **`ripley`** implementa un motor de alta precisión basado en:

- **Tecnología Núcleo:** `Python Microkernel Architecture + Pluggy Dynamic Plugin System + Multi-Format Reporter (Rich, JSON, MD)`.
- **Aislamiento y Determinismo:** Diseñada para operar sin efectos colaterales en entornos de integración continua (CI), terminales de estudiantes y servidores docentes headless.
- **Manejo de Errores Pedagógico:** Todo fallo de sintaxis, memoria o lógica se traduce en una acción prescriptiva concreta con su respectiva justificación técnica.

---

(manual-ripley-ecosistema)=
## 8. Integración y Conexión con el Ecosistema

````{note}
Ninguna herramienta opera de forma aislada. **`ripley`** forma parte del pipeline integral de evaluación, verificación y enseñanza de la cátedra.
````

### Diagrama de Flujo e Interoperabilidad

````{mermaid}
graph TD
    SRC[Código C del Estudiante] --> RIP[Ripley: Microkernel de Cátedra]
    GAF[Gaff: Estilo 0x00XXh] --> RIP
    SPK[Spunkmeyer: Antipatrones 0x10XXh] --> RIP
    MOT[Motoko: Modularidad 0x20XXh] --> RIP
    KND[Kaneda: Seguridad 0x30XXh] --> RIP
    ZHO[Zhora: Macros 0x40XXh] --> RIP
    RIP -->|Evaluación Unificada| DRD[Dredd: Autograding Masivo]
    RIP -->|Reporte Pedagógico| TERM[Terminal del Estudiante]
````

### Matriz de Intercambio de Datos

| Canal | Herramientas Conectadas | Tipo de Datos Transferidos |
| :--- | :--- | :--- |
| **Entradas (Inputs)** | - `Código C de entregas de estudiantes` | Código fuente, AST, binarios, testcases, contratos |
| **Salidas (Outputs)** | - `dredd (orquestación masiva)`
- `Estudiante (diagnósticos en terminal)` | Informes Markdown, diagnósticos Rich, JSON, actas |
| **Sincronización** | `gaff`, `spunkmeyer`, `kaneda`, `zhora`, `motoko`, `wierzbowski`, `dredd` | Validación cruzada, flags compartidos y autofix |

### Pipeline de Integración Recomendado

Podés encadenar `ripley` con otras herramientas del ecosistema en una única línea de comando:

````{code-block} bash
# Pipeline de integración típico
ripley check src/ include/ --md reporte_auditoria.md
````

