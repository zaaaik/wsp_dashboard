// Lógica de la conversación, compartida por el bot con QR (index.js) y el de la API oficial (bot-api.js)
import { negocio, catalogo } from '../config.js';

const menu = () =>
  `🌸 ¡Hola! Bienvenido/a a *${negocio.nombre}* 🌸\n\n` +
  `Escribe el número de la opción:\n` +
  `1️⃣ Ver catálogo y precios\n` +
  `2️⃣ Hacer un pedido\n` +
  `3️⃣ Horario y dirección\n` +
  `4️⃣ Delivery y formas de pago\n` +
  `5️⃣ Hablar con una persona\n\n` +
  `📸 Instagram: ${negocio.instagram}`;

const respuestas = {
  '1': () =>
    `💐 *Catálogo*\n\n` +
    catalogo.map((p) => `• ${p.nombre}: ${p.precio}`).join('\n') +
    `\n\nMás fotos en nuestro Instagram: ${negocio.instagram}`,
  '2': () =>
    `📝 Para tu pedido envíanos en un solo mensaje:\n` +
    `• Producto\n• Fecha y hora de entrega\n• Dirección\n• Nombre de quien recibe\n• Mensaje para la tarjeta (opcional)\n\n` +
    `Te confirmaremos el total en breve 😊`,
  '3': () => `🕒 Horario: ${negocio.horario}\n📍 Dirección: ${negocio.direccion}`,
  '4': () => `🚚 ${negocio.delivery}\n💳 Pagos: ${negocio.pagos}`,
  '5': () => `🙋 En un momento una persona te atenderá. ¡Gracias por tu paciencia!`,
};

// Chats en modo "humano": el bot deja de responder
const conHumano = new Set();
const esperandoPedido = new Set();
const yaSaludado = new Set();

// Devuelve el texto a responder, o null si el bot no debe responder
export function obtenerRespuesta(chat, textoOriginal) {
  const texto = textoOriginal.trim().toLowerCase();

  // "menu" reactiva el bot aunque esté en modo humano
  if (texto === 'menu' || texto === 'menú') {
    conHumano.delete(chat);
    esperandoPedido.delete(chat);
    yaSaludado.add(chat);
    return menu();
  }
  if (conHumano.has(chat)) return null;

  // Después de la opción 2, el siguiente mensaje es el pedido
  if (esperandoPedido.has(chat) && !respuestas[texto]) {
    esperandoPedido.delete(chat);
    conHumano.add(chat);
    return '✅ ¡Recibimos tu pedido! En breve te confirmamos el total y la disponibilidad. 🌷';
  }

  if (respuestas[texto]) {
    esperandoPedido.delete(chat);
    if (texto === '2') esperandoPedido.add(chat);
    if (texto === '5') conHumano.add(chat);
    return respuestas[texto]();
  }
  if (/^(gracias|muchas gracias|ok|okey|listo|perfecto|dale)\b/.test(texto)) {
    return '🌸 ¡Con gusto! Escribe *menu* si necesitas algo más.';
  }
  if (yaSaludado.has(chat)) {
    return 'No entendí 🙈 Escribe un número del *1 al 5* o *menu* para ver las opciones.';
  }
  yaSaludado.add(chat);
  return menu();
}

export const pausaHumana = () => new Promise((r) => setTimeout(r, 1000 + Math.random() * 2000));
