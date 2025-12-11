/**
 * Validador de contraseña para el frontend
 * Valida que la contraseña tenga:
 * - Mínimo 8 caracteres
 * - Al menos una letra (a-z, A-Z)
 * - Al menos un número (0-9)
 */

function validarContraseña(password) {
    /**
     * Valida una contraseña según los requisitos del sistema.
     * 
     * @param {string} password - Contraseña a validar
     * @returns {object} - { esValida: boolean, mensajeError: string }
     */
    if (!password) {
        return {
            esValida: false,
            mensajeError: "La contraseña no puede estar vacía"
        };
    }
    
    // Verificar longitud mínima
    if (password.length < 8) {
        return {
            esValida: false,
            mensajeError: "La contraseña debe tener al menos 8 caracteres"
        };
    }
    
    // Verificar que tenga al menos una letra
    const tieneLetra = /[a-zA-Z]/.test(password);
    if (!tieneLetra) {
        return {
            esValida: false,
            mensajeError: "La contraseña debe contener al menos una letra"
        };
    }
    
    // Verificar que tenga al menos un número
    const tieneNumero = /[0-9]/.test(password);
    if (!tieneNumero) {
        return {
            esValida: false,
            mensajeError: "La contraseña debe contener al menos un número"
        };
    }
    
    return {
        esValida: true,
        mensajeError: null
    };
}

function agregarValidacionPassword(inputElement, mensajeElement) {
    /**
     * Agrega validación en tiempo real a un campo de contraseña.
     * 
     * @param {HTMLElement} inputElement - Elemento input de contraseña
     * @param {HTMLElement} mensajeElement - Elemento donde mostrar el mensaje de error
     */
    if (!inputElement || !mensajeElement) {
        return;
    }
    
    // Crear elemento de mensaje si no existe
    if (!mensajeElement) {
        mensajeElement = document.createElement('small');
        mensajeElement.className = 'password-error-message';
        mensajeElement.style.color = '#dc3545';
        mensajeElement.style.display = 'block';
        mensajeElement.style.marginTop = '0.25rem';
        inputElement.parentNode.appendChild(mensajeElement);
    }
    
    function validar() {
        const password = inputElement.value.trim();
        
        // Si el campo está vacío y no es requerido, no mostrar error
        if (!password && !inputElement.hasAttribute('required')) {
            mensajeElement.textContent = '';
            mensajeElement.style.display = 'none';
            inputElement.style.borderColor = '';
            return;
        }
        
        const resultado = validarContraseña(password);
        
        if (!resultado.esValida) {
            mensajeElement.textContent = resultado.mensajeError;
            mensajeElement.style.display = 'block';
            inputElement.style.borderColor = '#dc3545';
        } else {
            mensajeElement.textContent = '';
            mensajeElement.style.display = 'none';
            inputElement.style.borderColor = '#28a745';
        }
    }
    
    // Validar al escribir
    inputElement.addEventListener('input', validar);
    
    // Validar al perder el foco
    inputElement.addEventListener('blur', validar);
    
    // Validar al enviar el formulario
    const form = inputElement.closest('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const password = inputElement.value.trim();
            
            // Si el campo está vacío y no es requerido, permitir envío
            if (!password && !inputElement.hasAttribute('required')) {
                return;
            }
            
            const resultado = validarContraseña(password);
            if (!resultado.esValida) {
                e.preventDefault();
                alert(resultado.mensajeError);
                inputElement.focus();
                return false;
            }
        });
    }
}

