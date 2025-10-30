from django.contrib import admin
from .models import Usuario, Roles, Areas, CategoriasAjustes, Docentes, DirectoresCarreras, Carreras, Estudiantes, AsesoresPedagogicos, Solicitudes, Evidencias, Asignaturas, AsignaturasEnCurso, Entrevistas, AjusteRazonable, AjusteAsignado

# Register your models here.
admin.site.register(Usuario)
admin.site.register(Roles)
admin.site.register(Areas)
admin.site.register(CategoriasAjustes)
admin.site.register(Docentes)
admin.site.register(DirectoresCarreras)
admin.site.register(Carreras)
admin.site.register(Estudiantes)
admin.site.register(AsesoresPedagogicos)
admin.site.register(Solicitudes)
admin.site.register(Evidencias)
admin.site.register(Asignaturas)
admin.site.register(AsignaturasEnCurso)
admin.site.register(Entrevistas)
admin.site.register(AjusteRazonable)
admin.site.register(AjusteAsignado)
