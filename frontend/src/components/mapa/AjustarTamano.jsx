import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

/**
 * AjustarTamano: avisa a Leaflet que su contenedor cambió de tamaño.
 * Leaflet mide el contenedor al montarse; si después crece (pantalla completa)
 * sin avisarle, se ve cortado o con teselas grises. Cada vez que cambia `clave`
 * se llama a invalidateSize() en el siguiente cuadro, cuando el CSS ya se aplicó.
 * Debe ir dentro de <MapaBase> porque useMap() solo funciona dentro del mapa.
 */
function AjustarTamano({ clave }) {
  const map = useMap();

  useEffect(() => {
    const cuadro = requestAnimationFrame(() => map.invalidateSize());
    return () => cancelAnimationFrame(cuadro);
  }, [map, clave]);

  return null;
}

export default AjustarTamano;
