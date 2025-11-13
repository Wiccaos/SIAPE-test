from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Roles, Areas, CategoriasAjustes, PerfilUsuario, Carreras, Estudiantes, Solicitudes, 
    Evidencias, Asignaturas, AsignaturasEnCurso, Entrevistas, AjusteRazonable, AjusteAsignado, HorarioBloqueado
)

try:
    admin.site.unregister(Usuario)
except admin.sites.NotRegistered:
    pass

@admin.register(Usuario)
class CustomUserAdmin(UserAdmin):
    """
    Configuración personalizada del Admin para el modelo Usuario.
    """

    list_display = ('email', 'first_name', 'last_name', 'rut', 'is_staff')
    
    search_fields = ('email', 'first_name', 'last_name', 'rut')
    
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'rut', 'numero')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'password2', 'first_name', 'last_name', 'rut', 'is_staff', 'is_superuser'),
        }),
    )
    
    filter_horizontal = ('groups', 'user_permissions',)

admin.site.register(Roles)
admin.site.register(Areas)
admin.site.register(CategoriasAjustes)
admin.site.register(PerfilUsuario)
admin.site.register(Carreras)
admin.site.register(Estudiantes)
admin.site.register(Solicitudes)
admin.site.register(Evidencias)
admin.site.register(Asignaturas)
admin.site.register(AsignaturasEnCurso)
admin.site.register(Entrevistas)
admin.site.register(AjusteRazonable)
admin.site.register(AjusteAsignado)
admin.site.register(HorarioBloqueado)