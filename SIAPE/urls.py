from django.urls import path, include
from rest_framework import routers
from SIAPE import views

router = routers.DefaultRouter()

router.register(r'usuarios', views.UsuarioViewSet)
router.register(r'roles', views.RolesViewSet)
router.register(r'areas', views.AreasViewSet)
router.register(r'categorias_ajustes', views.CategoriasAjustesViewSet)
router.register(r'docentes', views.DocentesViewSet)
router.register(r'directores_carreras', views.DirectoresCarrerasViewSet)
router.register(r'carreras', views.CarrerasViewSet)
router.register(r'estudiantes', views.EstudiantesViewSet)
router.register(r'asesores_pedagogicos', views.AsesoresPedagogicosViewSet)
router.register(r'solicitudes', views.SolicitudesViewSet)
router.register(r'evidencias', views.EvidenciasViewSet)
router.register(r'asignaturas', views.AsignaturasViewSet)
router.register(r'asignaturas_en_curso', views.AsignaturasEnCursoViewSet)
router.register(r'entrevistas', views.EntrevistasViewSet)
router.register(r'ajuste_razonable', views.AjusteRazonableViewSet)
router.register(r'ajuste_asignado', views.AjusteAsignadoViewSet)

urlpatterns = [
    path('', include(router.urls))
]