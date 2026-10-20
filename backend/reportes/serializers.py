from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import Imagen, Reporte, TipoIncidente

MAX_IMAGENES = 3
MAX_TAMANO_IMAGEN = 5 * 1024 * 1024  # 5 MB


class CoordenadaField(serializers.DecimalField):
    def __init__(self, **kwargs):
        super().__init__(max_digits=9, decimal_places=6, **kwargs)

    def to_internal_value(self, data):
        try:
            data = Decimal(str(data).strip()).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            self.fail('invalid')
        return super().to_internal_value(data)

class TipoIncidenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoIncidente
        fields = ['id', 'nombre', 'descripcion']

class CrearReporteSerializer(serializers.ModelSerializer):
    latitud = CoordenadaField()
    longitud = CoordenadaField()
    imagenes = serializers.ListField(
        child=serializers.ImageField(),
        max_length=MAX_IMAGENES,
        required=False,
        write_only=True,
        error_messages={'max_length': f'Puedes adjuntar como máximo {MAX_IMAGENES} imágenes.'},
    )
    tipo_etiqueta = serializers.CharField(read_only=True)
    total_imagenes = serializers.SerializerMethodField()

    class Meta:
        model = Reporte
        fields = [
            'id', 'tipo', 'tipo_otro', 'tipo_etiqueta', 'titulo', 'descripcion', 'gravedad',
            'direccion', 'latitud', 'longitud', 'zona', 'estado', 'fecha_incidente',
            'creado_en', 'imagenes', 'total_imagenes',
        ]
        read_only_fields = ['zona', 'estado', 'creado_en']

    def get_total_imagenes(self, reporte):
        return reporte.imagenes.count()

    def validate_latitud(self, valor):
        Reporte._meta.get_field('latitud').run_validators(valor)
        return valor

    def validate_longitud(self, valor):
        Reporte._meta.get_field('longitud').run_validators(valor)
        return valor

    def validate_fecha_incidente(self, valor):
        if valor > timezone.now():
            raise serializers.ValidationError('La fecha del incidente no puede estar en el futuro.')
        return valor

    def validate_imagenes(self, imagenes):
        for imagen in imagenes:
            if imagen.size > MAX_TAMANO_IMAGEN:
                raise serializers.ValidationError('Cada imagen debe pesar como máximo 5 MB.')
            if imagen.content_type not in Imagen.Mime.values:
                raise serializers.ValidationError('Solo se aceptan imágenes JPG o PNG.')
        return imagenes

    def validate(self, datos):
        tipo = datos.get('tipo')
        if tipo and tipo.es_otro and not datos.get('tipo_otro', '').strip():
            raise serializers.ValidationError({'tipo_otro': 'Describe el tipo de incidente.'})
        return datos

    @transaction.atomic
    def create(self, datos):
        imagenes = datos.pop('imagenes', [])
        reporte = Reporte.objects.create(**datos)
        for imagen in imagenes:
            imagen.seek(0)
            Imagen.objects.create(reporte=reporte, contenido=imagen.read(), tipo_mime=imagen.content_type)
        return reporte
