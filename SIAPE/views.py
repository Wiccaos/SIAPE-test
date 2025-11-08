# Django
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import logout, login
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Count, Q
import json

from rest_framework import (
    viewsets, mixins, status
)

# APP
from .serializer import (
    UsuarioSerializer, PerfilUsuarioSerializer, RolesSerializer, AreasSerializer, CategoriasAjustesSerializer, CarrerasSerializer,
    EstudiantesSerializer, SolicitudesSerializer, EvidenciasSerializer, AsignaturasSerializer, AsignaturasEnCursoSerializer, 
    AjusteRazonableSerializer, AjusteAsignadoSerializer, EntrevistasSerializer, PublicaSolicitudSerializer
)
from .models import(
    Usuario, PerfilUsuario, Roles, Areas, CategoriasAjustes, Carreras, Estudiantes, Solicitudes, Evidencias,
    Asignaturas, AsignaturasEnCurso, Entrevistas, AjusteRazonable, AjusteAsignado
)  

# Django-restframework
from rest_framework.authentication import SessionAuthentication 
from rest_framework .permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .permissions import IsAsesorPedagogico

# ------------ CONSTANTES ------------
ROL_ASESOR = 'Asesor Pedagógico'
ROL_DIRECTOR = 'Director de Carrera'
ROL_DOCENTE = 'Docente'
ROL_ADMIN = 'Administrador'

# ----------------------------------------------
#           Vistas Públicas del Sistema
# ----------------------------------------------

class PublicSolicitudCreateView(APIView):
    """
    Endpoint público para que el Estudiante
    pueda enviar un formulario de solicitud de ajuste.
    """
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
            serializer = PublicaSolicitudSerializer(data=request.data)
            if serializer.is_valid():
                solicitud = serializer.save()

                return Response(
                    {
                        "message": "Solicitud creada con éxito.",
                        "solicitud_id": solicitud.id
                    },
                    status=status.HTTP_201_CREATED
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
def vista_formulario_solicitud(request):
    """
    Esta vista pública solo muestra la página HTML
    con el formulario de solicitud (formulario_solicitud.html).
    """

    try:
        carreras = Carreras.objects.all().order_by('nombre')
    except Carreras.DoesNotExist:
        carreras = []

    context = {
        'carreras': carreras,
    }

    return render(request, 'SIAPE/formulario_solicitud.html', context)

# ----------------------------------------------
#           Vistas Privadas del Sistema
# ----------------------------------------------

# ----------- Vistas para la página ------------
@login_required 
def pag_inicio(request):
    """
    Vista de inicio que actúa como enrutador basado en el rol.
    """
    
    rol = None

    if hasattr(request.user, 'perfil'):
        if request.user.perfil.rol:
            rol = request.user.perfil.rol.nombre_rol

    if rol == ROL_ASESOR:
        return redirect('dashboard_asesor')
    elif rol == ROL_DIRECTOR:
        return redirect('dashboard_director')
    elif rol == ROL_ADMIN:
        return redirect('dashboard_admin')

    # Si es superusuario pero no tiene rol (ej. 'admin' puro), va al admin de Django
    if request.user.is_superuser or request.user.is_staff:
        return redirect('admin:index')

    return render(request, 'SIAPE/inicio.html')
    
def vista_protegida(request):
    """    Redirecciona a login si el usuario no está autenticado """
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'vista_protegida.html')

def logout_view(request):
    logout(request)
    return redirect('login') 

