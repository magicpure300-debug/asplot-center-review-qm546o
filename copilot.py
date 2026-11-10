# -*- coding: utf-8 -*-
"""
ASPLOT CENTER - Sprint 7 (PB-12): Copilot administrativo NL -> SQL.

Agente conversacional para la directiva: traduce preguntas en lenguaje
natural a consultas SQL de SOLO LECTURA sobre la base de datos.

Diseno (Python puro, sin dependencias nuevas):

- 8 plantillas deterministas que funcionan SIEMPRE (sin API, sin internet).
- Cliente HTTP opcional para cualquier API compatible con OpenAI
  (`POST {COPILOT_BASE_URL}/chat/completions`) usando urllib.
- Validador de SQL en dos capas: sintaxis permitida (SELECT/WITH, sin
  escritura, sin comentarios, sentencia unica) + catalogo cerrado de tablas.
- Toda consulta queda envuelta con LIMIT para acotar el resultado.

El modulo no depende de Flask: la ejecucion real se inyecta desde la
aplicacion (`ejecutar`), lo que permite probarlo aislado.
"""

import json
import re
import unicodedata
import urllib.request
import urllib.error
from datetime import datetime, date

# =============================================================================
# Catalogo de tablas permitidas (la tabla `usuarios` queda FUERA a proposito:
# contiene hashes de contrasenas y no debe exponerse en consultas generadas).
# =============================================================================

TABLAS_PERMITIDAS = {
    'clientes', 'proyectos', 'tipos_plano', 'planos', 'materiales',
    'inventario', 'facturas', 'detalle_facturas',
}

# Descripcion del esquema que se envia al LLM (nunca datos de clientes).
ESQUEMA_PARA_LLM = """Tablas disponibles (solo lectura):
- clientes(id_cliente, nombre, apellido, email, telefono, direccion, id_usuario)
- proyectos(id_proyecto, id_cliente, nombre_proyecto, descripcion, tipo_servicio, archivo_solicitud, fecha_solicitud, fecha_inicio, fecha_fin, presupuesto, estado, notas)
  estados validos: solicitado, cotizado, aprobado, en_progreso, ejecutado, rechazado
  tipos de servicio: render, topografia, plano, correccion
- tipos_plano(id_tipo_plano, nombre_tipo, descripcion)
- planos(id_plano, id_proyecto, id_tipo_plano, id_usuario, nombre_plano, archivo, fecha_subida)
- materiales(id_material, nombre_material, descripcion, categoria, subcategoria, precio_unitario, precio_compra, unidad_medida, stock_minimo, activo)
- inventario(id_inventario, id_material, cantidad, fecha_actualizacion, ubicacion)
- facturas(id_factura, id_proyecto, id_cliente, id_usuario, fecha_factura, fecha_vencimiento, subtotal, impuesto, descuento, total, estado_pago, metodo_pago, referencia_pago, fecha_pago, notas)
  estados de pago: pendiente, pagada, vencida, cancelada
- detalle_facturas(id_detalle_factura, id_factura, id_plano, id_material, descripcion, cantidad, precio_unitario, descuento)"""

# Verbos y comandos prohibidos (se comprueban como palabras completas).
VERBOS_PROHIBIDOS = (
    'insert', 'update', 'delete', 'drop', 'alter', 'create', 'truncate',
    'grant', 'revoke', 'attach', 'detach', 'pragma', 'replace', 'merge',
    'call', 'execute', 'exec', 'vacuum', 'lock', 'load_file', 'outfile',
)

# Marcadores de comentario (MySQL/SQLite/estandar).
PATRONES_COMENTARIO = ('--', '/*', '*/', '#')


# =============================================================================
# Utilidades de texto
# =============================================================================

def _quitar_acentos(texto):
    """Normaliza el texto a ASCII sin acentos y en minusculas."""
    if not texto:
        return ''
    normalizado = unicodedata.normalize('NFD', texto)
    solo_ascii = ''.join(
        c for c in normalizado if unicodedata.category(c) != 'Mn')
    return solo_ascii.lower().strip()


