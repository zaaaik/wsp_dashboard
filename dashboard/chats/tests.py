from django.test import TestCase, override_settings

from .models import Contacto, Mensaje


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
        self.client.login(username='agente', password='x')
        with patch('chats.twilio_client.Client') as Cliente:
            Cliente.return_value.messages.create.return_value = MagicMock(sid='SM99')
            r = self.client.post('/plantilla/', {
                'telefono': '+56912345678', 'nombre': 'Carlos', 'pedido': '#1024', 'fecha': '3 de octubre'})
        self.assertContains(r, 'Plantilla enviada')
        m = Mensaje.objects.get()
        self.assertEqual((m.direccion, m.sid), ('out', 'SM99'))
        self.assertIn('#1024', m.texto)