# ------------- Páginas del Admin ------------
@login_required
def dashboard_admin(request):
    """
    Dashboard para Administradores del Sistema.
    Muestra KPIs globales y casos que requieren acción.
    """
    
    # Verificar permisos
    rol = None
    if hasattr(request.user, 'perfil'):
        if request.user.perfil.rol:
            rol = request.user.perfil.rol.nombre_rol

    if not request.user.is_superuser and rol != ROL_ADMIN:
        return redirect('home')

    # --- KPIs ---
    kpis = {
        'total_asesores': PerfilUsuario.objects.filter(rol__nombre_rol=ROL_ASESOR).count(),
        'total_directores': PerfilUsuario.objects.filter(rol__nombre_rol=ROL_DIRECTOR).count(),
        'total_docentes': PerfilUsuario.objects.filter(rol__nombre_rol=ROL_DOCENTE).count(),
        'total_estudiantes': Estudiantes.objects.count(),
        'total_solicitudes': Solicitudes.objects.count(),
        'solicitudes_en_proceso': Solicitudes.objects.filter(estado='en_proceso').count(),
        'solicitudes_aprobadas': Solicitudes.objects.filter(estado='aprobado').count(),
        'solicitudes_rechazadas': Solicitudes.objects.filter(estado='rechazado').count(),
    }

    # --- Tabla: Casos Críticos (Sin Asignar) ---
    # Solicitudes en proceso que no tienen ningún asesor
    solicitudes_sin_asignar = Solicitudes.objects.filter(
        asesores_pedagogicos__isnull=True,
        estado='en_proceso'
    ).select_related(
        'estudiantes', 
        'estudiantes__carreras'
    ).order_by('created_at') # <-- Más antiguas primero

    # --- Gráfico: Distribución de Solicitudes por Área ---
    distribucion_areas = Areas.objects.annotate(
        total_solicitudes=Count('carreras__estudiantes__solicitudes')
    ).filter(
        total_solicitudes__gt=0
    ).order_by('-total_solicitudes')
    
    total_solicitudes_grafico = sum(area.total_solicitudes for area in distribucion_areas)

    distribucion_con_porcentaje = []
    for area in distribucion_areas:
        porcentaje = (area.total_solicitudes / total_solicitudes_grafico * 100) if total_solicitudes_grafico > 0 else 0
        distribucion_con_porcentaje.append({
            'area': area,
            'total': area.total_solicitudes,
            'porcentaje': round(porcentaje, 1)
        })

    context = {
        'kpis': kpis,
        'solicitudes_sin_asignar': solicitudes_sin_asignar,
        'total_sin_asignar': solicitudes_sin_asignar.count(),
        'distribucion_apoyos': distribucion_con_porcentaje,
    }
    
    return render(request, 'SIAPE/dashboard_admin.html', context)

# ----------- Páginas de Asesor Pedagógco ------------

