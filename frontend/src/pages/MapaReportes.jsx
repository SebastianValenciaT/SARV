import { useState } from 'react';
import { Link } from 'react-router-dom';
import Alert from '../components/common/Alerts';
import Icon from '../components/common/Icon';
import ReportesHeader from '../components/reportes/ReportesHeader';
import { iconoPorId, iconoTipo } from '../constants/tipos';
import { nombreZona } from '../constants/zonas';
import { useReportesMapa } from '../hooks/useReportes';
import { useTipos } from '../hooks/useTipos';
import { formatCuando } from '../utils/fechas';
import { proyectarAPorcentaje } from '../utils/geo';
import './MapaReportes.css';

// Categorias rapidas (por nombre del tipo) que se muestran como chips sobre la lista
const CHIPS = ['Bache', 'Choque', 'Inundación'];

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

/**
 * Vista F — Mapa y reportes (vista mapa).
 * Lista lateral de reportes + mapa ilustrativo con pines. Al seleccionar
 * un reporte (en la lista o en el mapa) se muestra su resumen en el mapa.
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
  // Si no hay seleccion (o ya no esta en la lista filtrada), se muestra el primero.
  const selected = reportes.find((r) => r.id === selectedId) ?? reportes[0];
  const selectedPos = selected && proyectarAPorcentaje(selected.latitud, selected.longitud);

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
          <MapaBase />

          <div className="mapa-sort">
            Ordenar por <b>Más recientes</b>
            <Icon name="down" size={14} />
          </div>

          {/* Pines: posicion aproximada con utils/geo.js hasta integrar Leaflet */}
          {reportes.map((reporte) => {
            const pos = proyectarAPorcentaje(reporte.latitud, reporte.longitud);
            return (
              <button
                key={reporte.id}
                type="button"
                className={`mapa-pin ${reporte.id === selected?.id ? 'sel' : ''}`}
                style={{ left: `${pos.left}%`, top: `${pos.top}%` }}
                onClick={() => setSelectedId(reporte.id)}
                aria-label={reporte.titulo}
              >
                <Icon name={iconoPorId(tipos, reporte.tipo)} />
              </button>
            );
          })}

          {selected && (
            <div
              className="mapa-popup"
              style={{
                left: `${clamp(selectedPos.left - 18, 2, 70)}%`,
                top: `${clamp(selectedPos.top - 15, 8, 80)}%`,
              }}
            >
              <div className="thumb">
                <Icon name={iconoPorId(tipos, selected.tipo)} />
              </div>
              <div>
                <div className="mapa-popup-title">{selected.titulo}</div>
                <div className="mapa-popup-meta">
                  {selected.direccion} · {formatCuando(selected.fecha_incidente)}
                </div>
              </div>
              <Link to={`/reportes/${selected.id}`} className="mapa-popup-go" aria-label="Ver detalle">
                <Icon name="arrow-r" />
              </Link>
            </div>
          )}

          <div className="mapa-zoom">
            <div className="mapa-zoom-group">
              <button type="button" aria-label="Acercar">
                <Icon name="plus" />
              </button>
              <button type="button" aria-label="Alejar">
                <Icon name="minus" />
              </button>
            </div>
            <button type="button" className="mapa-zoom-single" aria-label="Mi ubicación">
              <Icon name="nav" />
            </button>
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

// Mapa ilustrativo de Ciudad Juárez (placeholder hasta integrar un mapa real)
function MapaBase() {
  return (
    <svg
      className="mapa-base"
      viewBox="0 0 1024 942"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <rect width="1024" height="942" fill="#EDEEF0" />
      <path d="M-20 60C250 40 520 75 1044 15" stroke="#D3DDF0" strokeWidth="42" fill="none" />
      <g fill="#DCE7D9">
        <rect x="270" y="132" width="160" height="62" rx="4" />
        <rect x="688" y="256" width="92" height="72" rx="4" />
        <rect x="230" y="598" width="130" height="102" rx="4" />
      </g>
      <g stroke="#fff" strokeWidth="8" fill="none" strokeLinecap="round">
        <path d="M0 116L1024 96" />
        <path d="M0 222L1024 214" />
        <path d="M90 125L740 540" />
        <path d="M560 96L575 942" />
        <path d="M212 226L120 942" />
        <path d="M0 516L1024 540" />
        <path d="M1010 330L820 942" />
        <path d="M0 766L1024 740" />
        <path d="M740 540L1024 560" strokeWidth="5" />
      </g>
      <g fontSize="9.5" fill="#8A93A3" fontFamily="Montserrat,Inter,sans-serif" fontWeight="500">
        <text x="404" y="53">Río Bravo</text>
        <text x="740" y="87">Blvd. Juan Pablo II</text>
        <text x="740" y="199">Av. 16 de Septiembre</text>
        <text x="276" y="165" fontSize="8">Parque El Chamizal</text>
        <text x="250" y="652" fontSize="8">Parque Central</text>
        <text x="10" y="505">Av. Ejército Nacional</text>
        <text x="650" y="730">Av. de las Torres</text>
        <text transform="translate(366 262) rotate(36)">Av. Paseo Triunfo de la República</text>
        <text transform="translate(590 690) rotate(90)">Av. Tecnológico</text>
        <text transform="translate(128 760) rotate(-80)">Av. Vicente Guerrero</text>
        <text transform="translate(880 700) rotate(-62)">Blvd. Zaragoza</text>
      </g>
    </svg>
  );
}

export default MapaReportes;
