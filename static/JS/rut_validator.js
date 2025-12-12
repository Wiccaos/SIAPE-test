/**
 * Validador de RUT chileno para frontend
 */

function validarRUTChileno(rut) {
    /**
     * Valida un RUT chileno.
     * 
     * @param {string} rut - RUT en formato "12345678-9" o "123456789"
     * @returns {object} - { esValido: boolean, mensajeError: string }
     */
    if (!rut) {
        return { esValido: false, mensajeError: "RUT inválido" };
    }
    
    // Limpiar el RUT: eliminar espacios y puntos, convertir a mayúsculas
    let rutLimpio = rut.trim().replace(/\./g, '').replace(/-/g, '').toUpperCase();
    
    // Verificar que tenga al menos 7 caracteres (mínimo para un RUT válido)
    if (rutLimpio.length < 7) {
        return { esValido: false, mensajeError: "RUT inválido" };
    }
    
    // Verificar que tenga máximo 9 caracteres (máximo para un RUT válido)
    if (rutLimpio.length > 9) {
        return { esValido: false, mensajeError: "RUT inválido" };
    }
    
    // Separar número y dígito verificador
    if (rutLimpio.length < 2) {
        return { esValido: false, mensajeError: "RUT inválido" };
    }
    
    let numeroRUT = rutLimpio.slice(0, -1);
    let digitoVerificador = rutLimpio.slice(-1);
    
    // Verificar que el número sea solo dígitos
    if (!/^\d+$/.test(numeroRUT)) {
        return { esValido: false, mensajeError: "RUT inválido" };
    }
    
    // Verificar que el dígito verificador sea un dígito o 'K'
    if (!(/^\d$/.test(digitoVerificador) || digitoVerificador === 'K')) {
        return { esValido: false, mensajeError: "RUT inválido" };
    }
    
    // Calcular el dígito verificador correcto
    let suma = 0;
    let multiplicador = 2;
    
    // Recorrer el número de derecha a izquierda
    for (let i = numeroRUT.length - 1; i >= 0; i--) {
        suma += parseInt(numeroRUT[i]) * multiplicador;
        multiplicador++;
        if (multiplicador > 7) {
            multiplicador = 2;
        }
    }
    
    // Calcular el resto
    let resto = suma % 11;
    let digitoCalculado = 11 - resto;
    
    // Ajustar según el algoritmo chileno
    if (digitoCalculado === 11) {
        digitoCalculado = '0';
    } else if (digitoCalculado === 10) {
        digitoCalculado = 'K';
    } else {
        digitoCalculado = String(digitoCalculado);
    }
    
    // Comparar con el dígito verificador ingresado
    if (digitoCalculado !== digitoVerificador) {
        return { 
            esValido: false, 
            mensajeError: "RUT inválido"
        };
    }
    
    return { esValido: true, mensajeError: null };
}

function formatearRUT(rut) {
    /**
     * Formatea un RUT agregando puntos y guion.
     * 
     * @param {string} rut - RUT sin formato o con formato
     * @returns {string} - RUT formateado como "12.345.678-9"
     */
    if (!rut) {
        return "";
    }
    
    // Limpiar el RUT
    let rutLimpio = rut.trim().replace(/\./g, '').replace(/-/g, '').toUpperCase();
    
    if (rutLimpio.length < 2) {
        return rut;
    }
    
    // Separar número y dígito verificador
    let numeroRUT = rutLimpio.slice(0, -1);
    let digitoVerificador = rutLimpio.slice(-1);
    
    // Agregar puntos cada 3 dígitos desde la derecha
    let numeroFormateado = "";
    for (let i = numeroRUT.length - 1; i >= 0; i--) {
        if (i < numeroRUT.length - 1 && (numeroRUT.length - 1 - i) % 3 === 0) {
            numeroFormateado = '.' + numeroFormateado;
        }
        numeroFormateado = numeroRUT[i] + numeroFormateado;
    }
    
    // Retornar con guion y dígito verificador
    return `${numeroFormateado}-${digitoVerificador}`;
}

// Función para agregar validación en tiempo real a un campo de RUT
function agregarValidacionRUT(inputElement, mensajeElement) {
    /**
     * Agrega validación en tiempo real a un campo de RUT.
     * 
     * @param {HTMLElement} inputElement - Campo de input del RUT
     * @param {HTMLElement} mensajeElement - Elemento donde mostrar mensajes de error (opcional)
     */
    if (!inputElement) return;
    
    inputElement.addEventListener('blur', function() {
        const rut = inputElement.value.trim();
        if (rut) {
            const validacion = validarRUTChileno(rut);
            if (!validacion.esValido) {
                inputElement.classList.add('error');
                if (mensajeElement) {
                    mensajeElement.textContent = validacion.mensajeError;
                    mensajeElement.style.display = 'block';
                    mensajeElement.className = 'error-message';
                }
            } else {
                inputElement.classList.remove('error');
                if (mensajeElement) {
                    mensajeElement.style.display = 'none';
                }
            }
        } else {
            inputElement.classList.remove('error');
            if (mensajeElement) {
                mensajeElement.style.display = 'none';
            }
        }
    });
    
    inputElement.addEventListener('input', function() {
        if (inputElement.classList.contains('error')) {
            inputElement.classList.remove('error');
            if (mensajeElement) {
                mensajeElement.style.display = 'none';
            }
        }
    });
}

