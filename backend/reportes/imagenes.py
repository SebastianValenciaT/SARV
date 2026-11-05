"""Validación y limpieza de las fotos que suben los usuarios.

Nunca confiamos en la extensión ni en el Content-Type que manda el navegador:
Pillow abre el archivo y nos dice qué formato es en realidad. Después se
re-codifica la imagen, lo que elimina los metadatos EXIF (las fotos de celular
traen la ubicación GPS exacta y las imágenes se sirven públicamente).
"""
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers

from .models import Imagen

MAX_BYTES = 5 * 1024 * 1024        # 5 MB por archivo
MAX_PIXELES = 40_000_000           # 40 megapíxeles: más que eso no es una foto normal
LADO_MAXIMO = 1600                 # px; reduce el tamaño guardado en la base de datos
CALIDAD_JPEG = 85

# Formato que detecta Pillow -> tipo_mime que guardamos
FORMATOS = {'JPEG': Imagen.Mime.JPEG, 'PNG': Imagen.Mime.PNG}


def procesar_imagen(archivo, etiqueta='La imagen'):
    """Valida un archivo subido y devuelve (bytes_limpios, tipo_mime).

    Lanza serializers.ValidationError con un mensaje legible si algo falla.
    """
    # 1) Tamaño ANTES de abrirlo: no gastamos memoria ni CPU en archivos enormes.
    if archivo.size > MAX_BYTES:
        raise serializers.ValidationError(f'{etiqueta} pesa más de 5 MB.')

    try:
        # 2) Pillow lee solo el encabezado: formato y dimensiones (todavía no los píxeles).
        with Image.open(archivo) as img:
            if img.format not in FORMATOS:
                raise serializers.ValidationError(f'{etiqueta} debe ser JPG o PNG.')
            ancho, alto = img.size
            if ancho * alto > MAX_PIXELES:
                raise serializers.ValidationError(f'{etiqueta} tiene demasiados píxeles (máximo 40 megapíxeles).')
            formato = img.format
            img.verify()  # revisa que la estructura del archivo no esté dañada

        # verify() deja la imagen inutilizable: se vuelve a abrir desde el inicio.
        archivo.seek(0)
        with Image.open(archivo) as img:
            img.load()  # decodifica los píxeles (aquí fallan los archivos truncados)
            # 3) Gira la imagen según la etiqueta EXIF de orientación, antes de borrar el EXIF.
            img = ImageOps.exif_transpose(img)
            # 4) Lado mayor a 1600 px como máximo, conservando la proporción.
            img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
            # 5) Re-codificar. Como no pasamos `exif=...` a save(), el EXIF (y el GPS) no se copia.
            salida = BytesIO()
            if formato == 'JPEG':
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')  # JPEG no admite transparencia ni CMYK/paleta aquí
                img.save(salida, format='JPEG', quality=CALIDAD_JPEG, optimize=True)
            else:
                img.save(salida, format='PNG', optimize=True)
    except serializers.ValidationError:
        raise
    except Image.DecompressionBombError:
        raise serializers.ValidationError(f'{etiqueta} es demasiado grande para procesarla.')
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        # UnidentifiedImageError: no es una imagen. OSError/SyntaxError: archivo dañado.
        raise serializers.ValidationError(f'{etiqueta} no es una imagen válida o está dañada.')

    return salida.getvalue(), FORMATOS[formato]
