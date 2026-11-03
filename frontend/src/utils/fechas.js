/*
  fechas.js — Formato de fechas en español. La API manda fechas ISO 8601;
  aquí se muestran siempre en la hora de Ciudad Juárez, sin importar la
  zona horaria de la computadora del usuario.
*/
const LOCALE = 'es-MX';
const TIME_ZONE = 'America/Ciudad_Juarez';

const formatoFechaHora = new Intl.DateTimeFormat(LOCALE, {
  day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: TIME_ZONE,
});
const formatoDiaMes = new Intl.DateTimeFormat(LOCALE, { day: 'numeric', month: 'short', timeZone: TIME_ZONE });
const formatoHora = new Intl.DateTimeFormat(LOCALE, { hour: '2-digit', minute: '2-digit', timeZone: TIME_ZONE });
// 'en-CA' da AAAA-MM-DD: sirve para comparar si dos fechas caen el mismo día en Juárez.
const formatoDia = new Intl.DateTimeFormat('en-CA', { timeZone: TIME_ZONE });
const relativo = new Intl.RelativeTimeFormat(LOCALE, { numeric: 'auto' });

const MINUTO = 60 * 1000;
const HORA = 60 * MINUTO;
const DIA = 24 * HORA;

// "19 sept 2026, 10:32"
export function formatFechaHora(iso) {
  return formatoFechaHora.format(new Date(iso));
}

// "Hoy, 10:14" · "Ayer, 19:40" · "22 sept, 21:50"
export function formatCuando(iso) {
  const fecha = new Date(iso);
  const dia = formatoDia.format(fecha);
  const hora = formatoHora.format(fecha);
  if (dia === formatoDia.format(new Date())) return `Hoy, ${hora}`;
  if (dia === formatoDia.format(new Date(Date.now() - DIA))) return `Ayer, ${hora}`;
  return `${formatoDiaMes.format(fecha)}, ${hora}`;
}

// "hace 5 minutos" · "hace 2 horas" · "ayer" · "hace 3 días"; más de una semana → fecha
export function formatRelativa(iso) {
  const diferencia = Date.now() - new Date(iso).getTime();
  if (diferencia < MINUTO) return 'hace un momento';
  if (diferencia < HORA) return relativo.format(-Math.floor(diferencia / MINUTO), 'minute');
  if (diferencia < DIA) return relativo.format(-Math.floor(diferencia / HORA), 'hour');
  if (diferencia < 7 * DIA) return relativo.format(-Math.floor(diferencia / DIA), 'day');
  return `el ${formatoDiaMes.format(new Date(iso))}`;
}

export function capitalizar(texto) {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

// Valor para <input type="datetime-local">: "AAAA-MM-DDTHH:mm" en la hora del dispositivo
export function fechaLocalParaInput(fecha) {
  const local = new Date(fecha.getTime() - fecha.getTimezoneOffset() * MINUTO);
  return local.toISOString().slice(0, 16);
}
