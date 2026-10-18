# -*- coding: utf-8 -*-
"""
=============================================================================
 ASPLOT CENTER - Sprint 1 (PB-02)
 Script alternativo de importación SQLite -> MySQL vía SQLAlchemy
=============================================================================
 Alternativa a la ejecución directa de `create_mysql_schema.sql`, pensada
 para entornos donde no se pueda correr el archivo SQL desde la consola o
 desde MySQL Workbench (por ejemplo, hosting con acceso solo por ORM).

 Lee el archivo portable `datos_exportados.json` generado por
 `migrate_sqlite_to_mysql.py` y carga los registros en MySQL respetando
 el orden de dependencias de las claves foráneas.

 Uso:
   python importar_a_mysql.py                     # usa migracion/datos_exportados.json
   python importar_a_mysql.py --json otro.json    # otro archivo de origen
   python importar_a_mysql.py --vaciar            # limpia las tablas antes de importar

 Variables de entorno MySQL:
   MYSQL_HOST (localhost), MYSQL_PORT (3306), MYSQL_USER (root),
   MYSQL_PASSWORD (vacía), MYSQL_DATABASE (asplot_center)
=============================================================================
"""

import argparse
import json
import os
import sys
from datetime import date, datetime

DB_NAME_DEFAULT = 'asplot_center'
JSON_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migracion', 'datos_exportados.json')


def crear_engine_mysql():
    """Crea el engine de SQLAlchemy apuntando a MySQL usando variables de entorno."""
    try:
        import pymysql  # noqa: F401  (driver requerido por SQLAlchemy para MySQL)
    except ImportError:
        print('[ERROR] pymysql no está instalado. Ejecute: pip install pymysql')
        sys.exit(1)

    from sqlalchemy import create_engine

    host = os.environ.get('MYSQL_HOST', 'localhost')
    port = os.environ.get('MYSQL_PORT', '3306')
    user = os.environ.get('MYSQL_USER', 'root')
    password = os.environ.get('MYSQL_PASSWORD', '')
    database = os.environ.get('MYSQL_DATABASE', DB_NAME_DEFAULT)

    uri = f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4'
    return create_engine(uri, pool_pre_ping=True)


def deserializar(valor):
    """Convierte los valores serializados del JSON a tipos Python nativos."""
    if not isinstance(valor, str):
        return valor
    # Fechas: 'YYYY-MM-DD HH:MM:SS[.ffffff]' o 'YYYY-MM-DD'
    if len(valor) >= 10 and valor[4] == '-' and valor[7] == '-':
        try:
            if len(valor) > 10:
                return datetime.fromisoformat(valor)
            return date.fromisoformat(valor)
        except ValueError:
            pass
    return valor


def importar(ruta_json, vaciar):
    if not os.path.exists(ruta_json):
        print(f'[ERROR] No se encontró el archivo de datos: {ruta_json}')
        print('        Ejecute primero: python migrate_sqlite_to_mysql.py')
        sys.exit(1)

    with open(ruta_json, 'r', encoding='utf-8') as f:
        paquete = json.load(f)
    datos = paquete['datos']

    engine = crear_engine_mysql()
    from sqlalchemy import text

    print('=' * 66)
    print(' ASPLOT CENTER - Importación alternativa a MySQL (Sprint 1)')
    print('=' * 66)
    print(f"\nArchivo de datos : {ruta_json}")
    print(f"Tablas           : {len(datos)}")

    with engine.begin() as conn:
        if vaciar:
            print('\n[AVISO] Se vaciarán las tablas antes de importar (--vaciar).')
            for tabla in reversed(list(datos.keys())):  # respetar dependencias inversas
                conn.execute(text(f'DELETE FROM `{tabla}`'))

        total = 0
        for tabla, info in datos.items():
            filas = info['filas']
            if not filas:
                print(f'  - {tabla:<20} sin registros (omitida)')
                continue
            columnas = info['columnas']
            cols_sql = ', '.join(f'`{c}`' for c in columnas)
            placeholders = ', '.join(f':{c}' for c in columnas)
            sentencia = text(f'INSERT INTO `{tabla}` ({cols_sql}) VALUES ({placeholders})')

            for fila in filas:
                conn.execute(sentencia, {c: deserializar(fila.get(c)) for c in columnas})
            total += len(filas)
            print(f'  - {tabla:<20} {len(filas):>4} registros importados')

    print(f'\n[OK] Importación finalizada: {total} registros en MySQL.')


def main():
    parser = argparse.ArgumentParser(description='Importación alternativa SQLite -> MySQL (Sprint 1)')
    parser.add_argument('--json', default=JSON_DEFAULT, help='Ruta del archivo datos_exportados.json')
    parser.add_argument('--vaciar', action='store_true', help='Vaciar tablas antes de importar')
    args = parser.parse_args()
    importar(args.json, args.vaciar)


if __name__ == '__main__':
    main()
