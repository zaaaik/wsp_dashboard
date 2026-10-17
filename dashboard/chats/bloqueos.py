"""Bloqueo progresivo del acceso: 5 min, y cada nuevo bloqueo dura el doble (10, 20, 40 min…).

Django Axes cuenta los intentos fallidos y bloquea al usuario. Aquí se decide cuánto dura cada bloqueo.
Axes borra sus registros cuando el bloqueo vence, así que el nivel se guarda en el modelo Bloqueo.
"""
import math
from datetime import timedelta

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.shortcuts import render
from django.utils import timezone

from axes.signals import user_locked_out

from .models import Bloqueo

BASE = timedelta(minutes=5)
TOPE = timedelta(hours=24)  # un bloqueo nunca dura más que esto
OLVIDO = timedelta(hours=24)  # si pasa este tiempo sin nuevo bloqueo, se vuelve a empezar en 5 min


def duracion(nivel):
    return min(BASE * 2 ** max(nivel - 1, 0), TOPE)


def tiempo_legible(delta):
    """Ej.: "4 min 32 s" o "1 h 05 min 00 s". La página de bloqueo usa el mismo formato en su cuenta regresiva."""
    segundos = max(math.ceil(delta.total_seconds()), 0)
    horas, resto = divmod(segundos, 3600)
    minutos, seg = divmod(resto, 60)
    if horas:
        return f'{horas} h {minutos:02d} min {seg:02d} s'
    return f'{minutos} min {seg:02d} s'


def cooloff(request):
    """Duración del bloqueo para el usuario del intento actual (AXES_COOLOFF_TIME)."""
    username = request.POST.get('username') if request is not None else None
    bloqueo = Bloqueo.objects.filter(username=username).first() if username else None
    return duracion(bloqueo.nivel if bloqueo else 1)


@receiver(user_locked_out)
def registrar_bloqueo(sender, request, username, **kwargs):
    if not username:
        return
    ahora = timezone.now()
    bloqueo, _ = Bloqueo.objects.get_or_create(username=username)
    if bloqueo.bloqueado_hasta and bloqueo.bloqueado_hasta > ahora:
        return  # sigue el mismo bloqueo, no sube de nivel
    olvidado = bloqueo.bloqueado_hasta is None or ahora - bloqueo.bloqueado_hasta > OLVIDO
    bloqueo.nivel = 1 if olvidado else bloqueo.nivel + 1
    bloqueo.bloqueado_hasta = ahora + duracion(bloqueo.nivel)
    bloqueo.save()


@receiver(user_logged_in)
def olvidar_bloqueos(sender, user, **kwargs):
    Bloqueo.objects.filter(username=user.get_username()).delete()


def respuesta_bloqueo(request, response=None, credentials=None):
    """Página que ve el usuario bloqueado (AXES_LOCKOUT_CALLABLE)."""
    username = (credentials or {}).get('username') or request.POST.get('username')
    bloqueo = Bloqueo.objects.filter(username=username).first() if username else None
    ahora = timezone.now()
    hasta = bloqueo.bloqueado_hasta if bloqueo and bloqueo.bloqueado_hasta else ahora + BASE
    restante = max(hasta - ahora, timedelta(0))
    contexto = {
        'tiempo': tiempo_legible(restante),
        'segundos': math.ceil(restante.total_seconds()),
        'hasta': hasta.isoformat(),
    }
    return render(request, 'chats/bloqueado.html', contexto, status=429)
