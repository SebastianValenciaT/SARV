import { useEffect, useState } from 'react';
import { Marker, useMap } from 'react-leaflet';
import { Link } from 'react-router-dom';
import Alert from '../components/common/Alerts';
import Icon from '../components/common/Icon';
import MapaBase from '../components/mapa/MapaBase';
import { crearPinIcon } from '../components/mapa/pinIcon';
import ReportesHeader from '../components/reportes/ReportesHeader';
import { iconoPorId, iconoTipo } from '../constants/tipos';
import { nombreZona } from '../constants/zonas';
import { useReportesMapa } from '../hooks/useReportes';
import { useTipos } from '../hooks/useTipos';
import { formatCuando } from '../utils/fechas';
import './MapaReportes.css';

// Categorias rapidas (por nombre del tipo) que se muestran como chips sobre la lista
const CHIPS = ['Bache', 'Choque', 'Inundación'];
const ZOOM_ENFOQUE = 15;

/**
 * CentrarEn: mueve el mapa con animacion cuando cambia el reporte enfocado.
 * Debe ir dentro de <MapaBase> porque useMap() solo funciona dentro del mapa.
 */
function CentrarEn({ reporte }) {
  const map = useMap();
  const latitud = reporte?.latitud;
  const longitud = reporte?.longitud;

  useEffect(() => {
    if (latitud == null || longitud == null) return;
    map.flyTo([latitud, longitud], Math.max(map.getZoom(), ZOOM_ENFOQUE), { duration: 0.8 });
  }, [map, latitud, longitud]);

  return null;
}

/**
 * Vista F — Mapa y reportes (vista mapa).
 * Lista lateral de reportes + mapa de OpenStreetMap con un pin por reporte.
 * Pin y lista estan sincronizados: seleccionar en uno marca el otro.
 */
function MapaReportes() {
  const [categoria, setCategoria] = useState('todos'); // 'todos' o id de tipo
  const [busqueda, setBusqueda] = useState('');
  const [selectedId, setSelectedId] = useState(null);

  const { data: tipos } = useTipos();
  const { data, loading, error } = useReportesMapa({
    tipo: categoria === 'todos' ? [] : [categoria],
    q: busqueda,
  });

  const reportes = data ?? [];
  // Reporte que eligio el usuario (el mapa solo se mueve cuando hay uno)
  const enfocado = reportes.find((r) => r.id === selectedId);
  // Si no hay seleccion (o ya no esta en la lista filtrada), la hoja muestra el primero.
  const selected = enfocado ?? reportes[0];

  return (
    <div className="mapa-page">
      <ReportesHeader
        total={data?.length}
        etiqueta="reportes activos"
        filtrosActivos={categoria === 'todos' ? 0 : 1}
        onBuscar={setBusqueda}
      />

      <div className="mapa-body">
        {/* columna izquierda: chips + lista */}
        <aside className="mapa-sidebar">
          <div className="mapa-chips">
            <button
              type="button"
              className={`mapa-chip ${categoria === 'todos' ? 'on' : ''}`}
              onClick={() => setCategoria('todos')}
            >
              <span className="mapa-chip-icon">
                <Icon name="list" />
              </span>
              Todos
            </button>
            {tipos?.filter((t) => CHIPS.includes(t.nombre)).map((tipo) => (
              <button
                key={tipo.id}
                type="button"
                className={`mapa-chip ${categoria === tipo.id ? 'on' : ''}`}
                onClick={() => setCategoria(tipo.id)}
              >
                <span className="mapa-chip-icon">
                  <Icon name={iconoTipo(tipo.nombre)} />
                </span>
                {tipo.nombre}
              </button>
            ))}
          </div>

          <div className="mapa-list">
            {loading && <p className="mapa-empty">Cargando reportes…</p>}
            {error && <Alert type="error" message="No se pudieron cargar los reportes del mapa." />}
            {reportes.map((reporte) => (
              <button
                key={reporte.id}
                type="button"
                className={`card mapa-rep ${reporte.id === selected?.id ? 'on' : ''}`}
                onClick={() => setSelectedId(reporte.id)}
              >
                <div className="thumb">
                  <Icon name={iconoPorId(tipos, reporte.tipo)} />
                </div>
                <div>
                  <div className="mapa-rep-title">{reporte.titulo}</div>
                  <div className="mapa-rep-meta">
                    <Icon name="pin" />
                    {reporte.direccion}
                  </div>
                  <div className="mapa-rep-meta">
                    <Icon name="clock" />
                    {formatCuando(reporte.fecha_incidente)}
                    <span className="sep-dot" />
                    {nombreZona(reporte.zona)}
                  </div>
                </div>
              </button>
            ))}
            {data && reportes.length === 0 && (
              <p className="mapa-empty">No hay reportes activos con estos filtros.</p>
            )}
          </div>
        </aside>

        {/* mapa */}
        <section className="mapa-map">
          <MapaBase>
            {reportes.map((reporte) => {
              const esSeleccionado = reporte.id === selected?.id;
              return (
                <Marker
                  key={reporte.id}
                  position={[reporte.latitud, reporte.longitud]}
                  icon={crearPinIcon(iconoPorId(tipos, reporte.tipo), esSeleccionado)}
                  title={reporte.titulo}
                  alt={reporte.titulo}
                  zIndexOffset={esSeleccionado ? 1000 : 0} // el seleccionado queda encima
                  eventHandlers={{ click: () => setSelectedId(reporte.id) }}
                />
              );
            })}
            <CentrarEn reporte={enfocado} />
          </MapaBase>

          <div className="mapa-sort">
            Ordenar por <b>Más recientes</b>
            <Icon name="down" size={14} />
          </div>

          {selected && (
            <div className="mapa-sheet">
              <div className="mapa-sheet-top">
                <span className="mapa-sheet-tab">Detalles</span>
                <span className="mapa-sheet-spacer" />
                <button type="button" className="icon-btn mapa-sheet-share" aria-label="Compartir">
                  <Icon name="share" />
                </button>
                <Link to={`/reportes/${selected.id}`} className="btn-primary">
                  Ver detalle <Icon name="arrow-r" />
                </Link>
              </div>
              <div className="mapa-sheet-cols">
                <div>
                  <div className="lbl">Tipo</div>
                  <div className="mapa-sheet-value">
                    <Icon name={iconoPorId(tipos, selected.tipo)} className="mapa-sheet-type-icon" />
                    {selected.tipo_etiqueta}
                  </div>
                </div>
                <div>
                  <div className="lbl">Ubicación</div>
                  <div className="mapa-sheet-value">{selected.direccion}</div>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default MapaReportes;
