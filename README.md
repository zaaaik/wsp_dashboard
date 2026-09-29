# Bot Floribri

Bot de WhatsApp para Florería Floribri.

## Estructura

```
src/
  config.js            # Datos del negocio y catálogo
  core/conversacion.js # Lógica de respuestas
  core/keepalive.js    # Ping para mantener vivo el servicio (Render)
  bots/baileys.js      # Bot vía WhatsApp Web (QR)          -> npm start
  bots/meta-api.js     # Bot vía WhatsApp Cloud API (Meta)  -> npm run api
  bots/twilio.js       # Bot vía Twilio                     -> npm run twilio
```

## Uso

1. `npm install`
2. Copia `.env.example` a `.env` y completa los valores.
3. Ejecuta el bot que prefieras con uno de los comandos de arriba.
