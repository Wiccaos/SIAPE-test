/**
 * JavaScript base para la plantilla principal
 * Maneja modo oscuro, accesibilidad y dropdowns
 */

document.addEventListener('DOMContentLoaded', () => {
    const body = document.body;
    
    // --- Lógica de Modo Oscuro ---
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    
    // Solo ejecutar si el elemento existe (no todas las páginas tienen el toggle)
    if (darkModeToggle) {
        const currentTheme = localStorage.getItem('theme');

        // Aplicar tema al cargar la página
        if (currentTheme === 'dark') {
            body.classList.add('dark-mode');
            darkModeToggle.checked = true;
        }

        // Listener para el botón
        darkModeToggle.addEventListener('change', () => {
            if (darkModeToggle.checked) {
                body.classList.add('dark-mode');
                localStorage.setItem('theme', 'dark');
            } else {
                body.classList.remove('dark-mode');
                localStorage.setItem('theme', 'light');
            }
        });
    }

    // --- Lógica de Accesibilidad ---
    const fontIncreaseBtn = document.getElementById('font-increase');
    const fontDecreaseBtn = document.getElementById('font-decrease');
    const accessibilityItem = document.getElementById('accessibility-item');
    const html = document.documentElement;
    
    // Obtener nivel de fuente guardado o usar 1x por defecto
    let currentFontLevel = parseFloat(localStorage.getItem('fontSizeLevel')) || 1.0;
    const minFontLevel = 1.0;
    const maxFontLevel = 3.0; // Máximo 3 veces el tamaño base
    const fontStep = 0.25; // Incremento de 0.25x cada vez
    const baseFontSize = 1.1; // Tamaño base en rem (debe coincidir con CSS)
    
    // Función para aplicar el tamaño de fuente
    function applyFontSize(level) {
        const fontSize = baseFontSize * level;
        // Cambiar el tamaño del html para que todos los rem escalen
        html.style.fontSize = `${fontSize}rem`;
        // También cambiar el body para mantener consistencia
        body.style.fontSize = `${fontSize}rem`;
        localStorage.setItem('fontSizeLevel', level);
        
        // Habilitar/deshabilitar botones según límites
        if (fontIncreaseBtn) {
            fontIncreaseBtn.disabled = level >= maxFontLevel;
        }
        if (fontDecreaseBtn) {
            fontDecreaseBtn.disabled = level <= minFontLevel;
        }
    }
    
    // Aplicar tamaño de fuente guardado al cargar
    applyFontSize(currentFontLevel);
    
    // Prevenir que el item de accesibilidad cierre el dropdown
    if (accessibilityItem) {
        accessibilityItem.addEventListener('click', (e) => {
            e.stopPropagation(); // Evita que se cierre el dropdown
        });
    }
    
    // Botón aumentar fuente
    if (fontIncreaseBtn) {
        fontIncreaseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (currentFontLevel < maxFontLevel) {
                currentFontLevel = Math.min(currentFontLevel + fontStep, maxFontLevel);
                applyFontSize(currentFontLevel);
            }
        });
    }
    
    // Botón disminuir fuente
    if (fontDecreaseBtn) {
        fontDecreaseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (currentFontLevel > minFontLevel) {
                currentFontLevel = Math.max(currentFontLevel - fontStep, minFontLevel);
                applyFontSize(currentFontLevel);
            }
        });
    }

    const dropdown = document.querySelector('.header-dropdown');
    if (dropdown) {
        const dropdownButton = dropdown.querySelector('.header-config-link');
        const dropdownMenu = dropdown.querySelector('.dropdown-menu');

        // 1. Abre/Cierra el menú al hacer clic en el botón
        dropdownButton.addEventListener('click', (e) => {
            e.stopPropagation(); // Evita que el clic se propague al 'window'
            dropdownMenu.classList.toggle('show');
        });

        // 2. Cierra el menú si se hace clic en cualquier otro lugar
        window.addEventListener('click', (e) => {
            if (dropdownMenu.classList.contains('show') && !dropdown.contains(e.target)) {
                dropdownMenu.classList.remove('show');
                // También cerrar el submenú de accesibilidad
                if (accessibilitySubmenu) {
                    accessibilitySubmenu.classList.remove('show');
                    const chevron = accessibilityToggle?.querySelector('.accessibility-chevron');
                    if (chevron) {
                        chevron.classList.remove('rotated');
                    }
                }
            }
        });
    }
});

