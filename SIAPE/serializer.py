from rest_framework import serializers
from .models import Usuario, Roles, Areas, CategoriasAjustes, Docentes, DirectoresCarreras, Carreras, Estudiantes, AsesoresPedagogicos, Solicitudes, Evidencias, Asignaturas, AsignaturasEnCurso, Entrevistas, AjusteRazonable, AjusteAsignado

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'

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

class DocentesSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='usuarios.first_name', read_only=True, label='Nombre')
    last_name = serializers.CharField(source='usuarios.last_name', read_only=True, label='Apellido')
    areas = serializers.CharField(source='areas.nombre_area', read_only=True, label='Área')
    roles = serializers.CharField(source='roles.nombre_rol', read_only=True, label='Rol')

    class Meta:
        model = Docentes
        fields = [
            'id',
            'first_name',
            'last_name',
            'areas',
            'roles',
        ]

class DirectoresCarrerasSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='usuarios.first_name', read_only=True, label='Nombre')
    last_name = serializers.CharField(source='usuarios.last_name', read_only=True, label='Apellido')
    areas = serializers.CharField(source='areas.nombre', read_only=True, label='Área')
    roles = serializers.CharField(source='roles.nombre_rol', read_only=True, label='Rol')
    usuarios = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        write_only=True
    )

    class Meta:
        model = DirectoresCarreras
        fields = [
            'id',
            'first_name',
            'last_name',
            'areas',
            'roles',
            'usuarios',
        ]

class CarrerasSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(max_length=100, label='Nombre de la Carrera')
    # lectura: información anidada del director (opcional)
    directores_carreras = DirectoresCarrerasSerializer(read_only=True)
    # lectura simple del id del director (entero)
    directores_carreras_id = serializers.IntegerField(read_only=True)
    # escritura: recibir el id del director para asignar la FK
    id_directores_carreras = serializers.PrimaryKeyRelatedField(
        queryset=DirectoresCarreras.objects.all(),
        source='directores_carreras',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Carreras
        fields = [
            'id',
            'nombre',
            'directores_carreras_id',
            'id_directores_carreras',
            'directores_carreras',
        ]

class EstudiantesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estudiantes
        fields = '__all__'

class AsesoresPedagogicosSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsesoresPedagogicos
        fields = '__all__'

class SolicitudesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Solicitudes
        fields = '__all__'

class EvidenciasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidencias
        fields = '__all__'

class AsignaturasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asignaturas
        fields = '__all__'

class AsignaturasEnCursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsignaturasEnCurso
        fields = '__all__'

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

