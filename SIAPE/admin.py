from django.contrib import admin
from .models import Usuario, PerfilUsuario, Roles, Areas, CategoriasAjustes, Carreras, Estudiantes, Solicitudes, Evidencias, Asignaturas, AsignaturasEnCurso, Entrevistas, AjusteRazonable, AjusteAsignado

# Register your models here.
admin.site.register(Usuario)
admin.site.register(Roles)
admin.site.register(Areas)
admin.site.register(CategoriasAjustes)
admin.site.register(Carreras)
admin.site.register(Estudiantes)
admin.site.register(Solicitudes)
admin.site.register(Evidencias)
admin.site.register(Asignaturas)
admin.site.register(AsignaturasEnCurso)
admin.site.register(Entrevistas)
admin.site.register(AjusteRazonable)
admin.site.register(AjusteAsignado)
admin.site.register(PerfilUsuario)