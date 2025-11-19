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

import json
from django.db.models import Count # Para el modelo de estadisticas.

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
    Asignaturas, AsignaturasEnCurso, Entrevistas, AjusteRazonable, AjusteAsignado, HorarioBloqueado
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
ROL_COORDINADORA = 'Encargado de Inclusión'
ROL_ASESORA_TECNICA = 'Coordinador Técnico Pedagógico'


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
    para una fecha específica, basado en las citas del Encargado de Inclusión.
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
            # Un horario está disponible si AL MENOS UNA coordinadora NO tiene cita ni horario bloqueado en ese horario
            slot_disponible = False
            for coord in coordinadoras:
                tiene_cita = Entrevistas.objects.filter(
                    coordinadora=coord,
                    fecha_entrevista=slot_datetime
                ).exclude(coordinadora__isnull=True).exists()
                
                # Verificar si el horario está bloqueado para esta coordinadora
                tiene_horario_bloqueado = HorarioBloqueado.objects.filter(
                    coordinadora=coord,
                    fecha_hora=slot_datetime
                ).exists()
                
                if not tiene_cita and not tiene_horario_bloqueado:
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
    horarios_bloqueados_por_coordinadora_dia = {}
    
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
    
    # Obtener TODOS los horarios bloqueados del mes de TODAS las coordinadoras
    todos_los_horarios_bloqueados = HorarioBloqueado.objects.filter(
        coordinadora__in=coordinadoras,
        fecha_hora__gte=primer_dia_mes,
        fecha_hora__lt=ultimo_dia_mes
    ).select_related('coordinadora').values_list('coordinadora_id', 'fecha_hora')
    
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
        horarios_bloqueados_por_coordinadora_dia[coord.id] = {}
    
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
    
    # Procesar cada horario bloqueado
    for coord_id, dt in todos_los_horarios_bloqueados:
        # Convertir a la zona horaria local de forma consistente
        dt_local = timezone.localtime(dt)
        dia_str = dt_local.strftime('%Y-%m-%d')
        # Normalizar la hora a solo la hora en punto
        hora_str = f"{dt_local.hour:02d}:00"
        
        if coord_id not in horarios_bloqueados_por_coordinadora_dia:
            horarios_bloqueados_por_coordinadora_dia[coord_id] = {}
        if dia_str not in horarios_bloqueados_por_coordinadora_dia[coord_id]:
            horarios_bloqueados_por_coordinadora_dia[coord_id][dia_str] = set()
        horarios_bloqueados_por_coordinadora_dia[coord_id][dia_str].add(hora_str)
        
        logger.debug(f"Horario bloqueado encontrado: Encargado de Inclusión {coord_id}, Día {dia_str}, Hora {hora_str}")
    
    # Debug: Log de citas encontradas por coordinadora
    for coord in coordinadoras:
        if coord.id in citas_por_coordinadora_dia:
            logger.debug(f"Encargado de Inclusión {coord.id}: {sum(len(horas) for horas in citas_por_coordinadora_dia[coord.id].values())} horas ocupadas")
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
            slot_bloqueado = False
            coordinadora_ocupada = None
            if coordinadoras.exists():
                for coord in coordinadoras:
                    citas_coord_dia = citas_por_coordinadora_dia.get(coord.id, {}).get(dia_actual_str, set())
                    horarios_bloqueados_coord_dia = horarios_bloqueados_por_coordinadora_dia.get(coord.id, {}).get(dia_actual_str, set())
                    
                    # Si esta coordinadora tiene una cita en este horario, el slot está ocupado
                    if hora_str in citas_coord_dia:
                        slot_ocupado = True
                        coordinadora_ocupada = coord.id
                        logger.debug(f"✓ Slot {hora_str} del día {dia_actual_str} está ocupado por coordinadora {coord.id} (cita)")
                        break
                    
                    # Si esta coordinadora tiene este horario bloqueado, el slot está bloqueado
                    if hora_str in horarios_bloqueados_coord_dia:
                        slot_bloqueado = True
                        coordinadora_ocupada = coord.id
                        logger.debug(f"✓ Slot {hora_str} del día {dia_actual_str} está bloqueado por coordinadora {coord.id}")
                        break
            
            # Si ninguna coordinadora tiene el horario ocupado ni bloqueado, está disponible
            if not slot_ocupado and not slot_bloqueado and coordinadoras.exists():
                slots_libres.append(hora_str)
                logger.debug(f"  Slot {hora_str} del día {dia_actual_str} está DISPONIBLE")
            else:
                # Al menos una coordinadora tiene este horario ocupado o bloqueado (o no hay coordinadoras)
                slots_no_disponibles.append(hora_str)
                if slot_ocupado:
                    logger.debug(f"  Slot {hora_str} del día {dia_actual_str} agregado a slots_no_disponibles (ocupado por coord {coordinadora_ocupada})")
                elif slot_bloqueado:
                    logger.debug(f"  Slot {hora_str} del día {dia_actual_str} agregado a slots_no_disponibles (bloqueado por coord {coordinadora_ocupada})")
                else:
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
    # Primero verificar si el usuario tiene un perfil con rol
    if hasattr(request.user, 'perfil') and request.user.perfil and request.user.perfil.rol:
        rol = request.user.perfil.rol.nombre_rol

        if rol == ROL_COORDINADORA:
            return redirect('dashboard_encargado_inclusion')
        elif rol == ROL_ASESORA_TECNICA:
            return redirect('dashboard_coordinador_tecnico_pedagogico')
        elif rol == ROL_ASESOR:
            return redirect('dashboard_asesor')
        elif rol == ROL_DIRECTOR:
            return redirect('dashboard_director')
        elif rol == ROL_ADMIN:
            return redirect('dashboard_admin')

    # Solo si no tiene rol o perfil, verificar si es superuser/staff para enviarlo al admin
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
    - Encargado de Inclusión: Casos pendientes de entrevista o asignados a él
    - Coordinador Técnico Pedagógico: Casos pendientes de formulación (que debe formular)
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
            # Encargado de Inclusión: Casos pendientes de entrevista o pendientes de formulación del caso
            filtros = Q(estado='pendiente_entrevista') | Q(estado='pendiente_formulacion_caso')
        elif rol_nombre == ROL_ASESORA_TECNICA:
            # Coordinador Técnico Pedagógico: Casos pendientes de formulación de ajustes (que debe formular)
            filtros = Q(estado='pendiente_formulacion_ajustes')
        elif rol_nombre == ROL_ASESOR:
            # Asesor Pedagógico: Casos pendientes de preaprobación
            filtros = Q(estado='pendiente_preaprobacion')
        elif rol_nombre == ROL_DIRECTOR:
            # Director: Casos pendientes de aprobación
            filtros = Q(estado='pendiente_aprobacion')

    # 3. Filtro por estado explícito (si se proporciona)
    # Si tiene_todos=True: El estado seleccionado es el único filtro (reemplaza el filtro por rol)
    # Si tiene_todos=False y es Asesora Pedagógica: Ignorar estado explícito, mantener filtro por rol
    # Si tiene_todos=False y tiene filtro por rol: El estado se combina con el filtro por rol (si existe)
    if tiene_estado_explicito:
        if tiene_todos:
            # Si quiere ver todos los casos, el estado seleccionado es el único filtro
            filtros = Q(estado=q_estado)
        elif rol_nombre == ROL_ASESOR and aplicar_filtro_por_rol:
            # Para Asesora Pedagógica, siempre mantener el filtro por rol (pendiente_preaprobacion)
            # Ignorar el estado seleccionado si no es "Ver Todos"
            pass  # Mantener el filtro por rol aplicado anteriormente
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
def dashboard_encargado_inclusion(request):
    """
    Dashboard principal para el Encargado de Inclusión.
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

    # KPI 2: Citas canceladas esta semana
    kpi_citas_canceladas = entrevistas_coordinadora.filter(
        estado='cancelada',
        updated_at__range=(start_of_week_dt, end_of_week_dt)
    ).count()

    # KPI 3: Casos pendientes de Formulación del caso
    # Contamos las solicitudes que están en estado 'pendiente_formulacion_caso'
    kpi_pendientes_formulacion_caso = Solicitudes.objects.filter(
        estado='pendiente_formulacion_caso'
    ).count()
    
    # KPI 4: Casos devueltos desde Coordinador Técnico Pedagógico
    # Casos que están en 'pendiente_formulacion_caso' y que tienen ajustes asignados
    # (lo que indica que fueron formulados por la asesora técnica y luego devueltos)
    kpi_casos_devueltos_asesor_tecnico = Solicitudes.objects.filter(
        estado='pendiente_formulacion_caso',
        ajusteasignado__isnull=False
    ).distinct().count()

    # 4. --- Preparar Contexto ---
    context = {
        'nombre_usuario': request.user.first_name,
        'kpis': {
            'citas_hoy': kpi_citas_hoy,
            'citas_canceladas': kpi_citas_canceladas,
            'pendientes_formulacion_caso': kpi_pendientes_formulacion_caso,
            'casos_devueltos_asesor_tecnico': kpi_casos_devueltos_asesor_tecnico,
        },
        'citas_del_dia_list': citas_hoy_qs, # Esta es la lista para la sección principal
    }

    # 5. --- Renderizar Template ---
    return render(request, 'SIAPE/dashboard_encargado_inclusion.html', context)

@require_POST
@login_required
def cancelar_cita_dashboard(request, entrevista_id):
    """
    Vista para que el Encargado de Inclusión cancele una cita desde el dashboard.
    """
    # 1. Verificar Permiso
    try:
        if request.user.perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('dashboard_encargado_inclusion')
    except AttributeError:
        return redirect('home')

    # 2. Lógica de la Acción
    try:
        # Cualquier coordinadora del rol puede cancelar cualquier entrevista del rol
        todas_las_coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
        entrevista = get_object_or_404(Entrevistas, id=entrevista_id, coordinadora__in=todas_las_coordinadoras)
        
        if entrevista.estado == 'pendiente':
            entrevista.estado = 'cancelada'
            entrevista.save()
            messages.success(request, 'Cita cancelada exitosamente.')
        else:
            messages.warning(request, 'Esta cita no puede ser cancelada porque ya fue realizada o cancelada anteriormente.')
    except Exception as e:
        messages.error(request, f'Error al cancelar la cita: {str(e)}')
        
    # 3. Redirigir siempre al dashboard
    return redirect('dashboard_coordinadora')

@login_required
def detalle_casos_encargado_inclusion(request, solicitud_id):
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
    # Permisos de edición: Solo Encargado de Inclusión, Asesor Pedagógico y Admin pueden editar la descripción del caso
    # El Coordinador Técnico Pedagógico NO puede editar el caso formulado por el Encargado de Inclusión
    puede_editar_descripcion = rol_nombre in [ROL_COORDINADORA, ROL_ASESOR, ROL_ADMIN]
    puede_agendar_cita = rol_nombre == ROL_COORDINADORA
    
    # Acciones de Encargado de Inclusión
    puede_formular_caso = rol_nombre == ROL_COORDINADORA and solicitud.estado == 'pendiente_formulacion_caso'
    puede_enviar_asesor_tecnico = rol_nombre == ROL_COORDINADORA and solicitud.estado == 'pendiente_formulacion_caso'
    
    # Acciones de Coordinador Técnico Pedagógico
    puede_formular_ajustes = rol_nombre == ROL_ASESORA_TECNICA and solicitud.estado == 'pendiente_formulacion_ajustes'
    puede_enviar_asesor_pedagogico = rol_nombre == ROL_ASESORA_TECNICA and solicitud.estado == 'pendiente_formulacion_ajustes'
    puede_devolver_a_coordinadora = rol_nombre == ROL_ASESORA_TECNICA and solicitud.estado == 'pendiente_formulacion_ajustes'
    
    # Acciones de Asesor Pedagógico
    puede_enviar_a_director = rol_nombre == ROL_ASESOR and solicitud.estado == 'pendiente_preaprobacion'
    puede_devolver_a_asesor_tecnico = rol_nombre == ROL_ASESOR and solicitud.estado == 'pendiente_preaprobacion'
    puede_editar_ajustes_asesor = rol_nombre == ROL_ASESOR and solicitud.estado == 'pendiente_preaprobacion'  # Asesora Pedagógica puede editar ajustes antes de enviar a Director
    
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
        'puede_formular_caso': puede_formular_caso,
        'puede_enviar_asesor_tecnico': puede_enviar_asesor_tecnico,
        'puede_formular_ajustes': puede_formular_ajustes,
        'puede_enviar_asesor_pedagogico': puede_enviar_asesor_pedagogico,
        'puede_devolver_a_coordinadora': puede_devolver_a_coordinadora,
        'puede_enviar_a_director': puede_enviar_a_director,
        'puede_devolver_a_asesor_tecnico': puede_devolver_a_asesor_tecnico,
        'puede_editar_ajustes_asesor': puede_editar_ajustes_asesor,
        'puede_aprobar': puede_aprobar,
        'puede_rechazar': puede_rechazar,
    }
    
    return render(request, 'SIAPE/detalle_casos_encargado_inclusion.html', context)

@login_required
def detalle_casos_asesor_tecnico(request, solicitud_id):
    """
    Vista para mostrar el detalle de un caso para el Coordinador Técnico Pedagógico.
    Es un wrapper que redirige a la misma vista pero con un contexto diferente.
    """
    # Verificar que el usuario es Coordinador Técnico Pedagógico
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
    return detalle_casos_encargado_inclusion(request, solicitud_id)

@require_POST
@login_required
def formular_ajuste_asesor_tecnico(request, solicitud_id):
    """
    Vista para que el Coordinador Técnico Pedagógico pueda crear y asignar ajustes a un caso.
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
    if solicitud.estado != 'pendiente_formulacion_ajustes':
        messages.error(request, 'Este caso no está en estado de formulación de ajustes.')
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

        # 8. --- Asignar Coordinador Técnico Pedagógico al caso si no está asignado ---
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
def editar_ajuste_asesor_tecnico(request, ajuste_asignado_id):
    """
    Vista para que el Coordinador Técnico Pedagógico pueda editar un ajuste ya asignado.
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

    # 2. --- Obtener el Ajuste Asignado ---
    ajuste_asignado = get_object_or_404(AjusteAsignado, id=ajuste_asignado_id)
    solicitud = ajuste_asignado.solicitudes
    
    # Verificar que el caso está en el estado correcto
    if solicitud.estado != 'pendiente_formulacion_ajustes':
        messages.error(request, 'Solo se pueden editar ajustes de casos en estado de formulación de ajustes.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud.id)

    # 3. --- Obtener Datos del Formulario ---
    descripcion = request.POST.get('descripcion', '').strip()
    categoria_id = request.POST.get('categoria_id', '')
    nueva_categoria = request.POST.get('nueva_categoria', '').strip()

    # 4. --- Validaciones ---
    if not descripcion:
        messages.error(request, 'La descripción del ajuste es requerida.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud.id)

    # Verificar si se seleccionó "nueva" o si hay una categoría seleccionada
    crear_nueva_categoria = categoria_id == 'nueva' or (not categoria_id and nueva_categoria)
    
    if not categoria_id and not nueva_categoria:
        messages.error(request, 'Debe seleccionar una categoría o crear una nueva.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud.id)

    if categoria_id and categoria_id != 'nueva' and nueva_categoria:
        messages.error(request, 'No puede seleccionar una categoría existente y crear una nueva a la vez.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud.id)

    if crear_nueva_categoria and not nueva_categoria:
        messages.error(request, 'Debe proporcionar el nombre de la nueva categoría.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud.id)

    try:
        # 5. --- Obtener o Crear Categoría ---
        if crear_nueva_categoria:
            if not nueva_categoria:
                messages.error(request, 'Debe proporcionar el nombre de la nueva categoría.')
                return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud.id)
            categoria, created = CategoriasAjustes.objects.get_or_create(
                nombre_categoria=nueva_categoria.strip().capitalize()
            )
            if created:
                messages.info(request, f'Categoría "{categoria.nombre_categoria}" creada exitosamente.')
        else:
            if not categoria_id or categoria_id == 'nueva':
                messages.error(request, 'Debe seleccionar una categoría válida.')
                return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud.id)
            categoria = get_object_or_404(CategoriasAjustes, id=categoria_id)

        # 6. --- Actualizar Ajuste Razonable ---
        ajuste_razonable = ajuste_asignado.ajuste_razonable
        ajuste_razonable.descripcion = descripcion
        ajuste_razonable.categorias_ajustes = categoria
        ajuste_razonable.save()

        messages.success(request, 'Ajuste actualizado exitosamente.')

    except Exception as e:
        logger.error(f"Error al editar ajuste: {str(e)}")
        messages.error(request, f'Error al editar el ajuste: {str(e)}')

    # 7. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud.id)

@require_POST
@login_required
def eliminar_ajuste_asesor_tecnico(request, ajuste_asignado_id):
    """
    Vista para que el Coordinador Técnico Pedagógico pueda eliminar un ajuste asignado.
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

    # 2. --- Obtener el Ajuste Asignado ---
    ajuste_asignado = get_object_or_404(AjusteAsignado, id=ajuste_asignado_id)
    solicitud = ajuste_asignado.solicitudes
    
    # Verificar que el caso está en el estado correcto
    if solicitud.estado != 'pendiente_formulacion_ajustes':
        messages.error(request, 'Solo se pueden eliminar ajustes de casos en estado de formulación de ajustes.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud.id)

    try:
        # 3. --- Eliminar el Ajuste Asignado y el Ajuste Razonable asociado ---
        ajuste_razonable = ajuste_asignado.ajuste_razonable
        solicitud_id = solicitud.id
        ajuste_asignado.delete()
        # También eliminamos el ajuste razonable si no está siendo usado por otros ajustes asignados
        if not AjusteAsignado.objects.filter(ajuste_razonable=ajuste_razonable).exists():
            ajuste_razonable.delete()
        
        messages.success(request, 'Ajuste eliminado exitosamente.')

    except Exception as e:
        logger.error(f"Error al eliminar ajuste: {str(e)}")
        messages.error(request, f'Error al eliminar el ajuste: {str(e)}')

    # 4. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)

@require_POST
@login_required
def enviar_a_asesor_tecnico(request, solicitud_id):
    """
    Vista para que el Encargado de Inclusión envíe el caso al Coordinador Técnico Pedagógico.
    Cambia el estado del caso de 'pendiente_formulacion_caso' a 'pendiente_formulacion_ajustes'.
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
    if solicitud.estado != 'pendiente_formulacion_caso':
        messages.error(request, 'Este caso no está en estado de formulación del caso. Solo se pueden enviar casos después de formular el caso.')
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso ---
        solicitud.estado = 'pendiente_formulacion_ajustes'
        solicitud.save()
        
        messages.success(request, 'Caso enviado al Coordinador Técnico Pedagógico exitosamente. El caso ahora está pendiente de formulación de ajustes.')
        
    except Exception as e:
        logger.error(f"Error al enviar caso a asesora técnica: {str(e)}")
        messages.error(request, f'Error al enviar el caso: {str(e)}')
    
    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)

@require_POST
@login_required
def enviar_a_asesor_pedagogico(request, solicitud_id):
    """
    Vista para que el Coordinador Técnico Pedagógico envíe el caso al siguiente estado
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
    if solicitud.estado != 'pendiente_formulacion_ajustes':
        messages.error(request, 'Este caso no está en estado de formulación de ajustes.')
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
    Vista para que el Coordinador Técnico Pedagógico devuelva el caso al Encargado de Inclusión.
    Cambia el estado del caso de 'pendiente_formulacion_ajustes' a 'pendiente_formulacion_caso'.
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
    if solicitud.estado != 'pendiente_formulacion_ajustes':
        messages.error(request, 'Este caso no está en estado de formulación de ajustes. Solo se pueden devolver casos pendientes de formulación de ajustes.')
        return redirect('detalle_casos_asesor_tecnico', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso ---
        solicitud.estado = 'pendiente_formulacion_caso'
        solicitud.save()
        
        messages.success(request, 'Caso devuelto al Encargado de Inclusión exitosamente. El caso ahora está pendiente de formulación del caso.')
        
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
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso ---
        solicitud.estado = 'pendiente_aprobacion'
        solicitud.save()
        
        messages.success(request, 'Caso enviado al Director exitosamente. El caso ahora está pendiente de aprobación.')
        
    except Exception as e:
        logger.error(f"Error al enviar caso a director: {str(e)}")
        messages.error(request, f'Error al enviar el caso: {str(e)}')
    
    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)

@require_POST
@login_required
def devolver_a_asesor_tecnico(request, solicitud_id):
    """
    Vista para que el Asesor Pedagógico devuelva el caso al Asesor Técnico Pedagógico.
    Cambia el estado del caso de 'pendiente_preaprobacion' a 'pendiente_formulacion_ajustes'.
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
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso ---
        solicitud.estado = 'pendiente_formulacion_ajustes'
        solicitud.save()
        
        messages.success(request, 'Caso devuelto al Asesor Técnico Pedagógico exitosamente. El caso ahora está pendiente de formulación de ajustes.')
        
    except Exception as e:
        logger.error(f"Error al devolver caso a asesor técnico: {str(e)}")
        messages.error(request, f'Error al devolver el caso: {str(e)}')
    
    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)

@require_POST
@login_required
def editar_ajuste_asesor(request, ajuste_asignado_id):
    """
    Vista para que la Asesora Pedagógica pueda editar un ajuste ya asignado
    cuando el caso está en estado 'pendiente_preaprobacion'.
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

    # 2. --- Obtener el Ajuste Asignado ---
    ajuste_asignado = get_object_or_404(AjusteAsignado, id=ajuste_asignado_id)
    solicitud = ajuste_asignado.solicitudes
    
    # Verificar que el caso está en el estado correcto
    if solicitud.estado != 'pendiente_preaprobacion':
        messages.error(request, 'Solo se pueden editar ajustes de casos en estado de preaprobación.')
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud.id)

    # 3. --- Obtener Datos del Formulario ---
    descripcion = request.POST.get('descripcion', '').strip()
    categoria_id = request.POST.get('categoria_id', '')
    nueva_categoria = request.POST.get('nueva_categoria', '').strip()

    # 4. --- Validaciones ---
    if not descripcion:
        messages.error(request, 'La descripción del ajuste es requerida.')
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud.id)

    # Verificar si se seleccionó "nueva" o si hay una categoría seleccionada
    crear_nueva_categoria = categoria_id == 'nueva' or (not categoria_id and nueva_categoria)
    
    if not categoria_id and not nueva_categoria:
        messages.error(request, 'Debe seleccionar una categoría o crear una nueva.')
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud.id)

    if categoria_id and categoria_id != 'nueva' and nueva_categoria:
        messages.error(request, 'No puede seleccionar una categoría existente y crear una nueva a la vez.')
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud.id)

    if crear_nueva_categoria and not nueva_categoria:
        messages.error(request, 'Debe proporcionar el nombre de la nueva categoría.')
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud.id)

    try:
        # 5. --- Obtener o Crear Categoría ---
        if crear_nueva_categoria:
            if not nueva_categoria:
                messages.error(request, 'Debe proporcionar el nombre de la nueva categoría.')
                return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud.id)
            categoria, created = CategoriasAjustes.objects.get_or_create(
                nombre_categoria=nueva_categoria.strip().capitalize()
            )
            if created:
                messages.info(request, f'Categoría "{categoria.nombre_categoria}" creada exitosamente.')
        else:
            if not categoria_id or categoria_id == 'nueva':
                messages.error(request, 'Debe seleccionar una categoría válida.')
                return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud.id)
            categoria = get_object_or_404(CategoriasAjustes, id=categoria_id)

        # 6. --- Actualizar Ajuste Razonable ---
        ajuste_razonable = ajuste_asignado.ajuste_razonable
        ajuste_razonable.descripcion = descripcion
        ajuste_razonable.categorias_ajustes = categoria
        ajuste_razonable.save()

        messages.success(request, 'Ajuste actualizado exitosamente.')

    except Exception as e:
        logger.error(f"Error al editar ajuste: {str(e)}")
        messages.error(request, f'Error al editar el ajuste: {str(e)}')

    # 7. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud.id)

