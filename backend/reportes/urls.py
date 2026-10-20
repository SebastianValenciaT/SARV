from django.urls import path
from . import views

urlpatterns = [
    path('tipos-incidente/', views.TipoIncidenteListView.as_view(), name='tipos-incidente'),
    path('reportes/', views.CrearReporteView.as_view(), name='crear-reporte'),
]
