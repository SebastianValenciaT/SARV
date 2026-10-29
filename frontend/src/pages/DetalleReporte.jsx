import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Alert from '../components/common/Alerts';
import EstadoBadge from '../components/common/EstadoBadge';
import Icon from '../components/common/Icon';
import MiniMap from '../components/common/MiniMap';
import DenunciaPanel from '../components/reportes/DenunciaPanel';
import ReaccionesCard from '../components/reportes/ReaccionesCard';
import { iconoPorId } from '../constants/tipos';
import { nombreZona } from '../constants/zonas';
import { useReporte } from '../hooks/useReporte';
import { getReporte } from '../services/reportes';
import { useTipos } from '../hooks/useTipos';
import { capitalizar, formatFechaHora, formatRelativa } from '../utils/fechas';
import './DetalleReporte.css';

const GRAVEDADES = { leve: 'Leve', moderado: 'Moderado', grave: 'Grave' };

// Titulo e icono de cada fase del seguimiento que calcula la API
const FASES = {
  creado: { titulo: 'Reporte creado', icono: 'flag' },
  confirmado: { titulo: 'Confirmado por la comunidad', icono: 'users' },
  resuelto: { titulo: 'Resuelto', icono: 'check' },
};

function textoFase(fase) {
  if (!fase.completada) return 'Pendiente';
  const fecha = formatFechaHora(fase.fecha);
  if (fase.fase === 'creado') return `${fecha} · ${fase.autor}`;
  if (fase.fase === 'confirmado') return `${fecha} · ${fase.confirmaciones} confirmaciones`;
  return fecha;
}

function VolverLink() {
  return (
    <Link to="/reportes" className="row detalle-back">
      <span className="icon-btn detalle-back-btn">
        <Icon name="arrow-l" />
      </span>
      Mapa y reportes
    </Link>
  );
}

/**
 * Vista H — Detalle de reporte, pagina completa (/reportes/:id).
 * Galeria de fotos, informacion, reacciones, ubicacion y seguimiento.
 */
