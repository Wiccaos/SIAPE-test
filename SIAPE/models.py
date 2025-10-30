from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# --- Modelo Usuario ---
class Usuario(AbstractUser):
    email = models.EmailField(max_length=191, unique=True)
    rut = models.CharField(max_length=20, unique=True)
    numero = models.IntegerField(null=True, blank=True,)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'rut']
    
    class Meta:
        db_table = 'usuarios'
    
    def __str__(self):
        return f'{self.first_name} {self.last_name}'
    

# --- Modelos Base ---

class Roles(models.Model):
    nombre_rol = models.CharField(max_length=100)
    class Meta:
        db_table = 'roles'

    def __str__(self):
        return self.nombre_rol

class Areas(models.Model):
    nombre = models.CharField(max_length=191)
    class Meta:
        db_table = 'areas'

    def __str__(self):
        return self.nombre


class CategoriasAjustes(models.Model):
    nombre_categoria = models.CharField(max_length=191)
    class Meta:
        db_table = 'categorias_ajustes'

    def __str__(self):
        return self.nombre_categoria

# --- Modelos con dependencias ---
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="perfil"
    )
    
    # Se define el rol del usuario
    rol = models.ForeignKey(
        Roles, 
        on_delete=models.SET_NULL, # Más seguro que CASCADE
        null=True, 
        blank=True
    )
    
    area = models.ForeignKey(
        Areas, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    class Meta:
        db_table = 'perfiles_usuario'

    def __str__(self):
        rol_nombre = self.rol.nombre_rol if self.rol else "Sin Rol"
        return f"{self.usuario.first_name} {self.usuario.last_name} ({rol_nombre})"

class Carreras(models.Model):
    nombre = models.CharField(max_length=191)
    director = models.ForeignKey(
            PerfilUsuario, 
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="carreras_dirigidas",
            limit_choices_to={'rol__nombre_rol': 'Director de Carrera'}
        )

    class Meta:
        db_table = 'carreras'

    def __str__(self):
        return self.nombre

class Estudiantes(models.Model):
    nombres = models.CharField(max_length=191)
    apellidos = models.CharField(max_length=191)
    rut = models.CharField(max_length=20, unique=True)
    email = models.EmailField(max_length=191, unique=True)
    carreras = models.ForeignKey(Carreras, on_delete=models.CASCADE)
    numero = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'estudiantes'

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


class Solicitudes(models.Model):
    asunto = models.CharField(max_length=191)
    created_at = models.DateTimeField(auto_now_add=True) 
    estudiantes = models.ForeignKey(Estudiantes, on_delete=models.CASCADE)
    asesor_pedagogico = models.ForeignKey(
        PerfilUsuario,
        on_delete=models.CASCADE,
        limit_choices_to={'rol__nombre_rol': 'Asesor Pedagógico'}
        )
    class Meta:
        db_table = 'solicitudes'

    def __str__(self):
            return f"Solicitud de {self.estudiantes}: {self.asunto}"

class Evidencias(models.Model):
    archivo = models.FileField(upload_to='evidencias/') 
    estudiantes = models.ForeignKey(Estudiantes, on_delete=models.CASCADE)
    solicitudes = models.ForeignKey(Solicitudes, on_delete=models.CASCADE)
    class Meta:
        db_table = 'evidencias'

    def __str__(self):
        return self.archivo.name

class Asignaturas(models.Model):
    nombre = models.CharField(max_length=150)
    seccion = models.CharField(max_length=150)
    carreras = models.ForeignKey(Carreras, on_delete=models.CASCADE)
    docente = models.ForeignKey(
            PerfilUsuario, 
            on_delete=models.CASCADE,
            limit_choices_to={'rol__nombre_rol': 'Docente'}
        )
    class Meta:
        db_table = 'asignaturas'

    def __str__(self):
        return f"{self.nombre} {self.seccion}"

class AsignaturasEnCurso(models.Model):
    estado = models.BooleanField()
    estudiantes = models.ForeignKey(Estudiantes, on_delete=models.CASCADE)
    asignaturas = models.ForeignKey(Asignaturas, on_delete=models.CASCADE)
    class Meta:
        db_table = 'asignaturas_en_curso'

    def __str__(self):
        return f"{self.estudiantes} cursando {self.asignaturas}"

class Entrevistas(models.Model):
    fecha = models.DateTimeField()
    modalidad = models.CharField(max_length=100)
    notas = models.TextField()
    solicitudes = models.ForeignKey(Solicitudes, on_delete=models.CASCADE)
    asesor_pedagogico = models.ForeignKey(
        PerfilUsuario,
        on_delete=models.CASCADE,
        limit_choices_to={'rol__nombre_rol': 'Asesor Pedagógico'}
        )

    class Meta:
        db_table = 'entrevistas'

    def __str__(self):
            return f"Entrevista sobre {self.solicitudes}"

class AjusteRazonable(models.Model):
    descripcion = models.TextField()
    categorias_ajustes = models.ForeignKey(CategoriasAjustes, on_delete=models.CASCADE)
    class Meta:
        db_table = 'ajuste_razonable'

    def __str__(self):
        return self.descripcion[:50] + "..."

class AjusteAsignado(models.Model):
    ajuste_razonable = models.ForeignKey(AjusteRazonable, on_delete=models.CASCADE)
    solicitudes = models.ForeignKey(Solicitudes, on_delete=models.CASCADE)
    class Meta:
        db_table = 'ajuste_asignado'

    def __str__(self):
        return f"Ajuste asignado a {self.solicitudes}"