@login_required
def dashboard_asesor(request):
    """ Dashboard exclusivo para Asesores Pedagógicos. """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            return redirect('home')
    except AttributeError:
        return redirect('home')

    total_solicitudes = Solicitudes.objects.count()
    casos_resueltos = Solicitudes.objects.filter(
        estado='aprobado',
        ajusteasignado__isnull=False
    ).distinct().count()
    
    casos_en_proceso = Solicitudes.objects.filter(estado='en_proceso').count()

    # Calcular citas de esta semana
    hoy = timezone.now().date()
    # Calcular el inicio de la semana (lunes)
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    # Calcular el fin de la semana (domingo)
    fin_semana = inicio_semana + timedelta(days=6)
    
    # Convertir a datetime para la comparación con fecha_entrevista
    inicio_semana_dt = timezone.make_aware(datetime.combine(inicio_semana, datetime.min.time()))
    fin_semana_dt = timezone.make_aware(datetime.combine(fin_semana, datetime.max.time()))
    
    # Obtener el perfil del asesor actual
    perfil_asesor = request.user.perfil
    
    # Contar las citas (entrevistas) de esta semana para el asesor actual
    citas_semana = Entrevistas.objects.filter(
        asesor_pedagogico=perfil_asesor,
        fecha_entrevista__gte=inicio_semana_dt,
        fecha_entrevista__lte=fin_semana_dt
    ).count()

    # Obtener distribución de apoyos por categoría de ajustes
    # Agrupar por categoría y contar por estado de solicitud
    categorias_con_estadisticas = []
    
    # Obtener todas las categorías que tienen ajustes asignados
    # Django crea automáticamente el related_name como nombre_modelo_set o nombre_modelo en minúsculas
    categorias = CategoriasAjustes.objects.filter(
        ajusterazonable__ajusteasignado__isnull=False
    ).distinct().annotate(
        total_aprobados=Count(
            'ajusterazonable__ajusteasignado__solicitudes',
            filter=Q(ajusterazonable__ajusteasignado__solicitudes__estado='aprobado'),
            distinct=True
        ),
        total_pendientes=Count(
            'ajusterazonable__ajusteasignado__solicitudes',
            filter=Q(ajusterazonable__ajusteasignado__solicitudes__estado='en_proceso'),
            distinct=True
        ),
        total_rechazados=Count(
            'ajusterazonable__ajusteasignado__solicitudes',
            filter=Q(ajusterazonable__ajusteasignado__solicitudes__estado='rechazado'),
            distinct=True
        )
    )
    
    # Calcular totales y porcentajes
    total_general = Solicitudes.objects.filter(
        ajusteasignado__isnull=False
    ).distinct().count()
    
    for categoria in categorias:
        total_categoria = categoria.total_aprobados + categoria.total_pendientes + categoria.total_rechazados
        porcentaje = (total_categoria / total_general * 100) if total_general > 0 else 0
        
        categorias_con_estadisticas.append({
            'categoria': categoria,
            'aprobados': categoria.total_aprobados,
            'pendientes': categoria.total_pendientes,
            'rechazados': categoria.total_rechazados,
            'total': total_categoria,
            'porcentaje': round(porcentaje, 1)
        })
    
    # Ordenar por total descendente
    categorias_con_estadisticas.sort(key=lambda x: x['total'], reverse=True)

    context = {
        'nombre_usuario': request.user.first_name,
        'total_solicitudes': total_solicitudes,
        'casos_resueltos': casos_resueltos,
        'casos_en_proceso': casos_en_proceso,
        'citas_semana': citas_semana,
        'distribucion_apoyos': categorias_con_estadisticas,
    }
    return render(request, 'SIAPE/dashboard_asesor.html', context)

@login_required
def casos_asesor(request):
    """
    Muestra la tabla de Casos Activos para el Asesor.
    """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            return redirect('home')
    except AttributeError:
        return redirect('home')

    lista_solicitudes = Solicitudes.objects.select_related('estudiantes').order_by('-created_at')

    context = {
        'solicitudes': lista_solicitudes,
        'total_casos': lista_solicitudes.count()
    }

    return render(request, 'SIAPE/casos_asesor.html', context)

@login_required
def detalle_caso_asesor(request, solicitud_id):
    """
    Muestra la vista detallada de un caso específico para el Asesor.
    """

    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            return redirect('home')
    except AttributeError:
        return redirect('home')

    solicitud = get_object_or_404(
        Solicitudes.objects.select_related('estudiantes'), 
        id=solicitud_id
    )

    evidencias = Evidencias.objects.filter(solicitudes=solicitud)
    ajustes = AjusteAsignado.objects.filter(solicitudes=solicitud).select_related('ajuste_razonable')
    entrevistas = Entrevistas.objects.filter(solicitudes=solicitud).order_by('fecha_entrevista')

    context = {
        'solicitud': solicitud,
        'evidencias': evidencias,
        'ajustes': ajustes,
        'entrevistas': entrevistas,
        'estudiante': solicitud.estudiantes,
    }

    return render(request, 'SIAPE/detalle_caso_asesor.html', context)

