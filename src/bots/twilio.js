// Bot para WhatsApp vía Twilio (sandbox de pruebas). Twilio envía cada mensaje a /whatsapp
// y el bot responde en la misma petición (TwiML), así que no necesita token.
import http from 'http';
import { obtenerRespuesta, pausaHumana } from '../core/conversacion.js';
import { mantenerDespierto } from '../core/keepalive.js';

const escaparXml = (t) =>
  t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

http.createServer((req, res) => {
  if (req.method === 'POST' && req.url.startsWith('/whatsapp')) {
    let cuerpo = '';
    req.on('data', (c) => (cuerpo += c));
    req.on('end', async () => {
      const datos = new URLSearchParams(cuerpo);
      const numero = datos.get('From') || '';
      const texto = datos.get('Body') || '';
      console.log(`📩 ${numero}: ${texto}`);

      const respuesta = obtenerRespuesta(numero, texto);
      if (respuesta) await pausaHumana();

      res.writeHead(200, { 'Content-Type': 'text/xml' });
      res.end(
        respuesta
          ? `<Response><Message>${escaparXml(respuesta)}</Message></Response>`
          : '<Response></Response>'
      );
    });
    return;
  }

  if (req.url === '/ping') return res.writeHead(200).end('pong');
  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' }).end('✅ Bot Twilio funcionando');
}).listen(process.env.PORT || 3000, () => console.log(`🚀 Bot Twilio escuchando en el puerto ${process.env.PORT || 3000}`));

mantenerDespierto();