@require_POST
@login_required
def eliminar_ajuste_asesor(request, ajuste_asignado_id):
    """
    Vista para que la Asesora Pedagógica pueda eliminar un ajuste asignado
    cuando el caso está en estado 'pendiente_preaprobacion'.
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

    # 2. --- Obtener el Ajuste Asignado ---
    ajuste_asignado = get_object_or_404(AjusteAsignado, id=ajuste_asignado_id)
    solicitud = ajuste_asignado.solicitudes
    
    # Verificar que el caso está en el estado correcto
    if solicitud.estado != 'pendiente_preaprobacion':
        messages.error(request, 'Solo se pueden eliminar ajustes de casos en estado de preaprobación.')
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud.id)

    try:
        # 3. --- Eliminar el Ajuste Asignado y el Ajuste Razonable asociado ---
        ajuste_razonable = ajuste_asignado.ajuste_razonable
        solicitud_id = solicitud.id
        ajuste_asignado.delete()
        # También eliminamos el ajuste razonable si no está siendo usado por otros ajustes asignados
        if not AjusteAsignado.objects.filter(ajuste_razonable=ajuste_razonable).exists():
            ajuste_razonable.delete()
        
        messages.success(request, 'Ajuste eliminado exitosamente.')

    except Exception as e:
        logger.error(f"Error al eliminar ajuste: {str(e)}")
        messages.error(request, f'Error al eliminar el ajuste: {str(e)}')

    # 4. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)

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
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso ---
        solicitud.estado = 'aprobado'
        solicitud.save()
        
        messages.success(request, 'Caso aprobado exitosamente. El caso ha sido aprobado e informado.')
        
    except Exception as e:
        logger.error(f"Error al aprobar caso: {str(e)}")
        messages.error(request, f'Error al aprobar el caso: {str(e)}')
    
    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)

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
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
    
    try:
        # 4. --- Cambiar el estado del caso (vuelve a Asesoría Pedagógica) ---
        solicitud.estado = 'pendiente_preaprobacion'
        solicitud.save()
        
        messages.warning(request, 'Caso rechazado. El caso ha sido devuelto a Asesoría Pedagógica para evaluación de corrección o archivo.')
        
    except Exception as e:
        logger.error(f"Error al rechazar caso: {str(e)}")
        messages.error(request, f'Error al rechazar el caso: {str(e)}')
    
    # 5. --- Redirigir de vuelta al detalle ---
    return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)

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
        # Solo Encargado de Inclusión, Asesor Pedagógico y Admin pueden editar la descripción del caso
        # El Coordinador Técnico Pedagógico NO puede editar el caso formulado por el Encargado de Inclusión
        ROLES_PERMITIDOS = [
            ROL_COORDINADORA,
            ROL_ASESOR,
            ROL_ADMIN
        ]
        if perfil.rol.nombre_rol not in ROLES_PERMITIDOS:
            messages.error(request, 'No tienes permisos para esta acción.')
            return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
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
            return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
        else:
            return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
    except AttributeError:
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)

@login_required
def panel_control_encargado_inclusion(request):
    """
    Panel de control para el Encargado de Inclusión.
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

    # 2. --- Obtener Citas para Todos los Encargados de Inclusión (Rol Completo) ---
    
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
    
    return render(request, 'SIAPE/panel_control_encargado_inclusion.html', context)