@login_required
def panel_control_asesor(request):
    """
    Panel de Control para Asesores Pedagógicos.
    Permite asignar casos, agendar citas, registrar ajustes razonables y ver próximas citas.
    """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            return redirect('home')
    except AttributeError:
        return redirect('home')

    perfil_asesor = request.user.perfil

    # Obtener todas las fechas de citas para el calendario
    citas_para_calendario = Entrevistas.objects.filter(
        asesor_pedagogico=perfil_asesor
    ).values_list('fecha_entrevista', flat=True)
    
    # Convertir a formato 'YYYY-MM-DD' y eliminar duplicados
    fechas_citas = sorted(list(set([
        dt.strftime('%Y-%m-%d') for dt in citas_para_calendario
    ])))
    
    # Casos disponibles para asignar (sin asesor asignado)
    casos_disponibles = Solicitudes.objects.filter(
        asesores_pedagogicos__isnull=True,
        estado='en_proceso'
    ).select_related('estudiantes').order_by('-created_at')[:10]
    
    # Próximas citas del asesor (pendientes y futuras)
    ahora = timezone.now()
    proximas_citas = Entrevistas.objects.filter(
        asesor_pedagogico=perfil_asesor,
        fecha_entrevista__gte=ahora,
        estado='pendiente'
    ).select_related('solicitudes', 'solicitudes__estudiantes').order_by('fecha_entrevista')[:10]
    
    # Citas pasadas pendientes de confirmación
    citas_pendientes_confirmar = Entrevistas.objects.filter(
        asesor_pedagogico=perfil_asesor,
        fecha_entrevista__lt=ahora,
        estado='pendiente'
    ).select_related('solicitudes', 'solicitudes__estudiantes').order_by('-fecha_entrevista')[:10]
    
    # Citas realizadas (para editar notas)
    citas_realizadas = Entrevistas.objects.filter(
        asesor_pedagogico=perfil_asesor,
        estado='realizada'
    ).select_related('solicitudes', 'solicitudes__estudiantes').order_by('-fecha_entrevista')[:10]
    
    # Citas no asistió (para reagendar)
    citas_no_asistio = Entrevistas.objects.filter(
        asesor_pedagogico=perfil_asesor,
        estado='no_asistio'
    ).select_related('solicitudes', 'solicitudes__estudiantes').order_by('-fecha_entrevista')[:10]
    
    # Categorías de ajustes para el formulario
    categorias_ajustes = CategoriasAjustes.objects.all()
    
    # Casos asignados al asesor actual con información de ajustes
    casos_asignados = Solicitudes.objects.filter(
        asesores_pedagogicos=perfil_asesor,
        estado='en_proceso'
    ).select_related('estudiantes').order_by('-created_at')
    
    # Agregar información de ajustes a cada caso
    casos_con_ajustes = []
    for caso in casos_asignados:
        ajustes_asignados = AjusteAsignado.objects.filter(solicitudes=caso).select_related('ajuste_razonable', 'ajuste_razonable__categorias_ajustes')
        tiene_ajuste = ajustes_asignados.exists()
        ajuste_actual = ajustes_asignados.first() if tiene_ajuste else None
        
        casos_con_ajustes.append({
            'caso': caso,
            'tiene_ajuste': tiene_ajuste,
            'ajuste_actual': ajuste_actual,
            'total_ajustes': ajustes_asignados.count()
        })

    context = {
        'casos_disponibles': casos_disponibles,
        'proximas_citas': proximas_citas,
        'citas_pendientes_confirmar': citas_pendientes_confirmar,
        'citas_realizadas': citas_realizadas,
        'citas_no_asistio': citas_no_asistio,
        'categorias_ajustes': categorias_ajustes,
        'casos_asignados': casos_asignados,
        'casos_con_ajustes': casos_con_ajustes,
        'fechas_citas_json': json.dumps(fechas_citas),
    }
    return render(request, 'SIAPE/panel_control_asesor.html', context)

@login_required
def asignar_caso_asesor(request, solicitud_id):
    """ Asignar un caso al asesor actual. """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')

    if request.method == 'POST':
        solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
        perfil_asesor = request.user.perfil
        
        if solicitud.asesores_pedagogicos is None:
            solicitud.asesores_pedagogicos = perfil_asesor
            solicitud.save()
            messages.success(request, f'Caso asignado correctamente: {solicitud.asunto}')
        else:
            messages.warning(request, 'Este caso ya está asignado a otro asesor.')
    
    return redirect('panel_control_asesor')

