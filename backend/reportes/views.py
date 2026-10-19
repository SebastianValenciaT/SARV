"""Vistas de reportes, mapa, imágenes y geocodificación.

Las vistas genéricas de DRF (ListCreateAPIView, RetrieveAPIView) ya saben listar,
paginar, crear y devolver 404; solo les decimos qué queryset y qué serializer usar.
Todo es público para leer; crear un reporte requiere sesión.
"""
from django.db.models import Count, F, Min, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import geo
from .filters import filtrar_reportes
from .models import Imagen, Reaccion, Reporte, TipoIncidente
from .serializers import (
    GeoBuscarSerializer,
    GeoInversaSerializer,
    ReporteCreateSerializer,
    ReporteDetailSerializer,
    ReporteListSerializer,
    ReporteMapaSerializer,
    TipoIncidenteSerializer,
)


def reportes_con_conteos():
    """Queryset base de lista y detalle, preparado para evitar consultas N+1.

    - select_related('tipo'): trae el tipo en la misma consulta (JOIN).
    - annotate(Count(...)): la base de datos cuenta reacciones e imágenes.
      distinct=True evita contar doble al unir dos tablas a la vez.
    - Prefetch de imágenes con only(): solo id, nunca el binario `contenido`.
    """
    return (
        Reporte.objects.select_related('tipo')
        .annotate(
            confirmaciones=Count('reacciones', distinct=True),
            total_imagenes=Count('imagenes', distinct=True),
        )
        .prefetch_related(Prefetch('imagenes', queryset=Imagen.objects.only('id', 'reporte_id')))
    )


def reportes_con_detalle():
    """Queryset del detalle: lo de la lista + conteos por tipo de reacción y autor."""
    return reportes_con_conteos().select_related('usuario').annotate(
        reacciones_sin_resolver=Count(
            'reacciones', filter=Q(reacciones__tipo=Reaccion.Tipo.SIN_RESOLVER), distinct=True
        ),
        reacciones_resuelto=Count(
            'reacciones', filter=Q(reacciones__tipo=Reaccion.Tipo.RESUELTO), distinct=True
        ),
        # Fase 2 del seguimiento: primera reacción de alguien distinto al autor.
        primera_confirmacion=Min(
            'reacciones__creada_en', filter=~Q(reacciones__usuario=F('usuario'))
        ),
    )


class TipoListView(generics.ListAPIView):
    """GET /api/tipos/ — catálogo de tipos de incidente (sin paginar)."""

    queryset = TipoIncidente.objects.all()
    serializer_class = TipoIncidenteSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class ReporteListCreateView(generics.ListCreateAPIView):
    """GET /api/reportes/ — listado paginado público, del más reciente al más antiguo.
    POST /api/reportes/ — crea un reporte (requiere sesión; multipart con hasta 3 imágenes).
    """

    def get_permissions(self):
        # El permiso depende del método: leer es público, crear requiere sesión.
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ReporteCreateSerializer
        return ReporteListSerializer

    def get_queryset(self):
        queryset = filtrar_reportes(reportes_con_conteos(), self.request.query_params)
        return queryset.order_by('-creado_en', '-id')

    def create(self, request, *args, **kwargs):
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)   # 400 con el detalle por campo
        reporte = entrada.save()
        # Se vuelve a leer con los conteos del detalle para responder igual que GET /reportes/{id}/
        detalle = reportes_con_detalle().get(pk=reporte.pk)
        salida = ReporteDetailSerializer(detalle, context=self.get_serializer_context())
        return Response(salida.data, status=status.HTTP_201_CREATED)


class ReporteDetailView(generics.RetrieveAPIView):
    """GET /api/reportes/{id}/ — detalle con reacciones y seguimiento."""

    serializer_class = ReporteDetailSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return reportes_con_detalle()


class MapaReportesView(generics.ListAPIView):
    """GET /api/mapa/reportes/ — pines ligeros, solo `sin_resolver`, sin paginar."""

    serializer_class = ReporteMapaSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = Reporte.objects.select_related('tipo').filter(estado=Reporte.Estado.SIN_RESOLVER)
        return filtrar_reportes(queryset, self.request.query_params).order_by('-creado_en', '-id')


@api_view(['GET'])
@permission_classes([AllowAny])
def imagen_view(request, pk):
    """GET /api/imagenes/{id}/ — devuelve el binario de la imagen, no JSON."""
    imagen = get_object_or_404(Imagen.objects.only('contenido', 'tipo_mime'), pk=pk)
    # PostgreSQL devuelve el BinaryField como memoryview; bytes() lo convierte.
    response = HttpResponse(bytes(imagen.contenido), content_type=imagen.tipo_mime)
    # Las imágenes no se editan: el navegador puede guardarlas en caché un día.
    response['Cache-Control'] = 'public, max-age=86400'
    # Evita que el navegador "adivine" otro tipo de contenido distinto a tipo_mime.
    response['X-Content-Type-Options'] = 'nosniff'
    return response


# ---------- geocodificación (Nominatim, siempre a través del backend) ----------

# TODO(auth): cambiar a IsAuthenticated cuando exista el login (el contrato pide sesión).
GEO_PERMISSION_CLASSES = [AllowAny]

MENSAJE_NO_DISPONIBLE = 'El servicio de direcciones no está disponible. Intenta de nuevo en unos minutos.'


class GeoBaseView(APIView):
    """Configuración común: permiso temporal y límite de peticiones (scope 'geo' en settings)."""

    permission_classes = GEO_PERMISSION_CLASSES
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'geo'

    def validar(self, serializer_class):
        serializer = serializer_class(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)  # 400 con el detalle del error
        return serializer.validated_data

    def no_disponible(self):
        return Response({'detail': MENSAJE_NO_DISPONIBLE}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class GeoBuscarView(GeoBaseView):
    """GET /api/geo/buscar/?q= — dirección escrita -> hasta 5 candidatos.

    Respuesta: {lat, lng, direccion, resultados: [{lat, lng, direccion}, ...]}.
    Los campos de nivel superior son los del primer candidato (contrato anterior).
    """

    def get(self, request):
        datos = self.validar(GeoBuscarSerializer)
        try:
            resultados = geo.buscar(datos['q'])
        except geo.NominatimNoDisponible:
            return self.no_disponible()
        if not resultados:
            return Response(
                {'detail': 'No encontramos esa dirección en Ciudad Juárez. Revisa el texto o coloca el pin a mano.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({**resultados[0], 'resultados': resultados})


class GeoInversaView(GeoBaseView):
    """GET /api/geo/inversa/?lat=&lng= — coordenadas -> {direccion} corta."""

    def get(self, request):
        datos = self.validar(GeoInversaSerializer)
        try:
            resultado = geo.inversa(datos['lat'], datos['lng'])
        except geo.NominatimNoDisponible:
            return self.no_disponible()
        if resultado is None:
            return Response(
                {'detail': 'No encontramos una dirección para esta ubicación. Escríbela a mano.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(resultado)
