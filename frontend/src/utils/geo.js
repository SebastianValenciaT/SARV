/*
  geo.js — Proyección TEMPORAL de coordenadas al mapa ilustrativo (SVG).
  Convierte latitud/longitud en porcentajes { left, top } dentro del
  rectángulo de Ciudad Juárez. Cuando se integre Leaflet, este archivo se
  elimina: Leaflet coloca los pines con las coordenadas reales.
*/

// Copiadas de backend/reportes/zonas.py (LAT_MIN/MAX, LNG_MIN/MAX). Si cambian allá, cámbialas aquí.
export const LAT_MIN = 31.5;
export const LAT_MAX = 31.8;
export const LNG_MIN = -106.7;
export const LNG_MAX = -106.15;

function clamp(valor, min, max) {
  return Math.min(Math.max(valor, min), max);
}

export function proyectarAPorcentaje(latitud, longitud) {
  // La longitud crece hacia el oriente (izquierda → derecha).
  const left = ((longitud - LNG_MIN) / (LNG_MAX - LNG_MIN)) * 100;
  // La latitud crece hacia el norte, pero en pantalla `top` crece hacia abajo: se invierte.
  const top = ((LAT_MAX - latitud) / (LAT_MAX - LAT_MIN)) * 100;
  // Margen para que el pin no quede cortado en el borde.
  return { left: clamp(left, 3, 97), top: clamp(top, 5, 95) };
}
