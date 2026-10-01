# Panel de atención por WhatsApp

Aplicación web para gestionar conversaciones de WhatsApp a través de Twilio. Desarrollada con Django y PostgreSQL.

## Funciones

- Recepción de mensajes mediante webhook de Twilio, con validación de firma.
- Bandeja de conversaciones con filtros, historial, respuesta de agentes y notas internas.
- Control de la ventana de 24 horas de WhatsApp.
- Envío de plantillas aprobadas con botones de respuesta rápida.

## Estructura

```
dashboard/
  config/            # Configuración de Django
  chats/
    models.py        # Contacto y Mensaje
    views.py         # Panel, webhook y envíos
    twilio_client.py # Integración con la API de Twilio
    templates/       # Interfaz (HTMX)
  Procfile           # Comando de arranque en Railway
  requirements.txt
```

## Desarrollo local

```bash
cd dashboard
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Pruebas:

```bash
python manage.py test
```

## Variables de entorno

Se describen en `dashboard/.env.example`. Las principales:

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta de Django |
| `DEBUG` | `False` en producción |
| `DATABASE_URL` | Conexión a PostgreSQL (SQLite si se omite) |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Dominio de la aplicación |
| `PUBLIC_BASE_URL` | URL pública, usada para validar la firma de Twilio |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | Credenciales de Twilio |
| `TWILIO_WHATSAPP_FROM` | Número remitente, formato `whatsapp:+...` |
| `TWILIO_TEMPLATE_PEDIDO_SID` | Content SID de la plantilla de pedido |

## Despliegue

Railway, con directorio raíz `dashboard` y un servicio PostgreSQL asociado. El comando de arranque aplica migraciones, recopila archivos estáticos e inicia Gunicorn.

Webhook de Twilio: `https://<dominio>/webhook/twilio/` (método POST).
