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
    path('', views.redireccionamiento_por_rol, name='home'),
    path('solicitud-publica/', PublicSolicitudCreateView.as_view(), name='solicitud-publica'),
    path('api/', include(router.urls)),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/coordinadora/', views.dashboard_coordinadora, name='dashboard_coordinadora'),
    path('dashboard/asesor/', views.dashboard_asesor, name='dashboard_asesor'),
    path('dashboard/director/', views.dashboard_director, name='dashboard_director'),
    path(
        'solicitud/aprobar/<int:solicitud_id>/', 
        views.aprobar_solicitud_director, 
        name='aprobar_solicitud_director'
        ),
    path(
        'solicitud/rechazar/<int:solicitud_id>/', 
        views.rechazar_solicitud_director, 
        name='rechazar_solicitud_director'
        ),
    path(
        'dashboard/director/carreras/', 
        views.carreras_director, 
        name='carreras_director'
        ),
    path('casos-coordinadora/', views.casos_coordinadora, name='casos_coordinadora'),
    path('panel-control-coordinadora/', views.panel_control_coordinadora, name='panel_control_coordinadora'),
]