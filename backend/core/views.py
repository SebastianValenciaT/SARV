from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def ping(request):
    """Endpoint de salud para verificar que la API responde."""
    return Response({'message': 'pong'})