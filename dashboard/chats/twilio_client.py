import json

from django.conf import settings
from django.utils import timezone
from twilio.rest import Client

from .models import Contacto, Mensaje

PLANTILLA_PEDIDO = 'Hola {0}, tu pedido {1} fue confirmado y llegará el {2}. ¿Qué quieres hacer?'


def enviar_plantilla_pedido(telefono, nombre, pedido, fecha):
    """Abre la conversación con la plantilla aprobada y guarda el mensaje saliente."""
    cliente = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    respuesta = cliente.messages.create(
        from_=settings.TWILIO_WHATSAPP_FROM,
        to=f'whatsapp:{telefono}',
        content_sid=settings.TWILIO_TEMPLATE_PEDIDO_SID,
        content_variables=json.dumps({'1': nombre, '2': pedido, '3': fecha}),
    )
    contacto, _ = Contacto.objects.get_or_create(telefono=telefono, defaults={'nombre': nombre})
    texto = PLANTILLA_PEDIDO.format(nombre, pedido, fecha)
    return Mensaje.objects.create(
        contacto=contacto, direccion=Mensaje.Direccion.SALIENTE, texto=texto, sid=respuesta.sid,
    )


def enviar_texto(contacto, texto):
    """Respuesta libre; solo válida dentro de la ventana de 24 h."""
    cliente = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    respuesta = cliente.messages.create(
        from_=settings.TWILIO_WHATSAPP_FROM, to=f'whatsapp:{contacto.telefono}', body=texto,
    )
    return Mensaje.objects.create(
        contacto=contacto, direccion=Mensaje.Direccion.SALIENTE, texto=texto, sid=respuesta.sid,
    )
