import { Marker } from 'react-leaflet';
import MapaBase from '../mapa/MapaBase';
import { crearPinIcon } from '../mapa/pinIcon';
import './MiniMap.css';

/**
 * MiniMap: mapa pequeño y fijo (no interactivo) con un pin en la ubicación.
 * Solo recibe coordenadas e ícono; no sabe de dónde vienen.
 */
function MiniMap({ latitud, longitud, icon = 'alert', zoom = 15, className = '' }) {
  return (
    <div className={`minimap ${className}`.trim()}>
      {/* key: MapContainer no se mueve si cambian las props; con otra key se vuelve a montar */}
      <MapaBase
        key={`${latitud},${longitud}`}
        center={[latitud, longitud]}
        zoom={zoom}
        interactivo={false}
      >
        <Marker position={[latitud, longitud]} icon={crearPinIcon(icon, true)} interactive={false} />
      </MapaBase>
    </div>
  );
}

export default MiniMap;
