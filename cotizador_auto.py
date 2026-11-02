# -*- coding: utf-8 -*-
"""
ASPLOT CENTER - Cubicación y cotización automática (Sprint 5, PB-10)

Módulo Python puro (sin Flask ni dependencias nativas) para que funcione
igual en Windows, Render (Linux) y el servidor Termux del G60.

- PDF: tamaño de página con pypdf (1 pt = 1/72 pulgada).
- DXF: lector propio de la cabecera ($INSUNITS, $EXTMIN, $EXTMAX).
- Precio: área x tarifa/m2 + insumos + margen, con Decimal y redondeo
  comercial a 2 decimales.
"""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# 1 punto PDF = 1/72 pulgada = 0.0254/72 metros
PUNTO_A_METRO = 0.0254 / 72.0

# Formatos ISO 216 (lado menor, lado mayor) en metros
FORMATOS_ISO = (
    ('A0', 0.841, 1.189),
    ('A1', 0.594, 0.841),
    ('A2', 0.420, 0.594),
    ('A3', 0.297, 0.420),
    ('A4', 0.210, 0.297),
)
TOLERANCIA_FORMATO = 0.02  # +-2 % sobre cada lado

# Unidades DXF ($INSUNITS) -> factor a metros
UNIDADES_DXF = {
    1: (0.0254, 'pulgadas'),
    2: (0.3048, 'pies'),
    4: (0.001, 'mm'),
    5: (0.01, 'cm'),
    6: (1.0, 'm'),
}

EXTENSIONES_ANALIZABLES = ('pdf', 'dxf')


def _decimal(valor):
    """Convierte un numero (float/str/Decimal/None) a Decimal seguro."""
    if valor is None:
        return Decimal('0')
    return Decimal(str(valor))


def _redondear(valor, decimales=2):
    """Redondeo comercial (mitad hacia arriba) con la cantidad de decimales dada."""
    cuantia = Decimal('1.' + '0' * decimales) if decimales > 0 else Decimal('1')
    return float(_decimal(valor).quantize(cuantia, rounding=ROUND_HALF_UP))


def _error(mensaje, advertencias=None):
    """Resultado uniforme de analisis fallido (nunca lanza excepcion)."""
    return {
        'ok': False,
        'mensaje': mensaje,
        'formato': None,
        'paginas': 0,
        'detalle_area': '',
        'ancho_m': 0.0,
        'alto_m': 0.0,
        'area_m2': 0.0,
        'advertencias': list(advertencias or []),
    }


def _resultado_ok(formato, paginas, detalle, ancho, alto, area,
                 advertencias=None, formato_iso='personalizado'):
    return {
        'ok': True,
        'mensaje': '',
        'formato': formato,
        'formato_iso': formato_iso,
        'paginas': paginas,
        'detalle_area': detalle,
        'ancho_m': _redondear(ancho, 4),
        'alto_m': _redondear(alto, 4),
        'area_m2': _redondear(area, 4),
        'advertencias': list(advertencias or []),
    }


def detectar_formato(ancho_m, alto_m):
    """Devuelve 'A0'..'A4' si las medidas coinciden (tolerancia +-2 %) o 'personalizado'."""
    menor, mayor = sorted((ancho_m, alto_m))
    for nombre, lado_menor, lado_mayor in FORMATOS_ISO:
        if (abs(menor - lado_menor) <= lado_menor * TOLERANCIA_FORMATO
                and abs(mayor - lado_mayor) <= lado_mayor * TOLERANCIA_FORMATO):
            return nombre
    return 'personalizado'


