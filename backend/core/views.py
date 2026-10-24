from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# Importaciones nuevas para el registro
from rest_framework import generics
from usuarios.serializers import RegistroUsuarioSerializer

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
