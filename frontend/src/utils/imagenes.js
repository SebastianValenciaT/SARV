/*
  imagenes.js — Prepara las fotos antes de subirlas.
  El servidor acepta JPG/PNG de máximo 5 MB. Las fotos de celular suelen pesar
  más, así que se comprimen aquí con un <canvas> antes de rechazarlas.
  (El servidor vuelve a validar todo: esto solo mejora la experiencia.)
*/
export const MAX_FOTOS = 3;
export const MAX_BYTES = 5 * 1024 * 1024;
export const TIPOS_PERMITIDOS = ['image/jpeg', 'image/png'];

// Intentos de compresión, de mejor a peor calidad, hasta un mínimo razonable
const PASOS = [
  { lado: 1600, calidad: 0.85 },
  { lado: 1600, calidad: 0.7 },
  { lado: 1280, calidad: 0.7 },
  { lado: 1024, calidad: 0.6 },
];

/**
 * Devuelve un File listo para subir, o lanza un Error con un mensaje legible.
 */
export async function prepararFoto(archivo) {
  if (!TIPOS_PERMITIDOS.includes(archivo.type)) {
    throw new Error(`"${archivo.name}" no es JPG ni PNG.`);
  }
  if (archivo.size <= MAX_BYTES) return archivo;
  return comprimir(archivo);
}

async function comprimir(archivo) {
  let bitmap;
  try {
    // createImageBitmap decodifica la imagen y respeta su orientación (fotos giradas)
    bitmap = await createImageBitmap(archivo, { imageOrientation: 'from-image' });
  } catch {
    throw new Error(`No pudimos abrir "${archivo.name}" para reducirla. Prueba con otra foto.`);
  }

  try {
    for (const paso of PASOS) {
      const blob = await dibujarJpeg(bitmap, paso);
      // Se vuelve a comprobar el peso: si aún no cabe, se intenta el siguiente paso
      if (blob && blob.size <= MAX_BYTES) {
        return new File([blob], nombreJpg(archivo.name), { type: 'image/jpeg' });
      }
    }
  } finally {
    bitmap.close(); // libera la memoria de la imagen decodificada
  }
  throw new Error(`"${archivo.name}" pesa más de 5 MB incluso después de reducirla. Elige otra foto.`);
}

function dibujarJpeg(bitmap, { lado, calidad }) {
  const escala = Math.min(1, lado / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * escala);
  canvas.height = Math.round(bitmap.height * escala);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#fff'; // JPEG no tiene transparencia: fondo blanco para los PNG
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  // toBlob usa callback; lo envolvemos en una promesa para poder usar await
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', calidad));
}

function nombreJpg(nombre) {
  return nombre.replace(/\.[^.]+$/, '') + '.jpg';
}
