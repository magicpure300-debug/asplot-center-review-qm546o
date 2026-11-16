# -*- coding: utf-8 -*-
"""
ASPLOT CENTER - Sprint 8: validacion de telefonos de Venezuela.

Reglas del plan de numeracion (CONATEL, plan cerrado de 11 digitos):

- Movil: 04XX + 7 digitos. Prefijos vigentes:
    0412 / 0422  Digitel
    0414 / 0424  Movistar
    0415         Tesan
    0416 / 0426  Movilnet
  Los prefijos 0417 y 0418 fueron eliminados en 2006: se rechazan.
- Fijo: 02XX + 7 digitos, con codigo de area existente (0212, 0241,
  0291, ...). Un 02XX inventado se rechaza.

Se acepta el numero escrito con espacios, guiones, puntos o parentesis y
con prefijo internacional +58 / 0058 / 58. La forma canonica que se guarda
en la base es siempre la local de 11 digitos: 04141917498.
"""

import re

# =============================================================================
# Catalogos
# =============================================================================

PREFIJOS_MOVIL = {
    '0412': 'Digitel',
    '0422': 'Digitel',
    '0414': 'Movistar',
    '0424': 'Movistar',
    '0415': 'Tesan',
    '0416': 'Movilnet',
    '0426': 'Movilnet',
}

# Codigo de area -> estado(s). Fuente: plan de numeracion de Venezuela.
CODIGOS_AREA = {
    '212': 'Distrito Capital / Miranda / Vargas',
    '234': 'Miranda',
    '235': 'Anzoategui / Bolivar / Guarico',
    '237': 'Dependencias Federales',
    '238': 'Guarico',
    '239': 'Miranda',
    '241': 'Carabobo',
    '242': 'Carabobo',
    '243': 'Aragua / Carabobo',
    '244': 'Aragua',
    '245': 'Aragua / Carabobo',
    '246': 'Aragua / Guarico',
    '247': 'Apure / Guarico',
    '248': 'Amazonas',
    '249': 'Carabobo',
    '251': 'Lara / Yaracuy',
    '252': 'Lara',
    '253': 'Lara / Yaracuy',
    '254': 'Yaracuy',
    '255': 'Portuguesa',
    '256': 'Portuguesa',
    '257': 'Portuguesa',
    '258': 'Cojedes',
    '259': 'Falcon',
    '260': 'Zulia (frontera con Colombia)',
    '261': 'Zulia',
    '262': 'Zulia',
    '263': 'Zulia',
    '264': 'Zulia',
    '265': 'Zulia',
    '266': 'Zulia',
    '267': 'Zulia',
    '268': 'Falcon',
    '269': 'Falcon',
    '270': 'Zulia (frontera con Colombia)',
    '271': 'Merida / Trujillo / Zulia',
    '272': 'Trujillo',
    '273': 'Barinas / Merida',
    '274': 'Merida',
    '275': 'Merida / Zulia',
    '276': 'Tachira',
    '277': 'Tachira',
    '278': 'Apure / Barinas',
    '281': 'Anzoategui',
    '282': 'Anzoategui',
    '283': 'Anzoategui',
    '285': 'Bolivar',
    '286': 'Bolivar',
    '287': 'Delta Amacuro / Monagas',
    '288': 'Bolivar',
    '291': 'Monagas',
    '292': 'Monagas',
    '293': 'Sucre',
    '294': 'Sucre',
    '295': 'Nueva Esparta',
}

CARACTERES_IGNORADOS = re.compile(r'[\s\-\.\(\)\/]')


# =============================================================================
# API publica
# =============================================================================

def normalizar_telefono(valor):
    """
    Valida y normaliza un telefono venezolano.

    Devuelve un diccionario:
        {
          'ok': bool,
          'valor': '04141917498' | '',
          'tipo': 'movil' | 'fijo' | None,
          'operadora': 'Movilnet' | None,
          'estado': 'Monagas' | None,
          'area': '0291' | None,
          'error': mensaje | None,
        }
    """
    resultado = {
        'ok': False, 'valor': '', 'tipo': None, 'operadora': None,
        'estado': None, 'area': None, 'error': None,
    }
    original = '' if valor is None else str(valor)
    limpio = CARACTERES_IGNORADOS.sub('', original.strip())

    if not limpio:
        resultado['error'] = 'El teléfono es obligatorio.'
        return resultado

    # Prefijo internacional: +58, 0058 o 58 (solo si quedan 10 digitos).
    if limpio.startswith('+'):
        limpio = limpio[1:]
    if limpio.startswith('0058'):
        limpio = limpio[4:]
    elif limpio.startswith('58') and len(limpio) == 12:
        limpio = limpio[2:]

    if not limpio.isdigit():
        resultado['error'] = ('El teléfono solo puede contener números '
                              '(se permiten espacios, guiones y paréntesis).')
        return resultado

    # Numero local sin el 0 inicial (formato internacional habitual).
    if len(limpio) == 10 and limpio[:1] in ('2', '4'):
        limpio = '0' + limpio

    if len(limpio) != 11:
        resultado['error'] = (
            'El teléfono debe tener 11 dígitos (ej. 04141917498). '
            'Se recibieron %d.' % len(limpio))
        return resultado

    if len(set(limpio)) == 1:
        resultado['error'] = ('El teléfono no puede tener todos los dígitos '
                              'iguales.')
        return resultado

    prefijo = limpio[:4]
    if prefijo in PREFIJOS_MOVIL:
        resultado.update({
            'ok': True, 'valor': limpio, 'tipo': 'movil',
            'operadora': PREFIJOS_MOVIL[prefijo],
        })
        return resultado

    if limpio[:2] == '02':
        clave = limpio[1:4]
        if clave in CODIGOS_AREA:
            resultado.update({
                'ok': True, 'valor': limpio, 'tipo': 'fijo',
                'area': '0' + clave, 'estado': CODIGOS_AREA[clave],
            })
            return resultado
        resultado['error'] = (
            'El código de área 0%s no existe en Venezuela '
            '(ej. 0212 Caracas, 0291 Monagas).' % clave)
        return resultado

    resultado['error'] = (
        'El prefijo %s no corresponde a una línea móvil '
        '(0412, 0414, 0415, 0416, 0422, 0424, 0426) ni a un fijo (02XX).'
        % prefijo)
    return resultado


def validar_telefono(valor, obligatorio=True):
    """
    Version corta para las rutas.

    Devuelve (ok, valor_normalizado, error). Si el campo es opcional y
    viene vacio, devuelve (True, '', None).
    """
    if not obligatorio and not (valor or '').strip():
        return True, '', None
    datos = normalizar_telefono(valor)
    return datos['ok'], datos['valor'], datos['error']


def formatear_telefono(valor):
    """Devuelve el telefono en formato legible: 0414-1917498."""
    datos = normalizar_telefono(valor)
    if not datos['ok']:
        return valor or ''
    return '%s-%s' % (datos['valor'][:4], datos['valor'][4:])


def describir_telefono(valor):
    """Describe la linea: 'Movil Movilnet' o 'Fijo - Monagas (0291)'."""
    datos = normalizar_telefono(valor)
    if not datos['ok']:
        return ''
    if datos['tipo'] == 'movil':
        return 'Móvil %s' % datos['operadora']
    return 'Fijo — %s (%s)' % (datos['estado'], datos['area'])
