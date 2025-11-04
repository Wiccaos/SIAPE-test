# Django
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import logout, login

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
    
    # Datos para el formulario
    try:
        carreras = Carreras.objects.all().order_by('nombre')
    except Carreras.DoesNotExist:
        carreras = []
    
    # context para enviar a la plantilla
    context = {
        'carreras': carreras,
    }
    
    # render de la plantilla
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

    try:
        rol = request.user.perfil.rol.nombre_rol
    except AttributeError:
        rol = None

    # Redireccionar según el rol
    if rol == 'Asesor Pedagógico':
            return redirect('dashboard_asesor')
        
    return render(request, 'SIAPE/inicio.html')
    
def vista_protegida(request):
    """    Redirecciona a login si el usuario no está autenticado """
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'vista_protegida.html')

def logout_view(request):
    # Cierra la sesión del usuario y limpia la data de SESSION
    logout(request)
    # Redirige a la página de inicio de sesión
    return redirect('login') 

@login_required
def dashboard_asesor(request):
    """ Dashboard exclusivo para Asesores Pedagógicos. """
    try:
        if request.user.perfil.rol.nombre_rol != 'Asesor Pedagógico':
            return redirect('home')
    except AttributeError:
        return redirect('home')
    
    # Si es Asesor, renderiza su dashboard
    context = {
        'nombre_usuario': request.user.first_name
    }
    return render(request, 'SIAPE/dashboard_asesor.html', context)



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
