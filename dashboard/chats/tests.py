from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from .models import Bloqueo, Contacto, Mensaje


@override_settings(TWILIO_AUTH_TOKEN='')
class WebhookTests(TestCase):
    def test_guarda_mensaje_y_evita_duplicados(self):
        datos = {'From': 'whatsapp:+56912345678', 'Body': 'Hola', 'MessageSid': 'SM1', 'ProfileName': 'Carlos'}
        self.assertEqual(self.client.post('/webhook/twilio/', datos).status_code, 204)
        self.client.post('/webhook/twilio/', datos)
        self.assertEqual(Mensaje.objects.count(), 1)
        c = Contacto.objects.get()
        self.assertEqual((c.telefono, c.nombre), ('+56912345678', 'Carlos'))
        self.assertIsNotNone(c.ultimo_mensaje_entrante)

    @override_settings(TWILIO_AUTH_TOKEN='x')
    def test_rechaza_firma_invalida(self):
        r = self.client.post('/webhook/twilio/', {'From': 'whatsapp:+56912345678'})
        self.assertEqual(r.status_code, 403)


class EnviarPlantillaTests(TestCase):
    def test_requiere_staff(self):
        self.assertEqual(self.client.get('/plantilla/').status_code, 302)

    def test_envia_y_guarda_mensaje_saliente(self):
        from unittest.mock import MagicMock, patch

        from django.contrib.auth.models import User
        User.objects.create_user('agente', password='x', is_staff=True)
        self.client.force_login(User.objects.get(username='agente'))
        with patch('chats.twilio_client.Client') as Cliente:
            Cliente.return_value.messages.create.return_value = MagicMock(sid='SM99')
            r = self.client.post('/plantilla/', {
                'telefono': '+56912345678', 'nombre': 'Carlos', 'pedido': '#1024', 'fecha': '3 de octubre'})
        self.assertContains(r, 'Plantilla enviada')
        m = Mensaje.objects.get()
        self.assertEqual((m.direccion, m.sid), ('out', 'SM99'))
        self.assertIn('#1024', m.texto)


class ChatTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        User.objects.create_user('agente', password='x', is_staff=True)
        self.c = Contacto.objects.create(telefono='+56911111111', nombre='Ana')

    def _entra(self):
        self.client.force_login(User.objects.get(username='agente'))

    def test_paginas_requieren_staff(self):
        for url in ('/', f'/chat/{self.c.pk}/', f'/chat/{self.c.pk}/mensajes/'):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_ventana_cerrada_bloquea_texto_libre(self):
        from datetime import timedelta

        from django.utils import timezone
        self.c.ultimo_mensaje_entrante = timezone.now() - timedelta(hours=25)
        self.c.save()
        self._entra()
        r = self.client.post(f'/chat/{self.c.pk}/enviar/', {'texto': 'hola'})
        self.assertContains(r, 'Solo se admite el envío de plantillas')
        self.assertEqual(Mensaje.objects.count(), 0)

    def test_ventana_abierta_envia_texto(self):
        from unittest.mock import MagicMock, patch

        from django.utils import timezone
        self.c.ultimo_mensaje_entrante = timezone.now()
        self.c.save()
        self._entra()
        with patch('chats.twilio_client.Client') as Cliente:
            Cliente.return_value.messages.create.return_value = MagicMock(sid='SM5')
            r = self.client.post(f'/chat/{self.c.pk}/enviar/', {'texto': 'Hola Ana'})
        self.assertContains(r, 'Hola Ana')
        self.assertEqual(Mensaje.objects.get().direccion, 'out')

    def test_lista_muestra_conversacion(self):
        Mensaje.objects.create(contacto=self.c, direccion='in', texto='necesito ayuda')
        self._entra()
        self.assertContains(self.client.get('/chats/lista/'), 'necesito ayuda')

    def test_ficha_muestra_tiempo_restante_de_la_ventana(self):
        from django.utils import timezone
        self.c.ultimo_mensaje_entrante = timezone.now()
        self.c.save()
        self._entra()
        r = self.client.get(f'/chat/{self.c.pk}/')
        self.assertContains(r, 'restantes')
        self.assertContains(self.client.get(f'/chat/{self.c.pk}/mensajes/'), 'id="ventana-ficha" hx-swap-oob')

    def test_boton_cerrar_conserva_filtro_y_busqueda(self):
        self._entra()
        r = self.client.get(f'/chat/{self.c.pk}/?f=abiertas&q=an')
        self.assertContains(r, 'href="/chats/?f=abiertas&q=an"')
        self.assertContains(r, 'aria-label="Cerrar conversación"')
        sin_busqueda = self.client.get(f'/chat/{self.c.pk}/?f=humano')
        self.assertContains(sin_busqueda, 'href="/chats/?f=humano"')

    def test_filtro_requiere_atencion_es_alerta_solo_si_hay_pendientes(self):
        Mensaje.objects.create(contacto=self.c, direccion='in', texto='confirmar pedido')
        self._entra()
        self.assertNotContains(self.client.get('/chats/lista/'), 'class="humano alerta')
        self.client.post(f'/chat/{self.c.pk}/humano/')
        self.assertContains(self.client.get('/chats/lista/'), 'class="humano alerta')

    def test_color_de_avatar_es_estable(self):
        self.assertEqual(self.c.color_avatar, Contacto.objects.get(pk=self.c.pk).color_avatar)
        self.assertRegex(self.c.color_avatar, r'^c[0-7]$')

    def test_marcar_y_resolver_necesita_humano(self):
        Mensaje.objects.create(contacto=self.c, direccion='in', texto='quiero confirmar mi pedido')
        self._entra()
        self.assertNotContains(self.client.get('/chats/lista/?f=humano'), 'quiero confirmar')
        r = self.client.post(f'/chat/{self.c.pk}/humano/', {'f': 'humano'})
        self.assertRedirects(r, f'/chat/{self.c.pk}/?f=humano')
        self.assertContains(self.client.get('/chats/lista/?f=humano'), 'quiero confirmar')
        self.client.post(f'/chat/{self.c.pk}/humano/')
        self.assertNotContains(self.client.get('/chats/lista/?f=humano'), 'quiero confirmar')

    def test_buscar_cliente_por_nombre(self):
        otro = Contacto.objects.create(telefono='+56922222222', nombre='Luis Vega')
        Mensaje.objects.create(contacto=self.c, direccion='in', texto='hola desde Ana')
        Mensaje.objects.create(contacto=otro, direccion='out', texto='hola desde Luis')  # ya respondido
        self._entra()
        r = self.client.get('/chats/lista/?q=vega&f=sin_responder')  # la búsqueda ignora el filtro
        self.assertContains(r, 'hola desde Luis')
        self.assertNotContains(r, 'hola desde Ana')
        self.assertContains(self.client.get('/chats/lista/?q=zzz'), 'Ningún cliente coincide')


class PaginasTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        User.objects.create_user('agente', password='x', is_staff=True)
        self.c = Contacto.objects.create(nombre='Ana Muñoz', telefono='+56911111111')
        Mensaje.objects.create(contacto=self.c, direccion='in', texto='necesito ayuda')
        self.client.force_login(User.objects.get(username='agente'))

    def test_inicio_muestra_metricas_y_pendientes(self):
        r = self.client.get('/')
        self.assertContains(r, 'Sin responder')
        self.assertContains(r, 'necesito ayuda')

    def test_chats_sin_seleccion_y_con_seleccion(self):
        self.assertContains(self.client.get('/chats/'), 'Seleccione una conversación')
        r = self.client.get(f'/chat/{self.c.pk}/')
        self.assertContains(r, 'Notas internas')
        self.assertContains(r, 'AM')

    def test_filtros_de_lista(self):
        self.assertContains(self.client.get('/chats/lista/?f=sin_responder'), 'Ana Muñoz')
        self.assertNotContains(self.client.get('/chats/lista/?f=abiertas'), 'Ana Muñoz')

    def test_guarda_notas(self):
        self.client.post(f'/chat/{self.c.pk}/notas/', {'notas': 'Prefiere transferencia'})
        self.c.refresh_from_db()
        self.assertEqual(self.c.notas, 'Prefiere transferencia')


class AccesoTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        User.objects.create_user('agente', password='clave-test-123', is_staff=True)
        User.objects.create_user('cliente', password='clave-test-123')

    def test_sin_sesion_redirige_al_login_propio(self):
        r = self.client.get('/chats/')
        self.assertRedirects(r, '/login/?next=/chats/')

    def test_pagina_de_login_se_muestra(self):
        r = self.client.get('/login/')
        self.assertContains(r, 'Iniciar sesión')
        self.assertContains(r, 'aria-label="Mostrar contraseña"')  # botón con el ojo

    def test_staff_entra_y_va_al_destino(self):
        r = self.client.post('/login/', {'username': 'agente', 'password': 'clave-test-123', 'next': '/chats/', 'recordar': '1'})
        self.assertRedirects(r, '/chats/', fetch_redirect_response=False)

    def test_sin_recordar_la_sesion_vence_en_el_servidor_en_12_horas(self):
        self.client.post('/login/', {'username': 'agente', 'password': 'clave-test-123'})
        self.assertEqual(self.client.session.get_expiry_age(), 12 * 3600)

    def test_recordar_sesion_la_mantiene_por_dos_semanas(self):
        self.client.post('/login/', {'username': 'agente', 'password': 'clave-test-123', 'recordar': '1'})
        self.assertFalse(self.client.session.get_expire_at_browser_close())
        self.assertEqual(self.client.session.get_expiry_age(), 14 * 24 * 3600)

    def test_clave_incorrecta_muestra_error(self):
        r = self.client.post('/login/', {'username': 'agente', 'password': 'mala'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'class="error"')

    def test_usuario_sin_acceso_al_panel_es_rechazado(self):
        r = self.client.post('/login/', {'username': 'cliente', 'password': 'clave-test-123'})
        self.assertContains(r, 'no tiene acceso al panel')
        self.assertEqual(self.client.get('/chats/').status_code, 302)

    def test_cerrar_sesion(self):
        self.client.force_login(User.objects.get(username='agente'))
        r = self.client.post('/logout/')
        self.assertRedirects(r, '/login/')
        self.assertEqual(self.client.get('/chats/').status_code, 302)


class LimiteDeIntentosTests(TestCase):
    def setUp(self):
        User.objects.create_user('agente', password='clave-test-123', is_staff=True)

    def _falla(self, usuario='agente'):
        return self.client.post('/login/', {'username': usuario, 'password': 'incorrecta'})

    def test_bloquea_tras_cinco_intentos_fallidos(self):
        for _ in range(4):
            self.assertEqual(self._falla().status_code, 200)
        r = self._falla()  # quinto fallo
        self.assertEqual(r.status_code, 429)
        self.assertContains(r, 'id="resta"', status_code=429)
        self.assertTrue(290 < r.context['segundos'] <= 300)

    def test_con_el_usuario_bloqueado_ni_la_clave_correcta_entra(self):
        for _ in range(5):
            self._falla()
        r = self.client.post('/login/', {'username': 'agente', 'password': 'clave-test-123'})
        self.assertEqual(r.status_code, 429)
        self.assertEqual(self.client.get('/chats/').status_code, 302)

    def test_el_bloqueo_es_por_usuario(self):
        User.objects.create_user('otro', password='clave-test-123', is_staff=True)
        for _ in range(5):
            self._falla('agente')
        r = self.client.post('/login/', {'username': 'otro', 'password': 'clave-test-123'})
        self.assertEqual(r.status_code, 302)

    def test_un_acierto_reinicia_el_contador(self):
        for _ in range(4):
            self._falla()
        self.client.post('/login/', {'username': 'agente', 'password': 'clave-test-123'})
        self.client.post('/logout/')
        for _ in range(4):
            self.assertEqual(self._falla().status_code, 200)

    def _pasa_el_bloqueo(self):
        """Simula que el bloqueo venció: Axes borra sus intentos y el plazo guardado queda atrás."""
        from datetime import timedelta

        from axes.models import AccessAttempt
        from django.utils import timezone
        AccessAttempt.objects.all().delete()
        Bloqueo.objects.update(bloqueado_hasta=timezone.now() - timedelta(minutes=1))

    def test_cada_bloqueo_dura_el_doble_que_el_anterior(self):
        for nivel, minutos in [(1, 5), (2, 10), (3, 20), (4, 40)]:
            for _ in range(4):
                self.assertEqual(self._falla().status_code, 200)
            r = self._falla()
            self.assertEqual(r.status_code, 429)
            self.assertTrue(minutos * 60 - 10 < r.context['segundos'] <= minutos * 60)
            self.assertEqual(Bloqueo.objects.get(username='agente').nivel, nivel)
            self._pasa_el_bloqueo()

    def test_intentar_durante_el_bloqueo_no_sube_el_nivel(self):
        for _ in range(5):
            self._falla()
        for _ in range(3):
            self.assertEqual(self._falla().status_code, 429)
        self.assertEqual(Bloqueo.objects.get(username='agente').nivel, 1)

    def test_entrar_bien_borra_el_historial_de_bloqueos(self):
        for _ in range(5):
            self._falla()
        self._pasa_el_bloqueo()
        self.client.post('/login/', {'username': 'agente', 'password': 'clave-test-123'})
        self.assertFalse(Bloqueo.objects.filter(username='agente').exists())

    def test_tras_24_horas_sin_bloqueos_se_empieza_de_nuevo(self):
        from datetime import timedelta

        from django.utils import timezone
        for _ in range(5):
            self._falla()
        self._pasa_el_bloqueo()
        Bloqueo.objects.update(nivel=3, bloqueado_hasta=timezone.now() - timedelta(hours=25))
        for _ in range(5):
            r = self._falla()
        self.assertTrue(290 < r.context['segundos'] <= 300)
        self.assertEqual(Bloqueo.objects.get(username='agente').nivel, 1)
