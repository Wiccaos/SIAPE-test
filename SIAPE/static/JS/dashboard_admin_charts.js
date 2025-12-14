/**
 * Dashboard Admin - Gráficos de Estadísticas
 * Este archivo maneja la inicialización de los gráficos Chart.js
 * para el panel de administrador.
 */

// Configuración global de Chart.js
Chart.defaults.font.family = "'Segoe UI', 'Roboto', sans-serif";

// Función para obtener colores según el modo (claro/oscuro)
function getChartColors() {
    const isDarkMode = document.body.classList.contains('dark-mode');
    return {
        textColor: isDarkMode ? '#d0d0d0' : '#6c757d',
        gridColor: isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)',
        borderColor: isDarkMode ? '#3a3a3a' : '#e0e0e0'
    };
}

// Colores para los gráficos
const coloresEstados = [
    '#3498db', // En Proceso
    '#9b59b6', // Pendiente Entrevista
    '#e67e22', // Pendiente Formulación
    '#f1c40f', // Pendiente Preaprobación
    '#1abc9c', // Pendiente Aprobación
    '#27ae60', // Aprobado
    '#e74c3c'  // Rechazado
];

const coloresRoles = [
    '#667eea', '#764ba2', '#11998e', '#38ef7d', 
    '#f093fb', '#f5576c', '#4facfe', '#00f2fe'
];

// Variables para almacenar las instancias de los gráficos
let activityChartInstance = null;
let statusChartInstance = null;
let rolesChartInstance = null;

/**
 * Inicializa el gráfico de actividad del sistema (líneas)
 */
function initActivityChart(labels, data) {
    const ctx = document.getElementById('activityChart');
    if (!ctx) return;
    
    const colors = getChartColors();
    
    // Destruir instancia anterior si existe
    if (activityChartInstance) {
        activityChartInstance.destroy();
    }
    
    activityChartInstance = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Solicitudes',
                data: data,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    padding: 12,
                    titleFont: { size: 14 },
                    bodyFont: { size: 13 }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        color: colors.textColor
                    },
                    grid: {
                        color: colors.gridColor
                    }
                },
                x: {
                    ticks: {
                        color: colors.textColor
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

/**
 * Inicializa el gráfico de distribución por estado (dona)
 */
function initStatusChart(labels, data) {
    const ctx = document.getElementById('statusChart');
    if (!ctx) return;
    
    // Destruir instancia anterior si existe
    if (statusChartInstance) {
        statusChartInstance.destroy();
    }
    
    if (data.some(v => v > 0)) {
        statusChartInstance = new Chart(ctx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: coloresEstados,
                    borderWidth: 2,
                    borderColor: document.body.classList.contains('dark-mode') ? '#1e1e1e' : '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 12,
                            padding: 8,
                            font: { size: 11 },
                            color: getChartColors().textColor
                        }
                    }
                },
                cutout: '60%'
            }
        });
    } else {
        ctx.parentElement.innerHTML = 
            '<div class="empty-activity"><i class="fas fa-chart-pie"></i><p>No hay datos de estados</p></div>';
    }
}

/**
 * Inicializa el gráfico de usuarios por rol (barras horizontales)
 */
function initRolesChart(labels, data) {
    const ctx = document.getElementById('rolesChart');
    if (!ctx) return;
    
    const colors = getChartColors();
    
    // Destruir instancia anterior si existe
    if (rolesChartInstance) {
        rolesChartInstance.destroy();
    }
    
    if (data.length > 0) {
        rolesChartInstance = new Chart(ctx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Usuarios',
                    data: data,
                    backgroundColor: coloresRoles,
                    borderRadius: 6,
                    barThickness: 20
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: colors.textColor
                        },
                        grid: {
                            color: colors.gridColor
                        }
                    },
                    y: {
                        ticks: {
                            color: colors.textColor
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    } else {
        ctx.parentElement.innerHTML = 
            '<div class="empty-activity"><i class="fas fa-users"></i><p>No hay datos de roles</p></div>';
    }
}

/**
 * Inicializa todos los gráficos del dashboard
 */
function initDashboardCharts(actividadLabels, actividadData, estadosLabels, estadosData, rolesLabels, rolesData) {
    initActivityChart(actividadLabels, actividadData);
    initStatusChart(estadosLabels, estadosData);
    initRolesChart(rolesLabels, rolesData);
}

// Escuchar cambios en el modo oscuro para actualizar colores
const darkModeObserver = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.attributeName === 'class') {
            // Re-renderizar gráficos cuando cambia el modo oscuro
            if (typeof actividadLabels !== 'undefined') {
                initDashboardCharts(
                    actividadLabels, actividadData,
                    estadosLabels, estadosData,
                    rolesLabels, rolesData
                );
            }
        }
    });
});

// Observar cambios en la clase del body
if (document.body) {
    darkModeObserver.observe(document.body, { attributes: true });
}

