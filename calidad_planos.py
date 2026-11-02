# -*- coding: utf-8 -*-
"""
ASPLOT CENTER - Calidad de planos (Sprint 6, PB-13)

Verifica, sin bloquear la subida:
  - formato declarado vs. contenido real (firma de bytes);
  - DPI en JPG/PNG leyendo la cabecera (JFIF / pHYs), sin Pillow;
  - tamano de pagina en PDF (A0-A4 o personalizado);
  - legibilidad del archivo.

Python puro + pypdf: funciona en Windows, Render y el G60 (Termux).
"""

from __future__ import annotations

import os
import struct

from cotizador_auto import PUNTO_A_METRO, detectar_formato

DPI_MINIMO_DEFECTO = 150

EXTENSION_A_FORMATO = {
    'pdf': 'pdf',
    'png': 'png',
    'jpg': 'jpg',
    'jpeg': 'jpg',
    'dwg': 'dwg',
    'dxf': 'dxf',
}


def _item(clave, etiqueta, estado, detalle):
    return {
        'clave': clave,
        'etiqueta': etiqueta,
        'estado': estado,
        'detalle': detalle,
    }


def _leer_cabecera(ruta, bytes_maximos=4096):
    try:
        with open(ruta, 'rb') as archivo:
            return archivo.read(bytes_maximos)
    except OSError:
        return b''


def _formato_real(ruta):
    cabecera = _leer_cabecera(ruta, 64)
    if cabecera.startswith(b'%PDF'):
        return 'pdf'
    if cabecera.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if cabecera.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if cabecera.startswith(b'AC10'):
        return 'dwg'
    if cabecera.startswith(b'AutoCAD Binary DXF'):
        return 'dxf'
    texto = _leer_cabecera(ruta, 4096).decode('utf-8', errors='replace')
    if 'SECTION' in texto and 'HEADER' in texto:
        return 'dxf'
    return None


def _dpi_jpg(ruta):
    """Lee la densidad declarada en el segmento APP0/JFIF del JPEG."""
    datos = _leer_cabecera(ruta, 65536)
    if not datos.startswith(b'\xff\xd8'):
        return None
    indice = 2
    total = len(datos)
    while indice + 4 <= total:
        if datos[indice] != 0xFF:
            indice += 1
            continue
        marcador = datos[indice + 1]
        if marcador in (0xD8, 0xD9):
            indice += 2
            continue
        if marcador == 0xDA:  # inicio de los datos de imagen
            break
        longitud = struct.unpack('>H', datos[indice + 2:indice + 4])[0]
        if longitud < 2:
            break
        if marcador == 0xE0 and datos[indice + 4:indice + 9] == b'JFIF\x00':
            if indice + 16 > total:
                return None
            unidades = datos[indice + 11]
            xdensidad = struct.unpack('>H', datos[indice + 12:indice + 14])[0]
            if unidades == 1:      # puntos por pulgada
                return float(xdensidad)
            if unidades == 2:      # puntos por centimetro
                return xdensidad * 2.54
            return None
        indice += 2 + longitud
    return None


def _dpi_png(ruta):
    """Lee el chunk pHYs (pixeles por metro) del PNG."""
    datos = _leer_cabecera(ruta, 262144)
    if not datos.startswith(b'\x89PNG\r\n\x1a\n'):
        return None
    indice = 8
    total = len(datos)
    while indice + 8 <= total:
        largo = struct.unpack('>I', datos[indice:indice + 4])[0]
        tipo = datos[indice + 4:indice + 8]
        if tipo == b'pHYs' and largo >= 9 and indice + 17 <= total:
            ppu = struct.unpack('>I', datos[indice + 8:indice + 12])[0]
            unidad = datos[indice + 16]
            if unidad == 1:        # pixeles por metro
                return ppu * 0.0254
            return None
        if tipo in (b'IDAT', b'IEND'):
            break
        indice += 12 + largo
    return None


def _chequeo_pagina_pdf(ruta):
    try:
        from pypdf import PdfReader
    except ImportError:
        return _item('pagina', 'Tamaño de página', 'no_verificable',
                     'El lector de PDF no está disponible')
    try:
        lector = PdfReader(ruta)
        if lector.is_encrypted:
            try:
                lector.decrypt('')
            except Exception:
                pass
            if lector.is_encrypted:
                return _item('pagina', 'Tamaño de página', 'aviso',
                             'PDF protegido con contraseña')
        paginas = list(lector.pages)
    except Exception:
        return _item('pagina', 'Tamaño de página', 'aviso',
                     'El PDF está corrupto o no se pudo leer')

    if not paginas:
        return _item('pagina', 'Tamaño de página', 'aviso', 'El PDF no tiene páginas')

    formatos = set()
    primera = None
    for pagina in paginas:
        try:
            caja = pagina.mediabox
            ancho = abs(float(caja.width)) * PUNTO_A_METRO
            alto = abs(float(caja.height)) * PUNTO_A_METRO
        except Exception:
            return _item('pagina', 'Tamaño de página', 'aviso',
                         'El PDF tiene una página ilegible')
        if ancho <= 0 or alto <= 0:
            return _item('pagina', 'Tamaño de página', 'aviso',
                         'El PDF declara una página sin dimensiones válidas')
        if primera is None:
            primera = (ancho, alto)
        formatos.add(detectar_formato(ancho, alto))

    if len(formatos) > 1:
        return _item('pagina', 'Tamaño de página', 'aviso',
                     'Las páginas tienen tamaños distintos: %s'
                     % ', '.join(sorted(formatos)))
    formato = next(iter(formatos))
    if formato == 'personalizado':
        return _item('pagina', 'Tamaño de página', 'aviso',
                     'Tamaño personalizado (%.2f x %.2f m); no es A0-A4'
                     % (primera[0], primera[1]))
    return _item('pagina', 'Tamaño de página', 'ok',
                 '%d página(s) %s' % (len(paginas), formato))


