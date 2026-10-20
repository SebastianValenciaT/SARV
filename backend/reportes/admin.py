from django.contrib import admin

from .models import Denuncia, Imagen, Reaccion, Reporte, TipoIncidente


@admin.register(TipoIncidente)
class TipoIncidenteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')


@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'estado', 'zona', 'usuario', 'creado_en')
    list_filter = ('estado', 'tipo', 'zona')
    search_fields = ('titulo', 'direccion')


admin.site.register(Reaccion)
admin.site.register(Denuncia)
admin.site.register(Imagen)
