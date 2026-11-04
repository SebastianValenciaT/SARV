import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Alert from '../components/common/Alerts';
import api from '../services/api';
import './MisReportes.css';

// `estado` viene del backend: sin_resolver, resuelto o expirado (calculado).
const ESTADOS = {
  sin_resolver: { texto: 'Sin resolver', clase: 'estado-pendiente' },
  resuelto: { texto: '✓ Resuelto', clase: 'estado-resuelto' },
  expirado: { texto: 'Expirado', clase: 'estado-expirado' },
};

// `valor` es lo que se manda como ?estado= ('' = sin filtro)
const FILTROS = [
  { valor: '', texto: 'Todos', clase: '' },
  { valor: 'sin_resolver', texto: 'Sin resolver', clase: 'chip-pendiente' },
  { valor: 'resuelto', texto: '✓ Resuelto', clase: 'chip-resuelto' },
];

// "Hace 2h", "Hace 3 días"... a partir de una fecha ISO del backend.
function haceCuanto(fechaIso) {
  const segundos = Math.floor((Date.now() - new Date(fechaIso)) / 1000);
  const minutos = Math.floor(segundos / 60);
  const horas = Math.floor(minutos / 60);
  const dias = Math.floor(horas / 24);

  if (minutos < 1) return 'Hace un momento';
  if (minutos < 60) return `Hace ${minutos} min`;
  if (horas < 24) return `Hace ${horas}h`;
  if (dias === 1) return 'Hace 1 día';
  if (dias < 7) return `Hace ${dias} días`;
  if (dias < 14) return 'Hace 1 semana';
  if (dias < 30) return `Hace ${Math.floor(dias / 7)} semanas`;
  return new Date(fechaIso).toLocaleDateString('es-MX');
}

function TarjetaReporte({ reporte, onEditar, onEliminar }) {
  const estado = ESTADOS[reporte.estado] ?? ESTADOS.sin_resolver;

  return (
    <div className="reporte-card">
      <div className="reporte-miniatura">
        {reporte.imagen_principal ? (
          <img src={reporte.imagen_principal} alt="" className="reporte-imagen" />
        ) : (
          '📷'
        )}
        {reporte.total_imagenes > 0 && (
          <span className="reporte-fotos">{reporte.total_imagenes}</span>
        )}
      </div>

      <div className="reporte-info">
        <div className="reporte-etiquetas">
          <span className="badge badge-categoria">{reporte.tipo_etiqueta}</span>
          <span className={`badge ${estado.clase}`}>{estado.texto}</span>
        </div>
        <p className="reporte-titulo">{reporte.titulo}</p>
        <p className="reporte-meta">
          {reporte.direccion || 'Sin dirección'} &nbsp;·&nbsp; {haceCuanto(reporte.creado_en)}
          &nbsp;·&nbsp; {reporte.confirmaciones} confirman
        </p>
      </div>

      <div className="reporte-acciones">
        {/* es_editable lo calcula el backend: false si está resuelto o expirado (RF-50) */}
        {reporte.es_editable ? (
          <>
            <button className="btn-accion btn-editar" onClick={() => onEditar(reporte.id)}>
              Editar
            </button>
            <button className="btn-accion btn-eliminar" onClick={() => onEliminar(reporte.id)}>
              Eliminar
            </button>
          </>
        ) : (
          <Link to={`/reportes/${reporte.id}`} className="btn-accion btn-detalle">
            Ver detalle →
          </Link>
        )}
      </div>
    </div>
  );
}

export default function MisReportes() {
  const navigate = useNavigate();
  const location = useLocation();
  // Mensaje que manda otra página al regresar aquí (por ejemplo, "Los cambios se guardaron.")
  const [mensaje, setMensaje] = useState(location.state?.mensaje ?? null);
  const [reportes, setReportes] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [filtro, setFiltro] = useState('');
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const cargarReportes = useCallback(() => {
    setCargando(true);
    setError(null);
    api.get('/mis-reportes/', { params: filtro ? { estado: filtro } : {} })
      .then((res) => {
        setReportes(res.data.results);
        setResumen(res.data.resumen);
      })
      .catch((err) => {
        const codigo = err.response?.status;
        if (codigo === 401 || codigo === 403) {
          setError('Inicia sesión para ver tus reportes.');
        } else {
          setError('No se pudieron cargar tus reportes. Revisa tu conexión e intenta de nuevo.');
        }
      })
      .finally(() => setCargando(false));
  }, [filtro]);

  // Borra el mensaje del historial para que no vuelva a salir al recargar la página
  useEffect(() => {
    if (location.state?.mensaje) navigate(location.pathname, { replace: true, state: null });
  }, [location, navigate]);

  // Se vuelve a pedir cada vez que cambia el filtro.
  useEffect(() => {
    cargarReportes();
  }, [cargarReportes]);

  const handleEditar = (id) => {
    navigate(`/reportes/${id}/editar`); // mismo formulario de crear, en modo editar (RF-45)
  };

  const handleEliminar = (id) => {
    // TODO: llamar a DELETE /api/reportes/{id}/ cuando exista el endpoint (RF-46)
    if (window.confirm('¿Estás seguro que deseas eliminar este reporte? Esta acción no se puede deshacer.')) {
      console.log('Eliminar reporte', id);
    }
  };

  const sinReportes = resumen?.total === 0;

  return (
    <div className="mis-reportes">
      <Link to="/mapa" className="volver">← Volver a Mapa y reportes</Link>

      {mensaje && <Alert type="success" message={mensaje} onClose={() => setMensaje(null)} />}

      <div className="mis-reportes-header">
        <h1>Mis reportes</h1>
        {resumen && !sinReportes && (
          <p className="resumen">
            <span className="punto"></span>
            {resumen.total} {resumen.total === 1 ? 'reporte' : 'reportes'} · {resumen.activos} sin
            resolver, {resumen.resueltos} {resumen.resueltos === 1 ? 'resuelto' : 'resueltos'}
            {resumen.expirados > 0 && `, ${resumen.expirados} expirados`}
          </p>
        )}
      </div>

      {!sinReportes && (
        <div className="filtros">
          {FILTROS.map((f) => (
            <button
              key={f.valor}
              className={`chip ${f.clase} ${filtro === f.valor ? 'chip-activo' : ''}`}
              onClick={() => setFiltro(f.valor)}
            >
              {f.texto}
            </button>
          ))}
        </div>
      )}

      <div className="lista-reportes">
        {cargando ? (
          <p className="sin-reportes">Cargando tus reportes...</p>
        ) : error ? (
          <div className="sin-reportes">
            <p>{error}</p>
            <button className="btn-accion btn-editar" onClick={cargarReportes}>
              Reintentar
            </button>
          </div>
        ) : sinReportes ? (
          // RF-49 / HU-024: solo el mensaje, sin botón (para crear está «Reportar» en la barra)
          <p className="sin-reportes">Sin reportes</p>
        ) : reportes.length === 0 ? (
          <p className="sin-reportes">No tienes reportes con este estado.</p>
        ) : (
          reportes.map((r) => (
            <TarjetaReporte
              key={r.id}
              reporte={r}
              onEditar={handleEditar}
              onEliminar={handleEliminar}
            />
          ))
        )}
      </div>
    </div>
  );
}