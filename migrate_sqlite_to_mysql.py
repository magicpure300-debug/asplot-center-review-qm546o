# -*- coding: utf-8 -*-
"""
=============================================================================
 ASPLOT CENTER - Sprint 1 (PB-01 / PB-02)
 Migración de base de datos: SQLite -> MySQL
 Patrón: Strangler Fig (migración incremental sin interrumpir el sistema)
=============================================================================
 Script principal de migración (Fase 1: exportación y transformación).

 Funcionalidades:
   1. Lee el esquema completo de SQLite mediante `sqlite_master`.
   2. Exporta todos los registros al archivo portable `datos_exportados.json`.
   3. Genera `create_mysql_schema.sql` con CREATE DATABASE, CREATE TABLE e
      INSERT compatibles con MySQL 8.0 (codificación utf8mb4).
   4. Convierte los tipos de datos SQLite -> MySQL:
        INTEGER   -> INT
        NUMERIC   -> DECIMAL(p, s)
        BOOLEAN   -> TINYINT(1)
        VARCHAR   -> VARCHAR(n)      (se conserva la longitud)
        TEXT      -> TEXT
        DATETIME  -> DATETIME
        DATE      -> DATE
   5. Preserva PRIMARY KEY, UNIQUE y FOREIGN KEY (las 9 tablas del sistema).

 Uso:
   python migrate_sqlite_to_mysql.py                     # solo exporta/genera SQL
   python migrate_sqlite_to_mysql.py --importar           # exporta + importa a MySQL
   python migrate_sqlite_to_mysql.py --solo-sql           # genera el SQL sin exportar JSON
   python migrate_sqlite_to_mysql.py --sqlite otro.db     # otra BD de origen

 Variables de entorno para la conexión MySQL (usadas por --importar):
   MYSQL_HOST (localhost), MYSQL_PORT (3306), MYSQL_USER (root),
   MYSQL_PASSWORD (vacía), MYSQL_DATABASE (asplot_center)
=============================================================================
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime
from decimal import Decimal

# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------
DB_NAME_DEFAULT = 'asplot_center'
CARPETA_SALIDA_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migracion')

# Mapeo de tipos SQLite -> MySQL
MAPA_TIPOS = [
    (re.compile(r'^INTEGER$', re.I), 'INT'),
    (re.compile(r'^NUMERIC\((\d+)\s*,\s*(\d+)\)$', re.I), 'DECIMAL({}, {})'),
    (re.compile(r'^NUMERIC$', re.I), 'DECIMAL(10, 2)'),
    (re.compile(r'^BOOLEAN$', re.I), 'TINYINT(1)'),
    (re.compile(r'^VARCHAR\((\d+)\)$', re.I), 'VARCHAR({})'),
    (re.compile(r'^TEXT$', re.I), 'TEXT'),
    (re.compile(r'^DATETIME$', re.I), 'DATETIME(6)'),
    (re.compile(r'^DATE$', re.I), 'DATE'),
]

# Tablas cuyos nombres NO deben migrarse
TABLAS_EXCLUIDAS = {'sqlite_sequence', 'sqlite_stat1'}


# =============================================================================
# Utilidades de conversión de datos
# =============================================================================
def serializar(valor):
    """Convierte un valor de SQLite a un tipo serializable en JSON."""
    if isinstance(valor, (datetime, date)):
        return valor.isoformat(sep=' ') if isinstance(valor, datetime) else valor.isoformat()
    if isinstance(valor, bytes):
        return valor.hex()
    return valor


def literal_sql(valor):
    """Devuelve un valor Python como literal SQL válido para MySQL."""
    if valor is None:
        return 'NULL'
    if isinstance(valor, bool):
        return '1' if valor else '0'
    if isinstance(valor, (int, float, Decimal)):
        return str(valor)
    if isinstance(valor, (datetime, date)):
        texto = valor.isoformat(sep=' ') if isinstance(valor, datetime) else valor.isoformat()
        return "'" + texto + "'"
    # Cadenas de texto: escapar comillas simples y contra barras
    texto = str(valor).replace('\\', '\\\\').replace("'", "''")
    return "'" + texto + "'"


def convertir_tipo(tipo_sqlite):
    """Convierte una definición de tipo SQLite a su equivalente MySQL."""
    tipo = tipo_sqlite.strip()
    for patron, mysql in MAPA_TIPOS:
        m = patron.match(tipo)
        if m:
            return mysql.format(*m.groups()) if m.groups() else mysql
    # Tipo no reconocido: se conserva tal cual (MySQL lo resolverá)
    return tipo


# =============================================================================
# Fase 1 - Lectura del esquema y datos de SQLite
# =============================================================================
def leer_esquema(ruta_sqlite):
    """Obtiene el esquema (tablas y SQL de creación) de la BD SQLite."""
    conn = sqlite3.connect(ruta_sqlite)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    esquema = {}
    for fila in cur.fetchall():
        if fila['name'] in TABLAS_EXCLUIDAS:
            continue
        esquema[fila['name']] = fila['sql']
    conn.close()
    return esquema


def leer_datos(ruta_sqlite, tablas):
    """Exporta todos los registros de las tablas indicadas a un dict."""
    conn = sqlite3.connect(ruta_sqlite)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    datos = {}
    for tabla in tablas:
        cur.execute(f'SELECT * FROM "{tabla}"')
        columnas = [d[0] for d in cur.description]
        filas = []
        for fila in cur.fetchall():
            filas.append({col: serializar(fila[col]) for col in columnas})
        datos[tabla] = {'columnas': columnas, 'filas': filas}
    conn.close()
    return datos


def ordenar_por_dependencias(esquema):
    """
    Ordena las tablas respetando las claves foráneas (dependencias primero),
    para que los INSERT se ejecuten sin violar restricciones de integridad.
    """
    def refs(tabla):
        sql = esquema[tabla]
        return set(re.findall(r'REFERENCES\s+(\w+)', sql, re.I))

    pendientes = set(esquema)
    orden = []
    while pendientes:
        # Tablas cuyas dependencias ya fueron agregadas (o que no dependen de otras)
        listas = sorted(t for t in pendientes if not (refs(t) & pendientes))
        if not listas:
            # Ciclo detectado (no ocurre en este esquema): se agregan las restantes
            listas = sorted(pendientes)
        for t in listas:
            orden.append(t)
            pendientes.discard(t)
    return orden


def parsear_definicion(sql_sqlite):
    """
    Parsea el CREATE TABLE de SQLite y devuelve:
      columnas:  lista de dicts {nombre, tipo_sqlite, tipo_mysql, not_null, unique}
      pk:        lista de columnas que forman la clave primaria
      uniques:   lista de listas de columnas con restricción UNIQUE
      fks:       lista de dicts {columna, tabla_ref, columna_ref}
    """
    cuerpo = re.search(r'\((.*)\)\s*$', sql_sqlite, re.S).group(1)

    columnas, pk, uniques, fks = [], [], [], []
    for linea_bruta in cuerpo.split('\n'):
        linea = linea_bruta.strip().rstrip(',')
        if not linea:
            continue
        mayus = linea.upper()

        if mayus.startswith('PRIMARY KEY'):
            pk = re.findall(r'\(([^)]+)\)', linea)[0].replace('"', '').split(',')
            continue
        if mayus.startswith('UNIQUE'):
            cols = re.findall(r'\(([^)]+)\)', linea)[0].replace('"', '').split(',')
            uniques.append([c.strip() for c in cols])
            continue
        if mayus.startswith('FOREIGN KEY'):
            m = re.match(r'FOREIGN KEY\s*\((\w+)\)\s*REFERENCES\s+(\w+)\s*\((\w+)\)', linea, re.I)
            if m:
                fks.append({'columna': m.group(1), 'tabla_ref': m.group(2), 'columna_ref': m.group(3)})
            continue
        if mayus.startswith('CONSTRAINT'):
            # CONSTRAINT xxx UNIQUE (col1, col2)
            m = re.search(r'UNIQUE\s*\(([^)]+)\)', linea, re.I)
            if m:
                uniques.append([c.strip().replace('"', '') for c in m.group(1).split(',')])
            continue

        # Definición de columna: nombre tipo [NOT NULL] [UNIQUE] [PRIMARY KEY]
        m = re.match(r'^("?\w+"?)\s+(\w+(?:\([^)]*\))?)\s*(.*)$', linea, re.I)
        if m:
            nombre = m.group(1).replace('"', '')
            resto = m.group(3).upper()
            columnas.append({
                'nombre': nombre,
                'tipo_sqlite': m.group(2),
                'tipo_mysql': convertir_tipo(m.group(2)),
                'not_null': 'NOT NULL' in resto,
                'unique': 'UNIQUE' in resto,
            })
            # PK declarada inline en la propia columna
            if 'PRIMARY KEY' in resto:
                pk = [nombre]

    return columnas, pk, uniques, fks


# =============================================================================
# Fase 2 - Generación del archivo SQL para MySQL
# =============================================================================
def generar_sql(esquema, datos, db_name, ruta_salida):
    """Genera create_mysql_schema.sql con CREATE DATABASE, TABLE e INSERT."""
    orden = ordenar_por_dependencias(esquema)
    lineas = []
    lineas.append('-- ====================================================================')
    lineas.append('-- ASPLOT CENTER - Esquema MySQL generado automáticamente')
    lineas.append('-- Origen: SQLite (migrate_sqlite_to_mysql.py) - Sprint 1 (PB-01)')
    lineas.append(f"-- Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lineas.append('-- ====================================================================')
    lineas.append('')
    lineas.append(f'CREATE DATABASE IF NOT EXISTS `{db_name}` '
                  'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
    lineas.append(f'USE `{db_name}`;')
    lineas.append('')

    # --- CREATE TABLE ---
    for tabla in orden:
        columnas, pk, uniques, fks = parsear_definicion(esquema[tabla])
        lineas.append(f'-- ------------------------------------------------------------')
        lineas.append(f'-- Tabla: {tabla}')
        lineas.append(f'-- ------------------------------------------------------------')
        lineas.append(f'CREATE TABLE IF NOT EXISTS `{tabla}` (')

        defs = []
        for col in columnas:
            d = f"  `{col['nombre']}` {col['tipo_mysql']}"
            if col['not_null']:
                d += ' NOT NULL'
            if col['unique']:
                d += ' UNIQUE'
            defs.append(d)
        if pk:
            defs.append(f"  PRIMARY KEY (`{'`, `'.join(pk)}`)")
        for cols in uniques:
            defs.append(f"  UNIQUE KEY `uq_{tabla}_{'_'.join(cols)}` (`{'`, `'.join(cols)}`)")
        for i, fk in enumerate(fks, 1):
            defs.append(f"  CONSTRAINT `fk_{tabla}_{fk['columna']}` FOREIGN KEY (`{fk['columna']}`) "
                        f"REFERENCES `{fk['tabla_ref']}` (`{fk['columna_ref']}`)")

        lineas.append(',\n'.join(defs))
        lineas.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;')
        lineas.append('')

    # --- INSERT ---
    lineas.append('-- ====================================================================')
    lineas.append('-- Datos migrados desde SQLite')
    lineas.append('-- ====================================================================')
    lineas.append('')
    for tabla in orden:
        info = datos.get(tabla)
        if not info or not info['filas']:
            lineas.append(f'-- {tabla}: sin registros (será poblada por el uso del sistema)')
            lineas.append('')
            continue
        columnas = info['columnas']
        cols_sql = ', '.join(f'`{c}`' for c in columnas)
        for fila in info['filas']:
            valores = ', '.join(literal_sql(fila.get(c)) for c in columnas)
            lineas.append(f'INSERT INTO `{tabla}` ({cols_sql}) VALUES ({valores});')
        lineas.append('')

    contenido = '\n'.join(lineas)
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        f.write(contenido)
    return contenido


# =============================================================================
# Fase 3 - Importación a MySQL (opcional, con --importar)
# =============================================================================
def importar_a_mysql(ruta_sql, cfg):
    """Ejecuta el archivo .sql contra el servidor MySQL usando pymysql."""
    try:
        import pymysql
    except ImportError:
        print('[ERROR] pymysql no está instalado. Ejecute: pip install pymysql')
        return False

    print(f"\n[MySQL] Conectando a {cfg['host']}:{cfg['port']} como {cfg['user']}...")
    conn = pymysql.connect(
        host=cfg['host'], port=cfg['port'], user=cfg['user'], password=cfg['password'],
        charset='utf8mb4', autocommit=True
    )
    try:
        with conn.cursor() as cur:
            with open(ruta_sql, 'r', encoding='utf-8') as f:
                contenido = f.read()

            # pymysql.execute_many no admite múltiples sentencias: se ejecuta
            # por bloques usando el parser de sentencias del cliente MySQL.
            for sentencia in partir_sentencias(contenido):
                cur.execute(sentencia)
        print('[MySQL] Esquema y datos importados correctamente.')
        return True
    finally:
        conn.close()


def partir_sentencias(sql):
    """
    Divide el contenido SQL en sentencias individuales.
    Respeta comillas simples y descarta las líneas de comentario.
    """
    sentencias, actual = [], []
    dentro_comilla = False
    for c in sql:
        if c == "'":
            dentro_comilla = not dentro_comilla
        if c == ';' and not dentro_comilla:
            bloque = ''.join(actual)
            limpia = '\n'.join(
                l for l in bloque.splitlines()
                if l.strip() and not l.strip().startswith('--')
            ).strip()
            if limpia:
                sentencias.append(limpia)
            actual = []
        else:
            actual.append(c)
    bloque = ''.join(actual)
    limpia = '\n'.join(
        l for l in bloque.splitlines()
        if l.strip() and not l.strip().startswith('--')
    ).strip()
    if limpia:
        sentencias.append(limpia)
    return sentencias


# =============================================================================
# Programa principal
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description='Migración SQLite -> MySQL (Sprint 1)')
    parser.add_argument('--sqlite', default=os.path.join('instance', 'asplot_database.db'),
                        help='Ruta de la BD SQLite de origen')
    parser.add_argument('--salida', default=CARPETA_SALIDA_DEFAULT,
                        help='Carpeta de salida de los archivos generados')
    parser.add_argument('--importar', action='store_true',
                        help='Importar directamente a MySQL tras generar los archivos')
    parser.add_argument('--solo-sql', action='store_true',
                        help='Generar solo el archivo SQL (sin exportar JSON)')
    args = parser.parse_args()

    if not os.path.exists(args.sqlite):
        print(f'[ERROR] No se encontró la base de datos SQLite: {args.sqlite}')
        sys.exit(1)

    os.makedirs(args.salida, exist_ok=True)
    db_name = os.environ.get('MYSQL_DATABASE', DB_NAME_DEFAULT)

    print('=' * 66)
    print(' ASPLOT CENTER - Migración SQLite -> MySQL (Sprint 1)')
    print('=' * 66)

    # ---- Fase 1: lectura ----
    print(f'\n[Fase 1] Leyendo esquema y datos desde: {args.sqlite}')
    esquema = leer_esquema(args.sqlite)
    orden = ordenar_por_dependencias(esquema)
    datos = leer_datos(args.sqlite, orden)
    total_registros = sum(len(v['filas']) for v in datos.values())
    print(f'         Tablas detectadas : {len(esquema)} ({", ".join(orden)})')
    print(f'         Registros totales: {total_registros}')

    # ---- Fase 2: generación de archivos ----
    print('\n[Fase 2] Generando archivos de migración...')
    ruta_sql = os.path.join(args.salida, 'create_mysql_schema.sql')
    generar_sql(esquema, datos, db_name, ruta_sql)
    print(f'         Esquema SQL      : {ruta_sql}')

    if not args.solo_sql:
        ruta_json = os.path.join(args.salida, 'datos_exportados.json')
        paquete = {
            'metadata': {
                'base_origen': os.path.abspath(args.sqlite),
                'base_destino': db_name,
                'fecha_exportacion': datetime.now().isoformat(),
                'tablas': len(esquema),
                'registros': total_registros,
            },
            'datos': datos,
        }
        with open(ruta_json, 'w', encoding='utf-8') as f:
            json.dump(paquete, f, ensure_ascii=False, indent=2)
        print(f'         Datos exportados : {ruta_json}')

    # ---- Fase 3: importación opcional ----
    if args.importar:
        cfg = {
            'host': os.environ.get('MYSQL_HOST', 'localhost'),
            'port': int(os.environ.get('MYSQL_PORT', '3306')),
            'user': os.environ.get('MYSQL_USER', 'root'),
            'password': os.environ.get('MYSQL_PASSWORD', ''),
        }
        ok = importar_a_mysql(ruta_sql, cfg)
        if not ok:
            sys.exit(1)
    else:
        print('\n[Info] Importación omitida (use --importar para ejecutarla).')
        print('       También puede ejecutar el archivo SQL manualmente en MySQL Workbench.')

    print('\n' + '=' * 66)
    print(' Migración completada. Siguiente paso: validar con validar_migracion.py')
    print('=' * 66)


if __name__ == '__main__':
    main()
