/*
  geo.js — Geocodificación a través del backend (el navegador nunca llama
  a Nominatim directamente). Solo búsquedas puntuales: sin autocompletado.
  Ambas funciones aceptan { signal } para cancelar respuestas obsoletas.
*/
import api from './api';

// Dirección escrita -> { lat, lng, direccion, resultados: [{ lat, lng, direccion }] }
export async function buscarDireccion(q, config) {
  const { data } = await api.get('/geo/buscar/', { ...config, params: { q } });
  return data;
}

// Coordenadas -> { direccion } (calle, número y colonia)
export async function direccionInversa(lat, lng, config) {
  const { data } = await api.get('/geo/inversa/', { ...config, params: { lat, lng } });
  return data;
}
