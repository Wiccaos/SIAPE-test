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


# ----------------------------------------------
#           NUEVAS VISTAS DE API (PÚBLICAS)
# ----------------------------------------------

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

        # 4. Encontrar citas ya tomadas para esa fecha por CUALQUIER coordinadora
        start_of_day = timezone.make_aware(datetime.combine(selected_date, time.min))
        end_of_day = timezone.make_aware(datetime.combine(selected_date, time.max))

        citas_existentes = Entrevistas.objects.filter(
            coordinadora__in=coordinadoras,
            fecha_entrevista__range=(start_of_day, end_of_day)
        ).values_list('fecha_entrevista', flat=True)

        # 5. Filtrar la lista
        taken_slots = set()
        for dt in citas_existentes:
            taken_slots.add(dt.astimezone(timezone.get_current_timezone()).strftime('%H:%M')) # Formato HH:MM
        available_slots = [slot for slot in all_slots if slot not in taken_slots]
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
        # Si no se provee mes, usa el mes actual
        if not month_str:
            target_date = date.today()
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

    # 3. Obtener todas las citas ya tomadas en ese mes
    citas_del_mes = Entrevistas.objects.filter(
        coordinadora__in=coordinadoras,
        fecha_entrevista__year=year,
        fecha_entrevista__month=month
    ).values_list('fecha_entrevista', flat=True)

    # Agrupar citas por día
    citas_por_dia = {}
    for dt in citas_del_mes:
        dia_str = dt.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d')
        hora_str = dt.astimezone(timezone.get_current_timezone()).strftime('%H:%M')
        if dia_str not in citas_por_dia:
            citas_por_dia[dia_str] = set()
        citas_por_dia[dia_str].add(hora_str)

    # 4. Definir los slots base y preparar la respuesta
    slots_base_por_hora = range(9, 18) # 9:00 a 17:00
    slots_base_set = set([f"{h:02d}:00" for h in slots_base_por_hora])
    
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

        # Omitir fines de semana y días pasados
        if dia_actual_date.weekday() >= 5 or dia_actual_date < date.today():
            continue

        citas_tomadas_ese_dia = citas_por_dia.get(dia_actual_str, set())
        slots_libres = []
        slots_no_disponibles = []
        for h in slots_base_por_hora:
            hora_str = f"{h:02d}:00"
            # Si la hora ya está tomada, no disponible
            if hora_str in citas_tomadas_ese_dia:
                slots_no_disponibles.append(hora_str)
                continue
            # Si es hoy, solo permitir con 2 horas de anticipación
            if dia_actual_str == hoy_str:
                if h <= now.hour + 1:  # Debe ser al menos 2 horas después de la actual
                    slots_no_disponibles.append(hora_str)
                    continue
            slots_libres.append(hora_str)

        if len(slots_libres) > 0:
            respuesta_api["fechasConDisponibilidad"].append(dia_actual_str)
            respuesta_api["slotsDetallados"][dia_actual_str] = slots_libres
            respuesta_api["slotsNoDisponibles"][dia_actual_str] = slots_no_disponibles
        else:
            respuesta_api["diasCompletos"].append(dia_actual_str)
            respuesta_api["slotsNoDisponibles"][dia_actual_str] = slots_no_disponibles

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
        return redirect('panel_control_asesora_tecnica')
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

# ------------- Páginas de Asesoría Pedagógica ------------

@login_required
def dashboard_asesor(request):
    return dashboard_coordinadora(request)

@login_required
def casos_asesor(request):
    return redirect('dashboard_coordinadora')

@login_required
def detalle_caso_asesor(request, solicitud_id):
    return redirect('dashboard_coordinadora')

@login_required
def panel_control_asesor(request):
    return redirect('dashboard_coordinadora')


@login_required
def asignar_caso_asesor(request, solicitud_id):
    # ... (tu código original) ...
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')
    if request.method == 'POST':
        solicitud = get_object_or_404(Solicitudes, id=solicitud_id)
        perfil_asesor = request.user.perfil
        if solicitud.asesor_pedagogico_asignado is None:
            solicitud.asesor_pedagogico_asignado = perfil_asesor
            solicitud.save()
            messages.success(request, f'Caso asignado correctamente: {solicitud.asunto}')
        else:
            messages.warning(request, 'Este caso ya está asignado a otro asesor.')
    return redirect('panel_control_asesor')


