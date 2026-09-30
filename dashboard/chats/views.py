from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseForbidden
from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator

from .models import Contacto, Mensaje
from .twilio_client import enviar_plantilla_pedido, enviar_texto


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


@staff_member_required
def enviar_plantilla(request):
    contexto = {'datos': {'telefono': request.GET.get('telefono', '')}}
    if request.method == 'POST':
        datos = {k: request.POST.get(k, '').strip() for k in ('telefono', 'nombre', 'pedido', 'fecha')}
        contexto['datos'] = datos
        if not all(datos.values()):
            contexto['error'] = 'Completa todos los campos.'
        else:
            try:
                enviar_plantilla_pedido(**datos)
                contexto['ok'] = f'Plantilla enviada a {datos["telefono"]}.'
            except TwilioRestException as e:
                contexto['error'] = f'Twilio rechazó el envío: {e.msg}'
    return render(request, 'chats/enviar_plantilla.html', contexto)


@staff_member_required
def lista_chats(request):
    return render(request, 'chats/lista.html')


@staff_member_required
def lista_parcial(request):
    ultimo = Mensaje.objects.filter(contacto=OuterRef('pk')).order_by('-creado')
    contactos = (
        Contacto.objects
        .annotate(ultima_fecha=Subquery(ultimo.values('creado')[:1]), ultimo_texto=Subquery(ultimo.values('texto')[:1]))
        .filter(ultima_fecha__isnull=False)
        .order_by('-ultima_fecha')
    )
    return render(request, 'chats/_lista.html', {'contactos': contactos})


@staff_member_required
def chat(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    return render(request, 'chats/chat.html', {'contacto': contacto, 'mensajes': contacto.mensajes.all()})


@staff_member_required
def chat_mensajes(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    return render(request, 'chats/_mensajes.html', {'contacto': contacto, 'mensajes': contacto.mensajes.all()})


@staff_member_required
@require_POST
def chat_enviar(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    texto = request.POST.get('texto', '').strip()
    error = ''
    if texto and not contacto.ventana_abierta:
        error = 'Pasaron más de 24 h desde el último mensaje del cliente: solo puedes enviar una plantilla.'
    elif texto:
        try:
            enviar_texto(contacto, texto)
        except TwilioRestException as e:
            error = f'Twilio rechazó el envío: {e.msg}'
    return render(request, 'chats/_mensajes.html', {'contacto': contacto, 'mensajes': contacto.mensajes.all(), 'error': error})
