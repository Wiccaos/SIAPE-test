"""
URL configuration for DRF project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from rest_framework import permissions
from SIAPE import views
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.urls import reverse_lazy

schema_view = get_schema_view(
    openapi.Info(
        title="Documentación SIAPE",
        default_version="v1",
        description="Sistema Institucional de Apoyos Perzonalizados para Estudiantes",
        terms_of_service="https://google.com/policies/terms/",
        contact=openapi.Contact(email="wiccaos.moon@outlook.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True
)


urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),

    # URLs de la app SIAPE
    path('SIAPE/', include('SIAPE.urls')),
    path('', include('SIAPE.urls')),

    # URLs publicas
    path('formulario-solicitud/', views.vista_formulario_solicitud, name='formulario-solicitud'),
    path('api/horarios-disponibles/', views.get_horarios_disponibles, name='api-horarios-disponibles'),
    path('api/calendario-disponible/', views.get_calendario_disponible, name='api-calendario-disponible'),

    # URLs del Administrador
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/admin/gestion-usuarios/', views.gestion_usuarios_admin, name='gestion_usuarios_admin'),
    path('dashboard/admin/gestion-usuarios/agregar/', views.agregar_usuario_admin, name='agregar_usuario_admin'),
    path('dashboard/admin/gestion-usuarios/editar/<int:perfil_id>/', views.editar_usuario_admin, name='editar_usuario_admin'),
    # GESTIÓN INSTITUCIONAL - ADMIN
    path('dashboard/admin/gestion-institucional/', views.gestion_institucional_admin, name='gestion_institucional_admin'),
    path('dashboard/admin/carreras/agregar/', views.agregar_carrera_admin, name='agregar_carrera_admin'),
    path('dashboard/admin/carreras/editar/<int:carrera_id>/', views.editar_carrera_admin, name='editar_carrera_admin'),
    path('dashboard/admin/asignaturas/agregar/', views.agregar_asignatura_admin, name='agregar_asignatura_admin'),
    path('dashboard/admin/asignaturas/editar/<int:asignatura_id>/', views.editar_asignatura_admin, name='editar_asignatura_admin'),
    path('dashboard/admin/roles/agregar/', views.agregar_rol_admin, name='agregar_rol_admin'),
    path('dashboard/admin/roles/editar/<int:rol_id>/', views.editar_rol_admin, name='editar_rol_admin'),

    # URLs de Asesor Pedagógico
    path('dashboard/asesor/', views.dashboard_asesor, name='dashboard_asesor'),
    path('dashboard/asesor/casos/', views.casos_asesor, name='casos_asesor'),
    path('dashboard/asesor/casos/<int:solicitud_id>/', views.detalle_caso_asesor, name='detalle_caso_asesor'),
    path('dashboard/asesor/panel-control/', views.panel_control_asesor, name='panel_control_asesor'),
    path('dashboard/asesor/asignar-caso/<int:solicitud_id>/', views.asignar_caso_asesor, name='asignar_caso_asesor'),
    path('dashboard/asesor/agendar-cita/', views.agendar_cita_asesor, name='agendar_cita_asesor'),
    path('dashboard/asesor/registrar-ajuste/', views.registrar_ajuste_razonable, name='registrar_ajuste_razonable'),
    path('dashboard/asesor/confirmar-cita/<int:entrevista_id>/', views.confirmar_cita_asesor, name='confirmar_cita_asesor'),
    path('dashboard/asesor/editar-notas-cita/<int:entrevista_id>/', views.editar_notas_cita, name='editar_notas_cita'),
    path('dashboard/asesor/reagendar-cita/<int:entrevista_id>/', views.reagendar_cita_asesor, name='reagendar_cita_asesor'),
    path('dashboard/asesor/aprobar-solicitud/<int:solicitud_id>/', views.aprobar_solicitud_asesor, name='aprobar_solicitud_asesor'),
    path('dashboard/asesor/rechazar-solicitud/<int:solicitud_id>/', views.rechazar_solicitud_asesor, name='rechazar_solicitud_asesor'),


    # URLs de Docente
    path('dashboard/docente/', views.dashboard_docente, name='dashboard_docente'),
    path('dashboard/docente/mis/asignaturas/', views.mis_asignaturas_docente, name='mis_asignaturas_docente'),
    path('dashboard/docente/mis/alumnos/', views.mis_alumnos_docente, name='mis_alumnos_docente'),
    path('dashboard/docente/asignatura/<int:asignatura_id>/', views.detalle_asignatura_docente, name='detalle_asignatura_docente'),
    path('dashboard/docente/alumno/<int:estudiante_id>/', views.detalle_ajuste_docente, name='detalle_ajuste_docente'),
    path('dashboard/docente/alumno/<int:estudiante_id>/', views.detalle_ajuste_docente, name='detalle_ajuste_docente'),

    # URLs de Coordinadora de Inclusión
    path('dashboard/coordinador/', views.dashboard_coordinadora, name='dashboard_coordinadora'),

    # URLs de Director de Carrera
    path('dashboard/director/', views.dashboard_director, name='dashboard_director'),

    # URLs documentación
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # URLs de autenticación
    path('accounts/', include('django.contrib.auth.urls')),
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        next_page=reverse_lazy('home')
    ), name='login'),
    path('logout/', views.logout_view, name='logout'),
    # path('registro/', views.registro, name='registro'),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)