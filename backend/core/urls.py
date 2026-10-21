from django.urls import path
from . import views

# Importaciones nuevas para los endpoints de autenticación
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegistroUsuarioView

urlpatterns = [
    # Ruta de salud original
    path('ping/', views.ping, name='ping'),
    
    # Nuevas rutas para tu frontend de React
    path('registro/', RegistroUsuarioView.as_view(), name='api_registro'),
    path('login/', TokenObtainPairView.as_view(), name='api_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
]