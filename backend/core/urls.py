from django.urls import path
from . import views

# Importaciones nuevas para los endpoints de autenticación
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, MeView, RegistroUsuarioView

urlpatterns = [
    # Ruta de salud original
    path('ping/', views.ping, name='ping'),

    # Nuevas rutas para tu frontend de React
    path('registro/', RegistroUsuarioView.as_view(), name='api_registro'),
    path('login/', LoginView.as_view(), name='api_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('me/', MeView.as_view(), name='api_me'),
]
