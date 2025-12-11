from rest_framework import serializers
from .models import (
    Usuario, PerfilUsuario, Roles, Areas, CategoriasAjustes, 
    Carreras, Estudiantes, Solicitudes, Evidencias, Asignaturas, 
    AsignaturasEnCurso, Entrevistas, AjusteRazonable, AjusteAsignado
)
from .validators import validar_contraseña
from datetime import datetime, timedelta, time
from django.utils import timezone

ROL_COORDINADORA = 'Encargado de Inclusión'

class UsuarioSerializer(serializers.ModelSerializer):
    # --- Lectura y Escritura ---
    first_name = serializers.CharField(label='Nombre')
    last_name = serializers.CharField(label='Apellido')
    email = serializers.EmailField(label='Email')
    rut = serializers.CharField(label='RUT')
    numero = serializers.CharField(label='Número Telefónico', required=False, allow_blank=True)
    password = serializers.CharField(label='Contraseña', write_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'rut',
            'numero',
            'password',
        ]

    def validate_password(self, value):
        """Validar la contraseña según los requisitos del sistema"""
        es_valida, mensaje_error = validar_contraseña(value)
        if not es_valida:
            raise serializers.ValidationError(mensaje_error)
        return value

    def create(self, validated_data):
        """ Crear usuario con contraseña hasheada """
        password = validated_data.pop('password')
        user = Usuario.objects.create_user(password=password, **validated_data)
        
        return user

    def update(self, instance, validated_data):
        """ Actualizar usuario y hashea nueva contraseña si se proporciona """
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()
            
        return user

class RolesSerializer(serializers.ModelSerializer):
    # --- Lectura y Escritura ---
    nombre_rol = serializers.CharField(max_length=100, label='Nombre')

    class Meta:
        model = Roles
        fields = [
            'id',
            'nombre_rol',
        ]

class AreasSerializer(serializers.ModelSerializer):
    #  --- Lectura y Escritura
    nombre = serializers.CharField(max_length=100, label='Nombre del Área')

    class Meta:
        model = Areas
        fields = [
            'id',
            'nombre',
        ]

class CategoriasAjustesSerializer(serializers.ModelSerializer):
    nombre_categoria = serializers.CharField(max_length=100, label='Nombre de la Categoría')

    class Meta:
        model = CategoriasAjustes
        fields = [
            'id',
            'nombre_categoria',
        ]

class PerfilUsuarioSerializer(serializers.ModelSerializer):
    # --- Lectura  ---
    first_name = serializers.CharField(source='usuario.first_name', read_only=True, label='Nombre')
    last_name = serializers.CharField(source='usuario.last_name', read_only=True, label='Apellido')
    email = serializers.EmailField(source='usuario.email', read_only=True, label='Email')
    rol = serializers.CharField(source='rol.nombre_rol', read_only=True, label='Rol')
    area = serializers.CharField(source='area.nombre', read_only=True, label='Área', allow_null=True)

    # --- Escritura  ---
    usuario = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        write_only=True
    )
    rol = serializers.PrimaryKeyRelatedField(
        queryset=Roles.objects.all(),
        write_only=True
    )
    area = serializers.PrimaryKeyRelatedField(
        queryset=Areas.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = PerfilUsuario
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'rol',
            'area',
            'usuario',
            'rol',
            'area',
        ]

class CarrerasSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(max_length=100, label='Nombre de la Carrera')

    # --- Lectura ---
    director = serializers.StringRelatedField(read_only=True)
    area = serializers.StringRelatedField(read_only=True)

    # --- Escritura ---
    director_id = serializers.PrimaryKeyRelatedField(
        queryset=PerfilUsuario.objects.filter(rol__nombre_rol='Director de Carrera'), 
        source='director',
        write_only=True,
        required=False,
        allow_null=True
    )
    area_id = serializers.PrimaryKeyRelatedField(
        queryset=Areas.objects.all(),
        source='area',
        write_only=True,
        required=True,
    )

    class Meta:
        model = Carreras
        fields = [
            'id',
            'nombre',
            'director',
            'director_id',
            'area',
            'area_id'
        ]

class EstudiantesSerializer(serializers.ModelSerializer):
    
    # --- Lectura  ---
    carreras = serializers.StringRelatedField(read_only=True)
    
    # --- Escritura ---
    carrera_id = serializers.PrimaryKeyRelatedField(
        queryset=Carreras.objects.all(),
        source='carreras',
        write_only=True,
        label='Carrera'
    )

    class Meta:
        model = Estudiantes
        fields = [
            'id', 
            'nombres', 
            'apellidos', 
            'rut', 
            'email', 
            'numero', 
            'semestre_actual',
            'carreras',
            'carrera_id',
        ]

