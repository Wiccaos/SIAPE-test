# Memoria: Implementación de Estadísticas del Asesor Pedagógico

## Resumen
Esta documentación describe cómo se implementó la pestaña de estadísticas con gráficos interactivos y exportación de reportes para el rol "Asesor Pedagógico". Esta funcionalidad permite al asesor visualizar estadísticas completas del sistema con filtros de tiempo y exportar reportes en PDF o CSV (PowerBI).

---

## 1. ARCHIVOS CREADOS/MODIFICADOS

### 1.1. Vista Principal (`SIAPE/views.py`)

#### Función: `estadisticas_asesor_pedagogico(request)`
- **Ubicación**: Agregar después de `dashboard_asesor`
- **Propósito**: Vista principal que muestra estadísticas completas con filtros de tiempo
- **Características**:
  - Filtro de rango de tiempo: "Último Mes", "Último Semestre", "Último Año", "Histórico"
  - KPIs: Casos nuevos, casos devueltos, casos por estado
  - Gráficos: Línea de tiempo, distribución por estado, distribución por ajustes, estadísticas por rol
  - Tablas detalladas con casos recientes

#### Función: `generar_reporte_pdf_asesor(request)`
- **Propósito**: Genera un PDF con las estadísticas según el rango de tiempo seleccionado
- **Formato**: Usa `xhtml2pdf` (pisa) para generar PDFs
- **Tema visual**: Rojo, blanco y negro (colores de INACAP)

#### Función: `generar_reporte_powerbi_asesor(request)`
- **Propósito**: Genera un CSV para importar en PowerBI
- **Formato**: CSV con múltiples secciones de datos

### 1.2. Template (`SIAPE/templates/SIAPE/estadisticas_asesor_pedagogico.html`)

**Estructura principal**:
```html
{% extends "plantilla.html" %}
{% load static %}

{% block extra_head %}
    <link rel="stylesheet" href="{% static 'CSS/dashboard.css' %}">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
{% endblock %}

{% block content %}
    <!-- Navbar con pestaña "Estadísticas" -->
    <!-- KPIs con clase kpi-container kpi-container-asesor -->
    <!-- Selector de rango de tiempo (debajo de KPIs) -->
    <!-- Gráficos con Chart.js -->
    <!-- Tablas de datos -->
{% endblock %}
```

**Componentes clave**:
1. **Navbar**: Incluye pestaña "Estadísticas" activa
2. **KPIs**: Usa clases `kpi-container` y `kpi-card` con layout horizontal (icono izquierda, texto derecha)
3. **Selector de tiempo**: Formulario con opciones: "ultimo_mes", "ultimo_semestre", "ultimo_anio", "historico"
4. **Gráficos Chart.js**:
   - Gráfico de línea: Tendencia de casos por fecha
   - Gráfico circular (doughnut): Distribución por estado
   - Gráfico circular (pie): Distribución por categorías de ajustes
   - Gráfico de barras: Estadísticas por rol
   - Gráfico de barras: Estadísticas por categoría de ajustes
5. **Tablas**: Casos recientes, ajustes recientes

### 1.3. URLs (`DRF/urls.py`)

Agregar estas rutas:
```python
path('dashboard/asesor/estadisticas/', views.estadisticas_asesor_pedagogico, name='estadisticas_asesor_pedagogico'),
path('dashboard/asesor/estadisticas/reporte-pdf/', views.generar_reporte_pdf_asesor, name='generar_reporte_pdf_asesor'),
path('dashboard/asesor/estadisticas/reporte-powerbi/', views.generar_reporte_powerbi_asesor, name='generar_reporte_powerbi_asesor'),
```

### 1.4. Navbar Updates

Actualizar los siguientes templates para incluir la pestaña "Estadísticas":
- `SIAPE/templates/SIAPE/dashboard_asesor.html`
- `SIAPE/templates/SIAPE/casos_generales.html` (cuando el rol es Asesor Pedagógico)
- `SIAPE/templates/SIAPE/detalle_casos_encargado_inclusion.html` (cuando el rol es Asesor Pedagógico)

---

## 2. LÓGICA DE FILTRADO POR RANGO DE TIEMPO

### 2.1. Función auxiliar (dentro de `estadisticas_asesor_pedagogico`)