def _chequeo_legible(ruta, formato_real):
    if formato_real == 'pdf':
        try:
            from pypdf import PdfReader
            lector = PdfReader(ruta)
            if lector.is_encrypted:
                try:
                    lector.decrypt('')
                except Exception:
                    pass
                if lector.is_encrypted:
                    return _item('legible', 'Legibilidad', 'aviso',
                                 'PDF protegido con contraseña')
            _ = len(lector.pages)
            return _item('legible', 'Legibilidad', 'ok', 'El PDF abre correctamente')
        except Exception:
            return _item('legible', 'Legibilidad', 'aviso',
                         'No se pudo leer el PDF')
    if formato_real == 'dxf':
        texto = _leer_cabecera(ruta, 4096).decode('utf-8', errors='replace')
        if 'SECTION' in texto:
            return _item('legible', 'Legibilidad', 'ok', 'Cabecera DXF válida')
        return _item('legible', 'Legibilidad', 'aviso', 'Cabecera DXF no reconocida')
    if formato_real == 'dwg':
        return _item('legible', 'Legibilidad', 'ok',
                     'Cabecera DWG válida (formato propietario, sin más verificación)')
    return _item('legible', 'Legibilidad', 'no_verificable',
                 'Sin verificaciones adicionales para este formato')


def verificar_archivo(ruta, dpi_minimo=DPI_MINIMO_DEFECTO):
    """Devuelve la lista de verificaciones. Nunca lanza excepción."""
    items = []

    if not ruta or not os.path.isfile(ruta):
        items.append(_item('archivo', 'Archivo', 'aviso',
                           'El archivo no existe en el servidor'))
        items.append(_item('formato', 'Formato declarado vs. real',
                           'no_verificable', 'Sin archivo'))
        items.append(_item('dpi', 'Resolución (DPI)', 'no_verificable', 'Sin archivo'))
        items.append(_item('pagina', 'Tamaño de página', 'no_verificable', 'Sin archivo'))
        return items

    tamano = os.path.getsize(ruta)
    if tamano == 0:
        items.append(_item('archivo', 'Archivo', 'aviso', 'El archivo está vacío (0 bytes)'))
    else:
        items.append(_item('archivo', 'Archivo', 'ok',
                           '%.1f KB' % (tamano / 1024.0)))

    extension = os.path.splitext(ruta)[1].lower().lstrip('.')
    esperado = EXTENSION_A_FORMATO.get(extension)
    real = _formato_real(ruta)

    if real is None:
        items.append(_item('formato', 'Formato declarado vs. real', 'aviso',
                           'No se reconoce el contenido del archivo'))
    elif esperado is None:
        items.append(_item('formato', 'Formato declarado vs. real', 'aviso',
                           'Extensión .%s no soportada' % extension))
    elif esperado != real:
        items.append(_item('formato', 'Formato declarado vs. real', 'aviso',
                           'La extensión .%s no coincide con el contenido (%s)'
                           % (extension, real.upper())))
    else:
        items.append(_item('formato', 'Formato declarado vs. real', 'ok',
                           '%s coincide con la extensión .%s'
                           % (real.upper(), extension)))

    if real == 'jpg':
        dpi = _dpi_jpg(ruta)
        origen = 'JPG'
    elif real == 'png':
        dpi = _dpi_png(ruta)
        origen = 'PNG'
    else:
        dpi = None
        origen = None

    if origen is None:
        items.append(_item('dpi', 'Resolución (DPI)', 'no_verificable',
                           'Solo se verifica en JPG/PNG'))
    elif dpi is None:
        items.append(_item('dpi', 'Resolución (DPI)', 'no_verificable',
                           'El %s no declara resolución' % origen))
    elif dpi < dpi_minimo:
        items.append(_item('dpi', 'Resolución (DPI)', 'aviso',
                           '%d DPI (mínimo recomendado %d)' % (round(dpi), round(dpi_minimo))))
    else:
        items.append(_item('dpi', 'Resolución (DPI)', 'ok',
                           '%d DPI' % round(dpi)))

    if real == 'pdf':
        items.append(_chequeo_pagina_pdf(ruta))
    else:
        items.append(_item('pagina', 'Tamaño de página', 'no_verificable',
                           'Solo se verifica en PDF'))

    items.append(_chequeo_legible(ruta, real))
    return items


def resumen_advertencias(items):
    """Frases cortas de los items en estado 'aviso' (para flashes)."""
    return ['%s: %s' % (item['etiqueta'], item['detalle'])
            for item in items if item['estado'] == 'aviso']
