// Bot para la API oficial de WhatsApp (Meta Cloud API). Recibe mensajes por webhook.
import http from 'http';
import { obtenerRespuesta, pausaHumana } from '../core/conversacion.js';

try { process.loadEnvFile('.env'); } catch { /* En Render las variables vienen del panel */ }

const { WHATSAPP_TOKEN, PHONE_NUMBER_ID, VERIFY_TOKEN } = process.env;
if (!WHATSAPP_TOKEN || !PHONE_NUMBER_ID || !VERIFY_TOKEN) {
  console.error('❌ Faltan WHATSAPP_TOKEN, PHONE_NUMBER_ID o VERIFY_TOKEN en el archivo .env');
  process.exit(1);
}

const API = `https://graph.facebook.com/v25.0/${PHONE_NUMBER_ID}/messages`;

async function llamarApi(body) {
  const res = await fetch(API, {
    method: 'POST',
    headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ messaging_product: 'whatsapp', ...body }),
  });
  if (!res.ok) console.error('⚠️ Error de la API:', await res.text());
}

async function atender(mensaje) {
  if (mensaje.type !== 'text') return;
  const numero = mensaje.from;
  console.log(`📩 ${numero}: ${mensaje.text.body}`);

  const respuesta = obtenerRespuesta(numero, mensaje.text.body);
  if (!respuesta) return;

  // Marca como leído y muestra "escribiendo..." mientras espera 1-3 segundos
  await llamarApi({ status: 'read', message_id: mensaje.id, typing_indicator: { type: 'text' } });
  await pausaHumana();
  await llamarApi({ to: numero, type: 'text', text: { body: respuesta } });
}

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');

  // Meta verifica el webhook con un GET al configurarlo
  if (req.method === 'GET' && url.pathname === '/webhook') {
    if (url.searchParams.get('hub.mode') === 'subscribe' && url.searchParams.get('hub.verify_token') === VERIFY_TOKEN) {
      console.log('✅ Webhook verificado por Meta');
      res.writeHead(200).end(url.searchParams.get('hub.challenge'));
    } else {
      res.writeHead(403).end();
    }
    return;
  }

  // Meta envía aquí los mensajes que recibe el número
  if (req.method === 'POST' && url.pathname === '/webhook') {
    let cuerpo = '';
    req.on('data', (c) => (cuerpo += c));
    req.on('end', () => {
      res.writeHead(200).end(); // Responder rápido para que Meta no reintente
      try {
        const datos = JSON.parse(cuerpo);
        for (const entrada of datos.entry ?? [])
          for (const cambio of entrada.changes ?? [])
            for (const mensaje of cambio.value?.messages ?? [])
              atender(mensaje).catch((e) => console.error('⚠️', e.message));
      } catch (e) {
        console.error('⚠️ Webhook inválido:', e.message);
      }
    });
    return;
  }

  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' }).end('✅ Bot API funcionando');
}).listen(process.env.PORT || 3000, () => console.log(`🚀 Bot API escuchando en el puerto ${process.env.PORT || 3000}`));
