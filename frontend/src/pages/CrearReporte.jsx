import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import Alert from '../components/common/Alerts';
import Icon from '../components/common/Icon';
import UbicacionPicker from '../components/ubicacion/UbicacionPicker';
import { iconoPorId, iconoTipo } from '../constants/tipos';
import { useTipos } from '../hooks/useTipos';
import { actualizarReporte, crearReporte, obtenerReporte } from '../services/reportes';
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
  'latitud', 'longitud', 'direccion', 'imagenes', 'imagenes_eliminar'];

function FieldError({ errores, campo }) {
  const mensajes = errores[campo];
  if (!mensajes) return null;
  return <p className="crear-error">{[].concat(mensajes).join(' ')}</p>;
}

/**
 * Formulario de reporte con dos modos:
 * - Crear  (/crear-reporte): POST /api/reportes/.
 * - Editar (/reportes/:id/editar): precarga el reporte y manda PATCH /api/reportes/{id}/
 *   (RF-45, HU-021). La fecha del incidente no se edita y las fotos ya guardadas
 *   se pueden quitar (se mandan sus id en `imagenes_eliminar`).
 * En ambos modos las fotos nuevas van con la clave `imagenes` repetida.
 */
function CrearReporte() {
  const navigate = useNavigate();
  const location = useLocation();
  const { id } = useParams();
  const editando = Boolean(id);
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
  // Fotos nuevas: { id, archivo, url }. Fotos ya guardadas (al editar): { id, imagenId, url }.
  const [fotos, setFotos] = useState([]);
  const [imagenesEliminar, setImagenesEliminar] = useState([]); // id de fotos guardadas que se quitan
  const [procesandoFotos, setProcesandoFotos] = useState(false);
  const [errores, setErrores] = useState({}); // { campo: ['mensaje'] }, del cliente o del servidor
  const [errorGeneral, setErrorGeneral] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [cargandoReporte, setCargandoReporte] = useState(editando);
  const [errorCarga, setErrorCarga] = useState(null);

  // Libera las URLs de las miniaturas nuevas al salir (las guardadas son URLs del servidor)
  const fotosRef = useRef(fotos);
  useEffect(() => {
    fotosRef.current = fotos;
  }, [fotos]);
  useEffect(
    () => () => fotosRef.current.forEach((f) => f.archivo && URL.revokeObjectURL(f.url)),
    [],
  );

  // Modo editar: precarga el reporte. Espera a los tipos para saber si es "Otro".
  useEffect(() => {
    if (!editando || !tipos) return;
    let activo = true;
    obtenerReporte(id)
      .then((r) => {
        if (!activo) return;
        if (!r.es_autor) {
          setErrorCarga('Solo el autor puede editar este reporte.');
          return;
        }
        if (r.estado !== 'sin_resolver') {
          setErrorCarga('Este reporte ya no se puede editar porque está resuelto o expiró.');
          return;
        }
        const esTipoOtro = tipos.find((t) => t.id === r.tipo)?.nombre === 'Otro';
        setForm({
          tipo: String(r.tipo),
          // Con tipo "Otro", tipo_etiqueta trae la descripción que escribió el usuario
          tipo_otro: esTipoOtro ? r.tipo_etiqueta : '',
          titulo: r.titulo,
          descripcion: r.descripcion,
          gravedad: r.gravedad,
          fecha: fechaLocalParaInput(new Date(r.fecha_incidente)),
        });
        setUbicacion({ latitud: r.latitud, longitud: r.longitud, direccion: r.direccion || '' });
        setFotos(r.imagenes.map((img) => ({ id: `guardada-${img.id}`, imagenId: img.id, url: img.url })));
      })
      .catch((err) => {
        if (!activo) return;
        setErrorCarga(
          statusDe(err) === 404
            ? 'Este reporte no existe.'
            : 'No se pudo cargar el reporte. Revisa tu conexión e intenta de nuevo.',
        );
      })
      .finally(() => activo && setCargandoReporte(false));
    return () => {
      activo = false;
    };
  }, [editando, id, tipos]);

  const tipoElegido = tipos?.find((t) => String(t.id) === form.tipo);
  const esOtro = tipoElegido?.nombre === 'Otro';
  const rutaRegreso = editando ? '/mis-reportes' : '/mapa';

  const cambiar = (campo) => (e) => setForm((prev) => ({ ...prev, [campo]: e.target.value }));
  const elegir = (campo, valor) => setForm((prev) => ({ ...prev, [campo]: valor }));
  const cambiarUbicacion = (cambios) => setUbicacion((prev) => ({ ...prev, ...cambios }));

  async function agregarFotos(e) {
    const archivos = Array.from(e.target.files);
    e.target.value = ''; // permite volver a elegir el mismo archivo
    if (archivos.length === 0) return;

    const espacio = MAX_FOTOS - fotos.length; // cuenta guardadas + nuevas
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

  function quitarFoto(fotoId) {
    const foto = fotos.find((f) => f.id === fotoId);
    if (foto?.archivo) URL.revokeObjectURL(foto.url);
    if (foto?.imagenId) setImagenesEliminar((prev) => [...prev, foto.imagenId]);
    setFotos((prev) => prev.filter((f) => f.id !== fotoId));
    setErrores((prev) => ({ ...prev, imagenes: undefined, imagenes_eliminar: undefined }));
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
    // Al editar, la fecha del incidente no se puede cambiar (HU-021): no se valida
    if (!editando) {
      if (!form.fecha) {
        e.fecha_incidente = ['Indica la fecha y hora del incidente.'];
      } else if (new Date(form.fecha).getTime() > Date.now() + MARGEN_FUTURO_MS) {
        e.fecha_incidente = ['La fecha del incidente no puede estar en el futuro.'];
      }
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
    fd.append('latitud', Number(ubicacion.latitud).toFixed(6));
    fd.append('longitud', Number(ubicacion.longitud).toFixed(6));
    fd.append('direccion', (ubicacion.direccion || '').trim());
    if (!editando) {
      // datetime-local está en la hora del dispositivo; toISOString() la convierte a UTC
      fd.append('fecha_incidente', new Date(form.fecha).toISOString());
    }
    // Solo las fotos nuevas; la MISMA clave repetida, una vez por archivo (no "imagenes[]")
    fotos.forEach((f) => f.archivo && fd.append('imagenes', f.archivo));
    imagenesEliminar.forEach((imagenId) => fd.append('imagenes_eliminar', imagenId));
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
      if (editando) {
        await actualizarReporte(id, construirFormData());
        // UC-06: al guardar se regresa a Mis reportes con un mensaje de éxito
        navigate('/mis-reportes', { state: { mensaje: 'Los cambios se guardaron.' } });
      } else {
        const reporte = await crearReporte(construirFormData());
        navigate(`/reportes/${reporte.id}`); // 201: al detalle del reporte nuevo
      }
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
      } else if (status === 401) {
        // La sesión venció y api.js no pudo renovarla: a /login, que regresa aquí al entrar
        navigate('/login', { state: { from: location } });
      } else if (status === 403) {
        setErrorGeneral(
          editando ? 'Solo el autor puede editar este reporte.' : 'No tienes permiso para publicar reportes.',
        );
      } else if (status === 404 && editando) {
        setErrorGeneral('Este reporte ya no existe.');
      } else if (status === 409) {
        // El reporte se resolvió o expiró mientras se editaba (RN-14); el servidor manda el motivo
        setErrorGeneral(err.response.data?.detail || 'Este reporte ya no admite cambios.');
      } else if (status === 429) {
        setErrorGeneral('Has enviado demasiados reportes, intenta más tarde.');
      } else {
        setErrorGeneral(
          editando
            ? 'No se pudieron guardar los cambios. Revisa tu conexión e intenta de nuevo.'
            : 'No se pudo publicar el reporte. Revisa tu conexión e intenta de nuevo.',
        );
      }
    } finally {
      setEnviando(false);
    }
  }

  const largoDescripcion = form.descripcion.trim().length;
  const errorUbicacion = [errores.latitud, errores.longitud, errores.direccion].flat().filter(Boolean).join(' ');
  const errorFotos = [errores.imagenes, errores.imagenes_eliminar].flat().filter(Boolean);

  const encabezado = (
    <>
      <Link to={rutaRegreso} className="row crear-back">
        <span className="icon-btn">
          <Icon name="arrow-l" />
        </span>
        {editando ? 'Mis reportes' : 'Mapa y reportes'}
      </Link>
      <h1 className="crear-title">{editando ? 'Editar reporte' : 'Reportar un incidente'}</h1>
    </>
  );

  // Modo editar: mientras carga, o si no se puede editar, no se muestra el formulario
  if (editando && (errorCarga || (errorTipos && !tipos))) {
    return (
      <div className="crear-page">
        {encabezado}
        <p className="crear-error">{errorCarga || 'No se pudieron cargar los tipos de incidente.'}</p>
      </div>
    );
  }
  if (editando && cargandoReporte) {
    return (
      <div className="crear-page">
        {encabezado}
        <p className="crear-ayuda">Cargando el reporte…</p>
      </div>
    );
  }

  return (
    <div className="crear-page">
      {encabezado}

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
              <input
                type="datetime-local"
                value={form.fecha}
                onChange={cambiar('fecha')}
                max={fechaMaxima}
                disabled={editando}
              />
              {editando && <span className="crear-ayuda">La fecha y hora del incidente no se pueden cambiar.</span>}
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
            {errorFotos.length > 0 && <p className="crear-error">{errorFotos.join(' ')}</p>}
          </section>

          <button type="submit" className="btn-primary crear-enviar" disabled={enviando || procesandoFotos}>
            {editando
              ? (enviando ? 'Guardando…' : 'Guardar cambios')
              : (enviando ? 'Publicando…' : 'Publicar reporte')}
          </button>
          {editando && (
            // UC-06: si cancela, se descartan los cambios y regresa a Mis reportes
            <button
              type="button"
              className="crear-cancelar"
              onClick={() => navigate('/mis-reportes')}
              disabled={enviando}
            >
              Cancelar
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default CrearReporte;