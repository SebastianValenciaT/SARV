"""Serializers: convierten modelos a JSON (y validan la entrada cuando haya escritura).

Hay uno por vista (lista, detalle, mapa) para mandar solo los campos necesarios.
Los campos `confirmaciones`, `total_imagenes`, etc. no existen en el modelo:
los calcula la base de datos con `annotate()` en views.py.

Coordenadas: en el modelo son DecimalField, que DRF convierte a texto ("31.739300").
Los tres serializers usan `FloatField(read_only=True)` para que lleguen como número
(31.7393), que es lo que necesita Leaflet.
"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers

from .imagenes import procesar_imagen
from .models import Imagen, Reaccion, Reporte, TipoIncidente, validar_latitud, validar_longitud
from .zonas import dentro_de_juarez

MAX_IMAGENES = 3
# El reloj del celular puede ir algo adelantado: se toleran unos minutos "en el futuro".
MARGEN_FECHA_FUTURA = timedelta(minutes=5)

# Convierte un datetime al mismo formato ISO que usan los demás campos de fecha.
fecha_iso = serializers.DateTimeField().to_representation


def url_imagen(request, imagen_id):
    """URL absoluta del endpoint que sirve el binario de una imagen."""
    return request.build_absolute_uri(reverse('imagen', args=[imagen_id]))


class TipoIncidenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoIncidente
        fields = ['id', 'nombre']


class ReporteListSerializer(serializers.ModelSerializer):
    tipo_etiqueta = serializers.CharField(read_only=True)        # propiedad del modelo
    latitud = serializers.FloatField(read_only=True)             # número, no texto
    longitud = serializers.FloatField(read_only=True)
    confirmaciones = serializers.IntegerField(read_only=True)    # annotate
    total_imagenes = serializers.IntegerField(read_only=True)    # annotate
    imagen_principal = serializers.SerializerMethodField()

    class Meta:
        model = Reporte
        fields = [
            'id', 'titulo', 'descripcion', 'tipo', 'tipo_etiqueta', 'direccion', 'zona', 'estado',
            'latitud', 'longitud', 'fecha_incidente', 'creado_en', 'confirmaciones', 'total_imagenes',
            'imagen_principal',
        ]

    def get_imagen_principal(self, obj):
        # obj.imagenes.all() usa el prefetch de la vista (sin el binario), no hace otra consulta.
        imagenes = obj.imagenes.all()
        if not imagenes:
            return None
        return url_imagen(self.context['request'], imagenes[0].id)


class ReporteDetailSerializer(ReporteListSerializer):
    # latitud/longitud se heredan de ReporteListSerializer (como número)
    imagenes = serializers.SerializerMethodField()
    reacciones = serializers.SerializerMethodField()
    seguimiento = serializers.SerializerMethodField()
    es_autor = serializers.SerializerMethodField()
    mi_reaccion = serializers.SerializerMethodField()
    ya_denuncie = serializers.SerializerMethodField()

    class Meta(ReporteListSerializer.Meta):
        fields = ReporteListSerializer.Meta.fields + [
            'gravedad', 'actualizado_en', 'imagenes', 'reacciones',
            'seguimiento', 'es_autor', 'mi_reaccion', 'ya_denuncie',
        ]

    def _usuario(self):
        """Usuario con sesión, o None si es anónimo (hoy siempre, hasta tener JWT)."""
        usuario = self.context['request'].user
        return usuario if usuario.is_authenticated else None

    def get_imagenes(self, obj):
        request = self.context['request']
        return [{'id': img.id, 'url': url_imagen(request, img.id)} for img in obj.imagenes.all()]

    def get_reacciones(self, obj):
        return {
            Reaccion.Tipo.SIN_RESOLVER: obj.reacciones_sin_resolver,
            Reaccion.Tipo.RESUELTO: obj.reacciones_resuelto,
        }

    def get_seguimiento(self, obj):
        """Las 3 fases se calculan con los datos del reporte; no hay tabla de seguimiento."""
        confirmado = obj.primera_confirmacion is not None
        resuelto = obj.resuelto_en is not None
        return [
            {
                'fase': 'creado',
                'completada': True,
                'fecha': fecha_iso(obj.creado_en),
                'autor': obj.usuario.nombre,
            },
            {
                'fase': 'confirmado',
                'completada': confirmado,
                'fecha': fecha_iso(obj.primera_confirmacion) if confirmado else None,
                'confirmaciones': obj.confirmaciones,
            },
            {
                'fase': 'resuelto',
                'completada': resuelto,
                'fecha': fecha_iso(obj.resuelto_en) if resuelto else None,
            },
        ]

    def get_es_autor(self, obj):
        usuario = self._usuario()
        return usuario is not None and obj.usuario_id == usuario.id

    def get_mi_reaccion(self, obj):
        usuario = self._usuario()
        if usuario is None:
            return None
        # .first() devuelve None si el usuario no ha reaccionado.
        return obj.reacciones.filter(usuario=usuario).values_list('tipo', flat=True).first()

    def get_ya_denuncie(self, obj):
        usuario = self._usuario()
        return usuario is not None and obj.denuncias.filter(usuario=usuario).exists()


class ReporteMapaSerializer(serializers.ModelSerializer):
    tipo_etiqueta = serializers.CharField(read_only=True)
    latitud = serializers.FloatField(read_only=True)             # mismo formato que lista y detalle
    longitud = serializers.FloatField(read_only=True)

    class Meta:
        model = Reporte
        fields = ['id', 'latitud', 'longitud', 'tipo', 'tipo_etiqueta', 'fecha_incidente', 'titulo', 'direccion', 'zona']



# ---------- creación de reportes (POST /api/reportes/) ----------

class CoordenadaField(serializers.DecimalField):
    """Decimal de 6 decimales que REDONDEA en vez de rechazar.

    El GPS manda valores como 31.73932847261. DRF valida la cantidad de decimales
    antes de redondear (validate_precision corre antes que quantize), así que el
    campo normal los rechazaría. Aquí redondeamos primero (6 decimales ≈ 10 cm).
    """

    SEIS_DECIMALES = Decimal('0.000001')

    def __init__(self, **kwargs):
        kwargs.setdefault('max_digits', 9)
        kwargs.setdefault('decimal_places', 6)
        super().__init__(**kwargs)

    def validate_precision(self, value):
        redondeado = value.quantize(self.SEIS_DECIMALES, rounding=ROUND_HALF_UP)
        return super().validate_precision(redondeado)


class ReporteCreateSerializer(serializers.ModelSerializer):
    """Valida la entrada del POST. La respuesta se arma con ReporteDetailSerializer.

    `usuario`, `estado`, `zona` y las fechas automáticas no están en `fields`:
    si el cliente los manda, se ignoran. Los asigna el servidor.
    """

    # Al declarar el campo a mano se pierden los validadores del modelo: se agregan aquí.
    latitud = CoordenadaField(validators=[validar_latitud])
    longitud = CoordenadaField(validators=[validar_longitud])
    imagenes = serializers.ListField(
        child=serializers.FileField(),
        max_length=MAX_IMAGENES,
        required=False,
        write_only=True,
    )

    class Meta:
        model = Reporte
        fields = [
            'tipo', 'tipo_otro', 'titulo', 'descripcion', 'gravedad',
            'latitud', 'longitud', 'direccion', 'fecha_incidente', 'imagenes',
        ]

    def validate_fecha_incidente(self, valor):
        if valor > timezone.now() + MARGEN_FECHA_FUTURA:
            raise serializers.ValidationError('La fecha del incidente no puede estar en el futuro.')
        return valor

    def validate_imagenes(self, archivos):
        # Devuelve [(bytes_limpios, tipo_mime), ...]; create() los guarda.
        return [procesar_imagen(archivo, f'La imagen {i}') for i, archivo in enumerate(archivos, start=1)]

    def validate(self, datos):
        # Misma regla que Reporte.clean(): ModelSerializer no llama a clean().
        tipo_otro = datos.get('tipo_otro', '').strip()
        datos['tipo_otro'] = tipo_otro
        if datos['tipo'].es_otro and not tipo_otro:
            raise serializers.ValidationError({'tipo_otro': 'Describe el tipo de incidente.'})
        return datos

    def create(self, validated_data):
        imagenes = validated_data.pop('imagenes', [])
        # Todo o nada: si falla una imagen, tampoco queda el reporte.
        with transaction.atomic():
            reporte = Reporte.objects.create(
                usuario=self.context['request'].user,
                estado=Reporte.Estado.SIN_RESOLVER,
                **validated_data,
            )   # Reporte.save() calcula la zona
            for contenido, tipo_mime in imagenes:
                Imagen.objects.create(reporte=reporte, contenido=contenido, tipo_mime=tipo_mime)
        return reporte

# ---------- geocodificación (solo validan los query params) ----------

class GeoBuscarSerializer(serializers.Serializer):
    # CharField quita espacios al inicio/fin antes de validar la longitud
    q = serializers.CharField(min_length=3, max_length=200)


class GeoInversaSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()

    def validate(self, datos):
        # validate() recibe todos los campos ya convertidos: se revisan juntos
        if not dentro_de_juarez(datos['lat'], datos['lng']):
            raise serializers.ValidationError('Las coordenadas están fuera de Ciudad Juárez.')
        return datos
