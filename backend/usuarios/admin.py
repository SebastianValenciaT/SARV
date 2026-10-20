from django.contrib import admin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('email', 'nombre', 'is_active', 'date_joined')
    search_fields = ('email', 'nombre')
    readonly_fields = ('password', 'date_joined', 'privacidad_aceptada_en')
