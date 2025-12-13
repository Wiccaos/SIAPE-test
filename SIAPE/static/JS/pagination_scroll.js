/**
 * Script para mantener la posición del scroll al cambiar de página en tablas paginadas
 */

(function() {
    'use strict';
    
    // Función para guardar la posición del scroll
    function guardarPosicionScroll() {
        const scrollY = window.scrollY || window.pageYOffset;
        const scrollX = window.scrollX || window.pageXOffset;
        
        // Guardar en sessionStorage
        sessionStorage.setItem('scrollPositionY', scrollY);
        sessionStorage.setItem('scrollPositionX', scrollX);
        
        // También guardar un timestamp para evitar restaurar posiciones muy antiguas
        sessionStorage.setItem('scrollTimestamp', Date.now());
    }
    
    // Función para restaurar la posición del scroll
    function restaurarPosicionScroll() {
        const scrollY = sessionStorage.getItem('scrollPositionY');
        const scrollX = sessionStorage.getItem('scrollPositionX');
        const scrollTimestamp = sessionStorage.getItem('scrollTimestamp');
        
        // Solo restaurar si la posición fue guardada hace menos de 5 segundos
        if (scrollY !== null && scrollTimestamp) {
            const tiempoTranscurrido = Date.now() - parseInt(scrollTimestamp);
            if (tiempoTranscurrido < 5000) { // 5 segundos
                // Usar requestAnimationFrame para asegurar que el DOM esté listo
                requestAnimationFrame(function() {
                    window.scrollTo(parseInt(scrollX || 0), parseInt(scrollY));
                    
                    // Limpiar después de restaurar
                    sessionStorage.removeItem('scrollPositionY');
                    sessionStorage.removeItem('scrollPositionX');
                    sessionStorage.removeItem('scrollTimestamp');
                });
            } else {
                // Limpiar si es muy antiguo
                sessionStorage.removeItem('scrollPositionY');
                sessionStorage.removeItem('scrollPositionX');
                sessionStorage.removeItem('scrollTimestamp');
            }
        }
    }
    
    // Interceptar clics en enlaces de paginación
    function interceptarEnlacesPaginacion() {
        // Buscar todos los contenedores de paginación
        const paginationContainers = document.querySelectorAll('.pagination-container');
        
        paginationContainers.forEach(function(container) {
            const enlaces = container.querySelectorAll('a');
            
            enlaces.forEach(function(enlace) {
                // Evitar múltiples listeners
                if (enlace.dataset.paginationListener === 'true') {
                    return;
                }
                enlace.dataset.paginationListener = 'true';
                
                enlace.addEventListener('click', function(e) {
                    // Guardar la posición del scroll antes de navegar
                    guardarPosicionScroll();
                    
                    // También guardar el ID del contenedor de la tabla para referencia
                    const tableContainer = container.closest('.table-container, .panel-control-container, section');
                    if (tableContainer && tableContainer.id) {
                        sessionStorage.setItem('scrollTargetId', tableContainer.id);
                    }
                });
            });
        });
    }
    
    // Ejecutar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            interceptarEnlacesPaginacion();
            restaurarPosicionScroll();
        });
    } else {
        // DOM ya está listo
        interceptarEnlacesPaginacion();
        restaurarPosicionScroll();
    }
    
    // También interceptar enlaces que se agreguen dinámicamente
    const observer = new MutationObserver(function(mutations) {
        let debeInterceptar = false;
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) {
                        // Verificar si es un contenedor de paginación o contiene uno
                        if (node.classList && node.classList.contains('pagination-container')) {
                            debeInterceptar = true;
                        } else if (node.querySelector && node.querySelector('.pagination-container')) {
                            debeInterceptar = true;
                        }
                    }
                });
            }
        });
        
        if (debeInterceptar) {
            interceptarEnlacesPaginacion();
        }
    });
    
    // Observar cambios en el DOM
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
})();

