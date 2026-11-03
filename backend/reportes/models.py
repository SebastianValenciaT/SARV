from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models
from django.db.models import DateTimeField, DurationField, ExpressionWrapper, F, Q, Value
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
    duracion_horas = models.PositiveSmallIntegerField(
        'duración (horas)',
        null=True,
        blank=True,
        help_text='Horas que un reporte de este tipo se muestra, contadas desde que se publica '
                  '(creado_en). Vacío = sin límite (nunca expira).',
    )

    class Meta:
        verbose_name = 'tipo de incidente'
        verbose_name_plural = 'tipos de incidente'
        ordering = ['id']

    def __str__(self):
        return self.nombre

    @property
    def es_otro(self):
        return self.nombre == self.NOMBRE_OTRO


class ReporteQuerySet(models.QuerySet):
    """Consultas de reportes que dependen de la expiración (se calcula, no se guarda).

    Es la versión "en base de datos" de Reporte.esta_expirado: sirve para filtrar
    mapa y lista sin recorrer los reportes en Python. Las dos deben coincidir
    (hay una prueba que lo revisa justo en el límite).
    `ahora` se calcula en Python (timezone.now()) y viaja como parámetro, no se
    usa NOW() de la base: así las pruebas pueden congelar el tiempo.
    """

    def con_expiracion(self):
        """Anota `expira_en_bd` = creado_en + duracion_horas * 1 hora.

        En PostgreSQL queda `creado_en + (duracion_horas * interval '1 hour')`.
        Si el tipo no tiene duración (NULL), el resultado también es NULL.
        ExpressionWrapper le dice a Django de qué tipo es el resultado, porque
        no puede adivinarlo al multiplicar un entero por una duración.
        """
        if 'expira_en_bd' in self.query.annotations:
            return self   # ya está anotado (por ejemplo, lista + filtros)
        duracion = ExpressionWrapper(
            F('tipo__duracion_horas') * Value(timedelta(hours=1)), output_field=DurationField()
        )
        return self.annotate(
            expira_en_bd=ExpressionWrapper(F('creado_en') + duracion, output_field=DateTimeField())
        )

    def expirados(self, ahora=None):
        """Sin resolver y con su duración cumplida (ahora >= expira_en)."""
        ahora = ahora or timezone.now()
        return self.con_expiracion().filter(estado=Reporte.Estado.SIN_RESOLVER, expira_en_bd__lte=ahora)

    def no_expirados(self, ahora=None):
        """El complemento exacto de expirados(): los resueltos nunca desaparecen por el tiempo.

        Se escribe en positivo y no con exclude(): con NULL de por medio (tipos sin
        duración), un NOT (... AND expira_en_bd <= ahora) da NULL y la base descartaría
        esas filas.
        """
        ahora = ahora or timezone.now()
        return self.con_expiracion().filter(
            Q(estado=Reporte.Estado.RESUELTO)
            | Q(expira_en_bd__isnull=True)
            | Q(expira_en_bd__gt=ahora)
        )


class Reporte(models.Model):
    # Estado derivado: no se guarda (la columna `estado` sigue en sin_resolver).
    ESTADO_EXPIRADO = 'expirado'

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

    objects = ReporteQuerySet.as_manager()

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
    def expira_en(self):
        """Momento en que deja de mostrarse, o None si su tipo no tiene límite."""
        horas = self.tipo.duracion_horas
        if horas is None or self.creado_en is None:
            return None
        return self.creado_en + timedelta(hours=horas)

    @property
    def esta_expirado(self):
        """Versión en Python de ReporteQuerySet.expirados(). Gana "resuelto": un
        reporte resuelto nunca está expirado, aunque haya pasado su duración."""
        expira_en = self.expira_en
        return (
            self.estado == self.Estado.SIN_RESOLVER
            and expira_en is not None
            and timezone.now() >= expira_en
        )

    @property
    def estado_efectivo(self):
        """Estado que ve la API: sin_resolver, resuelto o expirado."""
        return self.ESTADO_EXPIRADO if self.esta_expirado else self.estado

    @property
    def es_editable(self):
        """RN-14: un reporte resuelto o expirado es de solo lectura (también para el autor)."""
        return self.estado == self.Estado.SIN_RESOLVER and not self.esta_expirado

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