class SolicitudesSerializer(serializers.ModelSerializer):
    asunto = serializers.StringRelatedField(read_only=True)
    estudiante = serializers.StringRelatedField(source='estudiantes', read_only=True)
    descripcion = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True)
    coordinadora_asignada = serializers.StringRelatedField(read_only=True)
    coordinador_tecnico_pedagogico_asignado = serializers.StringRelatedField(read_only=True)
    asesor_pedagogico_asignado = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Solicitudes
        fields = [
            'id',
            'asunto',
            'descripcion',
            'estudiante',
            'created_at',
            'coordinadora_asignada',
            'coordinador_tecnico_pedagogico_asignado',
            'asesor_pedagogico_asignado',
        ]

class EvidenciasSerializer(serializers.ModelSerializer):
    # Validación de archivos para prevenir ataques
    archivo = serializers.FileField(
        max_length=100,
        allow_empty_file=False,
        use_url=False
    )
    
    class Meta:
        model = Evidencias
        fields = '__all__'
    
    def validate_archivo(self, value):
        """
        Validación de seguridad para archivos subidos.
        Previene ataques de inyección de archivos maliciosos.
        """
        import os
        from django.core.exceptions import ValidationError
        
        # Tamaño máximo: 10MB
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB en bytes
        
        # Extensiones permitidas (solo documentos)
        ALLOWED_EXTENSIONS = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
            '.jpg', '.jpeg', '.png', '.gif', '.txt'
        ]
        
        # Verificar tamaño
        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f"El archivo es demasiado grande. Tamaño máximo: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        # Verificar extensión
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Tipo de archivo no permitido. Extensiones permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Verificar nombre del archivo (prevenir path traversal)
        filename = os.path.basename(value.name)
        if '..' in filename or '/' in filename or '\\' in filename:
            raise serializers.ValidationError("Nombre de archivo inválido.")
        
        return value

class AsignaturasSerializer(serializers.ModelSerializer):
    # --- Lectura ---
    carreras = serializers.StringRelatedField(read_only=True)
    docente = serializers.StringRelatedField(read_only=True)

    # --- Escritura---
    carrera_id = serializers.PrimaryKeyRelatedField(
        queryset=Carreras.objects.all(),
        source='carreras',
        write_only=True,
        label='Carrera'
    )
    docente_id = serializers.PrimaryKeyRelatedField(
        queryset=PerfilUsuario.objects.filter(rol__nombre_rol='Docente'),
        source='docente',
        write_only=True,
        label='Docente'
    )

    class Meta:
        model = Asignaturas
        fields = [
            'id',
            'nombre',
            'seccion',
            'carreras',
            'docente',
            'carrera_id',
            'docente_id',
        ]

class AsignaturasEnCursoSerializer(serializers.ModelSerializer):
    """
    Serializer para AsignaturasEnCurso.
    Muestra nombres legibles para LECTURA (GET).
    Acepta IDs para ESCRITURA (POST/PUT).
    """
    
    # --- CAMPOS DE LECTURA (Read-only) ---
    # (Estos se mostrarán en las solicitudes GET)
    
    # Muestra el __str__ del Estudiante (e.g., "Javier Soto")
    estudiante_info = serializers.StringRelatedField(
        source='estudiantes', 
        read_only=True
    )
    
    # Muestra el __str__ de la Asignatura (e.g., "Proyecto Integrado PIS-001")
    asignatura_info = serializers.StringRelatedField(
        source='asignaturas', 
        read_only=True
    )

    # Muestra "Activo" o "Inactivo" usando la función del modelo
    estado_display = serializers.CharField(
        source='get_estado_display', 
        read_only=True
    )

    # --- CAMPOS DE ESCRITURA (Write-only) ---
    # (Estos se usarán para recibir datos en POST/PUT)
    
    # Acepta el ID del estudiante
    estudiantes = serializers.PrimaryKeyRelatedField(
        queryset=Estudiantes.objects.all(),
        write_only=True # Oculto en GET
    )
    
    # Acepta el ID de la asignatura
    asignaturas = serializers.PrimaryKeyRelatedField(
        queryset=Asignaturas.objects.all(),
        write_only=True # Oculto en GET
    )
    
    # El campo 'estado' (booleano) funciona tanto para lectura como escritura.
    # Se mostrará como True/False en GET y aceptará True/False en POST.
    # (Tu modelo se encarga de mostrar "Activo" en el Admin)

    class Meta:
        model = AsignaturasEnCurso
        fields = [
            'id', 
            
            # Campos de LECTURA (Output)
            'estudiante_info', 
            'asignatura_info',
            'estado_display', 
            
            # Campos de LECTURA Y ESCRITURA
            'estado',         # Muestra True/False Y Acepta True/False
            
            # Campos de ESCRITURA (Input)
            'estudiantes',   # Recibe ID de Estudiante
            'asignaturas'    # Recibe ID de Asignatura
        ]

