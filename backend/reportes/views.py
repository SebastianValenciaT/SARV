"""Vistas de reportes, mapa, imágenes y geocodificación.

Las vistas genéricas de DRF (ListCreateAPIView, RetrieveAPIView) ya saben listar,
paginar, crear y devolver 404; solo les decimos qué queryset y qué serializer usar.
Todo es público para leer; crear un reporte, reaccionar y denunciar requieren sesión.
"""
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Min, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, Throttled
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import geo
from .filters import filtrar_reportes
from .models import Denuncia, Imagen, Reaccion, Reporte, TipoIncidente
from .serializers import (
    DenunciaSerializer,
    GeoBuscarSerializer,
    GeoInversaSerializer,
    ReaccionSerializer,
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

    throttle_scope = 'reportes_crear'   # tasa en settings: REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']

    def get_throttles(self):
        # Solo el POST tiene límite por usuario; listar sigue libre.
        if self.request.method == 'POST':
            return [ScopedRateThrottle()]
        return []

    def throttled(self, request, wait):
        # Mismo 429 de DRF, con un mensaje propio (DRF agrega cuántos segundos faltan).
        raise Throttled(wait, detail='Has enviado demasiados reportes. Intenta de nuevo más tarde.')

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


# ---------- reacciones y denuncias (requieren sesión) ----------

def error(mensaje, codigo, http_status):
    """Error con mensaje propio. `codigo` permite al frontend distinguirlo de los
    errores genéricos de DRF (por ejemplo, el 403 de "no hay sesión")."""
    return Response({'detail': mensaje, 'codigo': codigo}, status=http_status)


def error_resuelto():
    # 409 Conflict: la petición es válida, pero choca con el estado del reporte (RN-14).
    return error(
        'Este reporte ya está resuelto y no admite cambios.', 'reporte_resuelto', status.HTTP_409_CONFLICT
    )


class AccionReporteView(APIView):
    """Base de las acciones de un usuario sobre un reporte (reaccionar, denunciar).

    Cada subclase define `throttle_scope` (tasa en settings) y `mensaje_throttle`.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    mensaje_throttle = 'Hiciste demasiadas acciones seguidas. Intenta de nuevo más tarde.'

    def throttled(self, request, wait):
        raise Throttled(wait, detail=self.mensaje_throttle)

    def bloquear_reporte(self, pk):
        """Lee el reporte y bloquea su fila hasta que termine la transacción (404 si no existe).

        Debe llamarse dentro de transaction.atomic(). select_for_update() hace que, si el
        autor lo está resolviendo justo ahora, esta petición espere y vea el estado nuevo.
        Va sobre Reporte.objects simple: bloquear con JOINs y conteos no hace falta.
        """
        try:
            return Reporte.objects.select_for_update().get(pk=pk)
        except Reporte.DoesNotExist:
            raise NotFound('Este reporte no existe.')

    def responder_detalle(self, pk, http_status=status.HTTP_200_OK):
        """Responde con el detalle actualizado (mismo JSON que GET /reportes/{id}/), así el
        frontend actualiza conteos, mi_reaccion, ya_denuncie y estado con una sola respuesta."""
        detalle = reportes_con_detalle().get(pk=pk)
        salida = ReporteDetailSerializer(detalle, context={'request': self.request})
        return Response(salida.data, status=http_status)


class ReaccionView(AccionReporteView):
    """PUT /api/reportes/{id}/reaccion/ {tipo} — crea o cambia mi reacción.
    DELETE /api/reportes/{id}/reaccion/ — quita mi reacción (idempotente).

    El autor no reacciona a su propio reporte: su "Resuelto" marca el reporte como
    resuelto (sin crear fila ni contar como confirmación) y su "Sin resolver" se ignora.
    """

    throttle_scope = 'reacciones'
    mensaje_throttle = 'Reaccionaste demasiadas veces seguidas. Espera un momento e intenta de nuevo.'

    def put(self, request, pk):
        entrada = ReaccionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)   # 400 si `tipo` falta o no es válido
        tipo = entrada.validated_data['tipo']

        with transaction.atomic():
            reporte = self.bloquear_reporte(pk)
            if not reporte.es_editable:
                return error_resuelto()
            if reporte.usuario_id == request.user.id:
                if tipo == Reaccion.Tipo.RESUELTO:
                    reporte.resolver()   # la lógica de RN-14 vive en el modelo
            else:
                # Una fila por usuario y reporte: si ya existe, solo cambia el tipo.
                # Si dos peticiones llegan a la vez, Django atrapa el IntegrityError
                # del UniqueConstraint y vuelve a leer la fila (no se duplica).
                Reaccion.objects.update_or_create(
                    reporte=reporte, usuario=request.user, defaults={'tipo': tipo}
                )
        return self.responder_detalle(pk)

    def delete(self, request, pk):
        with transaction.atomic():
            reporte = self.bloquear_reporte(pk)
            if not reporte.es_editable:
                return error_resuelto()
            # Si no había reacción, delete() no borra nada: la respuesta es la misma.
            Reaccion.objects.filter(reporte=reporte, usuario=request.user).delete()
        return self.responder_detalle(pk)


class DenunciaView(AccionReporteView):
    """POST /api/reportes/{id}/denuncias/ {motivo} — registra una denuncia.

    Solo se guarda: el reporte no se oculta ni cambia (no hay panel de administración).
    """

    throttle_scope = 'denuncias'
    mensaje_throttle = 'Enviaste demasiadas denuncias. Intenta de nuevo más tarde.'

    def post(self, request, pk):
        entrada = DenunciaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)   # 400 {motivo: [...]}

        with transaction.atomic():
            reporte = self.bloquear_reporte(pk)
            if not reporte.es_editable:
                return error_resuelto()
            if reporte.usuario_id == request.user.id:
                return error('No puedes denunciar tu propio reporte.', 'reporte_propio', status.HTTP_403_FORBIDDEN)
            if Denuncia.objects.filter(reporte=reporte, usuario=request.user).exists():
                return self.error_duplicada()
            try:
                # atomic() anidado = "savepoint": si el insert falla, solo se deshace
                # esta parte y la transacción de afuera sigue siendo válida.
                with transaction.atomic():
                    Denuncia.objects.create(
                        reporte=reporte, usuario=request.user, motivo=entrada.validated_data['motivo']
                    )
            except IntegrityError:
                # Dos envíos simultáneos: el UniqueConstraint detiene al segundo.
                return self.error_duplicada()
        return self.responder_detalle(pk, status.HTTP_201_CREATED)

    def error_duplicada(self):
        return error('Ya denunciaste este reporte.', 'denuncia_duplicada', status.HTTP_400_BAD_REQUEST)


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
