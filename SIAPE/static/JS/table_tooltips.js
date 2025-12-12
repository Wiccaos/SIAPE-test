/**
 * Script para agregar tooltips automáticos a las celdas de tablas con texto truncado
 * Se ejecuta automáticamente cuando el DOM está listo
 */

document.addEventListener('DOMContentLoaded', function() {
    /**
     * Agrega tooltips a las celdas de tabla que tienen texto truncado
     * @param {HTMLElement} table - La tabla a procesar
     */
    function agregarTooltipsATabla(table) {
        if (!table) return;
        
        // Obtener todas las celdas (td) de la tabla, excluyendo la columna de acciones
        const celdas = table.querySelectorAll('tbody td');
        
        celdas.forEach(function(celda) {
            // Saltar celdas que contienen botones o elementos de acción
            const tieneBotones = celda.querySelector('button, .btn-accion, .acciones-container');
            if (tieneBotones) {
                return; // No agregar tooltip a celdas con botones
            }
            
            // Obtener el texto completo de la celda (sin espacios extra)
            const textoCompleto = celda.textContent.trim();
            
            // Si no hay texto, no hacer nada
            if (!textoCompleto) {
                return;
            }
            
            // Crear un elemento temporal para medir el ancho del texto
            const span = document.createElement('span');
            span.style.visibility = 'hidden';
            span.style.position = 'absolute';
            span.style.whiteSpace = 'nowrap';
            span.style.font = window.getComputedStyle(celda).font;
            span.textContent = textoCompleto;
            document.body.appendChild(span);
            
            const anchoTexto = span.offsetWidth;
            const anchoCelda = celda.clientWidth;
            
            // Remover el elemento temporal
            document.body.removeChild(span);
            
            // Si el texto es más ancho que la celda, está truncado
            if (anchoTexto > anchoCelda) {
                celda.setAttribute('title', textoCompleto);
                celda.style.cursor = 'help';
            } else {
                // También agregar tooltip si el texto es muy largo (más de 50 caracteres)
                // para ayudar al usuario incluso si técnicamente cabe
                if (textoCompleto.length > 50) {
                    celda.setAttribute('title', textoCompleto);
                }
            }
        });
    }
    
    /**
     * Procesa todas las tablas en la página
     */
    function procesarTodasLasTablas() {
        // Buscar todas las tablas con la clase custom-table
        const tablas = document.querySelectorAll('.custom-table');
        
        tablas.forEach(function(tabla) {
            agregarTooltipsATabla(tabla);
        });
        
        // También buscar otras tablas comunes que puedan existir
        const otrasTablas = document.querySelectorAll('table:not(.custom-table)');
        otrasTablas.forEach(function(tabla) {
            agregarTooltipsATabla(tabla);
        });
    }
    
    // Ejecutar al cargar la página
    procesarTodasLasTablas();
    
    // También ejecutar después de un pequeño delay para asegurar que todo esté renderizado
    setTimeout(procesarTodasLasTablas, 100);
    
    // Observar cambios en el DOM (útil para tablas cargadas dinámicamente)
    const observer = new MutationObserver(function(mutations) {
        let debeReprocesar = false;
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                // Verificar si se agregaron nuevas tablas
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Es un elemento
                        if (node.tagName === 'TABLE' || node.querySelector && node.querySelector('table')) {
                            debeReprocesar = true;
                        }
                    }
                });
            }
        });
        
        if (debeReprocesar) {
            setTimeout(procesarTodasLasTablas, 50);
        }
    });
    
    // Observar cambios en el body
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

