/*
  Inicio.jsx : Vista de inicio
  Secciones: bienvenida (texto + espacio del mapa), 
  reportes recientes
  pasos para crear un reporte
*/

import { Link } from 'react-router-dom';
import {
  IconAlertTriangle,
  IconMap2,
  IconMessageCircle,
  IconCamera,
} from '@tabler/icons-react';
import './Inicio.css';

const PASOS = [
  {
    icono: IconAlertTriangle,
    titulo: 'Selecciona el tipo de incidente',
    descripcion: 'Elige entre accidente, inundación, tráfico o falla de infraestructura.',
  },
  {
    icono: IconMap2,
    titulo: 'Indica la ubicación',
    descripcion: 'Márcala en el mapa o usa tu ubicación actual de forma automática.',
  },
  {
    icono: IconMessageCircle,
    titulo: 'Describe lo ocurrido',
    descripcion: 'Escribe una breve descripción para dar contexto a la comunidad.',
  },
  {
    icono: IconCamera,
    titulo: 'Adjunta una fotografía',
    descripcion: 'Opcional: respalda tu reporte con evidencia fotográfica.',
  },
];

function Inicio()
{
    return (
    <div className="inicio">
      {/* Bienvenida + mapa */}
      <section className="inicio-bienvenida">
        <div className="inicio-bienvenida__texto">
          <h1>Reporta y consulta incidentes viales en Ciudad Juárez</h1>
          <p>
            Súmate a la comunidad que informa sobre accidentes, inundaciones y
            fallas de infraestructura en tiempo real.
          </p>
        </div>
 
        {/* TO DO: reemplazar por el componente del mapa cuando exista */}
        <div
          className="inicio-bienvenida__mapa"
          role="img"
          aria-label="Espacio reservado para el mapa de incidentes"
        />
      </section>
 
      {/* Reportes recientes */}
      <section className="inicio-reportes">
        <h2>Reportes recientes</h2>
 
        {/* TO DO: mapear los reportes reales cuando el modulo exista */}
        <div className="inicio-reportes__lista" />
 
        <div className="inicio-reportes__accion">
          <Link to="/crear-reporte" className="inicio-reportes__cta">
            Crear reporte
          </Link>
        </div>
      </section>
 
      {/* Pasos para reportar */}
      <section className="inicio-pasos">
        <h2>¿Cómo reportar un incidente?</h2>
        <p className="inicio-pasos__subtitulo">
          Cuatro pasos simples para avisar a la comunidad lo que está pasando en
          tu zona
        </p>
 
        <div className="inicio-pasos__lista">
          {PASOS.map(({ icono: IconoPaso, titulo, descripcion }, i) => (
            <article key={titulo} className="paso">
              <div className="paso__icono">
                <IconoPaso size={24} stroke={1.75} />
              </div>
              <span className="paso__numero">Paso {i + 1}</span>
              <h3>{titulo}</h3>
              <p>{descripcion}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );

}

export default Inicio;