def analizar_pdf(ruta):
    """Suma el area de todas las paginas del PDF. Devuelve dict uniforme."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return _error('El lector de PDF no esta disponible en el servidor '
                      '(falta la libreria pypdf)')

    try:
        lector = PdfReader(ruta)
        if lector.is_encrypted:
            try:
                lector.decrypt('')
            except Exception:
                return _error('El PDF esta protegido con contrasena')
            if lector.is_encrypted:
                return _error('El PDF esta protegido con contrasena')
    except Exception:
        return _error('El PDF esta corrupto o no se pudo leer')

    try:
        paginas = list(lector.pages)
    except Exception:
        return _error('El PDF esta corrupto o no se pudo leer')

    if not paginas:
        return _error('El PDF no tiene paginas')

    advertencias = []
    area_total = 0.0
    primera = None
    formatos = set()
    for numero, pagina in enumerate(paginas, start=1):
        try:
            caja = pagina.mediabox
            ancho = abs(float(caja.width)) * PUNTO_A_METRO
            alto = abs(float(caja.height)) * PUNTO_A_METRO
        except Exception:
            return _error('El PDF tiene una pagina ilegible (pagina %d)' % numero)
        if ancho <= 0 or alto <= 0:
            return _error('El PDF declara una pagina sin dimensiones validas')
        if primera is None:
            primera = (ancho, alto)
        formatos.add(detectar_formato(ancho, alto))
        area_total += ancho * alto

    if len(formatos) > 1:
        advertencias.append('Las paginas tienen tamanos distintos; el area es la suma de todas')

    formato = detectar_formato(*primera)
    if formato == 'personalizado':
        detalle = '%d pagina(s) de tamano personalizado' % len(paginas)
    else:
        detalle = '%d pagina(s) %s' % (len(paginas), formato)

    return _resultado_ok('pdf', len(paginas), detalle,
                         primera[0], primera[1], area_total, advertencias,
                         formato_iso=formato)


def _leer_cabecera_dxf(lineas):
    """Extrae $INSUNITS, $EXTMIN y $EXTMAX de la seccion HEADER del DXF."""
    variable = None
    unidades = None
    extmin = {}
    extmax = {}
    total = len(lineas)
    i = 0
    while i + 1 < total:
        codigo = lineas[i].strip()
        valor = lineas[i + 1].strip()
        i += 2
        if codigo == '9':
            variable = valor
            continue
        if variable == '$INSUNITS' and codigo == '70':
            try:
                unidades = int(float(valor))
            except ValueError:
                pass
        elif variable == '$EXTMIN' and codigo in ('10', '20'):
            try:
                extmin[codigo] = float(valor)
            except ValueError:
                pass
        elif variable == '$EXTMAX' and codigo in ('10', '20'):
            try:
                extmax[codigo] = float(valor)
            except ValueError:
                pass
    return unidades, extmin, extmax


def analizar_dxf(ruta):
    """Calcula la extension del dibujo a partir de $EXTMIN/$EXTMAX del DXF."""
    try:
        with open(ruta, 'rb') as archivo:
            cabecera = archivo.read(22)
        if cabecera.startswith(b'AutoCAD Binary DXF'):
            return _error('El DXF es binario y no se puede analizar; '
                          'guardalo como DXF ASCII o PDF')
        with open(ruta, 'r', encoding='utf-8', errors='replace') as archivo:
            lineas = archivo.read().splitlines()
    except OSError:
        return _error('No se pudo abrir el archivo DXF')

    if not lineas:
        return _error('El DXF esta vacio')

    unidades, extmin, extmax = _leer_cabecera_dxf(lineas)
    if not extmin or not extmax or '10' not in extmin or '20' not in extmin \
            or '10' not in extmax or '20' not in extmax:
        return _error('El DXF no declara las extensiones del dibujo '
                      '($EXTMIN/$EXTMAX)')

    advertencias = []
    factor, nombre_unidad = UNIDADES_DXF.get(unidades, (None, None))
    if factor is None:
        factor, nombre_unidad = 0.001, 'mm'
        advertencias.append('El DXF no declara unidades; se asumen milimetros')

    ancho = abs(extmax['10'] - extmin['10']) * factor
    alto = abs(extmax['20'] - extmin['20']) * factor
    if ancho <= 0 or alto <= 0:
        return _error('El DXF declara una extension de dibujo vacia')

    detalle = 'DXF %.2f x %.2f m (%s)' % (ancho, alto, nombre_unidad)
    return _resultado_ok('dxf', 1, detalle, ancho, alto, ancho * alto, advertencias)


def analizar_archivo(ruta):
    """Analiza un plano PDF o DXF segun su extension real."""
    if not ruta or not os.path.isfile(ruta):
        return _error('El archivo no existe en el servidor')
    extension = os.path.splitext(ruta)[1].lower().lstrip('.')
    if extension == 'pdf':
        return analizar_pdf(ruta)
    if extension == 'dxf':
        return analizar_dxf(ruta)
    return _error('Formato no analizable (%s); solo PDF o DXF' % (extension or 'desconocido'))


def calcular_precio(area_m2, papel, tinta, tarifa_m2, margen_pct,
                    rendimiento_rollo_m2, rendimiento_cartucho_m2):
    """
    Calcula el desglose de la cotizacion.

    papel/tinta: dict con nombre, precio_compra, unidad, stock (o None).
    Los insumos se consumen de forma proporcional al area.
    """
    advertencias = []
    area = _decimal(area_m2)

    if area <= 0:
        return {'ok': False, 'mensaje': 'El area debe ser mayor que cero'}

    base = _redondear(area * _decimal(tarifa_m2), 2)

    lineas = []

    def _linea_insumo(datos, rendimiento, unidad_defecto, etiqueta):
        if not datos:
            advertencias.append('No hay %s cargado en materiales' % etiqueta)
            return Decimal('0')
        rendimiento_dec = _decimal(rendimiento)
        if rendimiento_dec <= 0:
            advertencias.append('El rendimiento de %s no es valido' % etiqueta)
            return Decimal('0')
        fraccion = area / rendimiento_dec
        precio = _decimal(datos.get('precio_compra'))
        subtotal = _redondear(fraccion * precio, 2)
        if precio <= 0:
            advertencias.append('%s no tiene precio de compra cargado' % datos.get('nombre', etiqueta))
        stock = datos.get('stock')
        lineas.append({
            'nombre': datos.get('nombre', etiqueta),
            'cantidad': _redondear(fraccion, 4),
            'unidad': datos.get('unidad') or unidad_defecto,
            'precio': _redondear(precio, 2),
            'subtotal': subtotal,
            'stock': stock,
            'alcanza': None if stock is None else bool(stock >= float(fraccion)),
        })
        return _decimal(subtotal)

    subtotal_papel = _linea_insumo(papel, rendimiento_rollo_m2, 'rollo', 'papel')
    subtotal_tinta = _linea_insumo(tinta, rendimiento_cartucho_m2, 'cartucho', 'tinta')
    insumos = _redondear(subtotal_papel + subtotal_tinta, 2)

    margen = _redondear((_decimal(base) + _decimal(insumos)) * _decimal(margen_pct) / Decimal('100'), 2)
    total = _redondear(_decimal(base) + _decimal(insumos) + _decimal(margen), 2)

    return {
        'ok': True,
        'mensaje': '',
        'tarifa_m2': _redondear(tarifa_m2, 2),
        'base': base,
        'insumos': lineas,
        'subtotal_insumos': insumos,
        'margen_pct': _redondear(margen_pct, 2),
        'margen': margen,
        'total': total,
        'advertencias': advertencias,
    }


def texto_desglose(analisis, desglose, fecha=None):
    """Texto legible del desglose para concatenar en las notas del proyecto."""
    momento = fecha or datetime.now()
    lineas = [
        'Cotizacion automatica (%s)' % momento.strftime('%Y-%m-%d %H:%M'),
        'Archivo: %s' % analisis.get('detalle_area', ''),
        'Area de impresion: %.4f m2' % analisis.get('area_m2', 0.0),
        'Tarifa: $%.2f/m2 -> $%.2f' % (
            desglose.get('tarifa_m2', 0.0), desglose.get('base', 0.0)),
    ]
    for insumo in desglose.get('insumos', []):
        lineas.append('Insumo: %s %.4f %s x $%.2f = $%.2f' % (
            insumo['nombre'], insumo['cantidad'], insumo['unidad'],
            insumo['precio'], insumo['subtotal']))
    lineas.append('Margen %.0f%%: $%.2f' % (
        desglose.get('margen_pct', 0.0), desglose.get('margen', 0.0)))
    lineas.append('Total sugerido: $%.2f' % desglose.get('total', 0.0))
    for aviso in desglose.get('advertencias', []):
        lineas.append('Aviso: %s' % aviso)
    return '\n'.join(lineas)
