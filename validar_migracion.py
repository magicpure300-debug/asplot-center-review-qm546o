# -*- coding: utf-8 -*-
"""
=============================================================================
 ASPLOT CENTER - Sprint 1 (PB-03)
 Validación de integridad de datos después de la migración
=============================================================================
 Compara la base de datos SQLite de origen con la base MySQL de destino
 y genera un reporte de integridad:

   1. Existencia de las 9 tablas en MySQL.
   2. Conteo de registros por tabla (SQLite vs MySQL).
   3. Huella (fingerprint) de los datos: detecta valores alterados o perdidos
      normalizando las diferencias de representación entre motores
      (DECIMAL/float, TINYINT/bool, precisión de DATETIME).
   4. Integridad referencial en MySQL: registros huérfanos en claves foráneas.

 Uso:
   python validar_migracion.py
   python validar_migracion.py --sqlite instance/otra.db
   python validar_migracion.py --tolerante   (no aborta con código de error)

 Variables de entorno MySQL:
   MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
=============================================================================
"""

import argparse
import hashlib
import os
import re
import sqlite3
import sys
from datetime import date, datetime
from decimal import Decimal

DB_NAME_DEFAULT = 'asplot_center'
TABLAS_ESPERADAS = [
    'usuarios', 'clientes', 'proyectos', 'tipos_plano', 'planos',
    'materiales', 'inventario', 'facturas', 'detalle_facturas',
]


# =============================================================================
# Normalización de valores (SQLite vs MySQL representan distinto lo mismo)
# =============================================================================
def normalizar(valor):
    """Canoniza un valor para comparar entre SQLite y MySQL."""
    if valor is None:
        return 'NULL'
    if isinstance(valor, bool):
        return '1' if valor else '0'
    if isinstance(valor, Decimal):
        return f'{float(valor):.4f}'
    if isinstance(valor, float):
        return f'{valor:.4f}'
    if isinstance(valor, datetime):
        return valor.strftime('%Y-%m-%d %H:%M:%S')  # MySQL DATETIME: sin microsegundos
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, (bytes, bytearray)):
        return bytes(valor).hex()
    return str(valor).strip()


def huella(filas):
    """Hash determinista del conjunto de filas (ya normalizadas)."""
    canonico = '\n'.join(sorted('|'.join(f) for f in filas))
    return hashlib.sha256(canonico.encode('utf-8')).hexdigest()[:16]


# =============================================================================
# Lectura desde SQLite
# =============================================================================
def leer_sqlite(ruta_sqlite):
    conn = sqlite3.connect(ruta_sqlite)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tablas = [r[0] for r in cur.fetchall()]

    resultado = {}
    for tabla in tablas:
        cur.execute(f'SELECT * FROM "{tabla}"')
        columnas = [d[0] for d in cur.description]
        cur.execute(f'SELECT COUNT(*) FROM "{tabla}"')
        conteo = cur.fetchone()[0]
        cur.execute(f'SELECT * FROM "{tabla}"')
        filas = [[normalizar(v) for v in fila] for fila in cur.fetchall()]
        resultado[tabla] = {'columnas': columnas, 'conteo': conteo, 'huella': huella(filas)}
    conn.close()
    return resultado


# =============================================================================
# Lectura desde MySQL
# =============================================================================
def leer_mysql():
    try:
        import pymysql
    except ImportError:
        print('[ERROR] pymysql no está instalado. Ejecute: pip install pymysql')
        sys.exit(2)

    cfg = {
        'host': os.environ.get('MYSQL_HOST', 'localhost'),
        'port': int(os.environ.get('MYSQL_PORT', '3306')),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASSWORD', ''),
        'database': os.environ.get('MYSQL_DATABASE', DB_NAME_DEFAULT),
    }
    print(f"[MySQL] Conectando a {cfg['host']}:{cfg['port']} / {cfg['database']} ...")
    conn = pymysql.connect(host=cfg['host'], port=cfg['port'], user=cfg['user'],
                           password=cfg['password'], database=cfg['database'],
                           charset='utf8mb4', autocommit=True)
    resultado = {}
    try:
        with conn.cursor() as cur:
            cur.execute('SHOW TABLES')
            tablas = [r[0] for r in cur.fetchall()]
            for tabla in tablas:
                cur.execute(f'SELECT COUNT(*) FROM `{tabla}`')
                conteo = cur.fetchone()[0]
                cur.execute(f'SELECT * FROM `{tabla}`')
                desc = cur.description
                columnas = [d[0] for d in desc]
                filas = [[normalizar(v) for v in fila] for fila in cur.fetchall()]
                resultado[tabla] = {'columnas': columnas, 'conteo': conteo, 'huella': huella(filas)}
    finally:
        conn.close()
    return resultado, cfg


