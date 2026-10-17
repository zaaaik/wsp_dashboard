from functools import partial

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required as _staff_member_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseForbidden
from datetime import timedelta

from django.db.models import OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator

from .models import VENTANA, Contacto, Mensaje
from .twilio_client import enviar_plantilla_pedido, enviar_texto

# Las páginas del panel mandan a la pantalla de acceso propia, no a la de Django admin.
staff_member_required = partial(_staff_member_required, login_url='login')


class FormularioAcceso(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise ValidationError('Este usuario no tiene acceso al panel.', code='sin_acceso')


SESION_SIN_RECORDAR = 12 * 3600  # una jornada


class AccesoView(LoginView):
    template_name = 'chats/login.html'
    authentication_form = FormularioAcceso

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        if not self.request.POST.get('recordar'):
            # Vencimiento fijo en el servidor. Una cookie "de navegador" no basta: Chrome con
            # "Continuar donde lo dejaste" la restaura y la sesión seguiría válida.
            self.request.session.set_expiry(SESION_SIN_RECORDAR)
        return respuesta


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
            contexto['error'] = 'Todos los campos son obligatorios.'
        else:
            try:
                enviar_plantilla_pedido(**datos)
                contexto['ok'] = f'Plantilla enviada a {datos["telefono"]}.'
            except TwilioRestException as e:
                contexto['error'] = f'No se pudo enviar el mensaje: {e.msg}'
    return render(request, 'chats/enviar_plantilla.html', contexto)


def _conversaciones():
    """Contactos con al menos un mensaje, más reciente primero, con datos del último mensaje."""
    ultimo = Mensaje.objects.filter(contacto=OuterRef('pk')).order_by('-creado')
    return (
        Contacto.objects
        .annotate(
            ultima_fecha=Subquery(ultimo.values('creado')[:1]),
            ultimo_texto=Subquery(ultimo.values('texto')[:1]),
            ultima_dir=Subquery(ultimo.values('direccion')[:1]),
        )
        .filter(ultima_fecha__isnull=False)
        .order_by('-ultima_fecha')
    )


FILTROS = ('sin_responder', 'abiertas', 'todos', 'humano')


def _contexto_lista(filtro, seleccionado=None, q=''):
    filtro = filtro if filtro in FILTROS else 'todos'
    q = (q or '').strip()
    ahora = timezone.now()
    todas = _conversaciones()
    por_filtro = {
        'sin_responder': todas.filter(ultima_dir=Mensaje.Direccion.ENTRANTE),
        'abiertas': todas.filter(ultimo_mensaje_entrante__gte=ahora - VENTANA),
        'todos': todas,
        'humano': todas.filter(necesita_humano=True),
    }
    # La búsqueda ignora el filtro activo y recorre todos los chats; sin nombre, el contacto se muestra por su teléfono.
    conversaciones = todas.filter(Q(nombre__icontains=q) | Q(telefono__icontains=q)) if q else por_filtro[filtro]
    return {
        'filtro': filtro,
        'seleccionado': seleccionado,
        'q': q,
        'conversaciones': conversaciones,
        'cuentas': {k: v.count() for k, v in por_filtro.items()},
    }


@staff_member_required
def inicio(request):
    ahora = timezone.localtime()
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    sin_responder = _conversaciones().filter(ultima_dir=Mensaje.Direccion.ENTRANTE)
    saludo = 'Buenos días' if ahora.hour < 12 else 'Buenas tardes' if ahora.hour < 20 else 'Buenas noches'
    return render(request, 'chats/inicio.html', {
        'saludo': saludo,
        'nombre': request.user.first_name or request.user.get_username(),
        'ahora': ahora,
        'conversaciones_hoy': Contacto.objects.filter(mensajes__creado__gte=inicio_dia).distinct().count(),
        'sin_responder': sin_responder.count(),
        'ventanas_abiertas': Contacto.objects.filter(ultimo_mensaje_entrante__gte=timezone.now() - VENTANA).count(),
        'enviados_hoy': Mensaje.objects.filter(direccion=Mensaje.Direccion.SALIENTE, creado__gte=inicio_dia).count(),
        'recientes': sin_responder[:5],
    })


@staff_member_required
def chats(request, pk=None):
    contacto = get_object_or_404(Contacto, pk=pk) if pk else None
    contexto = _contexto_lista(request.GET.get('f'), pk, request.GET.get('q'))
    contexto.update({'contacto': contacto, 'mensajes': contacto.mensajes.all() if contacto else []})
    return render(request, 'chats/chats.html', contexto)


@staff_member_required
def lista_parcial(request):
    sel = request.GET.get('sel')
    return render(request, 'chats/_lista.html', _contexto_lista(request.GET.get('f'), int(sel) if sel and sel.isdigit() else None, request.GET.get('q')))


@staff_member_required
def chat_mensajes(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    return render(request, 'chats/_mensajes.html', {'contacto': contacto, 'mensajes': contacto.mensajes.all(), 'oob': True})


@staff_member_required
@require_POST
def chat_enviar(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    texto = request.POST.get('texto', '').strip()
    error = ''
    if texto and not contacto.ventana_abierta:
        error = 'La ventana de 24 h está cerrada. Solo se admite el envío de plantillas.'
    elif texto:
        try:
            enviar_texto(contacto, texto)
        except TwilioRestException as e:
            error = f'No se pudo enviar el mensaje: {e.msg}'
    return render(request, 'chats/_mensajes.html', {'contacto': contacto, 'mensajes': contacto.mensajes.all(), 'error': error, 'oob': True})


@staff_member_required
@require_POST
def chat_humano(request, pk):
    """Marca el chat como "Requiere atención" o lo da por atendido."""
    contacto = get_object_or_404(Contacto, pk=pk)
    contacto.necesita_humano = not contacto.necesita_humano
    contacto.save(update_fields=['necesita_humano'])
    filtro = request.POST.get('f')
    destino = reverse('chat', args=[pk])
    return redirect(f'{destino}?f={filtro}' if filtro in FILTROS else destino)


@staff_member_required
@require_POST
def chat_notas(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    contacto.notas = request.POST.get('notas', '').strip()
    contacto.save(update_fields=['notas'])
    return HttpResponse('Guardado')
