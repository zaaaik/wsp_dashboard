from django.contrib import admin

from .models import Contacto, Mensaje


@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ('telefono', 'nombre', 'ultimo_mensaje_entrante')


@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ('creado', 'contacto', 'direccion', 'texto')
    list_filter = ('direccion',)