class EntrevistasSerializer(serializers.ModelSerializer):
    # --- Campos de LECTURA (Read-only) ---
    solicitud_info = serializers.StringRelatedField(source='solicitudes', read_only=True, label="Solicitud")
    coordinadora_info = serializers.StringRelatedField(source='coordinadora', read_only=True, label="Coordinadora")
    # --- Campos de ESCRITURA (Write-only) ---
    solicitudes = serializers.PrimaryKeyRelatedField(queryset=Solicitudes.objects.all(), write_only=True, label="Solicitud")
    coordinadora = serializers.PrimaryKeyRelatedField(
        queryset=PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA),
        write_only=True,
        label="Encargado de Inclusión"
    )
    fecha_entrevista = serializers.DateTimeField(
        format="%d-%m-%Y %H:%M",
        input_formats=[
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d-%m-%Y %H:%M"
        ],
        label="Fecha (dd-mm-aaaa hh:mm)"
    )

    class Meta:
        model = Entrevistas
        fields = [
            'id',
            'solicitud_info',
            'coordinadora_info',
            'fecha_entrevista',
            'modalidad',
            'notas',
            'solicitudes',
            'coordinadora',
        ]

class AjusteRazonableSerializer(serializers.ModelSerializer):
    nombre_categoria = serializers.StringRelatedField(source='categorias_ajustes', read_only=True)
    
    categorias_ajustes = serializers.PrimaryKeyRelatedField(
        queryset=CategoriasAjustes.objects.all(),
        required=False,
        allow_null=True,
        label="Categoría Existente"
    )
    
    # Crear si no existe el tipo de categoría
    nueva_categoria_nombre = serializers.CharField(
        write_only=True, 
        required=False,
        allow_null=True,
        label="Crear Nueva Categoría (Opcional)"
    )

    # Asignar al estudiante
    solicitud_id_asignar = serializers.PrimaryKeyRelatedField(
        queryset=Solicitudes.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
        label="Asignar a Solicitud (ID)"
    )

    class Meta:
        model = AjusteRazonable
        fields = [
            'id', 
            'descripcion', 
            'nombre_categoria',
            'categorias_ajustes',
            'nueva_categoria_nombre',
            'solicitud_id_asignar'
        ]
        
    def validate(self, data):
        """ Validar que se elija una categoría existente o se cree una nueva, no ambas. """
        id_existente = data.get('categorias_ajustes')
        nombre_nuevo = data.get('nueva_categoria_nombre')
        
        if not id_existente and not nombre_nuevo:
            raise serializers.ValidationError(
                "Debe seleccionar una Categoría existente o proporcionar un nombre para crear una nueva."
            )
        if id_existente and nombre_nuevo:
            raise serializers.ValidationError(
                "No puede seleccionar una Categoría existente Y crear una nueva a la vez."
            )
            
        return data

    def create(self, validated_data):
        """ Crear AjusteRazonable, creando nueva categoría si es necesario. """
        nueva_categoria_nombre = validated_data.pop('nueva_categoria_nombre', None)
        
        if nueva_categoria_nombre:
            categoria, created = CategoriasAjustes.objects.get_or_create(
                nombre_categoria=nueva_categoria_nombre.strip().capitalize()
            )
            validated_data['categorias_ajustes'] = categoria

        return AjusteRazonable.objects.create(**validated_data)

class AjusteAsignadoSerializer(serializers.ModelSerializer):
    ajuste_descripcion = serializers.StringRelatedField(source='ajuste_razonable', read_only=True)
    solicitud_asunto = serializers.StringRelatedField(source='solicitudes', read_only=True)
    ajuste_razonable = serializers.PrimaryKeyRelatedField(queryset=AjusteRazonable.objects.all(), write_only=True)
    solicitudes = serializers.PrimaryKeyRelatedField(queryset=Solicitudes.objects.all(), write_only=True)

    class Meta:
        model = AjusteAsignado
        fields = ['id', 'ajuste_descripcion', 'solicitud_asunto', 'ajuste_razonable', 'solicitudes']