def _inicio_de_mes(hoy=None):
    """Primer dia del mes actual como datetime (compatible SQLite/MySQL)."""
    hoy = hoy or date.today()
    return datetime(hoy.year, hoy.month, 1)


# =============================================================================
# Plantillas deterministas (8)
# =============================================================================

def _consulta_facturacion_mes(hoy=None):
    inicio = _inicio_de_mes(hoy)
    sql = ("SELECT COUNT(*) AS cantidad_facturas, "
           "COALESCE(SUM(total), 0) AS total_facturado "
           "FROM facturas "
           "WHERE fecha_factura >= :inicio AND estado_pago <> 'cancelada'")
    return sql, {'inicio': inicio}


def _consulta_top_clientes(hoy=None):
    sql = ("SELECT c.nombre AS nombre, c.apellido AS apellido, "
           "COUNT(f.id_factura) AS cantidad_facturas, "
           "COALESCE(SUM(f.total), 0) AS total_facturado "
           "FROM clientes c "
           "JOIN facturas f ON f.id_cliente = c.id_cliente "
           "WHERE f.estado_pago <> 'cancelada' "
           "GROUP BY c.id_cliente, c.nombre, c.apellido "
           "ORDER BY total_facturado DESC")
    return sql, {}


def _consulta_proyectos_estado(hoy=None):
    sql = ("SELECT estado, COUNT(*) AS cantidad "
           "FROM proyectos "
           "GROUP BY estado "
           "ORDER BY cantidad DESC")
    return sql, {}


def _consulta_margen_proyecto(hoy=None):
    sql = ("SELECT pr.nombre_proyecto AS proyecto, "
           "fs.total_facturado AS facturado, "
           "COALESCE(cs.costo_insumos, 0) AS costo_insumos, "
           "fs.total_facturado - COALESCE(cs.costo_insumos, 0) AS margen "
           "FROM proyectos pr "
           "JOIN (SELECT id_proyecto, SUM(total) AS total_facturado "
           "      FROM facturas WHERE estado_pago <> 'cancelada' "
           "      GROUP BY id_proyecto) fs ON fs.id_proyecto = pr.id_proyecto "
           "LEFT JOIN (SELECT f2.id_proyecto, "
           "      SUM(df.cantidad * m.precio_compra) AS costo_insumos "
           "      FROM detalle_facturas df "
           "      JOIN facturas f2 ON f2.id_factura = df.id_factura "
           "      JOIN materiales m ON m.id_material = df.id_material "
           "      WHERE df.id_material IS NOT NULL "
           "      GROUP BY f2.id_proyecto) cs "
           "      ON cs.id_proyecto = pr.id_proyecto "
           "ORDER BY margen DESC")
    return sql, {}


def _consulta_consumo_insumos(hoy=None):
    inicio = _inicio_de_mes(hoy)
    sql = ("SELECT m.nombre_material AS material, m.unidad_medida, "
           "SUM(df.cantidad) AS cantidad_consumida "
           "FROM detalle_facturas df "
           "JOIN facturas f ON f.id_factura = df.id_factura "
           "JOIN materiales m ON m.id_material = df.id_material "
           "WHERE df.id_material IS NOT NULL AND f.fecha_factura >= :inicio "
           "GROUP BY m.id_material, m.nombre_material, m.unidad_medida "
           "ORDER BY cantidad_consumida DESC")
    return sql, {'inicio': inicio}


def _consulta_solicitudes_pendientes(hoy=None):
    sql = ("SELECT c.nombre AS nombre_cliente, c.apellido AS apellido_cliente, "
           "p.nombre_proyecto AS proyecto, p.tipo_servicio, p.fecha_solicitud "
           "FROM proyectos p "
           "JOIN clientes c ON c.id_cliente = p.id_cliente "
           "WHERE p.estado = 'solicitado' "
           "ORDER BY p.fecha_solicitud")
    return sql, {}


def _consulta_inventario_riesgo(hoy=None):
    sql = ("SELECT m.nombre_material AS material, i.cantidad AS stock_actual, "
           "m.stock_minimo, "
           "m.stock_minimo - i.cantidad AS faltante, m.unidad_medida "
           "FROM inventario i "
           "JOIN materiales m ON m.id_material = i.id_material "
           "WHERE i.cantidad <= m.stock_minimo "
           "ORDER BY faltante DESC")
    return sql, {}


