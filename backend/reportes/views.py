from rest_framework import generics
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from .models import Reporte, TipoIncidente
from .serializers import CrearReporteSerializer, TipoIncidenteSerializer


class TipoIncidenteListView(generics.ListAPIView):
    queryset = TipoIncidente.objects.all()
    serializer_class = TipoIncidenteSerializer
    pagination_class = None


class CrearReporteView(generics.CreateAPIView):
    queryset = Reporte.objects.all()
    serializer_class = CrearReporteSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)
