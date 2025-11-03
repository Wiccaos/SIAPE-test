from rest_framework import serializers
from .models import (
    Usuario, PerfilUsuario, Roles, Areas, CategoriasAjustes, 
    Carreras, Estudiantes, Solicitudes, Evidencias, Asignaturas, 
    AsignaturasEnCurso, Entrevistas, AjusteRazonable, AjusteAsignado
)

class UsuarioSerializer(serializers.ModelSerializer):
    # --- Lectura y Escritura ---
    first_name = serializers.CharField(label='Nombre')
    last_name = serializers.CharField(label='Apellido')
    email = serializers.EmailField(label='Email')
    rut = serializers.CharField(label='RUT')
    numero = serializers.CharField(label='Número Telefónico', required=False, allow_blank=True)
    
    # 1. Cambia el campo password a write_only (no debe ser leído)
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

    # 2. Sobrescribe el método create para usar el manager
    def create(self, validated_data):
        # Extraemos el password de los datos validados
        password = validated_data.pop('password')
        
        # Usamos el manager 'objects' que definiste en tu modelo Usuario
        # El método create_user() se encargará de hashear el password
        user = Usuario.objects.create_user(password=password, **validated_data)
        
        return user

    def update(self, instance, validated_data):
        # Extrae el password si viene en la petición
        password = validated_data.pop('password', None)
        
        # Llama al update() normal para los otros campos
        user = super().update(instance, validated_data)

        if password:
            # Si se proporcionó un nuevo password, hashealo y guárdalo
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
            'carreras',
            'carrera_id',
        ]

class SolicitudesSerializer(serializers.ModelSerializer):
    asunto = serializers.StringRelatedField(read_only=True)
    estudiante = serializers.StringRelatedField(source = 'estudiantes', read_only=True)
    descripcion = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True)
    asesores_pedagogicos = serializers.CharField(read_only=True)

    class Meta:
        model = Solicitudes
        fields = [
            'id',
            'asunto',
            'descripcion',
            'estudiante',
            'created_at',
            'asesores_pedagogicos'
        ]

class EvidenciasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidencias
        fields = '__all__'

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
    class Meta:
        model = Entrevistas
        fields = '__all__'

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
    nombres = serializers.CharField(max_length=191)
    apellidos = serializers.CharField(max_length=191)
    rut = serializers.CharField(max_length=20)
    email = serializers.EmailField(max_length=191)
    numero = serializers.IntegerField(required=False, allow_null=True, label="Teléfono (opcional)")
    carrera_id = serializers.PrimaryKeyRelatedField(
        queryset=Carreras.objects.all(),
        label="Carrera"
    )
    
    # --- Campos para el modelo Solicitudes ---
    asunto = serializers.CharField(max_length=191)
    descripcion = serializers.CharField(
        style={'base_template': 'textarea.html'}, 
        label="Descripción Detallada"
    )
    autorizacion_datos = serializers.BooleanField(
        label="Autorizo el tratamiento de mis datos personales"
    )
    
    # --- Campos para las relaciones ---
    asignaturas_solicitadas_ids = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Asignaturas.objects.all()),
        label="Ramos para los que solicita ajuste (IDs)",
        required=False,
        allow_empty=True
    )
    documentos_adjuntos = serializers.ListField(
        child=serializers.FileField(),
        label="Documentos adjuntos (evidencia)",
        write_only=True,
        required=False,
        allow_empty=True
    )

    def validate_autorizacion_datos(self, value):
        """ Valida que el checkbox de autorización esté marcado. """
        if value is not True:
            raise serializers.ValidationError(
                "Debe aceptar las políticas de privacidad y términos de servicio."
            )
        return value
        
    def validate_rut(self):
        """
        Función para validar el rut POR DESARROLLAR
        de momento no se agrega para poder crear ejemplos sin que tire error
        """
        pass

    def create(self, validated_data):

        datos_estudiante = {
            'nombres': validated_data['nombres'],
            'apellidos': validated_data['apellidos'],
            'email': validated_data['email'],
            'numero': validated_data.get('numero'),
            'carreras': validated_data['carrera_id']
        }
        datos_solicitud = {
            'asunto': validated_data['asunto'],
            'descripcion': validated_data['descripcion'],
            'autorizacion_datos': validated_data['autorizacion_datos'],
        }
        archivos = validated_data.get('documentos_adjuntos', [])
        asignaturas_objs = validated_data.get('asignaturas_solicitadas_ids', []) # Ya son objetos

        estudiante, created = Estudiantes.objects.update_or_create(
            rut=validated_data['rut'],
            defaults=datos_estudiante
        )

        solicitud = Solicitudes.objects.create(
            estudiantes=estudiante, 
            **datos_solicitud
        )

        if asignaturas_objs:
            solicitud.asignaturas_solicitadas.set(asignaturas_objs)
            
        for archivo in archivos:
            Evidencias.objects.create(
                solicitudes=solicitud,
                estudiantes=estudiante,
                archivo=archivo
            )
            
        return solicitud