@login_required
def agendar_cita_asesor(request):
    # ... (tu código original) ...
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
            fecha_entrevista = datetime.strptime(fecha_entrevista_str, '%Y-%m-%dT%H:%M')
            fecha_entrevista = timezone.make_aware(fecha_entrevista)
            Entrevistas.objects.create(
                solicitudes=solicitud, coordinadora=perfil_asesor,
                fecha_entrevista=fecha_entrevista, modalidad=modalidad, notas=notas
            )
            messages.success(request, 'Cita agendada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al agendar la cita: {str(e)}')
    return redirect('panel_control_asesor')


@login_required
def registrar_ajuste_razonable(request):
    # ... (tu código original) ...
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
            solicitud = get_object_or_404(Solicitudes, id=solicitud_id, asesor_pedagogico_asignado=request.user.perfil)
            if nueva_categoria:
                categoria = CategoriasAjustes.objects.create(nombre_categoria=nueva_categoria)
            elif categoria_id:
                categoria = get_object_or_404(CategoriasAjustes, id=categoria_id)
            else:
                messages.error(request, 'Debe seleccionar una categoría o crear una nueva.')
                return redirect('panel_control_asesor')
            if reasignar: pass
            ajuste_razonable = AjusteRazonable.objects.create(descripcion=descripcion, categorias_ajustes=categoria)
            AjusteAsignado.objects.create(ajuste_razonable=ajuste_razonable, solicitudes=solicitud)
            if reasignar:
                messages.success(request, 'Ajuste razonable reasignado correctamente.')
            else:
                messages.success(request, 'Ajuste razonable registrado y asignado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al registrar el ajuste: {str(e)}')
    return redirect('panel_control_asesor')


@login_required
def rechazar_solicitud_asesor(request, solicitud_id):
    # ... (tu código original) ...
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')
    if request.method == 'POST':
        motivo_rechazo = request.POST.get('motivo_rechazo', '').strip()
        try:
            solicitud = get_object_or_404(Solicitudes, id=solicitud_id, asesor_pedagogico_asignado=request.user.perfil)
            if solicitud.estado != 'en_proceso':
                messages.warning(request, 'Solo se pueden rechazar solicitudes en proceso.')
                return redirect('panel_control_asesor')
            solicitud.estado = 'rechazado'
            solicitud.save()
            if motivo_rechazo:
                messages.success(request, f'Solicitud rechazada. Motivo: {motivo_rechazo}')
            else:
                messages.success(request, 'Solicitud rechazada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al rechazar la solicitud: {str(e)}')
    return redirect('panel_control_asesor')


@login_required
def aprobar_solicitud_asesor(request, solicitud_id):
    # ... (tu código original) ...
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')
    if request.method == 'POST':
        try:
            solicitud = get_object_or_404(Solicitudes, id=solicitud_id, asesor_pedagogico_asignado=request.user.perfil)
            if solicitud.estado != 'en_proceso':
                messages.warning(request, 'Solo se pueden aprobar solicitudes en proceso.')
                return redirect('panel_control_asesor')
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
    # ... (tu código original) ...
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')
    if request.method == 'POST':
        accion = request.POST.get('accion')
        notas_adicionales = request.POST.get('notas_adicionales', '')
        try:
            entrevista = get_object_or_404(Entrevistas, id=entrevista_id, asesor_pedagogico=request.user.perfil)
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
                    messages.info(request, 'Cita marcada como no asistió. Puedes reagendarla desde el panel.')
            else:
                messages.error(request, 'Acción no válida.')
        except Exception as e:
            messages.error(request, f'Error al confirmar la cita: {str(e)}')
    return redirect('panel_control_asesor')


@login_required
def editar_notas_cita(request, entrevista_id):
    try:
        if request.user.perfil.rol.nombre_rol != ROL_ASESOR:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('panel_control_asesor')
    except AttributeError:
        return redirect('home')
    if request.method == 'POST':
        nuevas_notas = request.POST.get('notas', '')
        try:
            entrevista = get_object_or_404(Entrevistas, id=entrevista_id, asesor_pedagogico=request.user.perfil)
            entrevista.notas = nuevas_notas
            entrevista.save()
            messages.success(request, 'Notas actualizadas correctamente.')
        except Exception as e:
            messages.error(request, f'Error al actualizar las notas: {str(e)}')
    return redirect('panel_control_asesor')


