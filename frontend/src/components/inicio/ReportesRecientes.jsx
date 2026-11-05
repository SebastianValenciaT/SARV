import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { IconChevronLeft, IconChevronRight } from '@tabler/icons-react';
import Icon from '../common/Icon';
import { iconoPorId } from '../../constants/tipos';
import { useReportes } from '../../hooks/useReportes';
import { useTipos } from '../../hooks/useTipos';
import { capitalizar, formatRelativa } from '../../utils/fechas';
import './ReportesRecientes.css';

// Máximo de tarjetas en el carrusel
const CANTIDAD = 9;


function ReportesRecientes() {
  const { data, loading, error } = useReportes({ fecha: '7d' });
  const { data: tipos } = useTipos();
  const pistaRef = useRef(null);

  const reportes = (data?.results ?? []).slice(0, CANTIDAD);
  

  // Mueve el carrusel casi una "pantalla" hacia cada lado
  const mover = (direccion) => {
    const pista = pistaRef.current;
    if (!pista) return;
    pista.scrollBy({ left: direccion * pista.clientWidth * 0.8, behavior: 'smooth' });
  };

  if (loading) return <p className="rec-mensaje">Cargando reportes…</p>;
  if (error) return <p className="rec-mensaje rec-mensaje--error">No se pudieron cargar los reportes recientes.</p>;
  if (reportes.length === 0) return <p className="rec-mensaje">Aún no hay reportes recientes.</p>;

  return (
    <div className="rec-carrusel" role="region" aria-label="Reportes recientes">
      <button
        type="button"
        className="rec-flecha rec-flecha--izq"
        onClick={() => mover(-1)}
        aria-label="Ver reportes anteriores"
      >
        <IconChevronLeft size={20} />
      </button>

      <div className="rec-pista" ref={pistaRef}>
        {reportes.map((reporte) => (
          <Link
            key={reporte.id}
            to={`/reportes/${reporte.id}`}
            state={{ from: '/' }}
            className="rec-tarjeta"
          >
            <div className="rec-tarjeta__imagen">
              {reporte.imagen_principal ? (
                <img src={reporte.imagen_principal} alt={reporte.titulo} />
              ) : (
                <Icon name="image" size={32} />
              )}
              <span className="rec-tarjeta__tag">
               
                <Icon name={iconoPorId(tipos, reporte.tipo)} size={12} />
                {reporte.tipo_etiqueta}
              </span>
            </div>
            <div className="rec-tarjeta__info">
              <h3>{reporte.titulo}</h3>
              <p>{reporte.direccion} · {capitalizar(formatRelativa(reporte.fecha_incidente))}</p>
            </div>
          </Link>
        ))}
      </div>

      <button
        type="button"
        className="rec-flecha rec-flecha--der"
        onClick={() => mover(1)}
        aria-label="Ver reportes siguientes"
      >
        <IconChevronRight size={20} />
      </button>
    </div>
  );
}

export default ReportesRecientes;