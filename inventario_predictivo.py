# -*- coding: utf-8 -*-
"""
ASPLOT CENTER - Inventario predictivo (Sprint 6, PB-11)

Módulo Python puro (sin Flask) para calcular velocidad de consumo, dias
hasta agotarse, punto de reorden y compra sugerida, ademas de gestionar el
silencio de alertas en un JSON pequeno (sin tocar el esquema de la base).

Fuente de consumo: lineas de DetalleFactura dentro de la ventana configurable.
"""

from __future__ import annotations

import json
import math
import os
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

DIAS_PRELIMINAR = 14  # menos de esto se marca como estimacion preliminar


def _decimal(valor):
    if valor is None:
        return Decimal('0')
    return Decimal(str(valor))


def _redondear(valor, decimales=2):
    cuantia = Decimal('1.' + '0' * decimales) if decimales > 0 else Decimal('1')
    return float(_decimal(valor).quantize(cuantia, rounding=ROUND_HALF_UP))


def _fecha(valor):
    if isinstance(valor, datetime):
        return valor.date()
    return valor


def calcular_predicciones(materiales, consumos, proyectos_activos, params, hoy=None):
    """
    materiales: [{id, nombre, stock, stock_minimo, unidad, precio_compra}]
    consumos:   {id_material: {'total': float, 'primera': date, 'ultima': date}}
    params:     ventana_dias, dias_reposicion, dias_seguridad, dias_compra,
                factor_activo, tope_activo
    """
    hoy = _fecha(hoy) or date.today()
    ventana = int(params.get('ventana_dias', 90))
    reposicion = float(params.get('dias_reposicion', 7))
    seguridad = float(params.get('dias_seguridad', 7))
    dias_compra = float(params.get('dias_compra', 30))
    factor_activo = float(params.get('factor_activo', 0.10))
    tope_activo = float(params.get('tope_activo', 0.50))

    try:
        activos = max(0, int(proyectos_activos or 0))
    except (TypeError, ValueError):
        activos = 0
    ajuste = 1 + min(tope_activo, factor_activo * activos)

    predicciones = []
    for material in materiales:
        id_material = material.get('id')
        stock = float(material.get('stock') or 0)
        minimo = float(material.get('stock_minimo') or 0)
        avisos = []

        consumo = consumos.get(id_material)
        if consumo and float(consumo.get('total') or 0) > 0:
            total = float(consumo['total'])
            primera = _fecha(consumo.get('primera')) or hoy
            dias_base = max(1, min(ventana, (hoy - primera).days + 1))
            velocidad = total / dias_base
            if dias_base < DIAS_PRELIMINAR:
                avisos.append(
                    'Estimación preliminar: solo %d día(s) de histórico' % dias_base)
            con_historial = True
        else:
            velocidad = 0.0
            dias_base = 0
            con_historial = False
            avisos.append('Sin facturas en los últimos %d días' % ventana)

        velocidad_ajustada = velocidad * ajuste
        punto_reorden = velocidad_ajustada * (reposicion + seguridad)
        if velocidad_ajustada > 0:
            dias_restantes = stock / velocidad_ajustada
        else:
            dias_restantes = None

        faltante = velocidad_ajustada * dias_compra - stock
        compra_sugerida = max(0, int(math.ceil(faltante))) if faltante > 0 else 0

        if not con_historial:
            estado = 'sin_historial'
        elif stock <= punto_reorden or stock <= minimo:
            estado = 'riesgo'
        else:
            estado = 'ok'

        predicciones.append({
            'id_material': id_material,
            'nombre': material.get('nombre') or ('Material %s' % id_material),
            'unidad': material.get('unidad') or 'unidad',
            'stock': _redondear(stock, 2),
            'stock_minimo': _redondear(minimo, 2),
            'velocidad': _redondear(velocidad, 3),
            'velocidad_ajustada': _redondear(velocidad_ajustada, 3),
            'dias_base': dias_base,
            'dias_restantes': None if dias_restantes is None else _redondear(dias_restantes, 1),
            'punto_reorden': _redondear(punto_reorden, 2),
            'compra_sugerida': compra_sugerida,
            'ajuste': _redondear(ajuste, 2),
            'estado': estado,
            'avisos': avisos,
        })

    orden = {'riesgo': 0, 'sin_historial': 1, 'ok': 2, 'silenciada': 3}
    predicciones.sort(key=lambda p: (orden.get(p['estado'], 9), p['nombre'].lower()))
    return predicciones


def aplicar_silencios(predicciones, silencios):
    """Marca como 'silenciada' las predicciones con silencio vigente."""
    for prediccion in predicciones:
        if prediccion['id_material'] in silencios:
            prediccion['estado'] = 'silenciada'
            prediccion['silencio_hasta'] = silencios[prediccion['id_material']].isoformat()
    orden = {'riesgo': 0, 'sin_historial': 1, 'ok': 2, 'silenciada': 3}
    predicciones.sort(key=lambda p: (orden.get(p['estado'], 9), p['nombre'].lower()))
    return predicciones


def leer_silencios(ruta, hoy=None):
    """Devuelve {id_material: date_hasta} descartando vencidos o corruptos."""
    hoy = _fecha(hoy) or date.today()
    try:
        with open(ruta, 'r', encoding='utf-8') as archivo:
            datos = json.load(archivo)
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(datos, dict):
        return {}
    limpios = {}
    for clave, valor in datos.items():
        try:
            hasta = date.fromisoformat(str(valor))
            id_material = int(clave)
        except (ValueError, TypeError):
            continue
        if hasta >= hoy:
            limpios[id_material] = hasta
    return limpios


def guardar_silencios(ruta, datos):
    """Escritura atomica (temporal + os.replace). Devuelve True si pudo."""
    try:
        carpeta = os.path.dirname(ruta)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        serializable = {}
        for clave, valor in (datos or {}).items():
            if hasattr(valor, 'isoformat'):
                serializable[str(clave)] = valor.isoformat()
            else:
                serializable[str(clave)] = str(valor)
        temporal = ruta + '.tmp'
        with open(temporal, 'w', encoding='utf-8') as archivo:
            json.dump(serializable, archivo, ensure_ascii=False, indent=2)
        os.replace(temporal, ruta)
        return True
    except OSError:
        return False
