import { useState } from 'react';
import { Link } from 'react-router-dom';
import './MisReportes.css';

// Datos de prueba. Después estos vendrán del backend (services/api.js)
const REPORTES_DEMO = [
  {
    id: 1,
    categoria: 'Bache',
    icono: '🕳️',
    etiquetaCategoria: '⚠ Bache',
    estado: 'sin_resolver',
    titulo: 'Bache profundo en carril derecho',
    ubicacion: 'Av. Tecnológico y P. Elías Calles',
    tiempo: 'Hace 2h',
    fotos: 3,
    confirmaciones: 8,
  },
  {
    id: 2,
    categoria: 'Semáforo',
    icono: '🚦',
    etiquetaCategoria: '🚦 Semáforo',
    estado: 'sin_resolver',
    titulo: 'Semáforo dañado en el cruce',
    ubicacion: 'Blvd. Zaragoza y de la Raza',
    tiempo: 'Hace 1 día',
    fotos: 1,
    confirmaciones: 3,
  },
  {
    id: 3,
    categoria: 'Alumbrado',
    icono: '💡',
    etiquetaCategoria: '💡 Alumbrado',
    estado: 'resuelto',
    titulo: 'Alumbrado público sin funcionar',
    ubicacion: 'Calle 16 de Septiembre',
    tiempo: 'Hace 5 días',
    fotos: 2,
    confirmaciones: 14,
  },
  {
    id: 4,
    categoria: 'Otro',
    icono: '🔌',
    etiquetaCategoria: '🔌 Otro',
    estado: 'resuelto',
    titulo: 'Cable colgando en banqueta',
    ubicacion: 'Av. Ejército Nacional',
    tiempo: 'Hace 1 semana',
    fotos: 1,
    confirmaciones: 14,
  },
];

const ESTADOS = {
  sin_resolver: { texto: 'Sin resolver', clase: 'estado-pendiente' },
  resuelto: { texto: '✓ Resuelto', clase: 'estado-resuelto' },
};

const FILTROS = [
  { valor: 'todos', texto: 'Todos', clase: '' },
  { valor: 'sin_resolver', texto: 'Sin resolver', clase: 'chip-pendiente' },
  { valor: 'resuelto', texto: '✓ Resuelto', clase: 'chip-resuelto' },
];

function TarjetaReporte({ reporte, onEditar, onEliminar }) {
  const estado = ESTADOS[reporte.estado];
  const editable = reporte.estado === 'sin_resolver';

  return (
    <div className="reporte-card">
      <div className="reporte-miniatura">
        {reporte.icono}
        <span className="reporte-fotos">{reporte.fotos}</span>
      </div>

      <div className="reporte-info">
        <div className="reporte-etiquetas">
          <span className="badge badge-categoria">{reporte.etiquetaCategoria}</span>
          <span className={`badge ${estado.clase}`}>{estado.texto}</span>
        </div>
        <p className="reporte-titulo">{reporte.titulo}</p>
        <p className="reporte-meta">
           {reporte.ubicacion} &nbsp;·&nbsp;  {reporte.tiempo} &nbsp;·&nbsp; {' '}
          {reporte.confirmaciones} confirman
        </p>
      </div>

      <div className="reporte-acciones">
        {editable ? (
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
  const [reportes, setReportes] = useState(REPORTES_DEMO);
  const [filtro, setFiltro] = useState('todos');

  const visibles =
    filtro === 'todos' ? reportes : reportes.filter((r) => r.estado === filtro);

  const contar = (estado) => reportes.filter((r) => r.estado === estado).length;

  const handleEditar = (id) => {
    // TODO: navegar al formulario de edición
    console.log('Editar reporte', id);
  };

  const handleEliminar = (id) => {
    if (window.confirm('¿Seguro que quieres eliminar este reporte?')) {
      setReportes((prev) => prev.filter((r) => r.id !== id));
    }
  };

  return (
    <div className="mis-reportes">
      <Link to="/mapa" className="volver">← Volver a Mapa y reportes</Link>

      <div className="mis-reportes-header">
        <h1>Mis reportes</h1>
        <p className="resumen">
          <span className="punto"></span>
          {reportes.length} reportes · {contar('sin_resolver')} sin resolver,{' '}
          {contar('resuelto')} {contar('resuelto') === 1 ? 'resuelto' : 'resueltos'}
        </p>
      </div>

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

      <div className="lista-reportes">
        {visibles.length === 0 ? (
          <p className="sin-reportes">No tienes reportes con este estado.</p>
        ) : (
          visibles.map((r) => (
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