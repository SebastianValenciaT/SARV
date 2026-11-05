import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

/**
 * CentrarEn: mueve el mapa con animacion cuando cambian latitud/longitud.
 * Debe ir dentro de <MapaBase> porque useMap() solo funciona dentro del mapa.
 * Si no hay coordenadas, no hace nada.
 */
function CentrarEn({ latitud, longitud, zoomMinimo = 15 }) {
  const map = useMap();

  useEffect(() => {
    if (latitud == null || longitud == null) return;
    map.flyTo([latitud, longitud], Math.max(map.getZoom(), zoomMinimo), { duration: 0.8 });
  }, [map, latitud, longitud, zoomMinimo]);

  return null;
}

export default CentrarEn;