@login_required
def agendar_cita_asesor(request):
    """ Agendar una cita (entrevista) para un caso. """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')

    if request.method == 'POST':
        solicitud_id = request.POST.get('solicitud_id')
        fecha_entrevista_str = request.POST.get('fecha_entrevista')
        modalidad = request.POST.get('modalidad')
        notas = request.POST.get('notas', '')
        
        try:
            solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
            perfil_asesor = request.user.perfil
            
            # Convertir la fecha del formulario
            fecha_entrevista = datetime.strptime(fecha_entrevista_str, '%Y-%m-%dT%H:%M')
            fecha_entrevista = timezone.make_aware(fecha_entrevista)
            
            Entrevistas.objects.create(
                solicitudes=solicitud,
                asesor_pedagogico=perfil_asesor,
                fecha_entrevista=fecha_entrevista,
                modalidad=modalidad,
                notas=notas
            )
            messages.success(request, 'Cita agendada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al agendar la cita: {str(e)}')
    
    return redirect('panel_control_asesor')


@login_required
def registrar_ajuste_razonable(request):
    """ Registrar un ajuste razonable y asignarlo a un caso. """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')

    if request.method == 'POST':
        solicitud_id = request.POST.get('solicitud_id')
        descripcion = request.POST.get('descripcion')
        categoria_id = request.POST.get('categoria_id')
        nueva_categoria = request.POST.get('nueva_categoria', '').strip()
        reasignar = request.POST.get('reasignar', 'false') == 'true'
        
        try:
            solicitud = get_object_or_404(
                Solicitudes,
                id=solicitud_id,
                asesores_pedagogicos=request.user.perfil
            )
            
            # Determinar la categoría
            if nueva_categoria:
                # Crear nueva categoría
                categoria = CategoriasAjustes.objects.create(nombre_categoria=nueva_categoria)
            elif categoria_id:
                categoria = get_object_or_404(CategoriasAjustes, id=categoria_id)
            else:
                messages.error(request, 'Debe seleccionar una categoría o crear una nueva.')
                return redirect('panel_control_asesor')
            
            # Si es reasignación, eliminar los ajustes anteriores (opcional, o mantenerlos)
            # Por ahora, permitimos múltiples ajustes, pero podríamos eliminar los anteriores si se desea
            if reasignar:
                # Opcional: eliminar ajustes anteriores
                # AjusteAsignado.objects.filter(solicitudes=solicitud).delete()
                pass
            
            # Crear el ajuste razonable
            ajuste_razonable = AjusteRazonable.objects.create(
                descripcion=descripcion,
                categorias_ajustes=categoria
            )
            
            # Asignar el ajuste a la solicitud
            AjusteAsignado.objects.create(
                ajuste_razonable=ajuste_razonable,
                solicitudes=solicitud
            )
            
            if reasignar:
                messages.success(request, 'Ajuste razonable reasignado correctamente.')
            else:
                messages.success(request, 'Ajuste razonable registrado y asignado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al registrar el ajuste: {str(e)}')
    
    return redirect('panel_control_asesor')

@login_required
def rechazar_solicitud_asesor(request, solicitud_id):
    """ Rechazar una solicitud asignada al asesor actual. """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')

    if request.method == 'POST':
        motivo_rechazo = request.POST.get('motivo_rechazo', '').strip()
        
        try:
            solicitud = get_object_or_404(
                Solicitudes,
                id=solicitud_id,
                asesores_pedagogicos=request.user.perfil
            )
            
            # Solo se pueden rechazar solicitudes que estén en proceso
            if solicitud.estado != 'en_proceso':
                messages.warning(request, 'Solo se pueden rechazar solicitudes en proceso.')
                return redirect('panel_control_asesor')
            
            solicitud.estado = 'rechazado'
            solicitud.save()
            
            # Si se proporcionó un motivo, podríamos guardarlo en algún campo adicional
            # Por ahora solo mostramos el mensaje
            if motivo_rechazo:
                messages.success(request, f'Solicitud rechazada. Motivo: {motivo_rechazo}')
            else:
                messages.success(request, 'Solicitud rechazada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al rechazar la solicitud: {str(e)}')
    
    return redirect('panel_control_asesor')

