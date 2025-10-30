from rest_framework import serializers
from .models import (
    Usuario, PerfilUsuario, Roles, Areas, CategoriasAjustes, 
    Carreras, Estudiantes, Solicitudes, Evidencias, Asignaturas, 
    AsignaturasEnCurso, Entrevistas, AjusteRazonable, AjusteAsignado
)

class UsuarioSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(label='Nombre')
    last_name = serializers.CharField(label='Apellido')
    email = serializers.EmailField(label='Email')
    rut = serializers.CharField(label='RUT')
    numero = serializers.CharField(label='Número Telefónico')
    password = serializers.CharField(label='Contraseña')

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

class RolesSerializer(serializers.ModelSerializer):
    nombre_rol = serializers.CharField(max_length=100, label='Nombre')

    class Meta:
        model = Roles
        fields = [
            'id',
            'nombre_rol',
        ]

class AreasSerializer(serializers.ModelSerializer):
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
    # --- Campos de Lectura (Read-only) ---
    first_name = serializers.CharField(source='usuario.first_name', read_only=True, label='Nombre')
    last_name = serializers.CharField(source='usuario.last_name', read_only=True, label='Apellido')
    email = serializers.EmailField(source='usuario.email', read_only=True, label='Email')
    rol = serializers.CharField(source='rol.nombre_rol', read_only=True, label='Rol')
    area = serializers.CharField(source='area.nombre', read_only=True, label='Área', allow_null=True)

    # --- Campos de Escritura (Write-only) ---
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

    # --- Campo de Lectura ---
    director = serializers.StringRelatedField(read_only=True)

    # --- Campo de Escritura ---
    director_id = serializers.PrimaryKeyRelatedField(
        queryset=PerfilUsuario.objects.filter(rol__nombre_rol='Director de Carrera'), 
        source='director',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Carreras
        fields = [
            'id',
            'nombre',
            'director',
            'director_id',
        ]

class EstudiantesSerializer(serializers.ModelSerializer):
    
    # --- Campo de Lectura (Read-only) ---
    carreras = serializers.StringRelatedField(read_only=True)
    
    # --- Campo de Escritura (Write-only) ---
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
    class Meta:
        model = Solicitudes
        fields = '__all__'

class EvidenciasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidencias
        fields = '__all__'

class AsignaturasSerializer(serializers.ModelSerializer):
    # --- Campos de Lectura (Read-only) ---
    carreras = serializers.StringRelatedField(read_only=True)
    docente = serializers.StringRelatedField(read_only=True)

    # --- Campos de Escritura (Write-only) ---
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
    # --- Campos de Lectura (Read-only) ---
    estado = serializers.CharField(max_length=100, label='Estado de la Asignatura')
    estudiantes = serializers.StringRelatedField(read_only=True)
    asignaturas = serializers.StringRelatedField(read_only=True)

    # --- Campos de Escritura (Write-only) ---
    estudiante_id = serializers.PrimaryKeyRelatedField(
        queryset=Estudiantes.objects.all(),
        source='estudiantes',
        write_only=True,
        label='Estudiante'
    )
    asignatura_id = serializers.PrimaryKeyRelatedField(
        queryset=Asignaturas.objects.all(),
        source='asignaturas',
        write_only=True,
        label='Asignatura'
    )

    class Meta:
        model = AsignaturasEnCurso
        fields = [
            'id',
            'estado',
            'estudiantes',
            'asignaturas',
            'estudiante_id',
            'asignatura_id',
        ]

class EntrevistasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entrevistas
        fields = '__all__'

class AjusteRazonableSerializer(serializers.ModelSerializer):
    class Meta:
        model = AjusteRazonable
        fields = '__all__'

class AjusteAsignadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AjusteAsignado
        fields = '__all__'