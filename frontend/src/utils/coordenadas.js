import { LAT_MAX, LAT_MIN, LNG_MAX, LNG_MIN } from '../constants/juarez';

// Misma regla que dentro_de_juarez() en backend/reportes/zonas.py
export function dentroDeJuarez(latitud, longitud) {
  return latitud >= LAT_MIN && latitud <= LAT_MAX && longitud >= LNG_MIN && longitud <= LNG_MAX;
}

// 6 decimales ≈ 10 cm: lo que guarda la base de datos
export function redondear6(valor) {
  return Number(valor.toFixed(6));
}