@login_required
def aprobar_solicitud_asesor(request, solicitud_id):
    """ Aprobar una solicitud asignada al asesor actual. """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')

    if request.method == 'POST':
        try:
            solicitud = get_object_or_404(
                Solicitudes,
                id=solicitud_id,
                asesores_pedagogicos=request.user.perfil
            )
            
            # Solo se pueden aprobar solicitudes que estén en proceso
            if solicitud.estado != 'en_proceso':
                messages.warning(request, 'Solo se pueden aprobar solicitudes en proceso.')
                return redirect('panel_control_asesor')
            
            # Validar que la solicitud tenga al menos un ajuste asignado
            tiene_ajuste = AjusteAsignado.objects.filter(solicitudes=solicitud).exists()
            if not tiene_ajuste:
                messages.error(request, 'No se puede aprobar la solicitud. Debe asignar al menos un ajuste razonable antes de aprobar.')
                return redirect('panel_control_asesor')
            
            solicitud.estado = 'aprobado'
            solicitud.save()
            
            messages.success(request, 'Solicitud aprobada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al aprobar la solicitud: {str(e)}')
    
    return redirect('panel_control_asesor')

@login_required
def confirmar_cita_asesor(request, entrevista_id):
    """ Confirmar una cita como realizada o marcar como no asistió. """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')

    if request.method == 'POST':
        accion = request.POST.get('accion')  # 'realizada' o 'no_asistio'
        notas_adicionales = request.POST.get('notas_adicionales', '')
        
        try:
            entrevista = get_object_or_404(
                Entrevistas,
                id=entrevista_id,
                asesor_pedagogico=request.user.perfil
            )
            
            if accion in ['realizada', 'no_asistio']:
                entrevista.estado = accion
                # Agregar notas adicionales si se proporcionaron
                if notas_adicionales:
                    if entrevista.notas:
                        entrevista.notas += f"\n\n[Confirmación - {timezone.now().strftime('%d/%m/%Y %H:%M')}]: {notas_adicionales}"
                    else:
                        entrevista.notas = f"[Confirmación - {timezone.now().strftime('%d/%m/%Y %H:%M')}]: {notas_adicionales}"
                entrevista.save()
                
                if accion == 'realizada':
                    messages.success(request, 'Cita marcada como realizada.')
                else:
                    messages.info(request, 'Cita marcada como no asistió. Puedes reagendarla desde el panel.')
            else:
                messages.error(request, 'Acción no válida.')
        except Exception as e:
            messages.error(request, f'Error al confirmar la cita: {str(e)}')
    
    return redirect('panel_control_asesor')

@login_required
def editar_notas_cita(request, entrevista_id):
    """ Editar las notas de una cita. """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')

    if request.method == 'POST':
        nuevas_notas = request.POST.get('notas', '')
        
        try:
            entrevista = get_object_or_404(
                Entrevistas,
                id=entrevista_id,
                asesor_pedagogico=request.user.perfil
            )
            
            entrevista.notas = nuevas_notas
            entrevista.save()
            messages.success(request, 'Notas actualizadas correctamente.')
        except Exception as e:
            messages.error(request, f'Error al actualizar las notas: {str(e)}')
    
    return redirect('panel_control_asesor')

@login_required
def reagendar_cita_asesor(request, entrevista_id):
    """ Reagendar una cita que no se realizó. """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')

    if request.method == 'POST':
        nueva_fecha_str = request.POST.get('nueva_fecha_entrevista')
        nueva_modalidad = request.POST.get('nueva_modalidad', '')
        notas_reagendamiento = request.POST.get('notas_reagendamiento', '')
        
        try:
            entrevista_original = get_object_or_404(
                Entrevistas,
                id=entrevista_id,
                asesor_pedagogico=request.user.perfil
            )
            
            # Convertir la nueva fecha
            nueva_fecha = datetime.strptime(nueva_fecha_str, '%Y-%m-%dT%H:%M')
            nueva_fecha = timezone.make_aware(nueva_fecha)
            
            # Crear nueva cita
            nueva_entrevista = Entrevistas.objects.create(
                solicitudes=entrevista_original.solicitudes,
                asesor_pedagogico=entrevista_original.asesor_pedagogico,
                fecha_entrevista=nueva_fecha,
                modalidad=nueva_modalidad or entrevista_original.modalidad,
                notas=f"Reagendada desde cita del {entrevista_original.fecha_entrevista.strftime('%d/%m/%Y %H:%M')}. {notas_reagendamiento}" if notas_reagendamiento else f"Reagendada desde cita del {entrevista_original.fecha_entrevista.strftime('%d/%m/%Y %H:%M')}.",
                estado='pendiente'
            )
            
            # Marcar la cita original como no asistió si aún está pendiente
            if entrevista_original.estado == 'pendiente':
                entrevista_original.estado = 'no_asistio'
                entrevista_original.save()
            
            messages.success(request, 'Cita reagendada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al reagendar la cita: {str(e)}')
    
    return redirect('panel_control_asesor')


