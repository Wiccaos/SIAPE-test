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
    path('api/docente/caso/<int:solicitud_id>/', views.obtener_datos_caso_docente, name='api-datos-caso-docente'),
    path('api/docente/ajuste/<int:ajuste_asignado_id>/comentario/', views.agregar_comentario_ajuste_docente, name='api-comentario-ajuste-docente'),
    path('api/buscar-estudiante/', views.buscar_estudiante_por_rut, name='api-buscar-estudiante'),

    # URLs del Administrador
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/admin/gestion-usuarios/', views.gestion_usuarios_admin, name='gestion_usuarios_admin'),
    path('dashboard/admin/gestion-usuarios/agregar/', views.agregar_usuario_admin, name='agregar_usuario_admin'),
    path('dashboard/admin/gestion-usuarios/editar/<int:perfil_id>/', views.editar_usuario_admin, name='editar_usuario_admin'),
    # GESTIÓN INSTITUCIONAL - ADMIN
    path('dashboard/admin/gestion-institucional/', views.gestion_institucional_admin, name='gestion_institucional_admin'),
    # path('dashboard/admin/asignar-estudiantes-asignaturas/', views.asignar_estudiantes_asignaturas_admin, name='asignar_estudiantes_asignaturas_admin'),  # Eliminado - ahora lo hace el Director
    path('dashboard/admin/carreras/agregar/', views.agregar_carrera_admin, name='agregar_carrera_admin'),
    path('dashboard/admin/carreras/editar/<int:carrera_id>/', views.editar_carrera_admin, name='editar_carrera_admin'),
    path('dashboard/admin/carreras/eliminar/<int:carrera_id>/', views.eliminar_carrera_admin, name='eliminar_carrera_admin'),
    path('dashboard/admin/asignaturas/agregar/', views.agregar_asignatura_admin, name='agregar_asignatura_admin'),
    path('dashboard/admin/asignaturas/editar/<int:asignatura_id>/', views.editar_asignatura_admin, name='editar_asignatura_admin'),
    path('dashboard/admin/asignaturas/eliminar/<int:asignatura_id>/', views.eliminar_asignatura_admin, name='eliminar_asignatura_admin'),
    path('dashboard/admin/roles/agregar/', views.agregar_rol_admin, name='agregar_rol_admin'),
    path('dashboard/admin/roles/editar/<int:rol_id>/', views.editar_rol_admin, name='editar_rol_admin'),
    path('dashboard/admin/roles/eliminar/<int:rol_id>/', views.eliminar_rol_admin, name='eliminar_rol_admin'),
    path('dashboard/admin/areas/agregar/', views.agregar_area_admin, name='agregar_area_admin'),
    path('dashboard/admin/areas/editar/<int:area_id>/', views.editar_area_admin, name='editar_area_admin'),
    path('dashboard/admin/areas/eliminar/<int:area_id>/', views.eliminar_area_admin, name='eliminar_area_admin'),

    # # URLs de Asesor Pedagógico
    path('dashboard/asesor/', views.dashboard_asesor, name='dashboard_asesor'),
    # path('dashboard/asesor/casos/', views.casos_asesor, name='casos_asesor'),
    # path('dashboard/asesor/casos/<int:solicitud_id>/', views.detalle_caso_asesor, name='detalle_caso_asesor'),
    # path('dashboard/asesor/panel-control/', views.panel_control_asesor, name='panel_control_asesor'),
    # path('dashboard/asesor/asignar-caso/<int:solicitud_id>/', views.asignar_caso_asesor, name='asignar_caso_asesor'),
    # path('dashboard/asesor/agendar-cita/', views.agendar_cita_asesor, name='agendar_cita_asesor'),
    # path('dashboard/asesor/registrar-ajuste/', views.registrar_ajuste_razonable, name='registrar_ajuste_razonable'),
    # path('dashboard/asesor/confirmar-cita/<int:entrevista_id>/', views.confirmar_cita_asesor, name='confirmar_cita_asesor'),
    # path('dashboard/asesor/editar-notas-cita/<int:entrevista_id>/', views.editar_notas_cita, name='editar_notas_cita'),
    # path('dashboard/asesor/reagendar-cita/<int:entrevista_id>/', views.reagendar_cita_asesor, name='reagendar_cita_asesor'),
    # path('dashboard/asesor/aprobar-solicitud/<int:solicitud_id>/', views.aprobar_solicitud_asesor, name='aprobar_solicitud_asesor'),
    # path('dashboard/asesor/rechazar-solicitud/<int:solicitud_id>/', views.rechazar_solicitud_asesor, name='rechazar_solicitud_asesor'),


    # URLs de Docente
    path('dashboard/docente/', views.dashboard_docente, name='dashboard_docente'),
    path('dashboard/docente/mis/asignaturas/', views.mis_asignaturas_docente, name='mis_asignaturas_docente'),
    path('dashboard/docente/mis/alumnos/', views.mis_alumnos_docente, name='mis_alumnos_docente'),
    path('dashboard/docente/asignatura/<int:asignatura_id>/', views.detalle_asignatura_docente, name='detalle_asignatura_docente'),
    path('dashboard/docente/alumno/<int:estudiante_id>/', views.detalle_ajuste_docente, name='detalle_ajuste_docente'),
    path('dashboard/docente/alumno/<int:estudiante_id>/', views.detalle_ajuste_docente, name='detalle_ajuste_docente'),

    # URLs de Encargado de Inclusión (Coordinadora)
    path('dashboard/coordinador/', views.dashboard_encargado_inclusion, name='dashboard_encargado_inclusion'),
    path('dashboard/casos-generales/', views.casos_generales, name='casos_generales'),
    # URL genérica para ver casos (funciona para todos los roles)
    path('casos/<int:solicitud_id>/', views.detalle_casos_encargado_inclusion, name='detalle_caso'),
    # URLs específicas por rol (mantener para compatibilidad)
    path('dashboard/coordinador/casos/<int:solicitud_id>/', views.detalle_casos_encargado_inclusion, name='detalle_casos_encargado_inclusion'),
    path('dashboard/coordinador/panel-control/', views.panel_control_encargado_inclusion, name='panel_control_encargado_inclusion'),
    path('dashboard/coordinador/horarios-bloqueados/', views.gestionar_horarios_bloqueados, name='gestionar_horarios_bloqueados'),
    path('dashboard/coordinador/horarios-bloqueados/<int:horario_id>/eliminar/', views.eliminar_horario_bloqueado, name='eliminar_horario_bloqueado'),
    path('dashboard/coordinador/citas/<int:entrevista_id>/cancelar/', views.cancelar_cita_dashboard, name='cancelar_cita_dashboard'),
    path('dashboard/coordinador/casos/<int:solicitud_id>/actualizar-descripcion/', views.actualizar_descripcion_caso, name='actualizar_descripcion_caso'),
    path('dashboard/coordinador/casos/<int:solicitud_id>/enviar-asesor-tecnico/', views.enviar_a_asesor_tecnico, name='enviar_a_asesor_tecnico'),
    path('dashboard/coordinador/confirmar-cita/<int:entrevista_id>/', 
         views.confirmar_cita_coordinadora, 
         name='coordinadora_confirmar_cita'),
    path('dashboard/coordinador/editar-notas-cita/<int:entrevista_id>/', 
         views.editar_notas_cita_coordinadora, 
         name='coordinadora_editar_notas_cita'),
    path('dashboard/coordinador/agendar-cita/', views.agendar_cita_coordinadora, name='agendar_cita_coordinadora'),
    path('dashboard/coordinador/reagendar-cita/<int:entrevista_id>/', 
         views.reagendar_cita_coordinadora, 
         name='coordinadora_reagendar_cita'),

    # URLs de Director de Carrera
    path('dashboard/director/', views.dashboard_director, name='dashboard_director'),

    # URLs de Coordinador Técnico Pedagógico
    path('dashboard/asesor-tecnico/', views.dashboard_coordinador_tecnico_pedagogico, name='dashboard_coordinador_tecnico_pedagogico'),
    path('dashboard/asesor-tecnico/casos/<int:solicitud_id>/', views.detalle_casos_asesor_tecnico, name='detalle_casos_asesor_tecnico'),
    path('dashboard/asesor-tecnico/casos/<int:solicitud_id>/formular-ajuste/', views.formular_ajuste_asesor_tecnico, name='formular_ajuste_asesor_tecnico'),
    path('dashboard/asesor-tecnico/ajustes/<int:ajuste_asignado_id>/editar/', views.editar_ajuste_asesor_tecnico, name='editar_ajuste_asesor_tecnico'),
    path('dashboard/asesor-tecnico/ajustes/<int:ajuste_asignado_id>/eliminar/', views.eliminar_ajuste_asesor_tecnico, name='eliminar_ajuste_asesor_tecnico'),
    path('dashboard/asesor-tecnico/casos/<int:solicitud_id>/enviar-asesor-pedagogico/', views.enviar_a_asesor_pedagogico, name='enviar_a_asesor_pedagogico'),
    path('dashboard/asesor-tecnico/casos/<int:solicitud_id>/devolver-coordinadora/', views.devolver_a_coordinadora, name='devolver_a_coordinadora'),
    
    # URLs de Asesor Pedagógico
    path('dashboard/asesor/casos/<int:solicitud_id>/enviar-director/', views.enviar_a_director, name='enviar_a_director'),
    path('dashboard/asesor/casos/<int:solicitud_id>/devolver-asesor-tecnico/', views.devolver_a_asesor_tecnico, name='devolver_a_asesor_tecnico'),
    path('dashboard/asesor/ajustes/<int:ajuste_asignado_id>/editar/', views.editar_ajuste_asesor, name='editar_ajuste_asesor'),
    path('dashboard/asesor/ajustes/<int:ajuste_asignado_id>/eliminar/', views.eliminar_ajuste_asesor, name='eliminar_ajuste_asesor'),
    
    # URLs de Director de Carrera
    path('dashboard/director/casos/<int:solicitud_id>/aprobar/', views.aprobar_caso, name='aprobar_caso'),
    path('dashboard/director/casos/<int:solicitud_id>/rechazar/', views.rechazar_caso, name='rechazar_caso'),
    path('dashboard/director/ajustes/<int:ajuste_asignado_id>/aprobar/', views.aprobar_ajuste_director, name='aprobar_ajuste_director'),
    path('dashboard/director/ajustes/<int:ajuste_asignado_id>/rechazar/', views.rechazar_ajuste_director, name='rechazar_ajuste_director'),
    path('dashboard/director/carreras/', views.carreras_director, name='carreras_director'),
    path('dashboard/director/carreras/<int:carrera_id>/estudiantes/', views.estudiantes_por_carrera_director, name='estudiantes_carrera_director'),
    path('dashboard/director/estadisticas/', views.estadisticas_director, name='estadisticas_director'),
    
    # URLs de Carga Masiva (Director)
    path('dashboard/director/carga-masiva/', views.gestion_carga_masiva_director, name='gestion_carga_masiva_director'),
    path('dashboard/director/carga-masiva/estudiantes/', views.cargar_estudiantes_excel, name='cargar_estudiantes_excel'),
    path('dashboard/director/carga-masiva/docentes/', views.cargar_docentes_excel, name='cargar_docentes_excel'),
    path('dashboard/director/carga-masiva/asignaturas/', views.cargar_asignaturas_excel, name='cargar_asignaturas_excel'),
    path('dashboard/director/carga-masiva/inscripciones/', views.cargar_inscripciones_excel, name='cargar_inscripciones_excel'),
    path('dashboard/director/carga-masiva/plantilla/<str:tipo>/', views.descargar_plantilla_excel, name='descargar_plantilla_excel'),

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