def _consulta_planos_tipo(hoy=None):
    sql = ("SELECT tp.nombre_tipo AS tipo_plano, COUNT(p.id_plano) AS total "
           "FROM planos p "
           "JOIN tipos_plano tp ON tp.id_tipo_plano = p.id_tipo_plano "
           "GROUP BY tp.nombre_tipo "
           "ORDER BY total DESC")
    return sql, {}


PLANTILLAS = [
    {
        'id': 'facturacion_mes',
        'etiqueta': 'Facturación del mes',
        'ejemplo': '¿Cuánto se ha facturado este mes?',
        'palabras': ('facturacion', 'facturado', 'factura', 'facturas',
                     'mes', 'ingresos', 'cobrado', 'ventas'),
        'interpretacion': 'Total facturado en el mes en curso '
                          '(excluye facturas canceladas).',
        'consulta': _consulta_facturacion_mes,
    },
    {
        'id': 'top_clientes',
        'etiqueta': 'Top clientes',
        'ejemplo': '¿Quiénes son los clientes que más han facturado?',
        'palabras': ('quienes', 'quien', 'cliente', 'clientes', 'top',
                     'mayor', 'mejores', 'gasto'),
        'interpretacion': 'Clientes ordenados por total facturado '
                          '(excluye facturas canceladas).',
        'consulta': _consulta_top_clientes,
    },
    {
        'id': 'proyectos_estado',
        'etiqueta': 'Proyectos por estado',
        'ejemplo': '¿Cómo están los proyectos por estado?',
        'palabras': ('proyecto', 'proyectos', 'estado', 'estados',
                     'cuantos proyectos', 'avance'),
        'interpretacion': 'Cantidad de proyectos agrupados por su estado '
                          'actual (solicitado, cotizado, aprobado, '
                          'en progreso, ejecutado, rechazado).',
        'consulta': _consulta_proyectos_estado,
    },
    {
        'id': 'margen_proyecto',
        'etiqueta': 'Margen por proyecto',
        'ejemplo': '¿Cuál es el margen de ganancia de cada proyecto?',
        'palabras': ('margen', 'ganancia', 'beneficio', 'utilidad',
                     'rentabilidad', 'costo', 'costos', 'insumos por proyecto'),
        'interpretacion': 'Facturado vs costo de insumos consumidos por '
                          'proyecto (facturas no canceladas; el costo usa el '
                          'precio de compra de cada material).',
        'consulta': _consulta_margen_proyecto,
    },
    {
        'id': 'consumo_insumos',
        'etiqueta': 'Consumo de insumos',
        'ejemplo': '¿Qué insumos se han consumido este mes?',
        'palabras': ('consumo', 'consumido', 'insumo', 'insumos', 'material',
                     'materiales', 'papel', 'tinta', 'usado'),
        'interpretacion': 'Insumos consumidos en el mes en curso según el '
                          'detalle de las facturas emitidas.',
        'consulta': _consulta_consumo_insumos,
    },
    {
        'id': 'solicitudes_pendientes',
        'etiqueta': 'Solicitudes pendientes',
        'ejemplo': '¿Qué solicitudes están pendientes por atender?',
        'palabras': ('solicitud', 'solicitudes', 'pendiente', 'pendientes',
                     'por atender', 'nuevas', 'sin revisar', 'esperando'),
        'interpretacion': 'Proyectos en estado «solicitado» (pendientes de '
                          'cotización), del más antiguo al más reciente.',
        'consulta': _consulta_solicitudes_pendientes,
    },
    {
        'id': 'inventario_riesgo',
        'etiqueta': 'Inventario en riesgo',
        'ejemplo': '¿Qué materiales están por debajo del mínimo?',
        'palabras': ('inventario', 'riesgo', 'stock', 'minimo', 'minimos',
                     'bajo', 'debajo', 'por debajo', 'faltante',
                     'reposicion', 'reorden', 'materiales bajo'),
        'interpretacion': 'Materiales con stock igual o por debajo del '
                          'mínimo definido, ordenados por faltante.',
        'consulta': _consulta_inventario_riesgo,
    },
    {
        'id': 'planos_tipo',
        'etiqueta': 'Planos por tipo',
        'ejemplo': '¿Cuántos planos hay de cada tipo?',
        'palabras': ('plano', 'planos', 'tipo', 'tipos', 'categorias',
                     'cuantos planos'),
        'interpretacion': 'Cantidad de planos subidos agrupados por tipo '
                          'de plano.',
        'consulta': _consulta_planos_tipo,
    },
]