@login_required
def confirmar_cita_coordinadora(request, entrevista_id):
    """
    Permite al Encargado de Inclusión confirmar la asistencia (realizada o no asistió) 
    de una entrevista que ella gestiona.
    """
    # 1. Verificar Permiso
    try:
        if request.user.perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_encargado_inclusion')
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
                    # Cuando la entrevista se marca como realizada, el caso pasa a pendiente_formulacion_caso
                    solicitud = entrevista.solicitudes
                    if solicitud.estado == 'pendiente_entrevista':
                        solicitud.estado = 'pendiente_formulacion_caso'
                        solicitud.save()
                    messages.success(request, 'Cita marcada como realizada. El caso ahora está pendiente de formulación del caso.')
                else:
                    messages.info(request, 'Cita marcada como no asistió. Puedes reagendarla.')
            else:
                messages.error(request, 'Acción no válida.')
        except Exception as e:
            messages.error(request, f'Error al confirmar la cita: {str(e)}')
            
    # 3. Redirigir siempre al panel de control
    return redirect('panel_control_encargado_inclusion')

@login_required
def gestionar_horarios_bloqueados(request):
    """
    Vista para que el Encargado de Inclusión gestione sus horarios bloqueados.
    Permite ver, crear y eliminar horarios bloqueados.
    """
    # 1. Verificar Permiso
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para acceder a esta página.')
            return redirect('home')
    except AttributeError:
        return redirect('home')
    
    # 2. Obtener horarios bloqueados de esta coordinadora
    horarios_bloqueados = HorarioBloqueado.objects.filter(
        coordinadora=perfil
    ).order_by('fecha_hora')
    
    # Filtrar solo horarios futuros o del día actual
    now = timezone.localtime(timezone.now())
    horarios_bloqueados = horarios_bloqueados.filter(fecha_hora__gte=now)
    
    # 3. Si es POST, crear nuevo horario bloqueado
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha_bloqueo')  # Formato: YYYY-MM-DD
        hora_str = request.POST.get('hora_bloqueo')    # Formato: HH:MM
        motivo = request.POST.get('motivo', '').strip()
        
        if not fecha_str or not hora_str:
            messages.error(request, 'Debe seleccionar una fecha y un horario.')
        else:
            try:
                # Parsear fecha y hora por separado
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                hora_obj = datetime.strptime(hora_str, '%H:%M').time()
                
                # Normalizar la hora a hora en punto (minutos y segundos en 0)
                hora_normalizada = hora_obj.replace(minute=0, second=0, microsecond=0)
                
                # Combinar fecha y hora en un datetime aware
                fecha_hora = timezone.make_aware(datetime.combine(fecha_obj, hora_normalizada))
                
                # Verificar que no esté en el pasado
                if fecha_hora < now:
                    messages.error(request, 'No se pueden bloquear horarios en el pasado.')
                else:
                    # Verificar que no haya una cita en ese horario
                    tiene_cita = Entrevistas.objects.filter(
                        coordinadora=perfil,
                        fecha_entrevista=fecha_hora,
                        estado='pendiente'
                    ).exists()
                    
                    if tiene_cita:
                        messages.error(request, 'No se puede bloquear un horario que ya tiene una cita programada.')
                    else:
                        # Verificar que no esté ya bloqueado
                        ya_bloqueado = HorarioBloqueado.objects.filter(
                            coordinadora=perfil,
                            fecha_hora=fecha_hora
                        ).exists()
                        
                        if ya_bloqueado:
                            messages.error(request, 'Este horario ya está bloqueado.')
                        else:
                            # Crear el horario bloqueado
                            HorarioBloqueado.objects.create(
                                coordinadora=perfil,
                                fecha_hora=fecha_hora,
                                motivo=motivo
                            )
                            messages.success(request, 'Horario bloqueado exitosamente.')
            except ValueError as e:
                messages.error(request, f'Formato de fecha u hora inválido: {str(e)}')
            except Exception as e:
                messages.error(request, f'Error al bloquear el horario: {str(e)}')
        
        return redirect('gestionar_horarios_bloqueados')
    
    # 4. Preparar contexto
    context = {
        'horarios_bloqueados': horarios_bloqueados,
    }
    
    return render(request, 'SIAPE/gestionar_horarios_bloqueados.html', context)