def validar_fk_orfanos(cfg):
    """Busca registros huérfanos en claves foráneas usando INFORMATION_SCHEMA."""
    try:
        import pymysql
    except ImportError:
        return []

    conn = pymysql.connect(host=cfg['host'], port=cfg['port'], user=cfg['user'],
                           password=cfg['password'], database=cfg['database'],
                           charset='utf8mb4', autocommit=True)
    problemas = []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL
            """, (cfg['database'],))
            for tabla, col, tabla_ref, col_ref in cur.fetchall():
                cur.execute(
                    f'SELECT COUNT(*) FROM `{tabla}` h '
                    f'LEFT JOIN `{tabla_ref}` p ON h.`{col}` = p.`{col_ref}` '
                    f'WHERE h.`{col}` IS NOT NULL AND p.`{col_ref}` IS NULL'
                )
                n = cur.fetchone()[0]
                if n:
                    problemas.append(f'{tabla}.{col} -> {tabla_ref}.{col_ref}: {n} registro(s) huérfano(s)')
    finally:
        conn.close()
    return problemas


# =============================================================================
# Programa principal
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description='Validación de integridad SQLite -> MySQL (Sprint 1)')
    parser.add_argument('--sqlite', default=os.path.join('instance', 'asplot_database.db'),
                        help='Ruta de la BD SQLite de origen')
    parser.add_argument('--tolerante', action='store_true',
                        help='No retornar código de error si hay diferencias')
    args = parser.parse_args()

    print('=' * 66)
    print(' ASPLOT CENTER - Validación de integridad (Sprint 1 / PB-03)')
    print('=' * 66)

    if not os.path.exists(args.sqlite):
        print(f'[ERROR] No se encontró la BD SQLite: {args.sqlite}')
        sys.exit(1)

    sqlite_info = leer_sqlite(args.sqlite)
    print(f'[SQLite] {args.sqlite}: {len(sqlite_info)} tablas, '
          f'{sum(v["conteo"] for v in sqlite_info.values())} registros\n')

    try:
        mysql_info, cfg = leer_mysql()
    except Exception as e:
        print(f'[ERROR] No se pudo conectar a MySQL: {e}')
        print('        Verifique que el servidor esté activo y las variables')
        print('        MYSQL_HOST / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE definidas.')
        sys.exit(2)

    fallos = []
    print(f'[MySQL]  {len(mysql_info)} tablas, {sum(v["conteo"] for v in mysql_info.values())} registros\n')

    print('-' * 66)
    print(f'{"TABLA":<20} {"SQLite":>8} {"MySQL":>8} {"Datos":>10}  Estado')
    print('-' * 66)

    for tabla in TABLAS_ESPERADAS:
        s = sqlite_info.get(tabla)
        m = mysql_info.get(tabla)
        if s is None:
            print(f'{tabla:<20} {"-":>8} {m["conteo"] if m else "-":>8} {"-":>10}  FALTA en SQLite')
            fallos.append(f'{tabla}: no existe en SQLite')
            continue
        if m is None:
            print(f'{tabla:<20} {s["conteo"]:>8} {"-":>8} {"-":>10}  FALTA en MySQL')
            fallos.append(f'{tabla}: no fue creada en MySQL')
            continue

        conteo_ok = s['conteo'] == m['conteo']
        datos_ok = s['huella'] == m['huella']
        estado = 'OK' if (conteo_ok and datos_ok) else ('DIFERENCIA' if conteo_ok else 'CONTEO DISTINTO')
        marca = '\033[92m' if estado == 'OK' else '\033[91m'
        print(f'{tabla:<20} {s["conteo"]:>8} {m["conteo"]:>8} {"iguales" if datos_ok else "DISTINTOS":>10}  {marca}{estado}\033[0m')
        if not conteo_ok:
            fallos.append(f'{tabla}: conteo SQLite={s["conteo"]} vs MySQL={m["conteo"]}')
        if not datos_ok:
            fallos.append(f'{tabla}: los datos no coinciden (huella distinta)')

    # Tablas extra en MySQL (no deberían existir)
    extra = set(mysql_info) - set(TABLAS_ESPERADAS)
    if extra:
        print(f'\n[AVISO] Tablas adicionales en MySQL: {", ".join(sorted(extra))}')

    print('-' * 66)

    # Integridad referencial
    print('\n[PB-03] Verificando integridad referencial en MySQL...')
    orfanos = validar_fk_orfanos(cfg)
    if orfanos:
        for o in orfanos:
            print(f'  [FALLO] {o}')
            fallos.append(o)
    else:
        print('  [OK] Sin registros huérfanos en claves foráneas.')

    # Resultado
    print('\n' + '=' * 66)
    if fallos:
        print(f' RESULTADO: MIGRACIÓN CON DIFERENCIAS ({len(fallos)} problema(s))')
        for f in fallos:
            print(f'   - {f}')
        print('=' * 66)
        sys.exit(0 if args.tolerante else 1)
    print(' RESULTADO: MIGRACIÓN EXITOSA - Integridad verificada en las 9 tablas')
    print('=' * 66)
    sys.exit(0)


if __name__ == '__main__':
    main()
