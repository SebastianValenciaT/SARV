from rest_framework import serializers
from django.utils import timezone
from .models import Usuario
#from usuarios.models import Usuario

class RegistroUsuarioSerializer(serializers.ModelSerializer):
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

    def validate_aceptaPrivacidad(self, value):
        if not value:
            raise serializers.ValidationError("Debes aceptar el aviso de privacidad.")
        return value

    def create(self, validated_data):
        # Extraemos los campos temporales
        apellido = validated_data.pop('apellido')
        acepta_privacidad = validated_data.pop('aceptaPrivacidad')
        
        # Combinamos nombre y apellido en el campo 'nombre' que espera la DB
        nombre_completo = f"{validated_data['nombre']} {apellido}"
        
        # Convertimos el true/false en un registro de fecha y hora
        fecha_aceptacion = timezone.now() if acepta_privacidad else None

        # Usamos el manager del modelo que ya aplica el hash a la contraseña
        usuario = Usuario.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            nombre=nombre_completo,
            privacidad_aceptada_en=fecha_aceptacion
        )
        return usuario