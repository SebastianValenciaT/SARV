/*
  Centro y límites de Ciudad Juárez para los mapas.
  Copiados de backend/reportes/zonas.py (CENTRO_LAT/LNG, LAT_MIN/MAX, LNG_MIN/MAX).
  Si cambian allá, cámbialos aquí.
*/
export const CENTRO_LAT = 31.7385;
export const CENTRO_LNG = -106.487;

export const LAT_MIN = 31.5;
export const LAT_MAX = 31.8;
export const LNG_MIN = -106.7;
export const LNG_MAX = -106.15;

// Formatos que espera Leaflet: [lat, lng] y [[sur, oeste], [norte, este]]
export const CENTRO = [CENTRO_LAT, CENTRO_LNG];
export const LIMITES = [
  [LAT_MIN, LNG_MIN],
  [LAT_MAX, LNG_MAX],
];
