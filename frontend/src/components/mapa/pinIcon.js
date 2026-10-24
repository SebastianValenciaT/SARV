/*
  pinIcon.js — Ícono de los pines del mapa.
  No usamos el marcador por defecto de Leaflet: sus imágenes PNG no se
  resuelven bien con Vite. En su lugar, L.divIcon pinta HTML propio: el
  componente <Icon> convertido a texto con renderToStaticMarkup.
*/
import L from 'leaflet';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import Icon from '../common/Icon';

const TAMANO_NORMAL = 34;
const TAMANO_SELECCIONADO = 44;
const PICO = 6; // el pico inferior sobresale unos píxeles

// Cada combinación (ícono, seleccionado) se crea una sola vez y se reutiliza.
const cache = new Map();

export function crearPinIcon(iconName, seleccionado = false) {
  const clave = `${iconName}|${seleccionado}`;
  if (!cache.has(clave)) {
    const tamano = seleccionado ? TAMANO_SELECCIONADO : TAMANO_NORMAL;
    const svg = renderToStaticMarkup(createElement(Icon, { name: iconName }));
    cache.set(
      clave,
      L.divIcon({
        // Reemplaza la clase por defecto de Leaflet (que pone fondo blanco y borde)
        className: 'map-pin-wrap',
        html: `<span class="map-pin${seleccionado ? ' sel' : ''}">${svg}</span>`,
        iconSize: [tamano, tamano],
        // Punto del ícono que cae exactamente en la coordenada: la punta del pico
        iconAnchor: [tamano / 2, tamano + PICO],
      }),
    );
  }
  return cache.get(clave);
}
