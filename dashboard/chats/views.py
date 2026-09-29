from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from twilio.request_validator import RequestValidator

from .models import Contacto, Mensaje


@csrf_exempt
@require_POST
def webhook_twilio(request):
    if settings.TWILIO_AUTH_TOKEN:
        url = settings.PUBLIC_BASE_URL.rstrip('/') + request.path if settings.PUBLIC_BASE_URL else request.build_absolute_uri()
        firma = request.headers.get('X-Twilio-Signature', '')
        if not RequestValidator(settings.TWILIO_AUTH_TOKEN).validate(url, request.POST.dict(), firma):
            return HttpResponseForbidden('Firma inválida')

    telefono = request.POST.get('From', '').removeprefix('whatsapp:')
    sid = request.POST.get('MessageSid') or None
    if not telefono:
        return HttpResponse(status=400)
    if sid and Mensaje.objects.filter(sid=sid).exists():  # reintento de Twilio
        return HttpResponse(status=204)

    texto = request.POST.get('Body') or request.POST.get('ButtonText', '')
    contacto, _ = Contacto.objects.get_or_create(telefono=telefono)
    nombre = request.POST.get('ProfileName')
    if nombre and contacto.nombre != nombre:
        contacto.nombre = nombre
    contacto.ultimo_mensaje_entrante = timezone.now()
    contacto.save()
    Mensaje.objects.create(contacto=contacto, direccion=Mensaje.Direccion.ENTRANTE, texto=texto, sid=sid)
    return HttpResponse(status=204)
