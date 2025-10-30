from django.shortcuts import render
from rest_framework import viewsets
from .serializer import UsuarioSerializer, RolesSerializer, AreasSerializer, CategoriasAjustesSerializer, DocentesSerializer, DirectoresCarrerasSerializer, CarrerasSerializer, EstudiantesSerializer, AsesoresPedagogicosSerializer, SolicitudesSerializer, EvidenciasSerializer, AsignaturasSerializer, AsignaturasEnCursoSerializer, EntrevistasSerializer, AjusteRazonableSerializer, AjusteAsignadoSerializer
from .models import Usuario, Roles, Areas, CategoriasAjustes, Docentes, DirectoresCarreras, Carreras, Estudiantes, AsesoresPedagogicos, Solicitudes, Evidencias, Asignaturas, AsignaturasEnCurso, Entrevistas, AjusteRazonable, AjusteAsignado
from rest_framework.authentication import SessionAuthentication 
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect
from rest_framework .permissions import IsAuthenticated


# Create your views here.
@login_required 
def pag_inicio(request):
    return render(request, 'SIAPE/inicio.html')

def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registro Exitoso. ¡Bienvenido!")
            return redirect('/')
        else:
            messages.error(request, "No ha sido posible Registrarlo. Por favor revise el formulario por errores.")
    else:
        form = UserCreationForm()
        return render(request, 'SIAPE/registro.html', {'form':form}) 
    
def vista_protegida(request):
    if not request.user.is_authenticated:
    # Redirecciona a login si el usuario no está autenticado
        return redirect('login')
    return render(request, 'vista_protegida.html')

def logout_view(request):
    # Cierra la sesión del usuario y limpia la data de SESSION
    logout(request)
    # Redirige a la página de inicio de sesión
    return redirect('login') 

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

class DocentesViewSet(viewsets.ModelViewSet):
    queryset = Docentes.objects.all()
    serializer_class = DocentesSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class DirectoresCarrerasViewSet(viewsets.ModelViewSet):
    queryset = DirectoresCarreras.objects.all()
    serializer_class = DirectoresCarrerasSerializer
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

class AsesoresPedagogicosViewSet(viewsets.ModelViewSet):
    queryset = AsesoresPedagogicos.objects.all()
    serializer_class = AsesoresPedagogicosSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

class SolicitudesViewSet(viewsets.ModelViewSet):
    queryset = Solicitudes.objects.all()
    serializer_class = SolicitudesSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

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