@require_POST
@login_required
def eliminar_horario_bloqueado(request, horario_id):
    """
    Vista para que el Encargado de Inclusión elimine un horario bloqueado.
    """
    # 1. Verificar Permiso
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('home')
    except AttributeError:
        return redirect('home')
    
    # 2. Obtener y eliminar el horario bloqueado
    try:
        horario = get_object_or_404(HorarioBloqueado, id=horario_id, coordinadora=perfil)
        horario.delete()
        messages.success(request, 'Horario desbloqueado exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al desbloquear el horario: {str(e)}')
    
    return redirect('gestionar_horarios_bloqueados')

@login_required
def editar_notas_cita_coordinadora(request, entrevista_id):
    """
    Permite al Encargado de Inclusión editar las notas de una cita que él gestiona.
    """
    # 1. Verificar Permiso
    try:
        if request.user.perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_encargado_inclusion')
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
    return redirect('panel_control_encargado_inclusion')

@login_required
def agendar_cita_coordinadora(request):
    """
    Permite al Encargado de Inclusión agendar una nueva cita para un caso.
    """
    # 1. Verificar Permiso
    try:
        if request.user.perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('home')
    except AttributeError:
        return redirect('home')

    # 2. Lógica de la Acción
    if request.method == 'POST':
        solicitud_id = request.POST.get('solicitud_id')
        fecha_str = request.POST.get('fecha_agendar')  # Formato: YYYY-MM-DD
        hora_str = request.POST.get('hora_agendar')    # Formato: HH:MM
        modalidad = request.POST.get('modalidad', '')
        notas = request.POST.get('notas', '')
        
        try:
            solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
            
            if not fecha_str or not hora_str:
                messages.error(request, 'Debe seleccionar una fecha y un horario.')
                return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
            
            # Parsear fecha y hora por separado
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            hora_obj = datetime.strptime(hora_str, '%H:%M').time()
            
            # Normalizar la hora a hora en punto (minutos y segundos en 0)
            hora_normalizada = hora_obj.replace(minute=0, second=0, microsecond=0)
            
            # Combinar fecha y hora en un datetime aware
            fecha_entrevista = timezone.make_aware(datetime.combine(fecha_obj, hora_normalizada))
            
            # Verificar que no esté en el pasado
            now = timezone.localtime(timezone.now())
            if fecha_entrevista < now:
                messages.error(request, 'No se pueden agendar citas en el pasado.')
                return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
            
            # Buscar coordinadora disponible para el horario seleccionado
            todas_las_coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
            coordinadora_asignada = None
            
            from .models import HorarioBloqueado
            for coord in todas_las_coordinadoras:
                tiene_cita = Entrevistas.objects.filter(
                    coordinadora=coord,
                    fecha_entrevista=hora_normalizada
                ).exists()
                tiene_horario_bloqueado = HorarioBloqueado.objects.filter(
                    coordinadora=coord,
                    fecha_hora=hora_normalizada
                ).exists()
                if not tiene_cita and not tiene_horario_bloqueado:
                    coordinadora_asignada = coord
                    break
            
            # Si ninguna coordinadora está disponible, usar la primera (fallback)
            if not coordinadora_asignada:
                coordinadora_asignada = todas_las_coordinadoras.first()
            
            if not coordinadora_asignada:
                messages.error(request, 'No hay coordinadoras disponibles para agendar la cita.')
                return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
            
            # Verificar que no haya una cita ya agendada para esta solicitud en este horario
            cita_existente = Entrevistas.objects.filter(
                solicitudes=solicitud,
                fecha_entrevista=hora_normalizada
            ).exists()
            
            if cita_existente:
                messages.error(request, 'Ya existe una cita agendada para este caso en ese horario.')
                return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
            
            # Crear la nueva entrevista
            nueva_entrevista = Entrevistas.objects.create(
                solicitudes=solicitud,
                coordinadora=coordinadora_asignada,
                fecha_entrevista=hora_normalizada,
                modalidad=modalidad,
                notas=notas,
                estado='pendiente'
            )
            
            # Si el caso está en estado 'pendiente_entrevista', mantenerlo así
            # (no cambiar el estado automáticamente al agendar)
            
            messages.success(request, 'Cita agendada correctamente.')
        except ValueError as e:
            messages.error(request, f'Formato de fecha inválido: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al agendar la cita: {str(e)}')
    
    # 3. Redirigir al detalle del caso
    solicitud_id = request.POST.get('solicitud_id') if request.method == 'POST' else request.GET.get('solicitud_id')
    if solicitud_id:
        return redirect('detalle_casos_encargado_inclusion', solicitud_id=solicitud_id)
    return redirect('casos_generales')