# --- VISTA DIRECTOR DE CARRERA ---
@login_required
def dashboard_director(request):
    """
    Dashboard para Directores de Carrera. Muestra KPIs
    y distribución por carreras (basado en el mockup).
    """

    try:

        if request.user.perfil.rol.nombre_rol != ROL_DIRECTOR:
            return redirect('home')
    except AttributeError:
        return redirect('home')

    total_solicitudes = Solicitudes.objects.count()
    casos_resueltos = Solicitudes.objects.filter(
        estado='aprobado',
        ajusteasignado__isnull=False
    ).distinct().count()
    casos_en_proceso = Solicitudes.objects.filter(estado='en_proceso').count()
    
    carreras = Carreras.objects.all() 

    context = {
        'nombre_usuario': request.user.first_name,
        'total_solicitudes': total_solicitudes,
        'casos_resueltos': casos_resueltos,
        'casos_en_proceso': casos_en_proceso,
        'carreras': carreras, 
    }
    return render(request, 'SIAPE/dashboard_director.html', context)




# ----------- Vistas de los modelos ------------

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class RolesViewSet(viewsets.ModelViewSet):
    queryset = Roles.objects.all()
    serializer_class = RolesSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class AreasViewSet(viewsets.ModelViewSet):
    queryset = Areas.objects.all()
    serializer_class = AreasSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class CategoriasAjustesViewSet(viewsets.ModelViewSet):
    queryset = CategoriasAjustes.objects.all()
    serializer_class = CategoriasAjustesSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class CarrerasViewSet(viewsets.ModelViewSet):
    queryset = Carreras.objects.all()
    serializer_class = CarrerasSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class EstudiantesViewSet(viewsets.ModelViewSet):
    queryset = Estudiantes.objects.all()
    serializer_class = EstudiantesSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class SolicitudesViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    
    queryset = Solicitudes.objects.all().order_by('-created_at')
    serializer_class = SolicitudesSerializer
    permission_classes = [IsAsesorPedagogico | IsAdminUser]

class EvidenciasViewSet(viewsets.ModelViewSet):
    queryset = Evidencias.objects.all()
    serializer_class = EvidenciasSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class AsignaturasViewSet(viewsets.ModelViewSet):
    queryset = Asignaturas.objects.all()
    serializer_class = AsignaturasSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class AsignaturasEnCursoViewSet(viewsets.ModelViewSet):
    queryset = AsignaturasEnCurso.objects.all()
    serializer_class = AsignaturasEnCursoSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class EntrevistasViewSet(viewsets.ModelViewSet):
    queryset = Entrevistas.objects.all()
    serializer_class = EntrevistasSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class AjusteRazonableViewSet(viewsets.ModelViewSet):
    queryset = AjusteRazonable.objects.all()
    serializer_class = AjusteRazonableSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class AjusteAsignadoViewSet(viewsets.ModelViewSet):
    queryset = AjusteAsignado.objects.all()
    serializer_class = AjusteAsignadoSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class PerfilUsuarioViewSet(viewsets.ModelViewSet):
    queryset = PerfilUsuario.objects.all()
    serializer_class = PerfilUsuarioSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]