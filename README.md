# WhatsApp Bot Dashboard

Bot conversacional de WhatsApp con tres conectores intercambiables sobre una misma lógica de respuestas.

## Arquitectura

```
src/
  config.js              # Datos del negocio y catálogo (configurable)
  core/
    conversacion.js      # Lógica de conversación, independiente del canal
    keepalive.js         # Ping periódico para hosting que duerme el servicio
  bots/
    baileys.js           # Conector WhatsApp Web (QR)        -> npm start
    meta-api.js          # Conector WhatsApp Cloud API       -> npm run api
    twilio.js            # Conector Twilio                   -> npm run twilio
```

- **core**: recibe un mensaje y devuelve la respuesta; no conoce el canal.
- **bots**: adaptadores que reciben mensajes del proveedor, llaman al core y envían la respuesta.
- **config**: contenido del negocio, separado del código.

## Requisitos

- Node.js 18+

## Puesta en marcha

1. `npm install`
2. Copia `.env.example` a `.env` y completa las variables.
3. Ejecuta el conector elegido con el script correspondiente.

## Notas

- `.env` y `sesion/` (credenciales y sesión de WhatsApp) están en `.gitignore`; no se versionan.
