<!-- VERSIÓN (Cargado desde plantilla: version_section.jinja2.md) -->
## Versión {{ numero_version }} - {{ fecha_hora }}

### Resumen de Cambios y Archivos
- **Archivos nuevos:** {{ archivos_nuevos }}
- **Archivos modificados:** {{ archivos_modificados }}
- **Archivos sin cambios:** {{ archivos_sin_cambios }}
- **Archivos ignorados/no permitidos:** {{ archivos_ignorados }}

{% if diff_unificado %}
```diff
{{ diff_unificado }}
```
{% endif %}

### Compilación, Estilo y Análisis Estático

| Archivo | Estado Compilación | Evaluación de Estilo | Valgrind (Fugas) | Cppcheck / Rules |
| ----- | ----- | ----- | ----- | ----- |
{% for item in resultados_compilacion %}
| `{{ item.nombre_archivo }}` | {{ item.estado }} | {{ item.estado_estilo }} | {{ item.estado_valgrind }} | {{ item.estado_cppcheck }} |
{% endfor %}

#### Observaciones de Estilo y Formato
{% for observacion in observaciones_estilo %}
- **`{{ observacion.archivo }}` (Línea {{ observacion.linea }}):** {{ observacion.mensaje }}
{% else %}
_No se detectaron faltas de estilo según las reglas configuradas._
{% endfor %}

#### Logs de Compilación y Linter
```text
{{ logs_detallados_compilacion }}
```

### Pruebas de Entrada/Salida (Test Cases)

| Ejercicio | Caso de Prueba | Argumentos CLI | Resultado | Tiempo Exec. |
| ----- | ----- | ----- | ----- | ----- |
{% for test in resultados_pruebas %}
| `{{ test.ejercicio }}` | {{ test.nombre_caso }} | `{{ test.argumentos_cli }}` | {{ test.resultado }} | {{ test.tiempo_ms }} ms |
{% endfor %}

### Nota Preliminar Estimada: {{ nota_preliminar }} / 10
_Desglose: Compilación ({{ nota_compilacion }}), Estilo ({{ nota_estilo }}), Linter ({{ nota_linter }}), Test Cases ({{ nota_pruebas }})_
