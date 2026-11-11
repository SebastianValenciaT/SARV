from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from .models import Usuario
#from usuarios.models import Usuario

MENSAJE_CORREO_DUPLICADO = 'Ya existe una cuenta con este correo electrónico.'


class RegistroUsuarioSerializer(serializers.ModelSerializer):
    # Correo declarado a mano para que la unicidad no distinga mayúsculas: el validador
    # que DRF crea desde el modelo compara exacto y dejaría pasar Demo@x si existe demo@x.
    email = serializers.EmailField(
        max_length=254,
        validators=[UniqueValidator(queryset=Usuario.objects.all(), lookup='iexact', message=MENSAJE_CORREO_DUPLICADO)],
    )
    # Declaramos estos campos adicionales que llegan de React pero no están en el modelo
    apellido = serializers.CharField(write_only=True, required=True)
    aceptaPrivacidad = serializers.BooleanField(write_only=True, required=True)

    class Meta:
        model = Usuario
        # Especificamos 'email' tal como está en el modelo
        fields = ['email', 'nombre', 'apellido', 'password', 'aceptaPrivacidad']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_email(self, value):
        # Se guarda siempre en minúsculas (el login también las usa)
        return value.lower()

    def validate_aceptaPrivacidad(self, value):
        if not value:
            raise serializers.ValidationError("Debes aceptar el aviso de privacidad.")
        return value

    def validate(self, attrs):
        # Validadores de AUTH_PASSWORD_VALIDATORS (longitud, comunes, solo números y
        # parecida al correo/nombre). El usuario sin guardar solo sirve para comparar.
        candidato = Usuario(email=attrs['email'], nombre=f"{attrs['nombre']} {attrs['apellido']}")
        try:
            validate_password(attrs['password'], user=candidato)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return attrs

    def create(self, validated_data):
        # Extraemos los campos temporales
        apellido = validated_data.pop('apellido')
        acepta_privacidad = validated_data.pop('aceptaPrivacidad')

        # Combinamos nombre y apellido en el campo 'nombre' que espera la DB
        nombre_completo = f"{validated_data['nombre']} {apellido}"

        # Convertimos el true/false en un registro de fecha y hora
        fecha_aceptacion = timezone.now() if acepta_privacidad else None

        # Usamos el manager del modelo que ya aplica el hash a la contraseña.
        # Respaldo: si dos registros con el mismo correo llegan a la vez, ambos pasan la
        # validación y la base rechaza el segundo; respondemos 400 en lugar de 500.
        try:
            with transaction.atomic():
                usuario = Usuario.objects.create_user(
                    email=validated_data['email'],
                    password=validated_data['password'],
                    nombre=nombre_completo,
                    privacidad_aceptada_en=fecha_aceptacion
                )
        except IntegrityError:
            raise serializers.ValidationError({'email': [MENSAJE_CORREO_DUPLICADO]})
        return usuario


class LoginSerializer(TokenObtainPairSerializer):
    """Mismo login de simplejwt ({email, password} -> {access, refresh}), pero el
    correo se pasa a minúsculas antes de buscar al usuario (se guardan así)."""

    def validate(self, attrs):
        attrs[self.username_field] = attrs[self.username_field].strip().lower()
        return super().validate(attrs)


class UsuarioSerializer(serializers.ModelSerializer):
    """Datos públicos de quien tiene la sesión (GET /api/me/)."""

    class Meta:
        model = Usuario
        fields = ['id', 'email', 'nombre']