class PublicaSolicitudSerializer(serializers.Serializer):
    # --- Campos para el modelo Estudiantes ---
    nombres = serializers.CharField(
        max_length=191,
        min_length=2,
        trim_whitespace=True
    )
    apellidos = serializers.CharField(
        max_length=191,
        min_length=2,
        trim_whitespace=True
    )
    rut = serializers.CharField(
        max_length=20,
        min_length=8,
        trim_whitespace=True
    )
    email = serializers.EmailField(
        max_length=191,
        trim_whitespace=True
    )
    
    def validate_rut(self, value):
        """
        Validación básica de RUT chileno (formato simple).
        """
        import re
        # Remover puntos y guiones para validación
        rut_limpio = re.sub(r'[.\-]', '', value)
        if not re.match(r'^\d{7,8}[0-9kK]?$', rut_limpio):
            raise serializers.ValidationError("Formato de RUT inválido.")
        return value
    
    def validate_nombres(self, value):
        """
        Validar que el nombre solo contenga letras y espacios.
        """
        import re
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', value):
            raise serializers.ValidationError("El nombre solo puede contener letras y espacios.")
        return value
    
    def validate_apellidos(self, value):
        """
        Validar que el apellido solo contenga letras y espacios.
        """
        import re
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', value):
            raise serializers.ValidationError("El apellido solo puede contener letras y espacios.")
        return value
    numero = serializers.IntegerField(required=False, allow_null=True, label="Teléfono (opcional)")
    carrera_id = serializers.PrimaryKeyRelatedField(
        queryset=Carreras.objects.all(),
        label="Carrera"
    )
    
    # --- Campos para el modelo Solicitudes (simplificado) ---
    asunto = serializers.CharField(
        max_length=191,
        min_length=5,
        trim_whitespace=True
    )
    # 'descripcion' se elimina, ahora la llena la coordinadora
    autorizacion_datos = serializers.BooleanField(
        label="Autorizo el tratamiento de mis datos personales"
    )
    
    # --- Campos NUEVOS para la Cita (no van al modelo Solicitud) ---
    fecha_cita = serializers.DateField(write_only=True)
    hora_cita = serializers.CharField(write_only=True)
    modalidad = serializers.CharField(
        write_only=True, 
        max_length=100,
        trim_whitespace=True
    )

    # --- Campos para las relaciones (Evidencias) ---
    documentos_adjuntos = serializers.ListField(
        child=serializers.FileField(),
        label="Documentos adjuntos (evidencia)",
        write_only=True,
        required=False,
        allow_empty=True,
        max_length=10  # Máximo 10 archivos
    )
    
    def validate_documentos_adjuntos(self, value):
        """
        Validación de seguridad para múltiples archivos.
        """
        import os
        
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        ALLOWED_EXTENSIONS = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
            '.jpg', '.jpeg', '.png', '.gif', '.txt'
        ]
        
        if len(value) > 10:
            raise serializers.ValidationError("Máximo 10 archivos permitidos.")
        
        for archivo in value:
            # Verificar tamaño
            if archivo.size > MAX_FILE_SIZE:
                raise serializers.ValidationError(
                    f"El archivo {archivo.name} es demasiado grande. Tamaño máximo: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
                )
            
            # Verificar extensión
            ext = os.path.splitext(archivo.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise serializers.ValidationError(
                    f"Tipo de archivo no permitido para {archivo.name}. Extensiones permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
                )
            
            # Prevenir path traversal
            filename = os.path.basename(archivo.name)
            if '..' in filename or '/' in filename or '\\' in filename:
                raise serializers.ValidationError(f"Nombre de archivo inválido: {archivo.name}")
        
        return value

    def validate_autorizacion_datos(self, value):
        """ Valida que el checkbox de autorización esté marcado. """
        if value is not True:
            raise serializers.ValidationError(
                "Debe aceptar las políticas de privacidad y términos de servicio."
            )
        return value
        
    def validate(self, data):
        """
        Validación cruzada para la fecha y hora de la cita.
        Previene que dos personas tomen la misma hora (race condition).
        """
        fecha = data.get('fecha_cita')
        hora_str = data.get('hora_cita') # "HH:MM"

        if not fecha or not hora_str:
            raise serializers.ValidationError("Debe seleccionar una fecha y hora para la cita.")
            
        try:
            hora_obj = datetime.strptime(hora_str, '%H:%M').time()
        except ValueError:
            raise serializers.ValidationError("Formato de hora inválido.")

        # 1. Combinar fecha y hora en un datetime consciente de la zona horaria
        # Normalizar la hora a hora en punto (minutos y segundos en 0)
        hora_normalizada = hora_obj.replace(minute=0, second=0, microsecond=0)
        fecha_hora_cita = timezone.make_aware(datetime.combine(fecha, hora_normalizada))

        # 2. Re-validar que la hora no esté tomada ni bloqueada
        # Usar rango de fechas para evitar problemas con zonas horarias
        # Buscar citas en el mismo día y hora (normalizada)
        inicio_slot = fecha_hora_cita
        fin_slot = fecha_hora_cita + timedelta(hours=1)
        
        coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
        
        # Buscar citas que se solapen con este slot (mismo día y hora)
        cita_tomada = Entrevistas.objects.filter(
            coordinadora__in=coordinadoras,
            fecha_entrevista__gte=inicio_slot,
            fecha_entrevista__lt=fin_slot
        ).exclude(coordinadora__isnull=True).exists()
        
        # Buscar horarios bloqueados que se solapen con este slot
        from .models import HorarioBloqueado
        horario_bloqueado = HorarioBloqueado.objects.filter(
            coordinadora__in=coordinadoras,
            fecha_hora__gte=inicio_slot,
            fecha_hora__lt=fin_slot
        ).exists()

        if cita_tomada:
            raise serializers.ValidationError(
                f"Lo sentimos, la hora de las {hora_str} el {fecha.strftime('%d-%m-%Y')} acaba de ser tomada. Por favor, seleccione otra."
            )
        
        if horario_bloqueado:
            raise serializers.ValidationError(
                f"Lo sentimos, la hora de las {hora_str} el {fecha.strftime('%d-%m-%Y')} no está disponible. Por favor, seleccione otra."
            )
            
        # 3. Pasar el datetime completo al método .create()
        data['fecha_entrevista_completa'] = fecha_hora_cita
        return data

    def create(self, validated_data):
        """ Crea Estudiante, Solicitud y la Entrevista inicial, asignando coordinadora. """

        # 1. Datos del Estudiante
        datos_estudiante = {
            'nombres': validated_data['nombres'],
            'apellidos': validated_data['apellidos'],
            'email': validated_data['email'],
            'numero': validated_data.get('numero'),
            'carreras': validated_data['carrera_id']
            
        }

        # 2. Buscar coordinadora disponible para el horario seleccionado
        fecha_hora_cita = validated_data['fecha_entrevista_completa']
        coordinadoras = PerfilUsuario.objects.filter(rol__nombre_rol=ROL_COORDINADORA)
        
        # Buscar una coordinadora que no tenga una cita ni horario bloqueado en ese horario
        coordinadora_asignada = None
        from .models import HorarioBloqueado
        for coord in coordinadoras:
            tiene_cita = Entrevistas.objects.filter(
                coordinadora=coord,
                fecha_entrevista=fecha_hora_cita
            ).exists()
            tiene_horario_bloqueado = HorarioBloqueado.objects.filter(
                coordinadora=coord,
                fecha_hora=fecha_hora_cita
            ).exists()
            if not tiene_cita and not tiene_horario_bloqueado:
                coordinadora_asignada = coord
                break
        
        # Si ninguna coordinadora está disponible, usar la primera (fallback)
        if not coordinadora_asignada:
            coordinadora_asignada = coordinadoras.first()
        
        if not coordinadora_asignada:
            raise serializers.ValidationError("No hay coordinadoras disponibles en el sistema.")

        # 3. Datos de la Solicitud (incluye coordinadora)
        datos_solicitud = {
            'asunto': validated_data['asunto'],
            'descripcion': validated_data.get('descripcion', ''),
            'autorizacion_datos': validated_data['autorizacion_datos'],
            'estado': 'pendiente_entrevista',
            'coordinadora_asignada': coordinadora_asignada
        }

        archivos = validated_data.get('documentos_adjuntos', [])

        # 4. Crear/Actualizar Estudiante
        estudiante, created = Estudiantes.objects.update_or_create(
            rut=validated_data['rut'],
            defaults=datos_estudiante
        )

        # 5. Crear Solicitud (con coordinadora asignada)
        solicitud = Solicitudes.objects.create(
            estudiantes=estudiante,
            **datos_solicitud
        )

        # 6. Crear la Entrevista con la coordinadora y la fecha/hora seleccionadas
        Entrevistas.objects.create(
            solicitudes=solicitud,
            coordinadora=coordinadora_asignada,
            fecha_entrevista=validated_data['fecha_entrevista_completa'],
            modalidad=validated_data.get('modalidad', 'No definida'),
            estado='pendiente'
        )

        # 7. Guardar Evidencias (si las hay)
        for archivo in archivos:
            Evidencias.objects.create(
                solicitudes=solicitud,
                estudiantes=estudiante,
                archivo=archivo
            )

        return solicitud