@login_required
def reagendar_cita_coordinadora(request, entrevista_id):
    """
    Permite al Encargado de Inclusión reagendar una cita (usualmente una que 'no asistió').
    Crea una nueva entrevista y actualiza la antigua.
    """
    # 1. Verificar Permiso
    try:
        if request.user.perfil.rol.nombre_rol != ROL_COORDINADORA:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_encargado_inclusion')
    except AttributeError:
        return redirect('home')

    # 2. Lógica de la Acción
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha_reagendar')  # Formato: YYYY-MM-DD
        hora_str = request.POST.get('hora_reagendar')    # Formato: HH:MM
        nueva_modalidad = request.POST.get('nueva_modalidad', '')
        notas_reagendamiento = request.POST.get('notas_reagendamiento', '')
        try:
            # Cualquier coordinadora del rol puede reagendar cualquier entrevista del rol
            todas_las_coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
            entrevista_original = get_object_or_404(Entrevistas, id=entrevista_id, coordinadora__in=todas_las_coordinadoras)
            
            if not fecha_str or not hora_str:
                messages.error(request, 'Debe seleccionar una fecha y un horario.')
                return redirect('panel_control_encargado_inclusion')
            
            # Parsear fecha y hora por separado
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            hora_obj = datetime.strptime(hora_str, '%H:%M').time()
            
            # Normalizar la hora a hora en punto (minutos y segundos en 0)
            hora_normalizada = hora_obj.replace(minute=0, second=0, microsecond=0)
            
            # Combinar fecha y hora en un datetime aware
            nueva_fecha = timezone.make_aware(datetime.combine(fecha_obj, hora_normalizada))
            
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
    return redirect('panel_control_encargado_inclusion')