@login_required
def reagendar_cita_asesor(request, entrevista_id):
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
            entrevista_original = get_object_or_404(Entrevistas, id=entrevista_id, asesor_pedagogico=request.user.perfil)
            nueva_fecha = datetime.strptime(nueva_fecha_str, '%Y-%m-%dT%H:%M')
            nueva_fecha = timezone.make_aware(nueva_fecha)
            nueva_entrevista = Entrevistas.objects.create(
                solicitudes=entrevista_original.solicitudes, asesor_pedagogico=entrevista_original.asesor_pedagogico,
                fecha_entrevista=nueva_fecha, modalidad=nueva_modalidad or entrevista_original.modalidad,
                notas=f"Reagendada desde cita del {entrevista_original.fecha_entrevista.strftime('%d/%m/%Y %H:%M')}. {notas_reagendamiento}" if notas_reagendamiento else f"Reagendada desde cita del {entrevista_original.fecha_entrevista.strftime('%d/%m/%Y %H:%M')}.",
                estado='pendiente'
            )
            if entrevista_original.estado == 'pendiente':
                entrevista_original.estado = 'no_asistio'
                entrevista_original.save()
            messages.success(request, 'Cita reagendada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al reagendar la cita: {str(e)}')
    return redirect('panel_control_asesor')


@login_required
def dashboard_coordinadora(request):
    try:
        if request.user.perfil.rol.nombre_rol != ROL_COORDINADORA:
            return redirect('home')
    except AttributeError:
        return redirect('home')
    total_solicitudes = Solicitudes.objects.count()
    casos_resueltos = Solicitudes.objects.filter(estado='aprobado', ajusteasignado__isnull=False).distinct().count()
    casos_en_proceso = Solicitudes.objects.filter(estado='en_proceso').count()
    hoy = timezone.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    inicio_semana_dt = timezone.make_aware(datetime.combine(inicio_semana, datetime.min.time()))
    fin_semana_dt = timezone.make_aware(datetime.combine(fin_semana, datetime.max.time()))
    perfil_coordinadora = request.user.perfil
    citas_semana = Entrevistas.objects.filter(coordinadora=perfil_coordinadora, fecha_entrevista__gte=inicio_semana_dt, fecha_entrevista__lte=fin_semana_dt).count()
    categorias_con_estadisticas = []
    categorias = CategoriasAjustes.objects.filter(ajusterazonable__ajusteasignado__isnull=False).distinct().annotate(
        total_aprobados=Count('ajusterazonable__ajusteasignado__solicitudes', filter=Q(ajusterazonable__ajusteasignado__solicitudes__estado='aprobado'), distinct=True),
        total_pendientes=Count('ajusterazonable__ajusteasignado__solicitudes', filter=Q(ajusterazonable__ajusteasignado__solicitudes__estado='en_proceso'), distinct=True),
        total_rechazados=Count('ajusterazonable__ajusteasignado__solicitudes', filter=Q(ajusterazonable__ajusteasignado__solicitudes__estado='rechazado'), distinct=True)
    )
    total_general = Solicitudes.objects.filter(ajusteasignado__isnull=False).distinct().count()
    for categoria in categorias:
        total_categoria = categoria.total_aprobados + categoria.total_pendientes + categoria.total_rechazados
        porcentaje = (total_categoria / total_general * 100) if total_general > 0 else 0
        categorias_con_estadisticas.append({
            'categoria': categoria, 'aprobados': categoria.total_aprobados, 'pendientes': categoria.total_pendientes,
            'rechazados': categoria.total_rechazados, 'total': total_categoria, 'porcentaje': round(porcentaje, 1)
        })
    categorias_con_estadisticas.sort(key=lambda x: x['total'], reverse=True)
    context = {
        'nombre_usuario': request.user.first_name, 'total_solicitudes': total_solicitudes, 'casos_resueltos': casos_resueltos,
        'casos_en_proceso': casos_en_proceso, 'citas_semana': citas_semana, 'distribucion_apoyos': categorias_con_estadisticas,
    }
    return render(request, 'SIAPE/dashboard_coordinadora.html', context)

# --- VISTA DIRECTOR DE CARRERA ---
@login_required
def dashboard_director(request):
    # ... (tu código original) ...
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

@login_required
def casos_coordinadora(request):
    # Mostrar solo solicitudes asignadas a la coordinadora logueada
    if hasattr(request.user, 'perfil'):
        perfil = request.user.perfil
        solicitudes = Solicitudes.objects.filter(coordinadora_asignada=perfil).select_related('estudiantes').order_by('-created_at')
    else:
        solicitudes = Solicitudes.objects.none()
    context = {'solicitudes': solicitudes, 'total_casos': solicitudes.count()}
    return render(request, 'SIAPE/casos_coordinadora.html', context)

@login_required
def panel_control_coordinadora(request):
    # Similar a panel_control_asesor pero para coordinadora
    # Puedes personalizar la lógica según lo que deba ver la coordinadora
    return render(request, 'SIAPE/panel_control_coordinadora.html')