```python
def obtener_datos_estadisticas_por_rango(rango_seleccionado):
    """
    Calcula las fechas de inicio y fin según el rango seleccionado.
    Retorna: (fecha_inicio, fecha_fin, titulo_rango)
    """
    ahora = timezone.now()
    
    if rango_seleccionado == 'ultimo_mes':
        fecha_inicio = ahora - timedelta(days=30)
        titulo = "Último Mes"
    elif rango_seleccionado == 'ultimo_semestre':
        fecha_inicio = ahora - timedelta(days=180)
        titulo = "Último Semestre"
    elif rango_seleccionado == 'ultimo_anio':
        fecha_inicio = ahora - timedelta(days=365)
        titulo = "Último Año"
    else:  # historico
        fecha_inicio = None  # Sin límite
        titulo = "Histórico"
    
    fecha_fin = ahora
    return fecha_inicio, fecha_fin, titulo
```

### 2.2. Aplicación del filtro

```python
# En la vista, aplicar el filtro a todas las consultas:
rango_seleccionado = request.GET.get('rango', 'ultimo_mes')
fecha_inicio, fecha_fin, titulo_rango = obtener_datos_estadisticas_por_rango(rango_seleccionado)

# Aplicar a consultas:
if fecha_inicio:
    solicitudes = Solicitudes.objects.filter(created_at__gte=fecha_inicio, created_at__lte=fecha_fin)
else:
    solicitudes = Solicitudes.objects.all()
```

---

## 3. GRÁFICOS CON CHART.JS

### 3.1. Configuración de gráficos circulares

**Tamaño y aspecto**:
- Contenedor: `display: flex; justify-content: center; align-items: center; height: 300px;`
- Canvas: `max-width: 250px; max-height: 250px;`
- Opciones Chart.js: `maintainAspectRatio: false`, `aspectRatio: 1`

**Leyenda personalizada**:
```javascript
plugins: {
    legend: {
        position: 'right',
        generateLabels: function(chart) {
            const original = Chart.defaults.plugins.legend.labels.generateLabels;
            const labels = original.call(this, chart);
            labels.forEach((label, i) => {
                const meta = chart.getDatasetMeta(0);
                const data = meta.data[i];
                const value = chart.data.datasets[0].data[i];
                const total = chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                label.text = `${label.text}: ${value} (${percentage}%)`;
                // Asegurar que el strikethrough funcione cuando se oculta
                if (data.hidden) {
                    label.hidden = true;
                }
            });
            return labels;
        }
    },
    tooltip: {
        callbacks: {
            label: function(context) {
                // Mostrar nombre completo en tooltip
                return context.label + ': ' + context.parsed;
            }
        }
    }
}
```

**CSS para strikethrough**:
```css
.chart-legend-item {
    text-decoration: line-through;
}
```

### 3.2. Tipos de gráficos implementados

1. **Gráfico de línea** (`line`): Tendencia de casos por fecha
2. **Gráfico circular doughnut** (`doughnut`): Distribución por estado
3. **Gráfico circular pie** (`pie`): Distribución por categorías de ajustes
4. **Gráfico de barras** (`bar`): Estadísticas por rol y por categoría

---

## 4. EXPORTACIÓN DE REPORTES

### 4.1. PDF con xhtml2pdf

**Template**: `SIAPE/templates/SIAPE/pdf/reporte_estadistico_asesor.html`

