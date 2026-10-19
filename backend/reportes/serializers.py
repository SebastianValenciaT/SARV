"""Serializers: convierten modelos a JSON (y validan la entrada cuando haya escritura).

Hay uno por vista (lista, detalle, mapa) para mandar solo los campos necesarios.
Los campos `confirmaciones`, `total_imagenes`, etc. no existen en el modelo:
los calcula la base de datos con `annotate()` en views.py.
"""
from django.urls import reverse
from rest_framework import serializers

from .models import Reaccion, Reporte, TipoIncidente

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
    confirmaciones = serializers.IntegerField(read_only=True)    # annotate
    total_imagenes = serializers.IntegerField(read_only=True)    # annotate
    imagen_principal = serializers.SerializerMethodField()

    class Meta:
        model = Reporte
        fields = [
            'id', 'titulo', 'descripcion', 'tipo', 'tipo_etiqueta', 'direccion', 'zona', 'estado',
            'fecha_incidente', 'creado_en', 'confirmaciones', 'total_imagenes', 'imagen_principal',
        ]

    def get_imagen_principal(self, obj):
        # obj.imagenes.all() usa el prefetch de la vista (sin el binario), no hace otra consulta.
        imagenes = obj.imagenes.all()
        if not imagenes:
            return None
        return url_imagen(self.context['request'], imagenes[0].id)


class ReporteDetailSerializer(ReporteListSerializer):
    # FloatField para que lleguen como número (DecimalField llega como texto).
    latitud = serializers.FloatField(read_only=True)
    longitud = serializers.FloatField(read_only=True)
    imagenes = serializers.SerializerMethodField()
    reacciones = serializers.SerializerMethodField()
    seguimiento = serializers.SerializerMethodField()
    es_autor = serializers.SerializerMethodField()
    mi_reaccion = serializers.SerializerMethodField()
    ya_denuncie = serializers.SerializerMethodField()

    class Meta(ReporteListSerializer.Meta):
        fields = ReporteListSerializer.Meta.fields + [
            'gravedad', 'latitud', 'longitud', 'actualizado_en', 'imagenes', 'reacciones',
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
    latitud = serializers.FloatField(read_only=True)
    longitud = serializers.FloatField(read_only=True)

    class Meta:
        model = Reporte
        fields = ['id', 'latitud', 'longitud', 'tipo', 'tipo_etiqueta', 'fecha_incidente', 'titulo', 'direccion', 'zona']