# --- VISTA ASESOR PEDAGÓGICO ---
@login_required
def dashboard_asesor(request):
    """
    Dashboard principal para la Asesora Pedagógica.
    La Asesora Pedagógica es la Jefa del área de asesoría pedagógica,
    por ende debe monitorear la información de todos los casos.
    """
    # 1. --- Verificación de Permisos ---
    try:
        perfil = request.user.perfil
        if perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para acceder a este panel.')
            return redirect('home')
    except AttributeError:
        logger.warning(f"Usuario {request.user.email} sin perfil/rol intentó acceder al dashboard de asesora pedagógica.")
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
    
    # KPI 1: Casos nuevos (creados esta semana)
    casos_nuevos_semana = Solicitudes.objects.filter(
        created_at__range=(start_of_week_dt, end_of_week_dt)
    ).count()
    
    # KPI 2: Casos devueltos desde Director de Carrera
    # Casos que están en 'pendiente_preaprobacion' y que tienen ajustes asignados
    # (lo que indica que fueron preaprobados y enviados al Director, pero fueron rechazados/devueltos)
    # Esto es una aproximación: casos con ajustes que están en preaprobación
    casos_devueltos_director = Solicitudes.objects.filter(
        estado='pendiente_preaprobacion',
        ajusteasignado__isnull=False
    ).distinct().count()
    
    # KPI 3-9: Un KPI por cada estado de los casos
    # Crear lista de tuplas (estado_valor, estado_nombre, cantidad) para facilitar el acceso en el template
    estados_con_cantidad = []
    for estado_valor, estado_nombre in Solicitudes.ESTADO_CHOICES:
        cantidad = Solicitudes.objects.filter(estado=estado_valor).count()
        estados_con_cantidad.append({
            'valor': estado_valor,
            'nombre': estado_nombre,
            'cantidad': cantidad
        })
    
    # 4. --- Obtener Lista de Casos Pendientes de Preaprobación ---
    # Casos que están en estado 'pendiente_preaprobacion' y que requieren revisión por parte de la Asesora Pedagógica
    casos_pendientes_preaprobacion = Solicitudes.objects.filter(
        estado='pendiente_preaprobacion'
    ).select_related(
        'estudiantes',
        'estudiantes__carreras'
    ).order_by('-updated_at')[:10]  # Los más recientes primero, limitar a 10
    
    # 5. --- Preparar Contexto ---
    context = {
        'nombre_usuario': request.user.first_name,
        'kpis': {
            'casos_nuevos_semana': casos_nuevos_semana,
            'casos_devueltos_director': casos_devueltos_director,
        },
        'estados_con_cantidad': estados_con_cantidad,
        'casos_pendientes_preaprobacion': casos_pendientes_preaprobacion,
    }
    
    return render(request, 'SIAPE/dashboard_asesor.html', context)

