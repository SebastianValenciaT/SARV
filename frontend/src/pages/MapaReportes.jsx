import { useCallback, useRef, useState } from 'react';
import { Marker } from 'react-leaflet';
import { Link } from 'react-router-dom';
import Alert from '../components/common/Alerts';
import Icon from '../components/common/Icon';
import AjustarTamano from '../components/mapa/AjustarTamano';
import CentrarEn from '../components/mapa/CentrarEn';
import ChipsTipo from '../components/mapa/ChipsTipo';
import MapaBase from '../components/mapa/MapaBase';
import { crearPinIcon } from '../components/mapa/pinIcon';
import ReportesHeader from '../components/reportes/ReportesHeader';
import { iconoPorId } from '../constants/tipos';
import { nombreZona } from '../constants/zonas';
import { usePantallaCompleta } from '../hooks/usePantallaCompleta';
import { useReportesMapa } from '../hooks/useReportes';
import { useTipos } from '../hooks/useTipos';
import { formatCuando } from '../utils/fechas';
import './MapaReportes.css';

/**
 * Vista F — Mapa y reportes (vista mapa).
 * Lista lateral de reportes + mapa de OpenStreetMap con un pin por reporte.
 * Pin y lista estan sincronizados: seleccionar en uno marca el otro.
 *
 * Pantalla completa: se hace con CSS (clase mapa-map--full), no con la API
 * requestFullscreen (en iPhone no funciona para elementos que no son video).
 * Es el mismo MapContainer, solo cambia su tamaño: se conservan centro, zoom,
 * filtro y pin seleccionado.
 */
function MapaReportes() {
  const [categoria, setCategoria] = useState('todos'); // 'todos' o id de tipo
  const [busqueda, setBusqueda] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [completa, setCompleta] = useState(false);
  const mapaRef = useRef(null);
  const botonCompletaRef = useRef(null);

  // Escape (o el botón) sale; el foco vuelve al botón que abre el modo.
  // useCallback: el hook necesita una función estable para no rehacer su efecto en cada render.
  const salirDeCompleta = useCallback(() => {
    setCompleta(false);
    botonCompletaRef.current?.focus();
  }, []);
  usePantallaCompleta(completa, mapaRef, salirDeCompleta);

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
  // Solo cuando ya cargó y no hay nada (nunca mientras carga).
  const sinResultados = Boolean(data) && reportes.length === 0;

  return (
    <div className="mapa-page">
      <ReportesHeader
        total={data?.length}
        etiqueta="reportes activos"
        onBuscar={setBusqueda}
      />

      <div className="mapa-body">
        {/* columna izquierda: chips + lista */}
        <aside className="mapa-sidebar">
          <ChipsTipo tipos={tipos} valor={categoria} onChange={setCategoria} />

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
            {sinResultados && <p className="mapa-empty">No hay reportes activos con estos filtros.</p>}
          </div>
        </aside>

        {/* mapa */}
        <section ref={mapaRef} className={`mapa-map ${completa ? 'mapa-map--full' : ''}`.trim()}>
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
            <CentrarEn latitud={enfocado?.latitud} longitud={enfocado?.longitud} />
            <AjustarTamano clave={completa} />
          </MapaBase>

          {/* barra superior: chips (solo en pantalla completa) y botón entrar/salir */}
          <div className="mapa-barra">
            {completa && (
              <ChipsTipo
                tipos={tipos}
                valor={categoria}
                onChange={setCategoria}
                variante="desplazar"
                className="mapa-barra-chips"
              />
            )}
            <button
              ref={botonCompletaRef}
              type="button"
              className="mapa-full-btn"
              aria-pressed={completa}
              aria-label={completa ? 'Salir de pantalla completa' : 'Ver mapa en pantalla completa'}
              title={completa ? 'Salir de pantalla completa (Esc)' : 'Ver mapa en pantalla completa'}
              onClick={() => (completa ? salirDeCompleta() : setCompleta(true))}
            >
              <Icon name={completa ? 'shrink' : 'expand'} />
              {completa && <span aria-hidden="true">Salir</span>}
            </button>
          </div>

          {sinResultados && (
            <p className="mapa-vacio" role="status">
              {categoria === 'todos'
                ? 'No hay reportes activos con estos filtros'
                : 'No hay reportes activos con este tipo'}
            </p>
          )}

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