def resolver_plantilla(texto):
    """
    Busca la plantilla cuya puntuacion de palabras clave sea la mayor.

    Devuelve el diccionario de la plantilla o None si ninguna coincide.
    1) Coincidencia exacta con una pregunta frecuente (los chips la usan).
    2) Puntuacion: cantidad de palabras clave presentes en el texto, con
       bonus por las frases de varias palabras y por empezar la pregunta.
    """
    normalizado = _quitar_acentos(texto)
    if not normalizado:
        return None

    # 1) Coincidencia exacta con el ejemplo de una plantilla
    for plantilla in PLANTILLAS:
        if _quitar_acentos(plantilla['ejemplo']) == normalizado:
            return plantilla

    # 2) Puntuacion por palabras clave
    mejor = None
    mejor_puntaje = 0
    for plantilla in PLANTILLAS:
        puntaje = 0
        for palabra in plantilla['palabras']:
            if ' ' in palabra:
                if palabra in normalizado:
                    puntaje += 2
            elif re.search(r'\b' + re.escape(palabra) + r'\b', normalizado):
                puntaje += 1
                if normalizado.startswith(palabra):
                    puntaje += 1
        if puntaje > mejor_puntaje:
            mejor = plantilla
            mejor_puntaje = puntaje

    return mejor if mejor_puntaje > 0 else None


# =============================================================================
# Validador de SQL (segunda capa de seguridad)
# =============================================================================

def validar_sql(sql, max_filas=200):
    """
    Valida un SELECT generado (por plantilla o por el LLM).

    Devuelve (ok, sql_envuelto, error):
    - ok: True si el SQL es un SELECT unico, sin escritura ni comentarios y
      solo usa tablas del catalogo.
    - sql_envuelto: la consulta envuelta con LIMIT para acotar el resultado.
    - error: mensaje de rechazo cuando ok es False.
    """
    if not sql or not sql.strip():
        return False, None, 'La consulta esta vacia.'

    limpio = sql.strip()

    # Sentencia unica: se tolera un punto y coma final, nada mas.
    sin_final = limpio.rstrip(';').strip()
    if ';' in sin_final:
        return False, None, 'Solo se permite una sentencia por consulta.'

    # Comentarios: rechazados en cualquier posicion.
    for patron in PATRONES_COMENTARIO:
        if patron in limpio:
            return False, None, (
                'La consulta no puede incluir comentarios (%s).' % patron)

    # Debe comenzar por SELECT o WITH.
    if not re.match(r'^(select|with)\b', sin_final, re.IGNORECASE):
        return False, None, (
            'Solo se permiten consultas SELECT (o WITH).')

    # Verbos prohibidos como palabras completas.
    for verbo in VERBOS_PROHIBIDOS:
        if re.search(r'\b' + verbo + r'\b', sin_final, re.IGNORECASE):
            return False, None, (
                'La consulta incluye el verbo no permitido «%s». '
                'El copilot es de solo lectura.' % verbo.upper())

    # Catalogo de tablas: se extraen los nombres tras FROM/JOIN.
    tablas = re.findall(
        r'\b(?:from|join)\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?',
        sin_final, re.IGNORECASE)
    # Los CTE definidos con WITH son alias locales, no tablas reales.
    ctes = re.findall(r'\b(?:with|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+as\b',
                       sin_final, re.IGNORECASE)
    permitidas = TABLAS_PERMITIDAS | set(c.lower() for c in ctes)
    for tabla in tablas:
        if tabla.lower() not in permitidas:
            return False, None, (
                'La tabla «%s» no esta en el catalogo permitido del copilot.'
                % tabla)

    sql_envuelto = ('SELECT * FROM (%s) AS copilot_resultado LIMIT %d'
                    % (sin_final, max_filas))
    return True, sql_envuelto, None


