from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models
from django.utils import timezone

from .zonas import LAT_MAX, LAT_MIN, LNG_MAX, LNG_MIN, zona_de


def validar_latitud(valor):
    if not (LAT_MIN <= float(valor) <= LAT_MAX):
        raise ValidationError('La ubicación debe estar dentro de Ciudad Juárez.')


def validar_longitud(valor):
    if not (LNG_MIN <= float(valor) <= LNG_MAX):
        raise ValidationError('La ubicación debe estar dentro de Ciudad Juárez.')


class TipoIncidente(models.Model):
    """Catálogo: Bache, Choque, Inundación, Tráfico, Obstrucción, Otro."""

    NOMBRE_OTRO = 'Otro'

    nombre = models.CharField(max_length=60, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'tipo de incidente'
        verbose_name_plural = 'tipos de incidente'
        ordering = ['id']

    def __str__(self):
        return self.nombre

    @property
    def es_otro(self):
        return self.nombre == self.NOMBRE_OTRO


class Reporte(models.Model):
    class Estado(models.TextChoices):
        SIN_RESOLVER = 'sin_resolver', 'Sin resolver'
        RESUELTO = 'resuelto', 'Resuelto'

    class Gravedad(models.TextChoices):
        LEVE = 'leve', 'Leve'
        MODERADO = 'moderado', 'Moderado'
        GRAVE = 'grave', 'Grave'

    class Zona(models.TextChoices):
        CENTRO = 'centro', 'Centro'
        NORTE = 'norte', 'Norte'
        SUR = 'sur', 'Sur'
        ORIENTE = 'oriente', 'Oriente'
        PONIENTE = 'poniente', 'Poniente'

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reportes')
    tipo = models.ForeignKey(TipoIncidente, on_delete=models.PROTECT, related_name='reportes')
    # Solo cuando el tipo es "Otro": el usuario describe el incidente (semáforo descompuesto, retén, etc.).
    tipo_otro = models.CharField('descripción del tipo "Otro"', max_length=80, blank=True)
    titulo = models.CharField(max_length=120)
    descripcion = models.TextField(validators=[MinLengthValidator(10), MaxLengthValidator(500)])
    gravedad = models.CharField(max_length=10, choices=Gravedad.choices)
    # Texto de la ubicación que ven los demás; las coordenadas son la fuente de verdad (RN-10).
    direccion = models.CharField(max_length=255, blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, validators=[validar_latitud])
    longitud = models.DecimalField(max_digits=9, decimal_places=6, validators=[validar_longitud])
    zona = models.CharField(max_length=10, choices=Zona.choices, blank=True, editable=False)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.SIN_RESOLVER)
    fecha_incidente = models.DateTimeField()
    creado_en = models.DateTimeField(auto_now_add=True)       # RN-12
    actualizado_en = models.DateTimeField(auto_now=True)
    resuelto_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['estado', '-creado_en']),
            models.Index(fields=['zona']),
        ]

    def __str__(self):
        return f'{self.titulo} ({self.get_estado_display()})'

    @property
    def tipo_etiqueta(self):
        """Texto del tipo para mostrar: la descripción propia si es "Otro"."""
        return self.tipo_otro if self.tipo.es_otro and self.tipo_otro else self.tipo.nombre

    @property
    def es_editable(self):
        """RN-14: un reporte resuelto es de solo lectura."""
        return self.estado == self.Estado.SIN_RESOLVER

    def clean(self):
        super().clean()
        if self.tipo_id and self.tipo.es_otro and not self.tipo_otro.strip():
            raise ValidationError({'tipo_otro': 'Describe el tipo de incidente.'})

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if self.tipo_id and not self.tipo.es_otro:
            self.tipo_otro = ''
        if update_fields is None:
            self.zona = zona_de(self.latitud, self.longitud)
        super().save(*args, **kwargs)

    def resolver(self):
        """Marca el reporte como resuelto. Es de un solo sentido (RN-14)."""
        if self.estado == self.Estado.RESUELTO:
            return
        self.estado = self.Estado.RESUELTO
        self.resuelto_en = timezone.now()
        self.save(update_fields=['estado', 'resuelto_en', 'actualizado_en'])


class Imagen(models.Model):
    """Evidencia fotográfica guardada en la base de datos (hasta 3 por reporte)."""

    class Mime(models.TextChoices):
        JPEG = 'image/jpeg', 'JPG'
        PNG = 'image/png', 'PNG'

    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, related_name='imagenes')
    contenido = models.BinaryField(editable=False)
    tipo_mime = models.CharField(max_length=20, choices=Mime.choices)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'imágenes'
        ordering = ['id']


class Reaccion(models.Model):
    """Reacción de un usuario a un reporte. Una por usuario y reporte."""

    class Tipo(models.TextChoices):
        SIN_RESOLVER = 'sin_resolver', 'Sin resolver'
        RESUELTO = 'resuelto', 'Resuelto'

    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, related_name='reacciones')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reacciones')
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'reacción'
        verbose_name_plural = 'reacciones'
        constraints = [
            models.UniqueConstraint(fields=['reporte', 'usuario'], name='una_reaccion_por_usuario_y_reporte'),
        ]


class Denuncia(models.Model):
    """Un usuario marca como falso o dudoso el reporte de otro. Solo se registra."""

    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, related_name='denuncias')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='denuncias')
    motivo = models.CharField(max_length=300, validators=[MinLengthValidator(10)])
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['reporte', 'usuario'], name='una_denuncia_por_usuario_y_reporte'),
        ]
