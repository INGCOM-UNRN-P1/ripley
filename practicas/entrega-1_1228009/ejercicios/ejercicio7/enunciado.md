# Ejercicio 7: Conversor de Calificaciones ⭐⭐⭐⭐☆
**Identificador:** `ejercicio7` | **Módulo:** Práctica 1

---

## 1. Consigna
Convertí una calificación numérica decimal en escala de $0$ a $10$ a su correspondiente letra estándar (A, B, C, D, F) y su porcentaje equivalente ($0\% - 100\%$).

### Escala de Equivalencias:
- **$[9.0, 10.0]$:** Calificación `A` ($90\% - 100\%$)
- **$[8.0, 9.0)$:** Calificación `B` ($80\% - 89\%$)
- **$[7.0, 8.0)$:** Calificación `C` ($70\% - 79\%$)
- **$[6.0, 7.0)$:** Calificación `D` ($60\% - 69\%$)
- **$[0.0, 6.0)$:** Calificación `F` ($< 60\%$)

---

## 2. Entrada y Salida
- **Entrada (`stdin`):** Un número de punto flotante entre $0.0$ y $10.0$.
- **Salida (`stdout`):** La letra de calificación asignada seguida del porcentaje calculado en formato entero (ej. `A (95%)`).

---

## 3. Ejemplos de Ejecución
```text
Entrada:
9.5

Salida:
A (95%)
```

```text
Entrada:
4.0

Salida:
F (40%)
```
