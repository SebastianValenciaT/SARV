from django.urls import path

from . import views

urlpatterns = [
    path('tipos/', views.TipoListView.as_view(), name='tipos'),
    path('reportes/', views.ReporteListView.as_view(), name='reporte-lista'),
    # <int:pk> captura el id de la URL y se lo pasa a la vista como `pk`.
    path('reportes/<int:pk>/', views.ReporteDetailView.as_view(), name='reporte-detalle'),
    path('mapa/reportes/', views.MapaReportesView.as_view(), name='mapa-reportes'),
    path('imagenes/<int:pk>/', views.imagen_view, name='imagen'),
    path('geo/buscar/', views.GeoBuscarView.as_view(), name='geo-buscar'),
    path('geo/inversa/', views.GeoInversaView.as_view(), name='geo-inversa'),
]
