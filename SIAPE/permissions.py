# SIAPE/permissions.py

from rest_framework.permissions import BasePermission

# ----- PERMISOS GENERALES POR ROL -----

class IsAsesorPedagogico(BasePermission):
    """
    Permite el acceso solo a usuarios con el rol 'Asesor Pedagogico'.
    """
    message = "No tiene permisos de Asesor Pedagógico."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            rol_usuario = request.user.perfil.rol.nombre_rol
        except AttributeError:
            return False
        
        return rol_usuario == 'Asesor Pedagógico'

class IsDocente(BasePermission):
    """
    Permite el acceso solo a usuarios con el rol 'Docente'.
    """
    message = "No tiene permisos de Docente."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.perfil.rol.nombre_rol == 'Docente'
        except AttributeError:
            return False


class IsDirectorCarrera(BasePermission):
    """
    Permite el acceso solo a usuarios con el rol 'Director de Carrera'.
    """
    message = "No tiene permisos de Director de Carrera."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.perfil.rol.nombre_rol == 'Director de Carrera'
        except AttributeError:
            return False


class IsPersonalAcademico(BasePermission):
    """
    Permite el acceso a Asesores o Directores.
    """
    message = "Debe ser Asesor Pedagógico o Director de Carrera."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            rol_usuario = request.user.perfil.rol.nombre_rol
            return rol_usuario in ['Asesor Pedagogico', 'Director de Carrera']
        except AttributeError:
            return False