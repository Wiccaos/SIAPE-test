from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
# Django
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import logout, login
from django.utils import timezone
from datetime import timedelta, datetime, time, date
from django.db.models import Count, Q
import json
import calendar # Importar para el calendario mensual
import logging
from django.views.decorators.http import require_POST

from rest_framework import (
    viewsets, mixins, status
)
# --- Imports para las nuevas API de horarios ---
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
# --- Fin imports API ---

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
ROL_ASESOR = 'Asesora Pedagógica'
ROL_DIRECTOR = 'Director de Carrera'
ROL_DOCENTE = 'Docente'
ROL_ADMIN = 'Administrador'
ROL_COORDINADORA = 'Coordinadora de Inclusión'
ROL_ASESORA_TECNICA = 'Asesora Técnica Pedagógica'


# ----------------------------------------------
#           Vistas Públicas del Sistema
# ----------------------------------------------

class PublicSolicitudCreateView(APIView):
    """
    Endpoint público para que el Estudiante
    pueda enviar un formulario de solicitud de ajuste.
    (La lógica de creación ahora está en el Serializer)
    """
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
            # Usamos el serializer modificado que maneja la creación de la cita
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
            # Los errores de validación (incluyendo "hora tomada") se devuelven aquí
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


@api_view(['GET'])
@permission_classes([AllowAny])
def get_horarios_disponibles(request):
    """
    Endpoint público para obtener los slots de 1 hora disponibles
    para una fecha específica, basado en las citas de la Coordinadora.
    Recibe un parámetro GET: ?date=YYYY-MM-DD
    """
    
    # 1. Obtener la fecha de la consulta
    selected_date_str = request.GET.get('date')
    if not selected_date_str:
        return Response({"error": "Debe proporcionar una fecha (date=YYYY-MM-DD)."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

    # Validación extra: No permitir agendar fines de semana
    if selected_date.weekday() >= 5: # 5 = Sábado, 6 = Domingo
         return Response([], status=status.HTTP_200_OK) # Retorna lista vacía

    # 2. Definir todos los slots posibles (9:00 a 17:00, ya que 18:00 es el fin)
    possible_hours = range(9, 18)
    all_slots = [f"{hour:02d}:00" for hour in possible_hours]

    try:
        # 3. Encontrar la(s) coordinadora(s)
        coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
        if not coordinadoras.exists():
            return Response({"error": "No hay coordinadoras configuradas."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 4. Calcular horarios disponibles: un horario está disponible si AL MENOS UNA coordinadora lo tiene libre
        start_of_day = timezone.make_aware(datetime.combine(selected_date, time.min))
        end_of_day = timezone.make_aware(datetime.combine(selected_date, time.max))

        # Para cada slot, verificar si al menos una coordinadora lo tiene disponible
        available_slots = []
        for slot in all_slots:
            # Convertir el slot (ej: "10:00") a datetime
            hora_obj = datetime.strptime(slot, '%H:%M').time()
            slot_datetime = timezone.make_aware(datetime.combine(selected_date, hora_obj))
            
            # Verificar si al menos una coordinadora tiene este horario libre
            # Un horario está disponible si AL MENOS UNA coordinadora NO tiene cita en ese horario
            slot_disponible = False
            for coord in coordinadoras:
                tiene_cita = Entrevistas.objects.filter(
                    coordinadora=coord,
                    fecha_entrevista=slot_datetime
                ).exclude(coordinadora__isnull=True).exists()
                if not tiene_cita:
                    slot_disponible = True
                    break
            
            if slot_disponible:
                available_slots.append(slot)
        
        return Response(available_slots, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"Error interno del servidor: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_calendario_disponible(request):
    """
    Endpoint público para obtener la disponibilidad de un mes completo.
    Recibe un parámetro GET: ?month=YYYY-MM
    """
    
    # 1. Obtener el mes y año de la consulta
    month_str = request.GET.get('month')
    try:
        # Si no se provee mes, usa el mes actual (en zona horaria de Chile)
        if not month_str:
            target_date = timezone.localtime(timezone.now()).date()
        else:
            target_date = datetime.strptime(month_str, '%Y-%m').date()
    except ValueError:
        return Response({"error": "Formato de mes inválido. Use YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)

    year = target_date.year
    month = target_date.month

    # 2. Encontrar a las coordinadoras
    coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
    if not coordinadoras.exists():
        return Response({"error": "No hay coordinadoras configuradas."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 3. Obtener todas las citas ya tomadas en ese mes, agrupadas por coordinadora y día
    # Estructura: {coordinadora_id: {dia_str: set([hora1, hora2, ...])}}
    citas_por_coordinadora_dia = {}
    
    # Obtener TODAS las citas del mes de TODAS las coordinadoras de una vez
    # Usar rango de fechas en lugar de __year y __month para evitar problemas de zona horaria
    # Calcular el primer y último día del mes en la zona horaria local
    primer_dia_mes = timezone.make_aware(datetime(year, month, 1, 0, 0, 0))
    if month == 12:
        ultimo_dia_mes = timezone.make_aware(datetime(year + 1, 1, 1, 0, 0, 0))
    else:
        ultimo_dia_mes = timezone.make_aware(datetime(year, month + 1, 1, 0, 0, 0))
    
    print(f"[DEBUG] Buscando citas entre {primer_dia_mes} y {ultimo_dia_mes}")
    
    # Filtrar por rango de fechas (esto funciona correctamente con zonas horarias)
    todas_las_citas = Entrevistas.objects.filter(
        coordinadora__in=coordinadoras,
        fecha_entrevista__gte=primer_dia_mes,
        fecha_entrevista__lt=ultimo_dia_mes
    ).exclude(coordinadora__isnull=True).select_related('coordinadora').values_list('coordinadora_id', 'fecha_entrevista')
    
    # Debug: mostrar todas las citas encontradas
    total_citas = todas_las_citas.count()
    print(f"[DEBUG] Total de citas encontradas en {year}-{month:02d}: {total_citas}")
    for coord_id, dt in todas_las_citas:
        dt_local = timezone.localtime(dt)
        print(f"[DEBUG] Cita encontrada: Coord={coord_id}, Fecha UTC={dt}, Fecha Local={dt_local.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.debug(f"Total de citas encontradas en {year}-{month:02d}: {total_citas}")
    
    # Inicializar el diccionario para todas las coordinadoras
    for coord in coordinadoras:
        citas_por_coordinadora_dia[coord.id] = {}
    
    # Procesar cada cita
    for coord_id, dt in todas_las_citas:
        # Convertir a la zona horaria local de forma consistente
        dt_local = timezone.localtime(dt)
        dia_str = dt_local.strftime('%Y-%m-%d')
        # Normalizar la hora a solo la hora en punto (ej: "10:30" -> "10:00")
        # Esto es necesario porque los slots son de hora en punto
        hora_str = f"{dt_local.hour:02d}:00"
        
        if coord_id not in citas_por_coordinadora_dia:
            citas_por_coordinadora_dia[coord_id] = {}
        if dia_str not in citas_por_coordinadora_dia[coord_id]:
            citas_por_coordinadora_dia[coord_id][dia_str] = set()
        citas_por_coordinadora_dia[coord_id][dia_str].add(hora_str)
        
        print(f"[DEBUG] Cita encontrada: Coordinadora {coord_id}, Día {dia_str}, Hora {hora_str} (original: {dt_local.strftime('%Y-%m-%d %H:%M:%S')})")
        logger.debug(f"Cita encontrada: Coordinadora {coord_id}, Día {dia_str}, Hora {hora_str} (original: {dt_local.strftime('%Y-%m-%d %H:%M:%S')})")
    
    # Debug: Log de citas encontradas por coordinadora
    for coord in coordinadoras:
        if coord.id in citas_por_coordinadora_dia:
            logger.debug(f"Coordinadora {coord.id}: {sum(len(horas) for horas in citas_por_coordinadora_dia[coord.id].values())} horas ocupadas")
            for dia, horas in citas_por_coordinadora_dia[coord.id].items():
                logger.debug(f"  Día {dia}: horas ocupadas {sorted(horas)}")

    # 4. Definir los slots base y preparar la respuesta
    slots_base_por_hora = range(9, 18) # 9:00 a 17:00
    
    respuesta_api = {
        "fechasConDisponibilidad": [], # Días con al menos 1 hora libre
        "diasCompletos": [],           # Días sin horas libres
        "slotsDetallados": {},         # { "2025-11-13": ["09:00", "14:00"], ... }
        "slotsNoDisponibles": {}       # { "2025-11-13": ["10:00", ...], ... }
    }

    # 5. Iterar por cada día del mes
    _, num_dias_mes = calendar.monthrange(year, month)
    

    now = timezone.localtime(timezone.now())
    hoy_str = now.date().strftime('%Y-%m-%d')

    for dia in range(1, num_dias_mes + 1):
        dia_actual_date = date(year, month, dia)
        dia_actual_str = dia_actual_date.strftime('%Y-%m-%d')

        # Omitir fines de semana y días pasados (usar fecha actual en zona horaria de Chile)
        hoy_chile = timezone.localtime(timezone.now()).date()
        if dia_actual_date.weekday() >= 5 or dia_actual_date < hoy_chile:
            continue

        slots_libres = []
        slots_no_disponibles = []
        
        for h in slots_base_por_hora:
            hora_str = f"{h:02d}:00"
            
            # Si es hoy, solo permitir con 2 horas de anticipación
            if dia_actual_str == hoy_str:
                if h <= now.hour + 1:  # Debe ser al menos 2 horas después de la actual
                    slots_no_disponibles.append(hora_str)
                    continue
            
            slot_ocupado = False
            coordinadora_ocupada = None
            if coordinadoras.exists():
                for coord in coordinadoras:
                    citas_coord_dia = citas_por_coordinadora_dia.get(coord.id, {}).get(dia_actual_str, set())
                    # Debug: verificar qué hay en el set
                    if citas_coord_dia:
                        print(f"[DEBUG] Coordinadora {coord.id}, Día {dia_actual_str}: horas en set = {sorted(citas_coord_dia)}, buscando {hora_str}")
                        logger.debug(f"Coordinadora {coord.id}, Día {dia_actual_str}: horas en set = {sorted(citas_coord_dia)}, buscando {hora_str}")
                    # Si esta coordinadora tiene una cita en este horario, el slot está ocupado
                    if hora_str in citas_coord_dia:
                        slot_ocupado = True
                        coordinadora_ocupada = coord.id
                        print(f"[DEBUG] ✓ Slot {hora_str} del día {dia_actual_str} está ocupado por coordinadora {coord.id}")
                        logger.debug(f"✓ Slot {hora_str} del día {dia_actual_str} está ocupado por coordinadora {coord.id}")
                        break
            
            # Si ninguna coordinadora tiene el horario ocupado, está disponible
            if not slot_ocupado and coordinadoras.exists():
                slots_libres.append(hora_str)
                logger.debug(f"  Slot {hora_str} del día {dia_actual_str} está DISPONIBLE")
            else:
                # Al menos una coordinadora tiene este horario ocupado (o no hay coordinadoras)
                slots_no_disponibles.append(hora_str)
                if slot_ocupado:
                    print(f"[DEBUG] Slot {hora_str} del día {dia_actual_str} agregado a slots_no_disponibles (ocupado por coord {coordinadora_ocupada})")
                    logger.debug(f"  Slot {hora_str} del día {dia_actual_str} agregado a slots_no_disponibles (ocupado por coord {coordinadora_ocupada})")
                else:
                    print(f"[DEBUG] Slot {hora_str} del día {dia_actual_str} agregado a slots_no_disponibles (no hay coordinadoras)")
                    logger.debug(f"  Slot {hora_str} del día {dia_actual_str} agregado a slots_no_disponibles (no hay coordinadoras)")

        # Siempre agregar los slots detallados, incluso si no hay disponibles
        # Esto permite que el frontend muestre correctamente qué horarios están ocupados
        respuesta_api["slotsDetallados"][dia_actual_str] = slots_libres
        respuesta_api["slotsNoDisponibles"][dia_actual_str] = slots_no_disponibles
        
        # Debug: Log de slots para este día
        if slots_no_disponibles:
            print(f"[DEBUG] Día {dia_actual_str}: {len(slots_no_disponibles)} slots no disponibles: {sorted(slots_no_disponibles)}")
            logger.debug(f"Día {dia_actual_str}: {len(slots_no_disponibles)} slots no disponibles: {sorted(slots_no_disponibles)}")
        
        if len(slots_libres) > 0:
            respuesta_api["fechasConDisponibilidad"].append(dia_actual_str)
        else:
            respuesta_api["diasCompletos"].append(dia_actual_str)

    # Debug: Imprimir resumen final
    print(f"[DEBUG] Resumen final - Días con disponibilidad: {len(respuesta_api['fechasConDisponibilidad'])}")
    print(f"[DEBUG] Resumen final - Días completos: {len(respuesta_api['diasCompletos'])}")
    print(f"[DEBUG] Resumen final - Total días procesados: {len(respuesta_api['slotsDetallados'])}")
    for dia, slots in list(respuesta_api['slotsNoDisponibles'].items())[:5]:  # Mostrar primeros 5 días
        if slots:
            print(f"[DEBUG] Día {dia}: {len(slots)} slots no disponibles: {sorted(slots)}")
    
    return Response(respuesta_api, status=status.HTTP_200_OK)


# ----------------------------------------------
#           Vistas Privadas del Sistema
# ----------------------------------------------


# ----------- Vistas para la página ------------
@login_required
def redireccionamiento_por_rol(request):
    """
    Redirecciona al dashboard correspondiente según el rol del usuario.
    """
    rol = None
    if hasattr(request.user, 'perfil') and request.user.perfil.rol:
        rol = request.user.perfil.rol.nombre_rol

    if rol == ROL_COORDINADORA:
        return redirect('dashboard_coordinadora')
    elif rol == ROL_ASESORA_TECNICA:
        return redirect('dashboard_asesor_técnico')
    elif rol == ROL_ASESOR:
        return redirect('dashboard_asesor')
    elif rol == ROL_DIRECTOR:
        return redirect('dashboard_director')
    elif rol == ROL_ADMIN:
        return redirect('dashboard_admin')

    if request.user.is_superuser or request.user.is_staff:
        return redirect('admin:index')

    return redirect('login')
    

def vista_protegida(request):
    """    Redirecciona a login si el usuario no está autenticado """
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'vista_protegida.html')

def logout_view(request):
    logout(request)
    return redirect('login') 

@login_required
def casos_generales(request):
    """
    Vista unificada para buscar y filtrar todos los casos del sistema.
    Filtra casos según el rol del usuario:
    - Coordinadora: Casos pendientes de entrevista o asignados a ella
    - Asesora Técnica: Casos pendientes de formulación (que debe formular)
    - Asesor Pedagógico: Casos pendientes de preaprobación
    - Director: Casos pendientes de aprobación
    - Admin: Todos los casos
    """

    try:
        perfil = request.user.perfil
        rol_nombre = perfil.rol.nombre_rol
        ROLES_PERMITIDOS = [
            ROL_COORDINADORA,
            ROL_ASESORA_TECNICA,
            ROL_ASESOR,
            ROL_DIRECTOR,
            ROL_ADMIN
        ]
        if rol_nombre not in ROLES_PERMITIDOS:
            messages.error(request, 'No tienes permisos para acceder a esta vista.')
            return redirect('home')
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')
        rol_nombre = None
        perfil = None

    # Base query con relaciones optimizadas
    solicitudes_list = Solicitudes.objects.all().select_related(
        'estudiantes', 
        'estudiantes__carreras',
        'coordinadora_asignada',
        'asesor_tecnico_asignado',
        'asesor_pedagogico_asignado'
    ).prefetch_related(
        'ajusteasignado_set__ajuste_razonable__categorias_ajustes'
    ).distinct().order_by('-created_at')

    # Obtener parámetros de filtro
    q_nombre = request.GET.get('q_nombre', '').strip()
    q_fecha = request.GET.get('q_fecha', '').strip()
    q_ajuste = request.GET.get('q_ajuste', '').strip()
    q_estado = request.GET.get('q_estado', '').strip()  # Filtro por estado
    q_todos = request.GET.get('todos', '').strip()  # Permite ver todos los casos
    
    # Inicializar filtros
    filtros = Q()
    filtros_busqueda = Q()
    
    # 1. Determinar si el usuario quiere ver todos los casos (sin filtro por rol)
    tiene_todos = 'todos' in request.GET
    # Verificar si se seleccionó un estado específico (no vacío)
    tiene_estado_explicito = bool(q_estado and q_estado.strip())
    
    # 2. Aplicar filtro por defecto según el rol
    # Por defecto, SIEMPRE aplicar el filtro por rol (a menos que tenga_todos=True o sea Admin)
    # El filtro por rol se aplica a menos que el usuario explícitamente quiera ver todos los casos
    aplicar_filtro_por_rol = (not tiene_todos and rol_nombre and rol_nombre != ROL_ADMIN and perfil is not None)
    
    if aplicar_filtro_por_rol:
        if rol_nombre == ROL_COORDINADORA:
            # Coordinadora: Solo casos pendientes de entrevista (sin importar asignación)
            filtros = Q(estado='pendiente_entrevista')
        elif rol_nombre == ROL_ASESORA_TECNICA:
            # Asesora Técnica: Casos pendientes de formulación (que debe formular)
            filtros = Q(estado='pendiente_formulacion')
        elif rol_nombre == ROL_ASESOR:
            # Asesor Pedagógico: Casos pendientes de preaprobación
            filtros = Q(estado='pendiente_preaprobacion')
        elif rol_nombre == ROL_DIRECTOR:
            # Director: Casos pendientes de aprobación
            filtros = Q(estado='pendiente_aprobacion')

    # 3. Filtro por estado explícito (si se proporciona)
    # Si tiene_todos=True: El estado seleccionado es el único filtro (reemplaza el filtro por rol)
    # Si tiene_todos=False: El estado se combina con el filtro por rol (si existe)
    if tiene_estado_explicito:
        if tiene_todos:
            # Si quiere ver todos los casos, el estado seleccionado es el único filtro
            filtros = Q(estado=q_estado)
        elif aplicar_filtro_por_rol and filtros:
            # Si tiene filtro por rol activo, combinar con el estado seleccionado
            # Nota: Esto puede resultar en 0 resultados si el estado no coincide con el rol
            filtros &= Q(estado=q_estado)
        else:
            # Si no hay filtro por rol (admin o sin rol), usar solo el estado
            filtros = Q(estado=q_estado)

    # 4. Filtros de búsqueda (se aplican además del filtro por defecto o estado seleccionado)
    if q_nombre:
        filtros_busqueda &= (
            Q(estudiantes__nombres__icontains=q_nombre) | 
            Q(estudiantes__apellidos__icontains=q_nombre) |
            Q(estudiantes__rut__icontains=q_nombre)
        )

    if q_fecha:
        try:
            fecha_obj = datetime.strptime(q_fecha, '%Y-%m-%d').date()
            filtros_busqueda &= Q(created_at__date=fecha_obj)
        except ValueError:
            messages.error(request, "Formato de fecha inválido.")

    if q_ajuste:
        filtros_busqueda &= Q(ajusteasignado__ajuste_razonable__categorias_ajustes__id=q_ajuste)
    
    # 5. Combinar filtros base con filtros de búsqueda
    if filtros_busqueda:
        if filtros:  # Si hay filtro base (por defecto o estado), combinarlo con búsqueda
            filtros &= filtros_busqueda
        else:  # Si no hay filtro base, usar solo los de búsqueda
            filtros = filtros_busqueda
    
    # 6. Aplicar filtros
    # Aplicar filtros si existen
    if filtros:
        solicitudes_list = solicitudes_list.filter(filtros)
    # Si no hay filtros (solo para Admin con tiene_todos=True), mostrar todos los casos sin filtrar

    categorias_ajustes = CategoriasAjustes.objects.all().order_by('nombre_categoria')

    # Obtener opciones de estado para el filtro
    estados_disponibles = Solicitudes.ESTADO_CHOICES

    context = {
        'solicitudes': solicitudes_list,
        'total_casos': solicitudes_list.count(),
        'categorias_ajustes': categorias_ajustes,
        'estados_disponibles': estados_disponibles,
        'filtros_aplicados': {
            'q_nombre': q_nombre,
            'q_fecha': q_fecha,
            'q_ajuste': q_ajuste,
            'q_estado': q_estado,
        },
        'rol_usuario': rol_nombre,
        'mostrando_todos': tiene_todos
    }
    
    return render(request, 'SIAPE/casos_generales.html', context)

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
    solicitudes_sin_asignar = Solicitudes.objects.filter(
        asesor_pedagogico_asignado__isnull=True,
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

# --- Vistas de Gestión de Usuarios y Roles ---

def _check_admin_permission(request):
    """Función helper para verificar permisos de admin."""
    rol = None
    if hasattr(request.user, 'perfil') and request.user.perfil.rol:
        rol = request.user.perfil.rol.nombre_rol
    
    if not request.user.is_superuser and rol != ROL_ADMIN:
        return False
    return True

@login_required
def gestion_usuarios_admin(request):
    """
    Página para que el Admin vea y gestione usuarios y roles.
    """
    if not _check_admin_permission(request):
        return redirect('home')

    perfiles = PerfilUsuario.objects.select_related(
        'usuario', 
        'rol', 
        'area'
    ).all().order_by('usuario__first_name')
    
    roles_disponibles = Roles.objects.all()
    areas_disponibles = Areas.objects.all()
    roles_list = Roles.objects.all().order_by('nombre_rol')

    context = {
        'perfiles': perfiles,
        'roles_disponibles': roles_disponibles,
        'areas_disponibles': areas_disponibles,
        'roles_list': roles_list, 
    }
    
    return render(request, 'SIAPE/gestion_usuarios_admin.html', context)

@login_required
def agregar_usuario_admin(request):
    if not _check_admin_permission(request):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('gestion_usuarios_admin')

    if request.method == 'POST':
        email = request.POST.get('email')
        rut = request.POST.get('rut')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        rol_id = request.POST.get('rol_id')
        area_id = request.POST.get('area_id')

        try:
            if Usuario.objects.filter(Q(email=email) | Q(rut=rut)).exists():
                messages.error(request, f'Error: Ya existe un usuario con ese Email o RUT.')
                return redirect('gestion_usuarios_admin')
            
            rol_obj = get_object_or_404(Roles, id=rol_id)
            area_obj = None
            if area_id:
                area_obj = get_object_or_404(Areas, id=area_id)
                
            nuevo_usuario = Usuario.objects.create_user(
                email=email,
                password=password,
                rut=rut,
                first_name=first_name,
                last_name=last_name
            )
            
            PerfilUsuario.objects.create(
                usuario=nuevo_usuario,
                rol=rol_obj,
                area=area_obj
            )
            messages.success(request, f'Usuario {email} creado y asignado con el rol de {rol_obj.nombre_rol}.')
            
        except Exception as e:
            messages.error(request, f'Error al crear el usuario: {str(e)}')
    
    return redirect('gestion_usuarios_admin')


@login_required
def editar_usuario_admin(request, perfil_id):
    if not _check_admin_permission(request):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('gestion_usuarios_admin')

    if request.method == 'POST':
        try:
            perfil = get_object_or_404(PerfilUsuario.objects.select_related('usuario'), id=perfil_id)
            usuario = perfil.usuario
            
            rut = request.POST.get('rut')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            password = request.POST.get('password') 
            
            nuevo_rol_id = request.POST.get('rol_id')
            nuevo_area_id = request.POST.get('area_id')

            if rut != usuario.rut and Usuario.objects.filter(rut=rut).exclude(id=usuario.id).exists():
                messages.error(request, f'Error: El RUT "{rut}" ya está en uso por otro usuario.')
                return redirect('gestion_usuarios_admin')
            
            usuario.first_name = first_name
            usuario.last_name = last_name
            usuario.rut = rut
            
            if password:
                usuario.set_password(password)
            usuario.save()
            
            rol_obj = get_object_or_404(Roles, id=nuevo_rol_id)
            perfil.rol = rol_obj
            
            if nuevo_area_id:
                perfil.area = get_object_or_404(Areas, id=nuevo_area_id)
            else:
                 perfil.area = None
            perfil.save()
            
            messages.success(request, f'Se actualizó correctamente al usuario {usuario.email}.')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el usuario: {str(e)}')
            
    return redirect('gestion_usuarios_admin')

@login_required
def gestion_institucional_admin(request):
    if not _check_admin_permission(request):
        return redirect('home')
    carreras = Carreras.objects.select_related('director__usuario', 'area').all().order_by('nombre')
    asignaturas = Asignaturas.objects.select_related('carreras', 'docente__usuario').all().order_by('nombre')
    areas = Areas.objects.all().order_by('nombre')
    directores = PerfilUsuario.objects.select_related('usuario').filter(rol__nombre_rol=ROL_DIRECTOR).order_by('usuario__first_name')
    docentes = PerfilUsuario.objects.select_related('usuario').filter(rol__nombre_rol=ROL_DOCENTE).order_by('usuario__first_name')
    context = {
        'carreras_list': carreras,
        'asignaturas_list': asignaturas,
        'areas_list': areas,
        'directores_list': directores,
        'docentes_list': docentes,
    }
    return render(request, 'SIAPE/gestion_institucional_admin.html', context)
@login_required
def agregar_rol_admin(request):
    if not _check_admin_permission(request):
        messages.error(request, 'No tienes permisos.')
        return redirect('gestion_usuarios_admin')
    if request.method == 'POST':
        nombre_rol = request.POST.get('nombre_rol')
        if nombre_rol and not Roles.objects.filter(nombre_rol=nombre_rol).exists():
            Roles.objects.create(nombre_rol=nombre_rol)
            messages.success(request, f'Rol "{nombre_rol}" creado exitosamente.')
        else:
            messages.error(request, 'El nombre del rol no puede estar vacío o ya existe.')
    return redirect('gestion_usuarios_admin')
@login_required
def editar_rol_admin(request, rol_id):
    if not _check_admin_permission(request):
        messages.error(request, 'No tienes permisos.')
        return redirect('gestion_usuarios_admin')
    rol = get_object_or_404(Roles, id=rol_id)
    if request.method == 'POST':
        nombre_rol = request.POST.get('nombre_rol')
        if nombre_rol and not Roles.objects.filter(nombre_rol=nombre_rol).exclude(id=rol_id).exists():
            rol.nombre_rol = nombre_rol
            rol.save()
            messages.success(request, f'Rol actualizado a "{nombre_rol}".')
        else:
            messages.error(request, 'El nombre del rol no puede estar vacío o ya existe.')
    return redirect('gestion_usuarios_admin')
@login_required
def agregar_carrera_admin(request):
    if not _check_admin_permission(request):
        messages.error(request, 'No tienes permisos.')
        return redirect('gestion_institucional_admin')
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            area_id = request.POST.get('area_id')
            director_id = request.POST.get('director_id')
            area = get_object_or_404(Areas, id=area_id)
            director = None
            if director_id:
                director = get_object_or_404(PerfilUsuario, id=director_id, rol__nombre_rol=ROL_DIRECTOR)
            Carreras.objects.create(nombre=nombre, area=area, director=director)
            messages.success(request, f'Carrera "{nombre}" creada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al crear la carrera: {str(e)}')
    return redirect('gestion_institucional_admin')
@login_required
def editar_carrera_admin(request, carrera_id):
    if not _check_admin_permission(request):
        messages.error(request, 'No tienes permisos.')
        return redirect('gestion_institucional_admin')
    carrera = get_object_or_404(Carreras, id=carrera_id)
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            area_id = request.POST.get('area_id')
            director_id = request.POST.get('director_id')
            area = get_object_or_404(Areas, id=area_id)
            director = None
            if director_id:
                director = get_object_or_404(PerfilUsuario, id=director_id, rol__nombre_rol=ROL_DIRECTOR)
            carrera.nombre = nombre
            carrera.area = area
            carrera.director = director
            carrera.save()
            messages.success(request, f'Carrera "{nombre}" actualizada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al actualizar la carrera: {str(e)}')
    return redirect('gestion_institucional_admin')
@login_required
def agregar_asignatura_admin(request):
    if not _check_admin_permission(request):
        messages.error(request, 'No tienes permisos.')
        return redirect('gestion_institucional_admin')
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            seccion = request.POST.get('seccion')
            carrera_id = request.POST.get('carrera_id')
            docente_id = request.POST.get('docente_id')
            carrera = get_object_or_404(Carreras, id=carrera_id)
            docente = get_object_or_404(PerfilUsuario, id=docente_id, rol__nombre_rol=ROL_DOCENTE)
            Asignaturas.objects.create(nombre=nombre, seccion=seccion, carreras=carrera, docente=docente)
            messages.success(request, f'Asignatura "{nombre} - {seccion}" creada y asignada a {carrera.nombre}.')
        except Exception as e:
            messages.error(request, f'Error al crear la asignatura: {str(e)}')
    return redirect('gestion_institucional_admin')
@login_required
def editar_asignatura_admin(request, asignatura_id):
    if not _check_admin_permission(request):
        messages.error(request, 'No tienes permisos.')
        return redirect('gestion_institucional_admin')
    asignatura = get_object_or_404(Asignaturas, id=asignatura_id)
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            seccion = request.POST.get('seccion')
            carrera_id = request.POST.get('carrera_id')
            docente_id = request.POST.get('docente_id')
            carrera = get_object_or_404(Carreras, id=carrera_id)
            docente = get_object_or_404(PerfilUsuario, id=docente_id, rol__nombre_rol=ROL_DOCENTE)
            asignatura.nombre = nombre
            asignatura.seccion = seccion
            asignatura.carreras = carrera
            asignatura.docente = docente
            asignatura.save()
            messages.success(request, f'Asignatura "{nombre} - {seccion}" actualizada.')
        except Exception as e:
            messages.error(request, f'Error al actualizar la asignatura: {str(e)}')
    return redirect('gestion_institucional_admin')

# --- VISTA COORDINADORA DE INCLUSIÓN ---
logger = logging.getLogger(__name__)

@login_required
def dashboard_coordinadora(request):
    """
    Dashboard principal para la Coordinadora de Inclusión.
    Muestra KPIs y la lista de citas para el día de hoy.
    """
    
    # 1. --- Verificación de Permisos ---
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_COORDINADORA:
            # Si no es coordinadora, redirige a home
            messages.error(request, 'No tienes permisos para acceder a este panel.')
            return redirect('home')
    except AttributeError:
        # Si el usuario no tiene perfil o rol
        logger.warning(f"Usuario {request.user.email} sin perfil/rol intentó acceder al dashboard de coordinadora.")
        return redirect('home')

    # 2. --- Configuración de Fechas ---
    now = timezone.localtime(timezone.now())
    today = now.date()
    start_of_today = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    end_of_today = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # Cálculo de la semana (Lunes a Domingo)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    start_of_week_dt = timezone.make_aware(datetime.combine(start_of_week, datetime.min.time()))
    end_of_week_dt = timezone.make_aware(datetime.combine(end_of_week, datetime.max.time()))

    # 3. --- Obtener Datos para KPIs ---
    
    # Base de entrevistas para todas las coordinadoras (filtramos por rol)
    # Como todas las coordinadoras deben ver todas las entrevistas del rol
    todas_las_coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
    entrevistas_coordinadora = Entrevistas.objects.filter(
        coordinadora__in=todas_las_coordinadoras
    ).exclude(coordinadora__isnull=True)
    
    # KPI 1: Citas del día (Query que usaremos también para la lista)
    citas_hoy_qs = entrevistas_coordinadora.filter(
        fecha_entrevista__range=(start_of_today, end_of_today)
    ).select_related(
        'solicitudes', 
        'solicitudes__estudiantes', 
        'solicitudes__estudiantes__carreras'
    ).order_by('fecha_entrevista')
    
    kpi_citas_hoy = citas_hoy_qs.count()

    # KPI 2: Citas canceladas (Historial total de esta coordinadora)
    kpi_citas_canceladas = entrevistas_coordinadora.filter(
        estado='cancelada'
    ).count()

    # KPI 3: Solicitudes pendientes de entrevista
    # Contamos las entrevistas 'pendientes' de esta coordinadora
    # que correspondan a solicitudes 'pendientes_entrevista'
    kpi_solicitudes_pendientes = entrevistas_coordinadora.filter(
        estado='pendiente',
        solicitudes__estado='pendiente_entrevista'
    ).count()
    
    # KPI 4: Citas de la semana
    kpi_citas_semana = entrevistas_coordinadora.filter(
        fecha_entrevista__range=(start_of_week_dt, end_of_week_dt),
        estado__in=['pendiente', 'realizada'] # Contamos solo las programadas o hechas
    ).count()

    # 4. --- Preparar Contexto ---
    context = {
        'nombre_usuario': request.user.first_name,
        'kpis': {
            'citas_hoy': kpi_citas_hoy,
            'citas_canceladas': kpi_citas_canceladas,
            'solicitudes_pendientes': kpi_solicitudes_pendientes,
            'citas_semana': kpi_citas_semana,
        },
        'citas_del_dia_list': citas_hoy_qs, # Esta es la lista para la sección principal
    }

    # 5. --- Renderizar Template ---
    return render(request, 'SIAPE/dashboard_coordinadora.html', context)

@login_required
def detalle_casos_coordinadora(request, solicitud_id):
    """
    Muestra el detalle de un caso específico.
    Accesible por todos los roles de asesoría.
    """
    
    # 1. --- Verificación de Permisos (Ampliado) ---
    try:
        perfil = request.user.perfil
        ROLES_PERMITIDOS = [
            ROL_COORDINADORA,
            ROL_ASESORA_TECNICA,
            ROL_ASESOR,
            ROL_DIRECTOR,
            ROL_ADMIN
        ]
        if perfil.rol.nombre_rol not in ROLES_PERMITIDOS:
            messages.error(request, 'No tienes permisos para ver esta página.')
            return redirect('home')
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')

    # 2. --- Obtener Datos del Caso ---
    solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
    estudiante = solicitud.estudiantes
    
    # Obtenemos todos los ajustes asignados
    ajustes = AjusteAsignado.objects.filter(solicitudes=solicitud).select_related(
        'ajuste_razonable', 
        'ajuste_razonable__categorias_ajustes'
    )
    
    # Obtenemos todas las evidencias
    evidencias = Evidencias.objects.filter(solicitudes=solicitud)
    
    # Obtenemos TODAS las entrevistas relacionadas con esta solicitud
    entrevistas = Entrevistas.objects.filter(solicitudes=solicitud).order_by('-fecha_entrevista')
    
    # Obtenemos las categorías para el modal (si queremos añadir ajustes)
    categorias_ajustes = CategoriasAjustes.objects.all().order_by('nombre_categoria')

    # 3. --- Determinar acciones permitidas según el rol ---
    rol_nombre = perfil.rol.nombre_rol if perfil else None
    # Permisos de edición: Coordinadora, Asesora Técnica, Asesor Pedagógico y Admin pueden editar
    puede_editar_descripcion = rol_nombre in [ROL_COORDINADORA, ROL_ASESORA_TECNICA, ROL_ASESOR, ROL_ADMIN]
    puede_agendar_cita = rol_nombre == ROL_COORDINADORA
    
    # Acciones de Coordinadora
    puede_enviar_asesor_tecnico = rol_nombre == ROL_COORDINADORA and solicitud.estado == 'pendiente_entrevista'
    
    # Acciones de Asesora Técnica Pedagógica
    puede_formular_ajustes = rol_nombre == ROL_ASESORA_TECNICA and solicitud.estado == 'pendiente_formulacion'
    puede_enviar_asesor_pedagogico = rol_nombre == ROL_ASESORA_TECNICA and solicitud.estado == 'pendiente_formulacion'
    puede_devolver_a_coordinadora = rol_nombre == ROL_ASESORA_TECNICA and solicitud.estado == 'pendiente_formulacion'
    
    # Acciones de Asesor Pedagógico
    puede_enviar_a_director = rol_nombre == ROL_ASESOR and solicitud.estado == 'pendiente_preaprobacion'
    puede_devolver_a_asesor_tecnico = rol_nombre == ROL_ASESOR and solicitud.estado == 'pendiente_preaprobacion'
    
    # Acciones de Director
    puede_aprobar = rol_nombre == ROL_DIRECTOR and solicitud.estado == 'pendiente_aprobacion'
    puede_rechazar = rol_nombre == ROL_DIRECTOR and solicitud.estado == 'pendiente_aprobacion'

    context = {
        'solicitud': solicitud,
        'estudiante': estudiante,
        'ajustes_asignados': ajustes,
        'evidencias': evidencias,
        'entrevistas_list': entrevistas,
        'categorias_ajustes': categorias_ajustes, # Para el modal
        'rol_usuario': rol_nombre,
        'puede_editar_descripcion': puede_editar_descripcion,
        'puede_agendar_cita': puede_agendar_cita,
        'puede_enviar_asesor_tecnico': puede_enviar_asesor_tecnico,
        'puede_formular_ajustes': puede_formular_ajustes,
        'puede_enviar_asesor_pedagogico': puede_enviar_asesor_pedagogico,
        'puede_devolver_a_coordinadora': puede_devolver_a_coordinadora,
        'puede_enviar_a_director': puede_enviar_a_director,
        'puede_devolver_a_asesor_tecnico': puede_devolver_a_asesor_tecnico,
        'puede_aprobar': puede_aprobar,
        'puede_rechazar': puede_rechazar,
    }
    
    return render(request, 'SIAPE/detalle_casos_coordinadora.html', context)

@login_required
def detalle_casos_asesor_tecnico(request, solicitud_id):
    """
    Vista para mostrar el detalle de un caso para la Asesora Técnica Pedagógica.
    Es un wrapper que redirige a la misma vista pero con un contexto diferente.
    """
    # Verificar que el usuario es Asesora Técnica
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_ASESORA_TECNICA:
            messages.error(request, 'No tienes permisos para acceder a esta página.')
            return redirect('home')
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')
        perfil = None
    
    # Llamar a la misma función pero con el contexto específico
    return detalle_casos_coordinadora(request, solicitud_id)

@require_POST
@login_required
def formular_ajuste_asesor_tecnico(request, solicitud_id):
    """
    Vista para que la Asesora Técnica Pedagógica pueda crear y asignar ajustes a un caso.
    """
    # 1. --- Verificación de Permisos ---
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_ASESORA_TECNICA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('home')
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')
        perfil = None

    # 2. --- Obtener la Solicitud ---
    solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
    
    # Verificar que el caso está en el estado correcto
    if solicitud.estado != 'pendiente_formulacion':
        messages.error(request, 'Este caso no está en estado de formulación.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)

    # 3. --- Obtener Datos del Formulario ---
    descripcion = request.POST.get('descripcion', '').strip()
    categoria_id = request.POST.get('categoria_id', '')
    nueva_categoria = request.POST.get('nueva_categoria', '').strip()

    # 4. --- Validaciones ---
    if not descripcion:
        messages.error(request, 'La descripción del ajuste es requerida.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)

    # Verificar si se seleccionó "nueva" o si hay una categoría seleccionada
    crear_nueva_categoria = categoria_id == 'nueva' or (not categoria_id and nueva_categoria)
    
    if not categoria_id and not nueva_categoria:
        messages.error(request, 'Debe seleccionar una categoría o crear una nueva.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)

    if categoria_id and categoria_id != 'nueva' and nueva_categoria:
        messages.error(request, 'No puede seleccionar una categoría existente y crear una nueva a la vez.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)

    if crear_nueva_categoria and not nueva_categoria:
        messages.error(request, 'Debe proporcionar el nombre de la nueva categoría.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)

    try:
        # 5. --- Obtener o Crear Categoría ---
        if crear_nueva_categoria:
            if not nueva_categoria:
                messages.error(request, 'Debe proporcionar el nombre de la nueva categoría.')
                return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)
            categoria, created = CategoriasAjustes.objects.get_or_create(
                nombre_categoria=nueva_categoria.strip().capitalize()
            )
            if created:
                messages.info(request, f'Categoría "{categoria.nombre_categoria}" creada exitosamente.')
        else:
            if not categoria_id or categoria_id == 'nueva':
                messages.error(request, 'Debe seleccionar una categoría válida.')
                return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)
            categoria = get_object_or_404(CategoriasAjustes, id=categoria_id)

        # 6. --- Crear Ajuste Razonable ---
        ajuste_razonable = AjusteRazonable.objects.create(
            descripcion=descripcion,
            categorias_ajustes=categoria
        )

        # 7. --- Asignar Ajuste a la Solicitud ---
        AjusteAsignado.objects.create(
            ajuste_razonable=ajuste_razonable,
            solicitudes=solicitud
        )

        # 8. --- Asignar Asesora Técnica al caso si no está asignada ---
        if not solicitud.asesor_tecnico_asignado:
            solicitud.asesor_tecnico_asignado = perfil
            solicitud.save()

        messages.success(request, 'Ajuste formulado y asignado exitosamente.')

    except Exception as e:
        logger.error(f"Error al formular ajuste: {str(e)}")
        messages.error(request, f'Error al formular el ajuste: {str(e)}')

    # 9. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)

@require_POST
@login_required
def enviar_a_asesor_tecnico(request, solicitud_id):
    """
    Vista para que la Coordinadora envíe el caso a la Asesora Técnica Pedagógica.
    Cambia el estado del caso de 'pendiente_entrevista' a 'pendiente_formulacion'.
    """
    # 1. --- Verificación de Permisos ---
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('home')
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')
        perfil = None

    # 2. --- Obtener la Solicitud ---
    solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
    
    # 3. --- Verificar que el caso está en el estado correcto ---
    if solicitud.estado != 'pendiente_entrevista':
        messages.error(request, 'Este caso no está en estado de entrevista. Solo se pueden enviar casos pendientes de entrevista.')
        return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso ---
        solicitud.estado = 'pendiente_formulacion'
        solicitud.save()
        
        messages.success(request, 'Caso enviado a la Asesora Técnica Pedagógica exitosamente. El caso ahora está pendiente de formulación.')
        
    except Exception as e:
        logger.error(f"Error al enviar caso a asesora técnica: {str(e)}")
        messages.error(request, f'Error al enviar el caso: {str(e)}')
    
    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)

@require_POST
@login_required
def enviar_a_asesor_pedagogico(request, solicitud_id):
    """
    Vista para que la Asesora Técnica Pedagógica envíe el caso al siguiente estado
    (pendiente_preaprobacion) después de formular los ajustes.
    """
    # 1. --- Verificación de Permisos ---
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_ASESORA_TECNICA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('home')
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')

    # 2. --- Obtener la Solicitud ---
    solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
    
    # Verificar que el caso está en el estado correcto
    if solicitud.estado != 'pendiente_formulacion':
        messages.error(request, 'Este caso no está en estado de formulación.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)

    # 3. --- Verificar que hay ajustes asignados ---
    ajustes_count = AjusteAsignado.objects.filter(solicitudes=solicitud).count()
    if ajustes_count == 0:
        messages.error(request, 'Debe formular al menos un ajuste antes de enviar el caso al Asesor Pedagógico.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)

    try:
        # 4. --- Cambiar el estado del caso ---
        solicitud.estado = 'pendiente_preaprobacion'
        solicitud.save()
        
        messages.success(request, 'Caso enviado al Asesor Pedagógico exitosamente. El caso ahora está pendiente de preaprobación.')
        
    except Exception as e:
        logger.error(f"Error al enviar caso a asesor pedagógico: {str(e)}")
        messages.error(request, f'Error al enviar el caso: {str(e)}')

    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)

@require_POST
@login_required
def devolver_a_coordinadora(request, solicitud_id):
    """
    Vista para que la Asesora Técnica Pedagógica devuelva el caso a la Coordinadora.
    Cambia el estado del caso de 'pendiente_formulacion' a 'pendiente_entrevista'.
    """
    # 1. --- Verificación de Permisos ---
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_ASESORA_TECNICA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('home')
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')
        perfil = None

    # 2. --- Obtener la Solicitud ---
    solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
    
    # 3. --- Verificar que el caso está en el estado correcto ---
    if solicitud.estado != 'pendiente_formulacion':
        messages.error(request, 'Este caso no está en estado de formulación. Solo se pueden devolver casos pendientes de formulación.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso ---
        solicitud.estado = 'pendiente_entrevista'
        solicitud.save()
        
        messages.success(request, 'Caso devuelto a la Coordinadora exitosamente. El caso ahora está pendiente de entrevista.')
        
    except Exception as e:
        logger.error(f"Error al devolver caso a coordinadora: {str(e)}")
        messages.error(request, f'Error al devolver el caso: {str(e)}')
    
    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)

@require_POST
@login_required
def enviar_a_director(request, solicitud_id):
    """
    Vista para que el Asesor Pedagógico envíe el caso al Director.
    Cambia el estado del caso de 'pendiente_preaprobacion' a 'pendiente_aprobacion'.
    """
    # 1. --- Verificación de Permisos ---
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('home')
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')
        perfil = None

    # 2. --- Obtener la Solicitud ---
    solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
    
    # 3. --- Verificar que el caso está en el estado correcto ---
    if solicitud.estado != 'pendiente_preaprobacion':
        messages.error(request, 'Este caso no está en estado de preaprobación. Solo se pueden enviar casos pendientes de preaprobación.')
        return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso ---
        solicitud.estado = 'pendiente_aprobacion'
        solicitud.save()
        
        messages.success(request, 'Caso enviado al Director exitosamente. El caso ahora está pendiente de aprobación.')
        
    except Exception as e:
        logger.error(f"Error al enviar caso a director: {str(e)}")
        messages.error(request, f'Error al enviar el caso: {str(e)}')
    
    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)

@require_POST
@login_required
def devolver_a_asesor_tecnico(request, solicitud_id):
    """
    Vista para que el Asesor Pedagógico devuelva el caso al Asesor Técnico Pedagógico.
    Cambia el estado del caso de 'pendiente_preaprobacion' a 'pendiente_formulacion'.
    """
    # 1. --- Verificación de Permisos ---
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('home')
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')
        perfil = None

    # 2. --- Obtener la Solicitud ---
    solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
    
    # 3. --- Verificar que el caso está en el estado correcto ---
    if solicitud.estado != 'pendiente_preaprobacion':
        messages.error(request, 'Este caso no está en estado de preaprobación. Solo se pueden devolver casos pendientes de preaprobación.')
        return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso ---
        solicitud.estado = 'pendiente_formulacion'
        solicitud.save()
        
        messages.success(request, 'Caso devuelto al Asesor Técnico Pedagógico exitosamente. El caso ahora está pendiente de formulación.')
        
    except Exception as e:
        logger.error(f"Error al devolver caso a asesor técnico: {str(e)}")
        messages.error(request, f'Error al devolver el caso: {str(e)}')
    
    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)

@require_POST
@login_required
def aprobar_caso(request, solicitud_id):
    """
    Vista para que el Director apruebe el caso.
    Cambia el estado del caso de 'pendiente_aprobacion' a 'aprobado'.
    """
    # 1. --- Verificación de Permisos ---
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_DIRECTOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('home')
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')
        perfil = None

    # 2. --- Obtener la Solicitud ---
    solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
    
    # 3. --- Verificar que el caso está en el estado correcto ---
    if solicitud.estado != 'pendiente_aprobacion':
        messages.error(request, 'Este caso no está en estado de aprobación. Solo se pueden aprobar casos pendientes de aprobación.')
        return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso ---
        solicitud.estado = 'aprobado'
        solicitud.save()
        
        messages.success(request, 'Caso aprobado exitosamente. El caso ha sido aprobado e informado.')
        
    except Exception as e:
        logger.error(f"Error al aprobar caso: {str(e)}")
        messages.error(request, f'Error al aprobar el caso: {str(e)}')
    
    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)

@require_POST
@login_required
def rechazar_caso(request, solicitud_id):
    """
    Vista para que el Director rechace el caso.
    Cambia el estado del caso de 'pendiente_aprobacion' a 'pendiente_preaprobacion' 
    (vuelve a Asesoría Pedagógica para evaluación de corrección).
    """
    # 1. --- Verificación de Permisos ---
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_DIRECTOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('home')
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')
        perfil = None

    # 2. --- Obtener la Solicitud ---
    solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
    
    # 3. --- Verificar que el caso está en el estado correcto ---
    if solicitud.estado != 'pendiente_aprobacion':
        messages.error(request, 'Este caso no está en estado de aprobación. Solo se pueden rechazar casos pendientes de aprobación.')
        return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso (vuelve a Asesoría Pedagógica) ---
        solicitud.estado = 'pendiente_preaprobacion'
        solicitud.save()
        
        messages.warning(request, 'Caso rechazado. El caso ha sido devuelto a Asesoría Pedagógica para evaluación de corrección o archivo.')
        
    except Exception as e:
        logger.error(f"Error al rechazar caso: {str(e)}")
        messages.error(request, f'Error al rechazar el caso: {str(e)}')
    
    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)

@require_POST # Solo permite esta vista vía POST
@login_required
def actualizar_descripcion_caso(request, solicitud_id):
    """
    Vista de acción para actualizar la descripción principal (el "caso")
    de una solicitud.
    """
    # 1. --- Verificación de Permisos (Ampliado) ---
    try:
        perfil = request.user.perfil
        ROLES_PERMITIDOS = [
            ROL_COORDINADORA,
            ROL_ASESORA_TECNICA,
            ROL_ASESOR,
            ROL_ADMIN
        ]
        if perfil.rol.nombre_rol not in ROLES_PERMITIDOS:
            messages.error(request, 'No tienes permisos para esta acción.')
            return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)
    except AttributeError:
        if not request.user.is_superuser:
            return redirect('home')

    # 2. --- Actualizar la Descripción ---
    solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
    nueva_descripcion = request.POST.get('descripcion_caso')
    
    if nueva_descripcion is not None:
        solicitud.descripcion = nueva_descripcion
        solicitud.save()
        messages.success(request, 'Descripción del caso actualizada correctamente.')
    else:
        messages.error(request, 'No se recibió la descripción.')
        
    # 3. --- Determinar la URL de redirección según el rol ---
    try:
        perfil = request.user.perfil
        rol_nombre = perfil.rol.nombre_rol if perfil else None
        if rol_nombre == ROL_ASESORA_TECNICA:
            return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)
        elif rol_nombre == ROL_COORDINADORA:
            return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)
        else:
            return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)
    except AttributeError:
        return redirect('detalle_casos_coordinadora', solicitud_id=solicitud_id)

@login_required
def panel_control_coordinadora(request):
    """
    Panel de control para la Coordinadora de Inclusión.
    Muestra citas (hoy, semana), calendario interactivo y acciones de cita.
    """
    try:
        if request.user.perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para acceder a este panel.')
            return redirect('home')
    except AttributeError:
        return redirect('home')
    
    perfil_coordinadora = request.user.perfil
    
    # 1. --- Definición de Fechas ---
    now = timezone.localtime(timezone.now())
    today = now.date()
    start_of_today = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    end_of_today = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    start_of_week = today - timedelta(days=today.weekday()) # Lunes
    end_of_week = start_of_week + timedelta(days=6) # Domingo
    start_of_week_dt = timezone.make_aware(datetime.combine(start_of_week, datetime.min.time()))
    end_of_week_dt = timezone.make_aware(datetime.combine(end_of_week, datetime.max.time()))

    # 2. --- Obtener Citas para Todas las Coordinadoras (Rol Completo) ---
    
    # Verificar que el perfil de la coordinadora existe
    if not perfil_coordinadora:
        messages.error(request, 'Error: No se pudo obtener el perfil de la coordinadora.')
        return redirect('home')
    
    # Base de entrevistas para todas las coordinadoras del rol
    # Todas las coordinadoras deben ver todas las entrevistas agendadas del rol
    todas_las_coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
    entrevistas_coordinadora = Entrevistas.objects.filter(
        coordinadora__in=todas_las_coordinadoras
    ).exclude(coordinadora__isnull=True).select_related('solicitudes', 'solicitudes__estudiantes')

    # A. Citas del Día
    citas_hoy_list = entrevistas_coordinadora.filter(
        fecha_entrevista__range=(start_of_today, end_of_today)
    ).order_by('fecha_entrevista')

    # B. Citas de la Semana (Próximas de esta semana)
    citas_semana_list = entrevistas_coordinadora.filter(
        fecha_entrevista__range=(now, end_of_week_dt),
        estado='pendiente'
    ).order_by('fecha_entrevista')

    # C. Citas Pendientes de Confirmar (para la sección de "asistencia")
    citas_pendientes_confirmar = entrevistas_coordinadora.filter(
        estado='pendiente',
        fecha_entrevista__lt=now # Citas que ya pasaron
    ).order_by('fecha_entrevista')

    # D. Historial de Citas Pasadas (de la semana actual)
    citas_pasadas_semana = entrevistas_coordinadora.filter(
        fecha_entrevista__lt=now, # Citas pasadas
        fecha_entrevista__gte=start_of_week_dt, # Pero dentro de esta semana
        estado__in=['realizada', 'no_asistio']
    ).order_by('-fecha_entrevista')
    
    # 3. --- Obtener Datos para el Calendario (de TODAS las coordinadoras) ---
    todas_las_coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
    todas_las_entrevistas = Entrevistas.objects.filter(
        coordinadora__in=todas_las_coordinadoras
    ).select_related('solicitudes', 'solicitudes__estudiantes', 'coordinadora').order_by('fecha_entrevista')
    
    fechas_con_citas = set()
    citas_data = []
    
    for entrevista in todas_las_entrevistas:
        fecha_str = timezone.localtime(entrevista.fecha_entrevista).strftime('%Y-%m-%d')
        hora_str = timezone.localtime(entrevista.fecha_entrevista).strftime('%H:%M')
        fechas_con_citas.add(fecha_str)
        
        citas_data.append({
            'fecha': fecha_str,
            'hora': hora_str,
            'estudiante': f"{entrevista.solicitudes.estudiantes.nombres} {entrevista.solicitudes.estudiantes.apellidos}",
            'asunto': entrevista.solicitudes.asunto,
            'estado': entrevista.get_estado_display(),
            'estado_key': entrevista.estado,
        })
    
    fechas_citas_json = json.dumps(list(fechas_con_citas))
    citas_data_json = json.dumps(citas_data)
    
    # 4. --- Datos para Modales ---
    categorias_ajustes = CategoriasAjustes.objects.all().order_by('nombre_categoria')
    
    context = {
        'citas_hoy_list': citas_hoy_list,
        'citas_semana_list': citas_semana_list,
        'fechas_citas_json': fechas_citas_json,
        'citas_data_json': citas_data_json,
        'citas_pendientes_confirmar': citas_pendientes_confirmar,
        'citas_pasadas_semana_list': citas_pasadas_semana,
        'categorias_ajustes': categorias_ajustes,
        
        # Necesitaremos estos datos que antes estaban en esta vista pero
        # que ahora no estamos consultando. Los dejamos vacíos por ahora
        # para no romper los modales.
        'casos_disponibles': Solicitudes.objects.none(),
        'casos_con_ajustes': [],
        'proximas_citas': [], # Reemplazado por citas_semana_list
        'citas_realizadas': [], # Reemplazado por citas_pasadas_semana_list
        'citas_no_asistio': [], # Reemplazado por citas_pasadas_semana_list
    }
    
    return render(request, 'SIAPE/panel_control_coordinadora.html', context)

@login_required
def confirmar_cita_coordinadora(request, entrevista_id):
    """
    Permite a la Coordinadora confirmar la asistencia (realizada o no asistió) 
    de una entrevista que ella gestiona.
    """
    # 1. Verificar Permiso
    try:
        if request.user.perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_coordinadora')
    except AttributeError:
        return redirect('home')

    # 2. Lógica de la Acción
    if request.method == 'POST':
        accion = request.POST.get('accion')
        notas_adicionales = request.POST.get('notas_adicionales', '')
        try:
            # Cualquier coordinadora del rol puede confirmar cualquier entrevista del rol
            todas_las_coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
            entrevista = get_object_or_404(Entrevistas, id=entrevista_id, coordinadora__in=todas_las_coordinadoras)
            
            if accion in ['realizada', 'no_asistio']:
                entrevista.estado = accion
                if notas_adicionales:
                    if entrevista.notas:
                        entrevista.notas += f"\n\n[Confirmación - {timezone.now().strftime('%d/%m/%Y %H:%M')}]: {notas_adicionales}"
                    else:
                        entrevista.notas = f"[Confirmación - {timezone.now().strftime('%d/%m/%Y %H:%M')}]: {notas_adicionales}"
                entrevista.save()
                
                if accion == 'realizada':
                    messages.success(request, 'Cita marcada como realizada.')
                else:
                    messages.info(request, 'Cita marcada como no asistió. Puedes reagendarla.')
            else:
                messages.error(request, 'Acción no válida.')
        except Exception as e:
            messages.error(request, f'Error al confirmar la cita: {str(e)}')
            
    # 3. Redirigir siempre al panel de control
    return redirect('panel_control_coordinadora')


@login_required
def editar_notas_cita_coordinadora(request, entrevista_id):
    """
    Permite a la Coordinadora editar las notas de una cita que ella gestiona.
    """
    # 1. Verificar Permiso
    try:
        if request.user.perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_coordinadora')
    except AttributeError:
        return redirect('home')

    # 2. Lógica de la Acción
    if request.method == 'POST':
        nuevas_notas = request.POST.get('notas', '')
        try:
            # Cualquier coordinadora del rol puede editar notas de cualquier entrevista del rol
            todas_las_coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
            entrevista = get_object_or_404(Entrevistas, id=entrevista_id, coordinadora__in=todas_las_coordinadoras)
            entrevista.notas = nuevas_notas
            entrevista.save()
            messages.success(request, 'Notas actualizadas correctamente.')
        except Exception as e:
            messages.error(request, f'Error al actualizar las notas: {str(e)}')
            
    # 3. Redirigir
    return redirect('panel_control_coordinadora')


@login_required
def reagendar_cita_coordinadora(request, entrevista_id):
    """
    Permite a la Coordinadora reagendar una cita (usualmente una que 'no asistió').
    Crea una nueva entrevista y actualiza la antigua.
    """
    # 1. Verificar Permiso
    try:
        if request.user.perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_coordinadora')
    except AttributeError:
        return redirect('home')

    # 2. Lógica de la Acción
    if request.method == 'POST':
        nueva_fecha_str = request.POST.get('nueva_fecha_entrevista')
        nueva_modalidad = request.POST.get('nueva_modalidad', '')
        notas_reagendamiento = request.POST.get('notas_reagendamiento', '')
        try:
            # Cualquier coordinadora del rol puede reagendar cualquier entrevista del rol
            todas_las_coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
            entrevista_original = get_object_or_404(Entrevistas, id=entrevista_id, coordinadora__in=todas_las_coordinadoras)
            
            nueva_fecha = datetime.strptime(nueva_fecha_str, '%Y-%m-%dT%H:%M')
            nueva_fecha = timezone.make_aware(nueva_fecha)
            
            # Crear la nueva cita (mantenemos la misma coordinadora asignada originalmente)
            nueva_entrevista = Entrevistas.objects.create(
                solicitudes=entrevista_original.solicitudes, 
                coordinadora=entrevista_original.coordinadora, # Mantiene la coordinadora original
                fecha_entrevista=nueva_fecha, 
                modalidad=nueva_modalidad or entrevista_original.modalidad,
                notas=f"Reagendada desde cita del {entrevista_original.fecha_entrevista.strftime('%d/%m/%Y %H:%M')}. {notas_reagendamiento}" if notas_reagendamiento else f"Reagendada desde cita del {entrevista_original.fecha_entrevista.strftime('%d/%m/%Y %H:%M')}.",
                estado='pendiente' # La nueva cita está pendiente
            )
            
            # Actualizar la cita original a 'no asistió' si estaba 'pendiente'
            if entrevista_original.estado == 'pendiente':
                entrevista_original.estado = 'no_asistio' 
            # Si ya era 'no_asistio', se mantiene así.
            entrevista_original.save()
            
            messages.success(request, 'Cita reagendada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al reagendar la cita: {str(e)}')
            
    # 3. Redirigir
    return redirect('panel_control_coordinadora')


# --- VISTA ASESOR PEDAGÓGICO ---
@login_required
def dashboard_asesor(request):
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            return redirect('home')
    except AttributeError:
        return redirect('home')
    total_solicitudes = Solicitudes.objects.count()
    casos_resueltos = Solicitudes.objects.filter(estado='aprobado', ajusteasignado__isnull=False).distinct().count()
    casos_en_proceso = Solicitudes.objects.filter(estado='en_proceso').count()
    context = {
        'nombre_usuario': request.user.first_name, 'total_solicitudes': total_solicitudes, 'casos_resueltos': casos_resueltos,
        'casos_en_proceso': casos_en_proceso,
    }
    return render(request, 'SIAPE/dashboard_asesor.html', context)

# ----------------------------------------------------
#                VISTA DIRECTOR DE CARRERA
# ----------------------------------------------------

@login_required
def dashboard_director(request):
    try:
        if request.user.perfil.rol.nombre_rol != ROL_DIRECTOR:
            return redirect('home')
    except AttributeError:
        return redirect('home')
    total_solicitudes = Solicitudes.objects.count()
    casos_resueltos = Solicitudes.objects.filter(estado='aprobado', ajusteasignado__isnull=False).distinct().count()
    casos_en_proceso = Solicitudes.objects.filter(estado='en_proceso').count()
    carreras = Carreras.objects.all() 
    context = {
        'nombre_usuario': request.user.first_name, 'total_solicitudes': total_solicitudes, 'casos_resueltos': casos_resueltos,
        'casos_en_proceso': casos_en_proceso, 'carreras': carreras, 
    }
    return render(request, 'SIAPE/dashboard_director.html', context)


# ----------------------------------------------------
#                VISTA ASESORA TÉCNICA PEDAGÓGICA
# ----------------------------------------------------

@login_required
def dashboard_asesor_técnico(request):
    """
    Dashboard principal para la Asesora Técnica Pedagógica.
    Muestra KPIs de casos pendientes de formulación y estadísticas.
    """
    
    # 1. --- Verificación de Permisos ---
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_ASESORA_TECNICA:
            messages.error(request, 'No tienes permisos para acceder a este panel.')
            return redirect('home')
    except AttributeError:
        logger.warning(f"Usuario {request.user.email} sin perfil/rol intentó acceder al dashboard de asesora técnica.")
        return redirect('home')

    # 2. --- Configuración de Fechas ---
    now = timezone.localtime(timezone.now())
    today = now.date()
    
    # Cálculo de la semana (Lunes a Domingo)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    start_of_week_dt = timezone.make_aware(datetime.combine(start_of_week, datetime.min.time()))
    end_of_week_dt = timezone.make_aware(datetime.combine(end_of_week, datetime.max.time()))
    
    # 3. --- Obtener Datos para KPIs ---
    
    # Base de solicitudes para todas las asesoras técnicas (filtramos por rol)
    todas_las_asesoras_tecnicas = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_ASESORA_TECNICA)
    
    # KPI 1: Casos nuevos (pendiente_formulacion esta semana)
    # Casos que cambiaron a pendiente_formulacion esta semana
    casos_nuevos_semana = Solicitudes.objects.filter(
        estado='pendiente_formulacion',
        updated_at__range=(start_of_week_dt, end_of_week_dt)
    ).select_related('estudiantes', 'estudiantes__carreras').count()
    
    # KPI 2: Casos pendientes de formulación en total
    casos_pendientes_formulacion = Solicitudes.objects.filter(
        estado='pendiente_formulacion'
    ).select_related('estudiantes', 'estudiantes__carreras')
    kpi_casos_pendientes_total = casos_pendientes_formulacion.count()
    
    # KPI 3: Casos completados (que pasaron de pendiente_formulacion a estados más avanzados)
    # Esto incluye casos que ya están en preaprobación, aprobación o aprobados
    casos_completados = Solicitudes.objects.filter(
        estado__in=['pendiente_preaprobacion', 'pendiente_aprobacion', 'aprobado']
    ).count()
    
    # KPI 4: Casos asignados a esta asesora técnica específica
    casos_asignados = Solicitudes.objects.filter(
        asesor_tecnico_asignado=perfil,
        estado='pendiente_formulacion'
    ).select_related('estudiantes', 'estudiantes__carreras').count()
    
    # KPI 5: Casos en proceso (pendiente_preaprobacion, pendiente_aprobacion)
    # Estos son casos que la asesora técnica ya formuló y están en siguientes etapas
    casos_en_proceso = Solicitudes.objects.filter(
        estado__in=['pendiente_preaprobacion', 'pendiente_aprobacion']
    ).count()
    
    # KPI 6: Casos aprobados totales (que pasaron por formulación)
    casos_aprobados = Solicitudes.objects.filter(estado='aprobado').count()
    
    # 4. --- Obtener Lista de Casos Pendientes de Formulación ---
    # Los casos más recientes primero
    casos_pendientes_list = casos_pendientes_formulacion.order_by('-updated_at')[:10]
    
    # 5. --- Preparar Contexto ---
    context = {
        'nombre_usuario': request.user.first_name,
        'kpis': {
            'casos_nuevos_semana': casos_nuevos_semana,
            'casos_pendientes_total': kpi_casos_pendientes_total,
            'casos_completados': casos_completados,
            'casos_asignados': casos_asignados,
            'casos_en_proceso': casos_en_proceso,
            'casos_aprobados': casos_aprobados,
        },
        'casos_pendientes_list': casos_pendientes_list,
    }
    
    # 6. --- Renderizar Template ---
    return render(request, 'SIAPE/dashboard_asesor_técnico.html', context)


# ----------- Vistas de los modelos (API) ------------
# (Sin cambios)
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
class SolicitudesViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
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

