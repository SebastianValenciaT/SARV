import { Marker } from 'react-leaflet';
import { Link } from 'react-router-dom';
import MapaBase from '../mapa/MapaBase';
import { crearPinIcon } from '../mapa/pinIcon';
import { iconoPorId } from '../../constants/tipos';
import { useReportesMapa } from '../../hooks/useReportes';
import { useTipos } from '../../hooks/useTipos';
import './MapaInicio.css';

function MapaInicio() {
  const { data, error } = useReportesMapa({ tipo: [], q: '' });
  const { data: tipos } = useTipos();

  const reportes = data ?? [];

  return (
    <div className="mapa-inicio">
      <MapaBase interactivo={false} zoom={12}>
        {reportes.map((r) => (
          <Marker
            key={r.id}
            position={[r.latitud, r.longitud]}
            icon={crearPinIcon(iconoPorId(tipos, r.tipo), false)}
            title={r.titulo}
            interactive={false}
          />
        ))}
      </MapaBase>

      <Link to="/mapa" className="mapa-inicio__enlace" aria-label="Ver el mapa completo de incidentes">
        <span>Ver mapa completo</span>
      </Link>

      {error && (
        <p className="mapa-inicio__error" role="status">No se pudieron cargar los incidentes.</p>
      )}
    </div>
  );
}

export default MapaInicio;