**Características**:
- Tema visual: Rojo (#D32F2F), blanco, negro
- Incluye: KPIs, gráficos (como imágenes o tablas), tablas de datos
- Fecha de emisión y rango de tiempo

**Código de generación**:
```python
from xhtml2pdf import pisa
from django.template.loader import get_template

template = get_template('SIAPE/pdf/reporte_estadistico_asesor.html')
html = template.render(context)
response = HttpResponse(content_type='application/pdf')
response['Content-Disposition'] = f'attachment; filename="Reporte_Asesor_{timezone.now().strftime("%Y%m%d")}.pdf"'

pisa_status = pisa.CreatePDF(html, dest=response)
if pisa_status.err:
    return HttpResponse('Error generando PDF')
return response
```

### 4.2. CSV para PowerBI

**Formato**:
- Múltiples secciones separadas por líneas vacías
- Encabezados claros para cada sección
- Datos en formato CSV estándar

**Código de generación**:
```python
import csv
from django.http import HttpResponse

response = HttpResponse(content_type='text/csv; charset=utf-8')
response['Content-Disposition'] = f'attachment; filename="Reporte_PowerBI_{timezone.now().strftime("%Y%m%d")}.csv"'
response.write('\ufeff')  # BOM para Excel

writer = csv.writer(response)
# Escribir secciones de datos
writer.writerow(['SECCIÓN: CASOS POR ESTADO'])
writer.writerow(['Estado', 'Cantidad'])
for item in estados_stats:
    writer.writerow([item['nombre'], item['cantidad']])

writer.writerow([])  # Línea vacía
writer.writerow(['SECCIÓN: AJUSTES POR CATEGORÍA'])
# ... más secciones
```

---

## 5. ESTILOS CSS

### 5.1. KPIs (usar clases existentes)

```css
.kpi-container-asesor {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px 15px;
    margin-bottom: 30px;
}

.kpi-card {
    display: flex;
    flex-direction: row;
    align-items: center;
    text-align: left;
    padding: 10px 12px;
    gap: 12px;
    min-height: 75px;
    box-sizing: border-box;
    max-width: 100%;
}

.kpi-icon {
    font-size: 1.1rem;
    width: 26px;
    height: 26px;
    padding: 4px;
}

.kpi-value {
    font-size: 1.2rem;
}

.kpi-label {
    font-size: 0.65em;
    word-break: break-word;
}

/* Responsive */
@media (max-width: 768px) {
    .kpi-container-asesor {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 480px) {
    .kpi-container-asesor {
        grid-template-columns: 1fr;
    }
}
```

### 5.2. Selector de tiempo

```css
.time-range-selector {
    display: flex;
    gap: 10px;
    margin-bottom: 30px;
    padding: 15px;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.time-range-selector select {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
}
```

---

## 6. DATOS Y CONSULTAS PRINCIPALES

### 6.1. KPIs

```python
# Casos nuevos esta semana
semana_pasada = timezone.now() - timedelta(days=7)
casos_nuevos_semana = Solicitudes.objects.filter(
    created_at__gte=semana_pasada
).count()

# Casos devueltos desde Director
casos_devueltos_director = Solicitudes.objects.filter(
    estado='pendiente_preaprobacion',
    # Lógica para identificar devueltos
).count()

# Casos por estado
estados_con_cantidad = Solicitudes.objects.values('estado').annotate(
    cantidad=Count('id')
).order_by('estado')
```

### 6.2. Gráfico de tendencia

```python
# Agrupar por fecha (usar Python para evitar problemas con TruncDate)
fechas_solicitudes = Solicitudes.objects.filter(
    created_at__gte=fecha_inicio
).values_list('created_at', flat=True)

from collections import Counter
conteo_por_fecha = Counter()
for fecha in fechas_solicitudes:
    fecha_local = timezone.localtime(fecha)
    fecha_str = fecha_local.strftime('%Y-%m-%d')
    conteo_por_fecha[fecha_str] += 1

# Convertir a formato para Chart.js
labels = sorted(conteo_por_fecha.keys())
data = [conteo_por_fecha[label] for label in labels]
```

### 6.3. Distribución por estado

```python
estados_stats = Solicitudes.objects.filter(
    created_at__gte=fecha_inicio
).values('estado').annotate(
    cantidad=Count('id')
)

# Calcular porcentajes
total = sum(e['cantidad'] for e in estados_stats)
for estado in estados_stats:
    estado['porcentaje'] = (estado['cantidad'] / total * 100) if total > 0 else 0
```

### 6.4. Estadísticas por rol

```python
# Casos asignados por rol
casos_por_rol = {
    'Encargado de Inclusión': Solicitudes.objects.filter(
        coordinadora_asignada__isnull=False,
        created_at__gte=fecha_inicio
    ).count(),
    'Coordinador Técnico Pedagógico': Solicitudes.objects.filter(
        coordinador_tecnico_pedagogico_asignado__isnull=False,
        created_at__gte=fecha_inicio
    ).count(),
    'Asesor Pedagógico': Solicitudes.objects.filter(
        asesor_pedagogico_asignado__isnull=False,
        created_at__gte=fecha_inicio
    ).count(),
    'Director de Carrera': Solicitudes.objects.filter(
        estado='pendiente_aprobacion',
        created_at__gte=fecha_inicio
    ).count(),
}
```

### 6.5. Estadísticas por categorías de ajustes

```python
ajustes_por_categoria = AjusteAsignado.objects.filter(
    solicitudes__created_at__gte=fecha_inicio
).values(
    'ajuste_razonable__categorias_ajustes__nombre_categoria'
).annotate(
    cantidad=Count('id')
).order_by('-cantidad')
```

---

## 7. PASOS PARA IMPLEMENTAR EN OTRA RAMA

### 7.1. Archivos a crear/modificar

1. **`SIAPE/views.py`**: Agregar 3 funciones:
   - `estadisticas_asesor_pedagogico`
   - `generar_reporte_pdf_asesor`
   - `generar_reporte_powerbi_asesor`

2. **`SIAPE/templates/SIAPE/estadisticas_asesor_pedagogico.html`**: Crear template completo

3. **`SIAPE/templates/SIAPE/pdf/reporte_estadistico_asesor.html`**: Crear template para PDF

4. **`DRF/urls.py`**: Agregar 3 rutas

5. **Navbars**: Actualizar templates que muestran navbar para Asesor Pedagógico

### 7.2. Dependencias

Asegurar que estén instaladas:
- `xhtml2pdf` (para PDFs)
- `reportlab` (alternativa, pero se usó xhtml2pdf)
- `openpyxl` (ya está)
- Chart.js (CDN en template)

### 7.3. Orden de implementación recomendado

1. Crear función `estadisticas_asesor_pedagogico` con datos básicos
2. Crear template con KPIs y selector de tiempo
3. Agregar gráficos uno por uno
4. Implementar exportación PDF
5. Implementar exportación CSV
6. Actualizar navbars
7. Ajustar estilos CSS

---

## 8. NOTAS IMPORTANTES

- **Filtro de tiempo**: Se aplica a TODAS las consultas de estadísticas
- **Gráficos circulares**: Tamaño fijo (250x250px) y mismo tamaño ambos
- **Leyenda**: Muestra valores y porcentajes, con strikethrough cuando se oculta
- **Responsive**: KPIs en grid de 4 columnas (2 en tablet, 1 en móvil)
- **Tema visual**: Rojo (#D32F2F), blanco, negro en PDFs
- **Selector de tiempo**: Ubicado debajo de los KPIs, antes de los gráficos

---

## 9. EJEMPLO DE ESTRUCTURA DE DATOS PARA CHART.JS

```python
# Para gráfico de línea
chart_linea_data = {
    'labels': ['2024-01', '2024-02', ...],
    'datasets': [{
        'label': 'Casos',
        'data': [5, 8, 12, ...],
        'borderColor': '#D32F2F',
        'backgroundColor': 'rgba(211, 47, 47, 0.1)',
    }]
}

# Para gráfico circular
chart_estados_data = {
    'labels': ['Pendiente', 'Aprobado', ...],
    'datasets': [{
        'data': [10, 25, ...],
        'backgroundColor': ['#D32F2F', '#28a745', ...],
    }]
}

# En el template, convertir a JSON:
chart_linea_json = json.dumps(chart_linea_data)
```

---

## 10. CHECKLIST DE IMPLEMENTACIÓN

- [ ] Función `estadisticas_asesor_pedagogico` en `views.py`
- [ ] Función `generar_reporte_pdf_asesor` en `views.py`
- [ ] Función `generar_reporte_powerbi_asesor` en `views.py`
- [ ] Template `estadisticas_asesor_pedagogico.html`
- [ ] Template `pdf/reporte_estadistico_asesor.html`
- [ ] URLs en `DRF/urls.py`
- [ ] Navbar actualizado en `dashboard_asesor.html`
- [ ] Navbar actualizado en `casos_generales.html`
- [ ] Navbar actualizado en `detalle_casos_encargado_inclusion.html`
- [ ] Estilos CSS en `dashboard.css` (si no existen)
- [ ] Probar filtros de tiempo
- [ ] Probar exportación PDF
- [ ] Probar exportación CSV
- [ ] Verificar gráficos en diferentes navegadores
- [ ] Verificar responsive design

---

**Fecha de creación**: 2025-01-XX
**Última actualización**: 2025-01-XX

