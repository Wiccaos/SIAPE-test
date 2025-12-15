/* =============================================================
   JAVASCRIPT PARA ESTADÍSTICAS DEL DIRECTOR DE CARRERA
   ============================================================= */

document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. Gráfico de Tendencia (Línea) ---
    const ctxTendencia = document.getElementById('graficoTendencia').getContext('2d');
    const tendenciaData = JSON.parse(document.getElementById('tendencia-data').textContent);
    new Chart(ctxTendencia, {
        type: 'line',
        data: tendenciaData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });

    // --- 2. Gráfico de Estado de Ajustes (Doughnut) ---
    const ctxAjustes = document.getElementById('graficoAjustes').getContext('2d');
    const ajustesData = JSON.parse(document.getElementById('ajustes-data').textContent);
    new Chart(ctxAjustes, {
        type: 'doughnut',
        data: ajustesData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            aspectRatio: 1,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 15,
                        font: {
                            size: 14
                        }
                    },
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
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return context.label + ': ' + context.parsed + ' (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });

    // --- 3. Gráfico de Ajustes por Categoría (Barras Agrupadas) ---
    const ctxTipos = document.getElementById('graficoTipos').getContext('2d');
    const tiposData = JSON.parse(document.getElementById('tipos-data').textContent);
    if (tiposData.labels.length > 0) {
        new Chart(ctxTipos, {
            type: 'bar',
            data: tiposData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { 
                        display: true,
                        position: 'top'
                    } 
                },
                scales: {
                    y: { 
                        beginAtZero: true, 
                        ticks: { stepSize: 1 },
                        stacked: false
                    },
                    x: {
                        stacked: false
                    }
                }
            }
        });
    } else {
        document.getElementById('graficoTipos').parentElement.innerHTML = 
            '<div class="empty-state"><i class="fas fa-tags"></i><p>No hay ajustes para mostrar.</p></div>';
    }

    // --- 4. Gráfico de Secciones (Barras Horizontales) ---
    const ctxSecciones = document.getElementById('graficoSecciones').getContext('2d');
    const seccionesData = JSON.parse(document.getElementById('secciones-data').textContent);
    if (seccionesData.labels.length > 0) {
        new Chart(ctxSecciones, {
            type: 'bar',
            data: seccionesData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, ticks: { stepSize: 1 } }
                }
            }
        });
    } else {
        document.getElementById('graficoSecciones').parentElement.innerHTML = 
            '<div class="empty-state"><i class="fas fa-book-reader"></i><p>No hay datos de secciones con ajustes aprobados.</p></div>';
    }

});

