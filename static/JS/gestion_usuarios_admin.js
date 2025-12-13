/**
 * JavaScript para la gestión de usuarios y roles en el panel de administración
 */

// Variables globales para los modales (se inicializarán cuando el DOM esté listo)
let modalAgregar, modalEditar, modalAgregarRol, modalEditarRol, modalEliminarRol, formEditar;

// --- JavaScript para Modales de USUARIOS ---
function abrirModalAgregar() { 
    const modal = document.getElementById('modalAgregar');
    if (modal) {
        modal.style.display = 'block'; 
    }
}

function cerrarModalAgregar() { 
    const modal = document.getElementById('modalAgregar');
    if (modal) {
        modal.style.display = 'none'; 
        const form = modal.querySelector('form');
        if (form) {
            form.reset(); 
        }
    }
}

function abrirModalEditar(perfilId, email, firstName, lastName, rut, currentRolId, currentAreaId) {
    const form = document.getElementById('formEditar');
    if (form) {
        form.action = `/dashboard/admin/gestion-usuarios/editar/${perfilId}/`;
    }
    const emailInput = document.getElementById('editar_email');
    const firstNameInput = document.getElementById('editar_first_name');
    const lastNameInput = document.getElementById('editar_last_name');
    const rutInput = document.getElementById('editar_rut');
    const rolInput = document.getElementById('editar_rol_id');
    const areaInput = document.getElementById('editar_area_id');
    const passwordInput = document.getElementById('editar_password');
    
    if (emailInput) emailInput.value = email;
    if (firstNameInput) firstNameInput.value = firstName;
    if (lastNameInput) lastNameInput.value = lastName;
    if (rutInput) rutInput.value = rut;
    if (rolInput) rolInput.value = currentRolId;
    if (areaInput) areaInput.value = currentAreaId;
    if (passwordInput) passwordInput.value = "";
    
    const modal = document.getElementById('modalEditar');
    if (modal) {
        modal.style.display = 'block';
    }
}

function cerrarModalEditar() { 
    const modal = document.getElementById('modalEditar');
    if (modal) {
        modal.style.display = 'none'; 
    }
}

// --- JavaScript para Modales de ROLES ---
function abrirModalAgregarRol() { 
    const modal = document.getElementById('modalAgregarRol');
    if (modal) {
        modal.style.display = 'block'; 
    }
}

function cerrarModalAgregarRol() { 
    closeModal('modalAgregarRol'); 
}

function abrirModalEditarRol(rolId, nombre) {
    const formEditarRol = document.getElementById('formEditarRol');
    const nombreInput = document.getElementById('editar_nombre_rol');
    
    if (formEditarRol) {
        formEditarRol.action = `/dashboard/admin/roles/editar/${rolId}/`;
    }
    if (nombreInput) {
        nombreInput.value = nombre;
    }
    const modal = document.getElementById('modalEditarRol');
    if (modal) {
        modal.style.display = 'block';
    }
}

function cerrarModalEditarRol() { 
    closeModal('modalEditarRol'); 
}

function abrirModalEliminarRol(rolId, nombre) {
    const formEliminarRol = document.getElementById('formEliminarRol');
    const nombreInput = document.getElementById('eliminar_rol_nombre');
    
    if (formEliminarRol) {
        formEliminarRol.action = `/dashboard/admin/roles/eliminar/${rolId}/`;
    }
    if (nombreInput) {
        nombreInput.value = nombre;
    }
    const modal = document.getElementById('modalEliminarRol');
    if (modal) {
        modal.style.display = 'block';
    }
}

function cerrarModalEliminarRol() { 
    closeModal('modalEliminarRol'); 
}

// Helper para cerrar modales (usado por JS de Roles)
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

