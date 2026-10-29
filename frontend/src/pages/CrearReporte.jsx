import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Alert from '../components/common/Alerts';
import Icon from '../components/common/Icon';
import UbicacionPicker from '../components/ubicacion/UbicacionPicker';
import { iconoPorId, iconoTipo } from '../constants/tipos';
import { useTipos } from '../hooks/useTipos';
import { crearReporte } from '../services/reportes';
import { primerMensaje, statusDe } from '../utils/errores';
import { fechaLocalParaInput } from '../utils/fechas';
import { MAX_FOTOS, prepararFoto } from '../utils/imagenes';
import './CrearReporte.css';

const GRAVEDADES = [
  { id: 'leve', nombre: 'Leve' },
  { id: 'moderado', nombre: 'Moderado' },
  { id: 'grave', nombre: 'Grave' },
];
const DESCRIPCION_MIN = 10;
const DESCRIPCION_MAX = 500;
const MARGEN_FUTURO_MS = 5 * 60 * 1000; // mismo margen que el servidor (reloj del celular)

// Campos cuyo error 400 se muestra junto al campo; los demás (non_field_errors...) van en el Alert
const CAMPOS_CON_LUGAR = ['tipo', 'tipo_otro', 'titulo', 'descripcion', 'gravedad', 'fecha_incidente',
  'latitud', 'longitud', 'direccion', 'imagenes'];

function FieldError({ errores, campo }) {
  const mensajes = errores[campo];
  if (!mensajes) return null;
  return <p className="crear-error">{[].concat(mensajes).join(' ')}</p>;
}

/**
 * Página "Crear reporte" (/crear-reporte).
 * Arma un FormData con los campos, las fotos (clave `imagenes` repetida)
 * y la ubicación del UbicacionPicker, y lo envía a POST /api/reportes/.
 */
