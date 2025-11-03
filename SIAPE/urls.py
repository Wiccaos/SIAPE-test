from django.urls import path, include
from rest_framework import routers
from SIAPE import views
from .views import PublicSolicitudCreateView

router = routers.DefaultRouter()

router.register(r'usuarios', views.UsuarioViewSet)
router.register(r'roles', views.RolesViewSet)
router.register(r'areas', views.AreasViewSet)
router.register(r'categorias_ajustes', views.CategoriasAjustesViewSet)
router.register(r'carreras', views.CarrerasViewSet)
router.register(r'estudiantes', views.EstudiantesViewSet)
router.register(r'solicitudes', views.SolicitudesViewSet)
router.register(r'evidencias', views.EvidenciasViewSet)
router.register(r'asignaturas', views.AsignaturasViewSet)
router.register(r'asignaturas_en_curso', views.AsignaturasEnCursoViewSet)
router.register(r'entrevistas', views.EntrevistasViewSet)
router.register(r'ajuste_razonable', views.AjusteRazonableViewSet)
router.register(r'ajuste_asignado', views.AjusteAsignadoViewSet)
router.register(r'perfil_usuarios', views.PerfilUsuarioViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('solicitud-publica/', PublicSolicitudCreateView.as_view(), name='solicitud-publica'),
]