# =============================================================================
# Cliente LLM (API compatible con OpenAI)
# =============================================================================

class CopilotError(Exception):
    """Error controlado del copilot (red, formato o SQL rechazado)."""


class CopilotNoConfigurado(Exception):
    """No hay API key configurada: se debe usar el modo plantillas."""


def _prompt_sistema():
    return (
        'Eres un analista de datos de ASPLOT CENTER, una empresa de '
        'impresion de planos. Conviertes preguntas de la directiva en '
        'consultas SQL.\n'
        'REGLAS OBLIGATORIAS:\n'
        '1. SOLO consultas SELECT de lectura. Nunca INSERT, UPDATE, DELETE, '
        'DROP, ALTER ni PRAGMA.\n'
        '2. Solo puedes usar las tablas del esquema permitido. La tabla '
        'usuarios esta PROHIBIDA.\n'
        '3. SQL estandar compatible con MySQL 8 y SQLite: no uses funciones '
        'exclusivas de un motor (evita STRFTIME, DATE_TRUNC, etc.).\n'
        '4. Devuelve SIEMPRE un JSON valido con exactamente dos claves:\n'
        '   {"interpretacion": "<que entendiste, en espanol, 1-2 frases>", '
        '"sql": "<SELECT ...>"}\n'
        '5. No incluyas markdown ni bloques de codigo, solo el JSON.\n'
        '6. Limita el resultado a 100 filas con LIMIT.\n\n'
        'ESQUEMA PERMITIDO:\n' + ESQUEMA_PARA_LLM)


def _extraer_json(texto_llm):
    """Extrae el objeto JSON de la respuesta del modelo (tolera fences)."""
    if not texto_llm:
        raise CopilotError('El modelo no devolvio contenido.')
    limpio = texto_llm.strip()
    limpio = re.sub(r'^```(?:json)?\s*', '', limpio)
    limpio = re.sub(r'\s*```$', '', limpio)
    try:
        datos = json.loads(limpio)
    except (ValueError, TypeError):
        # Tolerancia: buscar el objeto entre llaves.
        coincidencia = re.search(r'\{.*\}', limpio, re.DOTALL)
        if not coincidencia:
            raise CopilotError('Respuesta del modelo sin JSON valido.')
        try:
            datos = json.loads(coincidencia.group(0))
        except (ValueError, TypeError):
            raise CopilotError('Respuesta del modelo sin JSON valido.')

    if not isinstance(datos, dict):
        raise CopilotError('Respuesta del modelo sin JSON valido.')
    sql = datos.get('sql') or ''
    interpretacion = datos.get('interpretacion') or ''
    if not sql.strip():
        raise CopilotError('El modelo no devolvio una consulta SQL.')
    return {'interpretacion': interpretacion.strip(),
            'sql': sql.strip()}