// Inicialización cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar referencias a los modales
    modalAgregar = document.getElementById('modalAgregar');
    modalEditar = document.getElementById('modalEditar');
    modalAgregarRol = document.getElementById('modalAgregarRol');
    modalEditarRol = document.getElementById('modalEditarRol');
    modalEliminarRol = document.getElementById('modalEliminarRol');
    formEditar = document.getElementById('formEditar');

    // Cerrar modales si se hace clic fuera de ellos
    window.onclick = function(event) {
        if (event.target == modalAgregar) { 
            cerrarModalAgregar(); 
        }
        if (event.target == modalEditar) { 
            cerrarModalEditar(); 
        }
        if (event.target == modalAgregarRol) { 
            cerrarModalAgregarRol(); 
        }
        if (event.target == modalEditarRol) { 
            cerrarModalEditarRol(); 
        }
        if (event.target == modalEliminarRol) { 
            cerrarModalEliminarRol(); 
        }
    };

    // Validación de RUT en formularios
    // Validar RUT en formulario de agregar usuario
    const formAgregar = document.querySelector('#modalAgregar form');
    const rutInputAgregar = document.getElementById('rut');
    
    if (formAgregar && rutInputAgregar) {
        formAgregar.addEventListener('submit', function(e) {
            const rut = rutInputAgregar.value.trim();
            if (rut) {
                const validacion = validarRUTChileno(rut);
                if (!validacion.esValido) {
                    e.preventDefault();
                    alert('Error: ' + validacion.mensajeError);
                    rutInputAgregar.focus();
                    return false;
                }
            }
        });
        
        // Validación en tiempo real
        agregarValidacionRUT(rutInputAgregar, null);
    }
    
    // Validar RUT en formulario de editar usuario
    const formEditar = document.getElementById('formEditar');
    const rutInputEditar = document.getElementById('editar_rut');
    
    if (formEditar && rutInputEditar) {
        formEditar.addEventListener('submit', function(e) {
            const rut = rutInputEditar.value.trim();
            if (rut) {
                const validacion = validarRUTChileno(rut);
                if (!validacion.esValido) {
                    e.preventDefault();
                    alert('Error: ' + validacion.mensajeError);
                    rutInputEditar.focus();
                    return false;
                }
            }
        });
        
        // Validación en tiempo real
        agregarValidacionRUT(rutInputEditar, null);
    }
    
    // Validación de contraseña en formulario de agregar usuario
    const passwordInput = document.getElementById('password');
    const passwordError = document.getElementById('password-error');
    if (passwordInput && passwordError) {
        agregarValidacionPassword(passwordInput, passwordError);
    }
    
    // Validación de contraseña en formulario de editar usuario
    const editarPasswordInput = document.getElementById('editar_password');
    const editarPasswordError = document.getElementById('editar_password-error');
    if (editarPasswordInput && editarPasswordError) {
        agregarValidacionPassword(editarPasswordInput, editarPasswordError);
    }
});

// Función auxiliar para obtener el token CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Función auxiliar para obtener el token CSRF de múltiples fuentes (disponible globalmente)
window.obtenerTokenCSRF = function() {
    // Intentar obtener del input hidden
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (csrfInput && csrfInput.value) {
        return csrfInput.value;
    }
    
    // Intentar obtener de las cookies
    const csrfCookie = getCookie('csrftoken');
    if (csrfCookie) {
        return csrfCookie;
    }
    
    // Si no se encuentra, intentar obtener de cualquier formulario
    const forms = document.querySelectorAll('form');
    for (let form of forms) {
        const token = form.querySelector('input[name="csrfmiddlewaretoken"]');
        if (token && token.value) {
            return token.value;
        }
    }
    
    console.error('No se pudo obtener el token CSRF');
    return null;
};

// Funciones para activar/desactivar usuarios (definidas globalmente)
window.confirmarDesactivarUsuario = function(perfilId, email) {
    console.log('confirmarDesactivarUsuario llamado con:', perfilId, email);
    
    if (!confirm(`¿Está seguro de que desea desactivar al usuario ${email}?\n\nEl usuario no podrá iniciar sesión hasta que sea reactivado.`)) {
        return;
    }
    
    const csrfValue = obtenerTokenCSRF();
    if (!csrfValue) {
        alert('Error: No se pudo obtener el token de seguridad. Por favor, recargue la página.');
        return;
    }
    
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/dashboard/admin/gestion-usuarios/activar-desactivar/${perfilId}/`;
    form.style.display = 'none';
    
    // Agregar CSRF token
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfValue;
    form.appendChild(csrfInput);
    
    document.body.appendChild(form);
    console.log('Enviando formulario para desactivar usuario:', perfilId);
    form.submit();
};

window.confirmarActivarUsuario = function(perfilId, email) {
    console.log('confirmarActivarUsuario llamado con:', perfilId, email);
    
    if (!confirm(`¿Está seguro de que desea activar al usuario ${email}?`)) {
        return;
    }
    
    const csrfValue = obtenerTokenCSRF();
    if (!csrfValue) {
        alert('Error: No se pudo obtener el token de seguridad. Por favor, recargue la página.');
        return;
    }
    
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/dashboard/admin/gestion-usuarios/activar-desactivar/${perfilId}/`;
    form.style.display = 'none';
    
    // Agregar CSRF token
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfValue;
    form.appendChild(csrfInput);
    
    document.body.appendChild(form);
    console.log('Enviando formulario para activar usuario:', perfilId);
    form.submit();
};

