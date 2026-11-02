from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import Throttled
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

# Importaciones nuevas para el registro
from rest_framework import generics
from usuarios.serializers import LoginSerializer, RegistroUsuarioSerializer, UsuarioSerializer

# Endpoint de salud original
@api_view(['GET'])
@permission_classes([AllowAny])
def ping(request):
    """Endpoint de salud para verificar que la API responde."""
    return Response({'message': 'pong'})

# Tu nueva vista para registrar usuarios
class RegistroUsuarioView(generics.CreateAPIView):
    serializer_class = RegistroUsuarioSerializer
    permission_classes = [AllowAny] # Permite que cualquier persona sin sesión pueda registrarse
    # Límite por IP (tasa en settings: REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'])
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_registro'

    def throttled(self, request, wait):
        raise Throttled(wait, detail='Se hicieron demasiados registros desde esta red. Intenta de nuevo más tarde.')


class LoginView(TokenObtainPairView):
    """POST /api/login/ — {email, password} -> {access, refresh}. 401 si no coinciden."""

    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_login'

    def throttled(self, request, wait):
        raise Throttled(wait, detail='Demasiados intentos de inicio de sesión. Espera un momento e intenta de nuevo.')


class MeView(APIView):
    """GET /api/me/ — quién es el usuario del token: {id, email, nombre}. 401 sin token."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)
