# SIAPE/permissions.py

from rest_framework.permissions import BasePermission, IsAdminUser

# ----- PERMISOS GENERALES POR ROL -----

class IsAsesorPedagogico(BasePermission):
    """
    Permite el acceso solo a usuarios con el rol 'Asesor Pedagógico'.
    """
    message = "No tiene permisos de Asesor Pedagógico."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusuarios tienen acceso
        if request.user.is_superuser:
            return True
        
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
        
        # Superusuarios tienen acceso
        if request.user.is_superuser:
            return True
        
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
        
        # Superusuarios tienen acceso
        if request.user.is_superuser:
            return True
        
        try:
            return request.user.perfil.rol.nombre_rol == 'Director de Carrera'
        except AttributeError:
            return False


class IsCoordinadora(BasePermission):
    """
    Permite el acceso solo a usuarios con el rol 'Encargado de Inclusión'.
    """
    message = "No tiene permisos de Encargado de Inclusión."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusuarios tienen acceso
        if request.user.is_superuser:
            return True
        
        try:
            return request.user.perfil.rol.nombre_rol == 'Encargado de Inclusión'
        except AttributeError:
            return False


class IsAsesorTecnico(BasePermission):
    """
    Permite el acceso solo a usuarios con el rol 'Coordinador Técnico Pedagógico'.
    """
    message = "No tiene permisos de Coordinador Técnico Pedagógico."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusuarios tienen acceso
        if request.user.is_superuser:
            return True
        
        try:
            return request.user.perfil.rol.nombre_rol == 'Coordinador Técnico Pedagógico'
        except AttributeError:
            return False


class IsAdminOrReadOnly(BasePermission):
    """
    Permite lectura a usuarios autenticados, pero escritura solo a administradores.
    """
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user and request.user.is_authenticated
        return request.user and (request.user.is_superuser or request.user.is_staff)


class IsPersonalAcademico(BasePermission):
    """
    Permite el acceso a Asesores o Directores.
    """
    message = "Debe ser Asesor Pedagógico o Director de Carrera."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusuarios tienen acceso
        if request.user.is_superuser:
            return True
        
        try:
            rol_usuario = request.user.perfil.rol.nombre_rol
            return rol_usuario in ['Asesor Pedagógico', 'Director de Carrera']
        except AttributeError:
            return False