function DetalleReporte() {
  const { id } = useParams();
  // setData reemplaza el reporte con el detalle que responde el servidor tras
  // reaccionar o denunciar: un solo origen de verdad, sin actualizaciones optimistas.
  const { data: reporte, loading, error, setData } = useReporte(id);
  const { data: tipos } = useTipos();
  const [foto, setFoto] = useState(0);

  // Vuelve a pedir el detalle (por ejemplo, tras un 409 o una denuncia duplicada).
  // Si falla, se queda el detalle que ya se ve.
  async function refrescar() {
    try {
      setData(await getReporte(id));
    } catch {
      // sin cambios
    }
  }

  if (loading) {
    return (
      <div className="detalle-page">
        <VolverLink />
        <p className="detalle-desc">Cargando reporte…</p>
      </div>
    );
  }

  if (error) {
    // 404: el id no existe. Cualquier otro error: problema de conexion o del servidor.
    const noExiste = error.response?.status === 404;
    return (
      <div className="detalle-page">
        <VolverLink />
        {noExiste ? (
          <p className="detalle-desc">El reporte que buscas no existe o fue eliminado.</p>
        ) : (
          <Alert type="error" message="No se pudo cargar el reporte. Intenta de nuevo." />
        )}
      </div>
    );
  }

  const icono = iconoPorId(tipos, reporte.tipo);
  const imagenes = reporte.imagenes;
  const totalFotos = imagenes.length;
  const actual = Math.min(foto, Math.max(totalFotos - 1, 0)); // por si cambia el reporte
  const anterior = () => setFoto((actual - 1 + totalFotos) % totalFotos);
  const siguiente = () => setFoto((actual + 1) % totalFotos);

  return (
    <div className="detalle-page">
      {/* barra superior */}
      <div className="row detalle-topbar">
        <VolverLink />
        <div className="row detalle-date">
          <Icon name="cal" size={14} />
          {formatFechaHora(reporte.fecha_incidente)}
        </div>
      </div>

      <div className="detalle-body">
        {/* columna principal */}
        <div className="detalle-main">
          <h1 className="detalle-title">{reporte.titulo}</h1>
          <div className="row detalle-meta">
            <EstadoBadge estado={reporte.estado} />
            <span className="row">
              <Icon name="clock" size={13} />
              Reportado {formatRelativa(reporte.creado_en)}
            </span>
            <span className="row">
              <Icon name="pin" size={13} />
              {nombreZona(reporte.zona)}
            </span>
            <span className="row">
              <Icon name="users" size={13} />
              {reporte.confirmaciones} confirman
            </span>
          </div>
          {reporte.estado === 'expirado' && (
            <Alert
              type="warning"
              message={`Este reporte expiró el ${formatFechaHora(reporte.expira_en)}. Ya no aparece en el mapa ni en la lista y no admite reacciones ni denuncias.`}
            />
          )}
          <p className="detalle-desc">{reporte.descripcion}</p>

          <div className="card detalle-gal">
            <div className="thumb detalle-gal-main">
              {totalFotos > 0 ? (
                <img src={imagenes[actual].url} alt={`Foto ${actual + 1} de ${reporte.titulo}`} />
              ) : (
                <Icon name="image" />
              )}
              <span className="cam">
                <Icon name="camera" />
                {totalFotos > 0 ? `${actual + 1}/${totalFotos}` : 'Sin fotos'}
              </span>
              {totalFotos > 1 && (
                <div className="detalle-gal-nav">
                  <button type="button" onClick={anterior} aria-label="Foto anterior">
                    <Icon name="left" />
                  </button>
                  <button type="button" onClick={siguiente} aria-label="Foto siguiente">
                    <Icon name="right" />
                  </button>
                </div>
              )}
            </div>
            {totalFotos > 1 && (
              <div className="detalle-gal-side">
                {imagenes.map((imagen, i) => (
                  <button
                    key={imagen.id}
                    type="button"
                    className={`thumb ${i === actual ? 'on' : ''}`}
                    onClick={() => setFoto(i)}
                    aria-label={`Ver foto ${i + 1}`}
                  >
                    <img src={imagen.url} alt="" />
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="detalle-cards">
            <div className="card detalle-info">
              <div className="lbl">Información</div>
              <div className="detalle-info-row">
                <span>Tipo</span>
                <b>
                  <Icon name={icono} size={15} />
                  {reporte.tipo_etiqueta}
                </b>
              </div>
              <div className="detalle-info-row">
                <span>Gravedad</span>
                <b>{GRAVEDADES[reporte.gravedad]}</b>
              </div>
              <div className="detalle-info-row">
                <span>Dirección</span>
                <b>{reporte.direccion}</b>
              </div>
              <div className="detalle-info-row">
                <span>Reportado</span>
                <b>{formatFechaHora(reporte.creado_en)}</b>
              </div>
              <div className="detalle-info-row">
                <span>Última actualización</span>
                <b>{capitalizar(formatRelativa(reporte.actualizado_en))}</b>
              </div>
            </div>

            {/* key: al cambiar de reporte, su estado local empieza de cero */}
            <ReaccionesCard
              key={reporte.id}
              reporte={reporte}
              onActualizado={setData}
              onRefrescar={refrescar}
            />
          </div>
        </div>

        {/* columna lateral */}
        <aside className="detalle-side">
          <div className="card detalle-location">
            <MiniMap
              latitud={reporte.latitud}
              longitud={reporte.longitud}
              icon={icono}
              className="detalle-location-map"
            />
            <div className="detalle-location-street">{reporte.direccion}</div>
            <div className="detalle-location-sub">{nombreZona(reporte.zona)} · Ciudad Juárez</div>
          </div>

          <div className="card detalle-timeline">
            <div className="lbl detalle-timeline-label">Seguimiento</div>
            {reporte.seguimiento.map((fase) => (
              <div key={fase.fase} className="detalle-tl">
                <span className={`detalle-tl-icon ${fase.completada ? '' : 'pend'}`}>
                  <Icon name={FASES[fase.fase].icono} />
                </span>
                <div>
                  <div className="detalle-tl-title">{FASES[fase.fase].titulo}</div>
                  <div className="detalle-tl-sub">{textoFase(fase)}</div>
                </div>
              </div>
            ))}
          </div>

          {/* No se muestra al autor (lo decide el propio panel con es_autor) */}
          <DenunciaPanel
            key={reporte.id}
            reporte={reporte}
            onActualizado={setData}
            onRefrescar={refrescar}
          />

          {/* Solo lo ve el autor (TODO(auth): es_autor llega en false hasta que api.js mande el token) */}
          {reporte.es_autor && (
            <div className="card detalle-author">
              <div className="detalle-author-name">{reporte.seguimiento[0].autor}</div>
              <div className="detalle-author-sub">Autor del reporte · visible solo para ti</div>
              {/* TODO: conectar con PATCH/DELETE reportes/{id}/ cuando existan */}
              <div className="row detalle-author-actions">
                <button type="button" className="btn-outline">
                  <Icon name="edit" size={15} />
                  Editar
                </button>
                <button type="button" className="btn-outline btn-danger">
                  <Icon name="trash" size={15} />
                  Eliminar
                </button>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

export default DetalleReporte;
