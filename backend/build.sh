#!/usr/bin/env bash
# Script de construcción para Render: se ejecuta en cada despliegue.
set -o errexit  # si un paso falla, el despliegue se detiene

pip install -r requirements.txt

# Reúne los archivos estáticos (admin, DRF) en STATIC_ROOT para que WhiteNoise los sirva.
python manage.py collectstatic --noinput

# Crea/actualiza las tablas en la base de datos de Render (incluye los 6 tipos de incidente).
python manage.py migrate --noinput

# Crea un superusuario para /admin/ solo si se definieron las variables en Render.
# El correo y la clave vienen del entorno; si el usuario ya existe, no pasa nada.
if [[ -n "${DJANGO_SUPERUSER_EMAIL:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
  python manage.py createsuperuser --noinput --nombre "${DJANGO_SUPERUSER_NOMBRE:-Admin}" || true
fi
