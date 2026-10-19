import { useState } from 'react';
import { Link } from 'react-router-dom';
import Alert from '../components/common/Alerts';
import Icon from '../components/common/Icon';
import MiniMap from '../components/common/MiniMap';
import ReportesHeader from '../components/reportes/ReportesHeader';
import { iconoPorId, iconoTipo } from '../constants/tipos';
import { ZONAS, nombreZona } from '../constants/zonas';
import { useReportes } from '../hooks/useReportes';
import { useTipos } from '../hooks/useTipos';
import { formatCuando } from '../utils/fechas';
import './ListaReportes.css';

const RANGOS = [
  { id: 'hoy', nombre: 'Hoy' },
  { id: '7d', nombre: '7 días' },
  { id: '30d', nombre: '30 días' },
];

// tipos: ids que vienen de GET /api/tipos/; zona: '' significa "todas"
const FILTROS_INICIALES = { tipos: [], rango: '7d', zona: '' };

/**
 * Vista G — Lista de reportes con panel de filtros.
 * El primer resultado se muestra expandido y el resto en cuadricula.
 */
function ListaReportes() {
  const [showFiltros, setShowFiltros] = useState(true);
  // borrador: lo que el usuario va marcando; aplicados: lo que se pide a la API
  const [borrador, setBorrador] = useState(FILTROS_INICIALES);
  const [aplicados, setAplicados] = useState(FILTROS_INICIALES);
  const [busqueda, setBusqueda] = useState('');

  const { data: tipos, error: errorTipos } = useTipos();
  // Cada vez que cambian estos parametros, el hook vuelve a pedir la lista.
  const { data, loading, error } = useReportes({
    tipo: aplicados.tipos,
    fecha: aplicados.rango,
    zona: aplicados.zona,
    q: busqueda,
  });

  const reportes = data?.results ?? [];
  const [destacado, ...resto] = reportes;

  const toggleTipo = (id) => {
    setBorrador((prev) => ({
      ...prev,
      tipos: prev.tipos.includes(id)
        ? prev.tipos.filter((t) => t !== id)
        : [...prev.tipos, id],
    }));
  };

  const limpiar = () => {
    setBorrador(FILTROS_INICIALES);
    setAplicados(FILTROS_INICIALES);
  };

  const nombresTipos = aplicados.tipos
    .map((id) => tipos?.find((t) => t.id === id)?.nombre)
    .filter(Boolean)
    .join(', ');

  return (
    <div className="lista-page">
      <ReportesHeader
        total={data?.count}
        filtrosActivos={aplicados.tipos.length + (aplicados.zona ? 1 : 0)}
        onToggleFiltros={() => setShowFiltros((v) => !v)}
        onBuscar={setBusqueda}
      />

      <div className="lista-body">
        {/* panel de filtros */}
        {showFiltros && (
          <aside className="lista-filters">
            <div className="row lista-filters-head">
              <span className="lista-filters-title">Filtros</span>
              <button type="button" className="lista-link-btn" onClick={limpiar}>
                Limpiar
              </button>
            </div>

            <div className="lbl lista-filters-section">Tipo de incidente</div>
            {errorTipos && <p className="lista-empty">No se pudieron cargar los tipos.</p>}
            <div className="lista-tiles">
              {tipos?.map((tipo) => (
                <button
                  key={tipo.id}
                  type="button"
                  className={`lista-tile ${borrador.tipos.includes(tipo.id) ? 'on' : ''}`}
                  onClick={() => toggleTipo(tipo.id)}
                  aria-pressed={borrador.tipos.includes(tipo.id)}
                >
                  <Icon name={iconoTipo(tipo.nombre)} />
                  {tipo.nombre}
                </button>
              ))}
            </div>

            <div className="lbl lista-filters-section">Fecha</div>
            <div className="lista-seg">
              {RANGOS.map((rango) => (
                <button
                  key={rango.id}
                  type="button"
                  className={borrador.rango === rango.id ? 'on' : ''}
                  onClick={() => setBorrador((prev) => ({ ...prev, rango: rango.id }))}
                >
                  {rango.nombre}
                </button>
              ))}
            </div>

            <label className="lbl lista-filters-section" htmlFor="filtro-zona">Zona</label>
            <select
              id="filtro-zona"
              className="lista-select"
              value={borrador.zona}
              onChange={(e) => setBorrador((prev) => ({ ...prev, zona: e.target.value }))}
            >
              <option value="">Todas las zonas</option>
              {ZONAS.map((zona) => (
                <option key={zona.id} value={zona.id}>
                  {zona.nombre}
                </option>
              ))}
            </select>

            <button
              type="button"
              className="btn-primary lista-apply"
              onClick={() => setAplicados(borrador)}
            >
              Aplicar filtros
            </button>
          </aside>
        )}

        {/* resultados */}
        <section className="lista-results">
          <div className="row lista-results-bar">
            <span>
              {data && (
                <>
                  Mostrando <b>{reportes.length} de {data.count} reportes</b>
                  {nombresTipos && ` · ${nombresTipos}`}
                  {busqueda && ` · "${busqueda}"`}
                </>
              )}
            </span>
            <span className="row lista-sort">
              <Icon name="sort" size={15} />
              Ordenar por <b>Más recientes</b>
              <Icon name="down" size={14} />
            </span>
          </div>

          {loading && <p className="lista-empty">Cargando reportes…</p>}
          {error && <Alert type="error" message="No se pudieron cargar los reportes. Intenta de nuevo." />}
          {data && !destacado && <p className="lista-empty">No hay reportes con estos filtros.</p>}

          {/* reporte expandido */}
          {destacado && (
            <article className="card lista-feat">
              <div className="thumb">
                {destacado.imagen_principal ? (
                  <img src={destacado.imagen_principal} alt={destacado.titulo} />
                ) : (
                  <Icon name="image" />
                )}
                <span className="lista-feat-tag">
                  <Icon name={iconoPorId(tipos, destacado.tipo)} />
                  {destacado.tipo_etiqueta}
                </span>
                {destacado.total_imagenes > 0 && (
                  <span className="cam">
                    <Icon name="camera" />
                    1/{destacado.total_imagenes}
                  </span>
                )}
              </div>

              <div className="lista-feat-body">
                <h2 className="lista-feat-title">{destacado.titulo}</h2>
                <div className="row lista-feat-meta">
                  <Icon name="pin" size={14} />
                  {destacado.direccion}
                  <span className="sep-dot" />
                  {nombreZona(destacado.zona)}
                  <span className="sep-dot" />
                  <Icon name="clock" size={14} />
                  {formatCuando(destacado.fecha_incidente)}
                </div>
                <p className="lista-feat-desc">{destacado.descripcion}</p>
                <div className="row lista-feat-footer">
                  <span className="lista-feat-count">
                    <b>{destacado.confirmaciones}</b> confirman
                  </span>
                  <span className="row lista-feat-actions">
                    {/* TODO(auth): habilitar cuando exista inicio de sesión (reaccionar requiere login) */}
                    <button
                      type="button"
                      className="btn-outline lista-feat-react"
                      disabled
                      title="Inicia sesión para reaccionar"
                    >
                      <Icon name="like" />
                      Reaccionar
                      <Icon name="down" size={14} />
                    </button>
                    <Link to={`/reportes/${destacado.id}`} className="btn-primary">
                      Ver detalle <Icon name="arrow-r" />
                    </Link>
                  </span>
                </div>
              </div>

              <MiniMap icon={iconoPorId(tipos, destacado.tipo)} className="lista-feat-map" />
            </article>
          )}

          {/* cuadricula */}
          <div className="lista-grid">
            {resto.map((reporte) => (
              <Link key={reporte.id} to={`/reportes/${reporte.id}`} className="card lista-rc">
                <div className="lista-rc-head">
                  <span className="lista-rc-icon">
                    <Icon name={iconoPorId(tipos, reporte.tipo)} />
                  </span>
                  <div>
                    <div className="lista-rc-title">{reporte.titulo}</div>
                    <div className="lista-rc-sub">{reporte.direccion}</div>
                  </div>
                  <Icon name="more" className="lista-rc-more" />
                </div>
                <div className="lista-rc-date">
                  <Icon name="cal" />
                  {formatCuando(reporte.fecha_incidente)}
                </div>
                <div className="lista-rc-count">
                  Confirmaciones<b>{reporte.confirmaciones}</b>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

export default ListaReportes;