def llamar_llm(pregunta, config):
    """
    Llama a una API compatible con OpenAI y devuelve el dict del modelo.

    Usa urllib (stdlib), timeout configurable y temperature 0 para
    respuestas deterministas. Lanza CopilotNoConfigurado si no hay API key
    y CopilotError ante cualquier fallo (red, formato, HTTP).
    """
    api_key = config.get('COPILOT_API_KEY')
    if not api_key:
        raise CopilotNoConfigurado(
            'No hay COPILOT_API_KEY configurada; se usa el modo plantillas.')

    base_url = (config.get('COPILOT_BASE_URL')
                or 'https://api.openai.com/v1').rstrip('/')
    modelo = config.get('COPILOT_MODEL') or 'gpt-4o-mini'
    timeout = config.get('COPILOT_TIMEOUT') or 15

    cuerpo = {
        'model': modelo,
        'temperature': 0,
        'messages': [
            {'role': 'system', 'content': _prompt_sistema()},
            {'role': 'user', 'content': pregunta},
        ],
    }
    peticion = urllib.request.Request(
        base_url + '/chat/completions',
        data=json.dumps(cuerpo).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + api_key,
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            datos = json.loads(respuesta.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        detalle = ''
        try:
            detalle = error.read().decode('utf-8', 'replace')[:200]
        except Exception:
            pass
        raise CopilotError('La API del copilot respondio %d. %s'
                           % (error.code, detalle))
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise CopilotError('No se pudo contactar la API del copilot: %s'
                           % error)

    try:
        contenido = datos['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        raise CopilotError('La respuesta del modelo no tiene el formato '
                           'esperado.')
    return _extraer_json(contenido)


# =============================================================================
# Orquestador con fallback
# =============================================================================

def responder(pregunta, ejecutar, config, hoy=None):
    """
    Responde una pregunta en lenguaje natural.

    - Con COPILOT_API_KEY: pregunta al LLM, valida su SQL y lo ejecuta.
      Si el LLM falla o su SQL es rechazado, cae a la plantilla mas cercana
      dejando un aviso (nunca error 500).
    - Sin API key: usa las plantillas deterministas.

    `ejecutar(sql, params)` -> (columnas, filas) es inyectado por la
    aplicacion. Devuelve un dict listo para renderizar.
    """
    max_filas = config.get('COPILOT_MAX_FILAS') or 200
    resultado = {
        'pregunta': pregunta,
        'ok': False,
        'fuente': None,          # 'ia' | 'plantilla' | None
        'interpretacion': '',
        'sql': '',
        'columnas': [],
        'filas': [],
        'aviso': '',
        'mensaje': '',
        'sugerencias': [p['etiqueta'] for p in PLANTILLAS],
    }

    if not pregunta or not pregunta.strip():
        resultado['mensaje'] = ('Escribe una pregunta o elige una de las '
                                'sugerencias.')
        return resultado

    # ---- Intento 1: LLM (solo si hay API key) --------------------------
    aviso_ia = ''
    resultado_ia = None
    if config.get('COPILOT_API_KEY'):
        try:
            propuesta = llamar_llm(pregunta, config)
            ok, sql_envuelto, error = validar_sql(propuesta['sql'], max_filas)
            if not ok:
                aviso_ia = ('La consulta propuesta por la IA fue rechazada '
                            'por el validador (%s). ' % error)
            else:
                try:
                    columnas, filas = ejecutar(sql_envuelto, {})
                    resultado_ia = {
                        'fuente': 'ia',
                        'interpretacion': propuesta['interpretacion'],
                        'sql': propuesta['sql'],
                        'columnas': columnas,
                        'filas': filas,
                    }
                except Exception as error:
                    aviso_ia = ('La consulta de la IA no pudo ejecutarse '
                                '(%s). ' % error)
        except CopilotError as error:
            aviso_ia = 'La IA no pudo responder (%s). ' % error

    if resultado_ia is not None:
        resultado.update(resultado_ia)
        resultado['ok'] = True
        return resultado

    # ---- Intento 2: plantilla determinista ------------------------------
    plantilla = resolver_plantilla(pregunta)
    if plantilla is None:
        resultado['aviso'] = aviso_ia
        resultado['mensaje'] = (
            'No reconozco esa pregunta. Prueba con una de las preguntas '
            'frecuentes o reformula usando palabras como «facturación», '
            '«clientes», «proyectos», «insumos» o «inventario».')
        return resultado

    sql, params = plantilla['consulta'](hoy)
    ok, sql_envuelto, error = validar_sql(sql, max_filas)
    if not ok:
        # No deberia ocurrir: las plantillas estan pre-validadas.
        resultado['aviso'] = aviso_ia
        resultado['mensaje'] = ('Error interno validando la plantilla: %s'
                                % error)
        return resultado

    try:
        columnas, filas = ejecutar(sql_envuelto, params)
    except Exception as error:
        resultado['aviso'] = aviso_ia
        resultado['mensaje'] = ('No se pudo ejecutar la consulta: %s' % error)
        return resultado
    resultado.update({
        'ok': True,
        'fuente': 'plantilla',
        'interpretacion': plantilla['interpretacion'],
        'sql': sql,
        'columnas': columnas,
        'filas': filas,
        'aviso': aviso_ia,
    })
    return resultado
