import makeWASocket, { useMultiFileAuthState, DisconnectReason } from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';
import pino from 'pino';
import { obtenerRespuesta, pausaHumana } from '../core/conversacion.js';
import http from 'http';
import QRCode from 'qrcode';
import { mantenerDespierto } from '../core/keepalive.js';

// --- Servidor web (Render necesita un puerto abierto) ---
let qrActual = null;
let conectado = false;

http.createServer(async (req, res) => {
  if (req.url === '/ping') return res.writeHead(200).end('pong');
  if (req.url === '/qr' && qrActual) {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(`<h2>Escanea con WhatsApp</h2><img src="${await QRCode.toDataURL(qrActual)}"><script>setTimeout(()=>location.reload(),20000)</script>`);
    return;
  }
  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end(conectado ? '✅ Bot conectado' : '⏳ Bot sin conectar. Abre /qr para escanear');
}).listen(process.env.PORT || 3000);

mantenerDespierto();

async function iniciar() {
  const { state, saveCreds } = await useMultiFileAuthState('sesion');
  const sock = makeWASocket({ auth: state, logger: pino({ level: 'silent' }) });

  sock.ev.on('creds.update', saveCreds);

  // Muestra "escribiendo..." y espera 1-3 segundos antes de responder
  const responder = async (chat, contenido) => {
    await sock.sendPresenceUpdate('composing', chat);
    await pausaHumana();
    await sock.sendPresenceUpdate('paused', chat);
    await sock.sendMessage(chat, contenido);
  };

  sock.ev.on('connection.update', ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      console.log('\nEscanea este QR con WhatsApp (Dispositivos vinculados):\n');
      qrcode.generate(qr, { small: true });
      qrActual = qr;
    }
    if (connection === 'open') {
      conectado = true;
      qrActual = null;
      console.log('✅ Bot conectado a WhatsApp');
    }
    if (connection === 'close') {
      conectado = false;
      const code = lastDisconnect?.error?.output?.statusCode;
      if (code === DisconnectReason.loggedOut) {
        console.log('❌ Sesión cerrada. Borra la carpeta "sesion" y vuelve a ejecutar.');
      } else {
        console.log('🔄 Reconectando...');
        iniciar();
      }
    }
  });

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const msg of messages) {
      const chat = msg.key.remoteJid;
      if (msg.key.fromMe || !chat || chat.endsWith('@g.us') || chat === 'status@broadcast') continue;

      const texto = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';
      const respuesta = obtenerRespuesta(chat, texto);
      if (respuesta) await responder(chat, { text: respuesta });
    }
  });
}

iniciar();
