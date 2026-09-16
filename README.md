# SARV

Plataforma para reportar incidentes viales en tiempo real en la ciudad.

# Integrantes

VALERIA SOSA JUÁREZ - 222761<br>
HÉCTOR FRANCISCO PIMENTEL RESÉNDEZ - 222627<br>
JENNIFER VELO DELGADO - 222745<br>
SEBASTIAN VALENCIA TERRAZAS - 222929<br>
EVELYN NAOMI BRAVO - 222645

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Django 6.1 + Django REST Framework |
| Frontend | React 19 + Vite 8 |
| Base de datos | PostgreSQL |
| Cliente HTTP | Axios |
| Herramienta de build | Vite |

## Requisitos previos

| Herramienta | Versión recomendada |
|---|---|
| Python | 3.12+ |
| Node.js | 18+ |
| PostgreSQL | 14+ |
| npm | 9+ |

---

## Configuración del entorno

### Backend

1. Crear y activar el entorno virtual:

```bash
cd backend
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

2. Instalar dependencias:

```bash
pip install django djangorestframework django-cors-headers python-decouple psycopg2-binary
```

3. Crear el archivo `backend/.env` con las variables de entorno:

```env
SECRET_KEY=django-insecure-change-me-in-env
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.postgresql
DB_NAME=sarv
DB_USER=sarv_user
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=5432

CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

4. Aplicar migraciones e iniciar el servidor:

```bash
python manage.py migrate
python manage.py runserver
```

El backend queda disponible en `http://localhost:8000`.

---

### Frontend

1. Instalar dependencias:

```bash
cd frontend
npm install
```

2. Crear el archivo `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000/api
```

3. Iniciar el servidor de desarrollo:

```bash
npm run dev
```

El frontend queda disponible en `http://localhost:5173`.

---

## Verificación

Con ambos servidores corriendo, abre `http://localhost:5173` — la página debe mostrar **Estado de la API: pong**, lo que confirma que el frontend se comunica correctamente con el backend.

También puedes verificar el backend directamente:

```bash
curl http://localhost:8000/api/ping/
# {"message":"pong"}
```