function CrearReporte() {
  const navigate = useNavigate();
  const { data: tipos, error: errorTipos } = useTipos();

  // La fecha máxima se calcula una vez al abrir la página (el servidor revalida al enviar)
  const [fechaMaxima] = useState(() => fechaLocalParaInput(new Date()));
  const [form, setForm] = useState(() => ({
    tipo: '',
    tipo_otro: '',
    titulo: '',
    descripcion: '',
    gravedad: '',
    fecha: fechaLocalParaInput(new Date()),
  }));
  const [ubicacion, setUbicacion] = useState({ latitud: null, longitud: null, direccion: '' });
  const [fotos, setFotos] = useState([]); // [{ id, archivo, url }]
  const [procesandoFotos, setProcesandoFotos] = useState(false);
  const [errores, setErrores] = useState({}); // { campo: ['mensaje'] }, del cliente o del servidor
  const [errorGeneral, setErrorGeneral] = useState(null);
  const [enviando, setEnviando] = useState(false);

  // Libera las URLs de las miniaturas al salir de la página
  const fotosRef = useRef(fotos);
  useEffect(() => {
    fotosRef.current = fotos;
  }, [fotos]);
  useEffect(() => () => fotosRef.current.forEach((f) => URL.revokeObjectURL(f.url)), []);

  const tipoElegido = tipos?.find((t) => String(t.id) === form.tipo);
  const esOtro = tipoElegido?.nombre === 'Otro';

  const cambiar = (campo) => (e) => setForm((prev) => ({ ...prev, [campo]: e.target.value }));
  const elegir = (campo, valor) => setForm((prev) => ({ ...prev, [campo]: valor }));
  const cambiarUbicacion = (cambios) => setUbicacion((prev) => ({ ...prev, ...cambios }));

  async function agregarFotos(e) {
    const archivos = Array.from(e.target.files);
    e.target.value = ''; // permite volver a elegir el mismo archivo
    if (archivos.length === 0) return;

    const espacio = MAX_FOTOS - fotos.length;
    const mensajes = [];
    if (archivos.length > espacio) mensajes.push(`Puedes subir máximo ${MAX_FOTOS} fotos.`);

    setProcesandoFotos(true);
    const nuevas = [];
    for (const archivo of archivos.slice(0, Math.max(espacio, 0))) {
      try {
        const listo = await prepararFoto(archivo); // valida tipo y comprime si pesa más de 5 MB
        nuevas.push({ id: crypto.randomUUID(), archivo: listo, url: URL.createObjectURL(listo) });
      } catch (err) {
        mensajes.push(err.message);
      }
    }
    setProcesandoFotos(false);
    setFotos((prev) => [...prev, ...nuevas]);
    setErrores((prev) => ({ ...prev, imagenes: mensajes.length ? mensajes : undefined }));
  }

  function quitarFoto(id) {
    const foto = fotos.find((f) => f.id === id);
    if (foto) URL.revokeObjectURL(foto.url);
    setFotos((prev) => prev.filter((f) => f.id !== id));
    setErrores((prev) => ({ ...prev, imagenes: undefined }));
  }

  // Validación rápida en el cliente; el servidor vuelve a validar todo.
  function validar() {
    const e = {};
    if (!form.tipo) e.tipo = ['Elige el tipo de incidente.'];
    if (esOtro && !form.tipo_otro.trim()) e.tipo_otro = ['Describe el tipo de incidente.'];
    if (!form.titulo.trim()) e.titulo = ['Escribe un título.'];
    const largo = form.descripcion.trim().length;
    if (largo < DESCRIPCION_MIN || largo > DESCRIPCION_MAX) {
      e.descripcion = [`La descripción debe tener entre ${DESCRIPCION_MIN} y ${DESCRIPCION_MAX} caracteres.`];
    }
    if (!form.gravedad) e.gravedad = ['Elige la gravedad.'];
    if (!form.fecha) {
      e.fecha_incidente = ['Indica la fecha y hora del incidente.'];
    } else if (new Date(form.fecha).getTime() > Date.now() + MARGEN_FUTURO_MS) {
      e.fecha_incidente = ['La fecha del incidente no puede estar en el futuro.'];
    }
    if (ubicacion.latitud == null) e.latitud = ['Coloca el pin en el mapa.'];
    return e;
  }

  function construirFormData() {
    const fd = new FormData();
    fd.append('tipo', form.tipo);
    if (esOtro) fd.append('tipo_otro', form.tipo_otro.trim());
    fd.append('titulo', form.titulo.trim());
    fd.append('descripcion', form.descripcion.trim());
    fd.append('gravedad', form.gravedad);
    fd.append('latitud', ubicacion.latitud.toFixed(6));
    fd.append('longitud', ubicacion.longitud.toFixed(6));
    fd.append('direccion', ubicacion.direccion.trim());
    // datetime-local está en la hora del dispositivo; toISOString() la convierte a UTC
    fd.append('fecha_incidente', new Date(form.fecha).toISOString());
    // La MISMA clave repetida, una vez por archivo (no "imagenes[]")
    fotos.forEach((f) => fd.append('imagenes', f.archivo));
    return fd;
  }

  async function enviar(e) {
    e.preventDefault();
    if (enviando) return;
    setErrorGeneral(null);

    const erroresCliente = validar();
    setErrores(erroresCliente);
    if (Object.keys(erroresCliente).length > 0) {
      setErrorGeneral('Revisa los campos marcados.');
      return;
    }

    setEnviando(true);
    try {
      const reporte = await crearReporte(construirFormData());
      navigate(`/reportes/${reporte.id}`); // 201: al detalle del reporte nuevo
    } catch (err) {
      const status = statusDe(err);
      if (status === 400) {
        const data = err.response.data;
        setErrores(data);
        // Errores sin campo propio (non_field_errors, detail...) van arriba
        const sinLugar = Object.keys(data).filter((campo) => !CAMPOS_CON_LUGAR.includes(campo));
        setErrorGeneral(
          sinLugar.length ? primerMensaje({ [sinLugar[0]]: data[sinLugar[0]] }) : 'Revisa los campos marcados.',
        );
      } else if (status === 401 || status === 403) {
        // TODO(auth): redirigir a /login y adjuntar el token cuando exista useAuth()
        setErrorGeneral('Debes iniciar sesión para publicar un reporte.');
      } else if (status === 429) {
        setErrorGeneral('Has enviado demasiados reportes, intenta más tarde.');
      } else {
        setErrorGeneral('No se pudo publicar el reporte. Revisa tu conexión e intenta de nuevo.');
      }
    } finally {
      setEnviando(false);
    }
  }

  const largoDescripcion = form.descripcion.trim().length;
  const errorUbicacion = [errores.latitud, errores.longitud, errores.direccion].flat().filter(Boolean).join(' ');

  return (
    <div className="crear-page">
      <Link to="/mapa" className="row crear-back">
        <span className="icon-btn">
          <Icon name="arrow-l" />
        </span>
        Mapa y reportes
      </Link>
      <h1 className="crear-title">Reportar un incidente</h1>

      {errorGeneral && <Alert type="error" message={errorGeneral} onClose={() => setErrorGeneral(null)} />}

      <form className="crear-form" onSubmit={enviar} noValidate>
        <div className="crear-col">
          <section className="card crear-card">
            <div className="lbl" id="lbl-tipo">Tipo de incidente</div>
            {errorTipos && <p className="crear-error">No se pudieron cargar los tipos.</p>}
            <div className="crear-tiles" role="radiogroup" aria-labelledby="lbl-tipo">
              {tipos?.map((tipo) => (
                <button
                  key={tipo.id}
                  type="button"
                  role="radio"
                  aria-checked={form.tipo === String(tipo.id)}
                  className={`crear-tile ${form.tipo === String(tipo.id) ? 'on' : ''}`}
                  onClick={() => elegir('tipo', String(tipo.id))}
                >
                  <Icon name={iconoTipo(tipo.nombre)} />
                  {tipo.nombre}
                </button>
              ))}
            </div>
            <FieldError errores={errores} campo="tipo" />
            {/* duracion_horas viene de /api/tipos/ (null = sin límite: no se avisa nada) */}
            {tipoElegido?.duracion_horas > 0 && (
              <p className="crear-ayuda">
                Este tipo de reporte se mostrará durante {tipoElegido.duracion_horas} horas.
              </p>
            )}

            {esOtro && (
              <label className="crear-field">
                <span>¿Qué tipo de incidente es?</span>
                <input
                  type="text"
                  value={form.tipo_otro}
                  onChange={cambiar('tipo_otro')}
                  maxLength={80}
                  placeholder="Por ejemplo: semáforo descompuesto"
                />
                <FieldError errores={errores} campo="tipo_otro" />
              </label>
            )}

            <label className="crear-field">
              <span>Título</span>
              <input
                type="text"
                value={form.titulo}
                onChange={cambiar('titulo')}
                maxLength={120}
                placeholder="Por ejemplo: bache profundo en carril derecho"
                autoCapitalize="sentences"
              />
              <FieldError errores={errores} campo="titulo" />
            </label>

            <label className="crear-field">
              <span>Descripción</span>
              <textarea
                value={form.descripcion}
                onChange={cambiar('descripcion')}
                maxLength={DESCRIPCION_MAX}
                rows={4}
                placeholder="¿Qué pasó? ¿Qué tan grave es? ¿Ocupa algún carril?"
                autoCapitalize="sentences"
              />
              <span
                className={`crear-contador ${largoDescripcion > 0 && largoDescripcion < DESCRIPCION_MIN ? 'bajo' : ''}`}
              >
                {largoDescripcion}/{DESCRIPCION_MAX} (mínimo {DESCRIPCION_MIN})
              </span>
              <FieldError errores={errores} campo="descripcion" />
            </label>

            <div className="lbl crear-sublbl" id="lbl-gravedad">Gravedad</div>
            <div className="crear-seg" role="radiogroup" aria-labelledby="lbl-gravedad">
              {GRAVEDADES.map((g) => (
                <button
                  key={g.id}
                  type="button"
                  role="radio"
                  aria-checked={form.gravedad === g.id}
                  className={form.gravedad === g.id ? 'on' : ''}
                  onClick={() => elegir('gravedad', g.id)}
                >
                  {g.nombre}
                </button>
              ))}
            </div>
            <FieldError errores={errores} campo="gravedad" />

            <label className="crear-field">
              <span>Fecha y hora del incidente</span>
              <input type="datetime-local" value={form.fecha} onChange={cambiar('fecha')} max={fechaMaxima} />
              <FieldError errores={errores} campo="fecha_incidente" />
            </label>
          </section>
        </div>

        <div className="crear-col">
          <section className="card crear-card">
            <div className="lbl">Ubicación del incidente</div>
            <UbicacionPicker
              value={ubicacion}
              onChange={cambiarUbicacion}
              error={errorUbicacion}
              icon={form.tipo ? iconoPorId(tipos, Number(form.tipo)) : 'pin'}
            />
          </section>

          <section className="card crear-card">
            <div className="lbl">Fotos (opcional, hasta {MAX_FOTOS})</div>
            <div className="crear-fotos">
              {fotos.map((foto, i) => (
                <div key={foto.id} className="thumb crear-foto">
                  <img src={foto.url} alt={`Foto ${i + 1}`} />
                  <button
                    type="button"
                    className="crear-foto-quitar"
                    onClick={() => quitarFoto(foto.id)}
                    aria-label={`Quitar foto ${i + 1}`}
                  >
                    ×
                  </button>
                </div>
              ))}
              {fotos.length < MAX_FOTOS && (
                <label className="crear-foto-agregar">
                  <Icon name="camera" />
                  {procesandoFotos ? 'Procesando…' : 'Agregar foto'}
                  <input
                    type="file"
                    accept="image/jpeg,image/png"
                    multiple
                    onChange={agregarFotos}
                    disabled={procesandoFotos}
                  />
                </label>
              )}
            </div>
            <p className="crear-ayuda">JPG o PNG, máximo 5 MB cada una. Las fotos grandes se reducen automáticamente.</p>
            <FieldError errores={errores} campo="imagenes" />
          </section>

          <button type="submit" className="btn-primary crear-enviar" disabled={enviando || procesandoFotos}>
            {enviando ? 'Publicando…' : 'Publicar reporte'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default CrearReporte;
