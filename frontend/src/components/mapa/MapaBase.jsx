import 'leaflet/dist/leaflet.css';
import { AttributionControl, MapContainer, TileLayer, ZoomControl } from 'react-leaflet';
import { CENTRO, LIMITES } from '../../constants/juarez';
import './MapaBase.css';

// Imágenes (tiles) de 256x256 px que sirve OpenStreetMap según zoom (z) y posición (x, y)
const TILES_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
// Atribución obligatoria según la política de uso de OpenStreetMap
const ATRIBUCION = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

/**
 * MapaBase: mapa de OpenStreetMap limitado a Ciudad Juárez.
 * - children: pines (<Marker>) u otros componentes de react-leaflet.
 * - interactivo=false: mapa fijo (sin arrastre, zoom ni controles), para mini mapas.
 * MapContainer solo lee center/zoom al montarse: para moverlo después se usa useMap().
 */
function MapaBase({ center = CENTRO, zoom = 12, interactivo = true, className = '', children }) {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      minZoom={11}
      maxBounds={LIMITES}
      maxBoundsViscosity={1}
      className={`map-base ${className}`.trim()}
      zoomControl={false}
      attributionControl={false}
      dragging={interactivo}
      scrollWheelZoom={interactivo}
      doubleClickZoom={interactivo}
      touchZoom={interactivo}
      boxZoom={interactivo}
      keyboard={interactivo}
    >
      <TileLayer url={TILES_URL} attribution={ATRIBUCION} maxZoom={19} />
      {/* En el mapa grande va arriba: abajo lo taparía la hoja de "Detalles" */}
      <AttributionControl position={interactivo ? 'topright' : 'bottomright'} prefix={false} />
      {interactivo && <ZoomControl position="topright" />}
      {children}
    </MapContainer>
  );
}

export default MapaBase;