# ----------------------------------------------------
#                VISTA DIRECTOR DE CARRERA
# ----------------------------------------------------

# @login_required
# def dashboard_director(request):
#     """
#     Dashboard para el Director de Carrera.
#     Muestra casos pendientes de su aprobación y un historial
#     de casos aprobados de sus carreras.
#     """
#     try:
#         perfil_director = request.user.perfil
#         if perfil_director.rol.nombre_rol != ROL_DIRECTOR:
#             messages.error(request, 'No tienes permisos para esta acción.')
#             return redirect('home')
#     except AttributeError:
#         return redirect('home')

#     # 1. Encontrar las carreras que este director gestiona
#     carreras_del_director = Carreras.objects.filter(director=perfil_director)
    
#     # 2. Base de solicitudes de sus carreras
#     solicitudes_base = Solicitudes.objects.filter(
#         estudiantes__carreras__in=carreras_del_director
#     ).select_related(
#         'estudiantes', 
#         'estudiantes__carreras'
#     )

#     # 3. Filtrar solicitudes PENDIENTES (estado 'pendiente_aprobacion')
#     solicitudes_pendientes = solicitudes_base.filter(
#         estado='pendiente_aprobacion'
#     ).order_by('updated_at') # Más antiguas (recién llegadas) primero

#     # 4. Filtrar el HISTORIAL (solo 'aprobado')
#     solicitudes_historial = solicitudes_base.filter(
#         estado='aprobado'
#     ).order_by('-updated_at') # Más recientes primero

#     # 5. KPIs (Específicos del Director)
#     kpis = {
#         'total_pendientes': solicitudes_pendientes.count(),
#         'total_aprobados': solicitudes_historial.count(),
#     }

#     context = {
#         'nombre_usuario': request.user.first_name,
#         'solicitudes_pendientes': solicitudes_pendientes,
#         'solicitudes_historial': solicitudes_historial,
#         'kpis': kpis,
#     }
    
#     return render(request, 'SIAPE/dashboard_director.html', context)
@login_required
def dashboard_director(request):
    """
    Dashboard para el Director de Carrera.
    Muestra casos pendientes de su aprobación y un historial
    de casos aprobados de sus carreras.
    """
    try:
        perfil_director = request.user.perfil
        if perfil_director.rol.nombre_rol != ROL_DIRECTOR:
            messages.error(request, 'No tienes permisos para esta acción.')
            return redirect('home')
    except AttributeError:
        return redirect('home')

    # 1. Encontrar las carreras que este director gestiona
    carreras_del_director = Carreras.objects.filter(director=perfil_director)
    
    # Si no tiene carreras asignadas, mostrar mensaje y retornar lista vacía
    if not carreras_del_director.exists():
        messages.warning(request, 'No tienes carreras asignadas. Contacta a un administrador para que te asigne carreras.')
        context = {
            'nombre_usuario': request.user.first_name,
            'solicitudes_pendientes': Solicitudes.objects.none(),
            'solicitudes_historial': Solicitudes.objects.none(),
            'kpis': {
                'total_pendientes': 0,
                'total_aprobados': 0,
                'total_rechazados': 0,
            },
        }
        return render(request, 'SIAPE/dashboard_director.html', context)
    
    # Obtener IDs de las carreras para hacer el filtro más eficiente
    carreras_ids = carreras_del_director.values_list('id', flat=True)
    
    # 2. Base de solicitudes de sus carreras - usando IDs para mejor rendimiento
    solicitudes_base = Solicitudes.objects.filter(
        estudiantes__carreras__id__in=carreras_ids
    ).select_related(
        'estudiantes', 
        'estudiantes__carreras'
    ).distinct()

    # 3. Filtrar solicitudes PENDIENTES (estado 'pendiente_aprobacion')
    # Estos son los casos que el Asesor Pedagógico le envió.
    solicitudes_pendientes = solicitudes_base.filter(
        estado='pendiente_aprobacion'
    ).order_by('updated_at') # Más antiguas (recién llegadas) primero

    # 4. Filtrar el HISTORIAL (casos 'aprobados' o 'rechazados')
    solicitudes_historial = solicitudes_base.filter(
        estado__in=['aprobado', 'rechazado']
    ).order_by('-updated_at') # Más recientes primero

    # 5. KPIs (Específicos del Director)
    kpis = {
        'total_pendientes': solicitudes_pendientes.count(),
        'total_aprobados': solicitudes_historial.filter(estado='aprobado').count(),
        'total_rechazados': solicitudes_historial.filter(estado='rechazado').count(),
    }

    context = {
        'nombre_usuario': request.user.first_name,
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_historial': solicitudes_historial,
        'kpis': kpis,
    }
    
    return render(request, 'SIAPE/dashboard_director.html', context)

@login_required
def carreras_director(request):
    """
    Muestra las carreras asignadas al Director de Carrera logueado.
    """
    try:
        perfil_director = request.user.perfil
        if perfil_director.rol.nombre_rol != ROL_DIRECTOR:
            messages.error(request, 'No tienes permisos para esta acción.')
            return redirect('home')
    except AttributeError:
        return redirect('home')

    # Buscamos las carreras donde el director sea el usuario actual
    carreras_list = Carreras.objects.filter(
        director=perfil_director
    ).select_related(
        'area'
    ).annotate(
        total_estudiantes=Count('estudiantes') # Contamos los estudiantes via FK
    ).order_by('nombre')

    context = {
        'carreras_list': carreras_list,
        'total_carreras': carreras_list.count()
    }
    return render(request, 'SIAPE/carreras_director.html', context)

@login_required
def estudiantes_por_carrera_director(request, carrera_id):
    """
    Muestra la lista de estudiantes de una carrera específica
    gestionada por el Director de Carrera.
    """
    try:
        perfil_director = request.user.perfil
        if perfil_director.rol.nombre_rol != ROL_DIRECTOR:
            messages.error(request, 'No tienes permisos para esta acción.')
            return redirect('home')
    except AttributeError:
        return redirect('home')

    # 1. Obtener la carrera y verificar que el director sea el correcto
    # Esta es la comprobación de seguridad:
    carrera = get_object_or_404(Carreras, id=carrera_id, director=perfil_director)

    # 2. Obtener los estudiantes de esa carrera
    estudiantes_list = Estudiantes.objects.filter(
        carreras=carrera
    ).order_by('apellidos', 'nombres')

    context = {
        'carrera': carrera,
        'estudiantes_list': estudiantes_list,
        'total_estudiantes': estudiantes_list.count(),
        'nombre_usuario': request.user.first_name, # Para la plantilla
    }
    # 3. Renderizar un nuevo template que crearemos a continuación
    return render(request, 'SIAPE/estudiantes_carrera_director.html', context)

