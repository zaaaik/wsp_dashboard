from datetime import timedelta

from django.db import models
from django.utils import timezone

VENTANA = timedelta(hours=24)


class Contacto(models.Model):
    telefono = models.CharField(max_length=32, unique=True)  # formato E.164, ej. +56912345678
    nombre = models.CharField(max_length=120, blank=True)
    ultimo_mensaje_entrante = models.DateTimeField(null=True, blank=True)  # base de la ventana de 24 h
    notas = models.TextField(blank=True)  # notas internas, el cliente no las ve
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre or self.telefono

    @property
    def iniciales(self):
        palabras = self.nombre.split()
        if palabras:
            return ''.join(p[0] for p in palabras[:2]).upper()
        return self.telefono[-2:]

    @property
    def ventana_cierra(self):
        return self.ultimo_mensaje_entrante + VENTANA if self.ultimo_mensaje_entrante else None

    @property
    def ventana_restante(self):
        if not self.ultimo_mensaje_entrante:
            return timedelta(0)
        return max(self.ultimo_mensaje_entrante + VENTANA - timezone.now(), timedelta(0))

    @property
    def ventana_abierta(self):
        return self.ventana_restante > timedelta(0)


class Mensaje(models.Model):
    class Direccion(models.TextChoices):
        ENTRANTE = 'in', 'Entrante'
        SALIENTE = 'out', 'Saliente'

    contacto = models.ForeignKey(Contacto, on_delete=models.CASCADE, related_name='mensajes')
    direccion = models.CharField(max_length=3, choices=Direccion.choices)
    texto = models.TextField(blank=True)
    sid = models.CharField(max_length=64, unique=True, null=True, blank=True)  # MessageSid de Twilio
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['creado']

    def __str__(self):
        return f'{self.get_direccion_display()} {self.contacto}: {self.texto[:40]}'
