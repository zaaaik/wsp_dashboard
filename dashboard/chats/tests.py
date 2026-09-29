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