@login_required
def estadisticas_director(request):
    """
    Panel de Estadísticas para el Director de Carrera.
    Muestra gráficos sobre el estado y tipo de ajustes.
    """
    
    # 1. --- Verificación de Permisos ---
    try:
        perfil_director = request.user.perfil
        if perfil_director.rol.nombre_rol != ROL_DIRECTOR:
            messages.error(request, 'No tienes permisos para esta acción.')
            return redirect('home')
    except AttributeError:
        return redirect('home')

    # 2. --- Base Query ---
    # Obtenemos todos los ajustes asignados a estudiantes de las carreras de este director
    carreras_del_director = Carreras.objects.filter(director=perfil_director)
    ajustes_base = AjusteAsignado.objects.filter(
        solicitudes__estudiantes__carreras__in=carreras_del_director
    )

    # 3. --- Gráfico 1: Estado de Ajustes (Pie Chart) ---
    # Esto responde a tu petición de "aprobados/rechazados/pendientes"
    estado_ajustes = ajustes_base.values('estado_aprobacion').annotate(
        total=Count('id')
    ).order_by('estado_aprobacion')

    # Formatear para Chart.js
    pie_labels = [d['estado_aprobacion'].capitalize() for d in estado_ajustes]
    pie_data = [d['total'] for d in estado_ajustes]
    
    pie_chart_data = {
        'labels': pie_labels,
        'datasets': [{
            'data': pie_data,
            'backgroundColor': [
                'rgba(40, 167, 69, 0.7)',  # Aprobado (Verde)
                'rgba(253, 126, 20, 0.7)', # Pendiente (Naranja)
                'rgba(220, 53, 69, 0.7)'   # Rechazado (Rojo)
            ],
            'borderColor': '#ffffff',
        }]
    }

    # 4. --- Gráfico 2: Tipos de Apoyo (Idea Adicional) ---
    # Muestra qué categorías de apoyo son más comunes.
    tipos_ajustes = ajustes_base.filter(estado_aprobacion='aprobado').values(
        'ajuste_razonable__categorias_ajustes__nombre_categoria'
    ).annotate(
        total=Count('id')
    ).order_by('-total') # De más común a menos común

    bar_labels_tipos = [d['ajuste_razonable__categorias_ajustes__nombre_categoria'] for d in tipos_ajustes]
    bar_data_tipos = [d['total'] for d in tipos_ajustes]

    bar_chart_tipos = {
        'labels': bar_labels_tipos,
        'datasets': [{
            'label': 'Ajustes Aprobados por Categoría',
            'data': bar_data_tipos,
            'backgroundColor': 'rgba(0, 123, 255, 0.7)', # Azul
        }]
    }

    # 5. --- Gráfico 3: Eficiencia/Concentración por Sección (Tu petición) ---
    # Muestra las 5 secciones (asignaturas) con más ajustes aprobados
    secciones_data = AjusteAsignado.objects.filter(
        solicitudes__estudiantes__carreras__in=carreras_del_director,
        estado_aprobacion='aprobado'
    ).values(
        'solicitudes__asignaturas_solicitadas__nombre', # Agrupa por nombre de asignatura
        'solicitudes__asignaturas_solicitadas__seccion' # y por sección
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5] # Top 5

    bar_labels_secciones = [f"{d['solicitudes__asignaturas_solicitadas__nombre']} ({d['solicitudes__asignaturas_solicitadas__seccion']})" for d in secciones_data]
    bar_data_secciones = [d['total'] for d in secciones_data]

    bar_chart_secciones = {
        'labels': bar_labels_secciones,
        'datasets': [{
            'label': 'Ajustes Aprobados por Sección (Top 5)',
            'data': bar_data_secciones,
            'backgroundColor': 'rgba(204, 0, 0, 0.7)', # Rojo INACAP
        }]
    }

    context = {
        'nombre_usuario': request.user.first_name,
        # Convertimos los datos a JSON para que JavaScript los pueda leer
        'pie_chart_data_json': json.dumps(pie_chart_data),
        'bar_chart_tipos_json': json.dumps(bar_chart_tipos),
        'bar_chart_secciones_json': json.dumps(bar_chart_secciones),
    }
    
    return render(request, 'SIAPE/estadisticas_director.html', context)



# ----------------------------------------------------
#                VISTA ASESORA TÉCNICA PEDAGÓGICA
# ----------------------------------------------------

@login_required
def dashboard_coordinador_tecnico_pedagogico(request):
    """
    Dashboard principal para el Coordinador Técnico Pedagógico.
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
    
    # KPI 1: Casos nuevos (pendiente_formulacion_ajustes esta semana)
    # Casos que cambiaron a pendiente_formulacion_ajustes esta semana
    casos_nuevos_semana = Solicitudes.objects.filter(
        estado='pendiente_formulacion_ajustes',
        updated_at__range=(start_of_week_dt, end_of_week_dt)
    ).select_related('estudiantes', 'estudiantes__carreras').count()
    
    # KPI 2: Casos pendientes de formulación de ajustes en total
    casos_pendientes_formulacion = Solicitudes.objects.filter(
        estado='pendiente_formulacion_ajustes'
    ).select_related('estudiantes', 'estudiantes__carreras')
    kpi_casos_pendientes_total = casos_pendientes_formulacion.count()
    
    # KPI 3: Casos devueltos desde Asesora Pedagógica
    # Casos que están en 'pendiente_formulacion_ajustes' y que tienen ajustes asignados
    # (lo que indica que fueron formulados y luego devueltos)
    # Esto es una aproximación: casos con ajustes que están pendientes de formulación
    casos_devueltos = Solicitudes.objects.filter(
        estado='pendiente_formulacion_ajustes',
        ajusteasignado__isnull=False
    ).distinct().count()
    
    # 4. --- Obtener Lista de Casos Pendientes de Formulación ---
    # Los casos más recientes primero
    casos_pendientes_list = casos_pendientes_formulacion.order_by('-updated_at')[:10]
    
    # 5. --- Preparar Contexto ---
    context = {
        'nombre_usuario': request.user.first_name,
        'kpis': {
            'casos_nuevos_semana': casos_nuevos_semana,
            'casos_pendientes_total': kpi_casos_pendientes_total,
            'casos_devueltos': casos_devueltos,
        },
        'casos_pendientes_list': casos_pendientes_list,
    }
    
    # 6. --- Renderizar Template ---
    return render(request, 'SIAPE/dashboard_coordinador_tecnico_pedagogico.html', context)


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

