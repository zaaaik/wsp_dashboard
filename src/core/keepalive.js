// Mantiene despierto el servidor en Render (plan gratis): se visita a sí mismo cada 5 minutos,
// con reintentos si un ping falla. Solo se activa en Render (RENDER_EXTERNAL_URL).
const INTERVALO = 5 * 60 * 1000;
const REINTENTOS = 3;

async function ping(url) {
  for (let intento = 1; intento <= REINTENTOS; intento++) {
    try {
      const res = await fetch(`${url}/ping`, { signal: AbortSignal.timeout(10000) });
      if (res.ok) return console.log('🏓 Ping OK');
    } catch (e) {
      console.log(`Ping falló (intento ${intento}/${REINTENTOS}): ${e.message}`);
    }
    await new Promise((r) => setTimeout(r, 15000));
  }
}

export function mantenerDespierto() {
  const url = process.env.RENDER_EXTERNAL_URL;
  if (!url) return;
  setInterval(() => ping(url), INTERVALO);
}
