from django.contrib import admin

from .models import Bloqueo, Contacto, Mensaje


@admin.register(Bloqueo)
class BloqueoAdmin(admin.ModelAdmin):
    list_display = ('username', 'nivel', 'bloqueado_hasta')  # borrar la fila reinicia los bloqueos del usuario


@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ('telefono', 'nombre', 'ultimo_mensaje_entrante')


@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ('creado', 'contacto', 'direccion', 'texto')
    list_filter = ('direccion',)
