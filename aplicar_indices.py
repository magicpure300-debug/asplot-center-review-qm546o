# -*- coding: utf-8 -*-
"""
=============================================================================
 ASPLOT CENTER - Sprint 2 (PB-05)
 Aplicación de índices de rendimiento en la base de datos
=============================================================================
 Script idempotente: puede ejecutarse cuantas veces se desee sobre SQLite
 o MySQL. Crea los índices definidos en `models.py` (__table_args__) solo
 si aún no existen en la base de datos indicada.

 Motivación (ver docs/PLAN_SPRINT_2.md): las tablas más consultadas
 (proyectos, planos, facturas, inventario) no tenían ningún índice más allá
 de las claves primarias y únicas, lo que obligaba a búsquedas completas
 (full table scan) en los listados y tableros del sistema.

 Uso:
   python aplicar_indices.py                       # SQLite (instance/asplot_database.db)
   python aplicar_indices.py --motor mysql         # MySQL (variables de entorno MYSQL_*)
   python aplicar_indices.py --listar              # solo listar índices existentes
=============================================================================
"""

import argparse
import os
import sys

# Índices a crear: (nombre, tabla, columnas)
INDICES = [
    # --- Seguridad / usuarios ---
    ('ix_usuarios_rol', 'usuarios', ['rol']),
    ('ix_usuarios_activo', 'usuarios', ['activo']),

    # --- Clientes ---
    ('ix_clientes_id_usuario', 'clientes', ['id_usuario']),
    ('ix_clientes_nombre_apellido', 'clientes', ['nombre', 'apellido']),

    # --- Proyectos (tablero, listados, portafolio) ---
    ('ix_proyectos_id_cliente', 'proyectos', ['id_cliente']),
    ('ix_proyectos_estado', 'proyectos', ['estado']),
    ('ix_proyectos_fecha_solicitud', 'proyectos', ['fecha_solicitud']),
    ('ix_proyectos_tipo_servicio', 'proyectos', ['tipo_servicio']),
    ('ix_proyectos_estado_tipo', 'proyectos', ['estado', 'tipo_servicio']),

    # --- Planos (listados, búsqueda con JOIN) ---
    ('ix_planos_id_proyecto', 'planos', ['id_proyecto']),
    ('ix_planos_id_tipo_plano', 'planos', ['id_tipo_plano']),
    ('ix_planos_id_usuario', 'planos', ['id_usuario']),
    ('ix_planos_fecha_subida', 'planos', ['fecha_subida']),

    # --- Materiales / inventario ---
    ('ix_materiales_categoria', 'materiales', ['categoria']),
    ('ix_materiales_activo', 'materiales', ['activo']),
    ('ix_inventario_id_material', 'inventario', ['id_material']),

    # --- Facturación (reportes financieros) ---
    ('ix_facturas_id_proyecto', 'facturas', ['id_proyecto']),
    ('ix_facturas_id_cliente', 'facturas', ['id_cliente']),
    ('ix_facturas_fecha_factura', 'facturas', ['fecha_factura']),
    ('ix_facturas_estado_pago', 'facturas', ['estado_pago']),
    ('ix_detalle_facturas_id_factura', 'detalle_facturas', ['id_factura']),
    ('ix_detalle_facturas_id_plano', 'detalle_facturas', ['id_plano']),
    ('ix_detalle_facturas_id_material', 'detalle_facturas', ['id_material']),
]


# =============================================================================
# Conexión según el motor
# =============================================================================
def conectar_sqlite(ruta_sqlite):
    import sqlite3
    if not os.path.exists(ruta_sqlite):
        print(f'[ERROR] No se encontró la BD SQLite: {ruta_sqlite}')
        sys.exit(1)
    conn = sqlite3.connect(ruta_sqlite)
    return conn, 'sqlite'


def conectar_mysql():
    try:
        import pymysql
    except ImportError:
        print('[ERROR] pymysql no está instalado. Ejecute: pip install pymysql')
        sys.exit(1)

    cfg = {
        'host': os.environ.get('MYSQL_HOST', 'localhost'),
        'port': int(os.environ.get('MYSQL_PORT', '3306')),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASSWORD', ''),
        'database': os.environ.get('MYSQL_DATABASE', 'asplot_center'),
    }
    print(f"[MySQL] Conectando a {cfg['host']}:{cfg['port']} / {cfg['database']} ...")
    try:
        conn = pymysql.connect(host=cfg['host'], port=cfg['port'], user=cfg['user'],
                               password=cfg['password'], database=cfg['database'],
                               charset='utf8mb4', autocommit=True)
    except Exception as e:
        print(f'[ERROR] No se pudo conectar a MySQL: {e}')
        sys.exit(1)
    return conn, 'mysql'


# =============================================================================
# Operaciones genéricas (funcionan sobre ambos motores)
# =============================================================================
def indices_existentes(conn, motor):
    """Devuelve el conjunto de nombres de índices existentes (excluyendo PK/UNIQUE)."""
    cur = conn.cursor()
    if motor == 'sqlite':
        cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
        return {r[0] for r in cur.fetchall()}
    # MySQL: excluir los índices implícitos de claves primarias y únicas
    cur.execute('SHOW INDEX')
    return {r[2] for r in cur.fetchall() if r[2] not in ('PRIMARY',) and r[3] != 0}


def listar_indices(conn, motor):
    cur = conn.cursor()
    print('\nÍndices existentes por tabla:')
    if motor == 'sqlite':
        cur.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name")
        for nombre, tabla in cur.fetchall():
            print(f'  {tabla:<20} {nombre}')
    else:
        cur.execute('SHOW INDEX')
        filas = {}
        for r in cur.fetchall():
            filas.setdefault(r[2], set()).add(r[4])
        for tabla in sorted(filas):
            print(f'  {tabla:<20} {", ".join(sorted(filas[tabla]))}')


def crear_indices(conn, motor, existentes):
    """Crea los índices que falten. Devuelve (creados, omitidos, errores)."""
    cur = conn.cursor()
    creados, omitidos, errores = [], [], []

    for nombre, tabla, columnas in INDICES:
        if nombre in existentes:
            omitidos.append(nombre)
            continue
        cols = ', '.join(f'`{c}`' for c in columnas) if motor == 'mysql' else ', '.join(f'"{c}"' for c in columnas)
        # IF NOT EXISTS: SQLite 3.9+ y MySQL 5.7+/8.0 lo soportan
        sentencia = f'CREATE INDEX IF NOT EXISTS `{nombre}` ON `{tabla}` ({cols})'
        try:
            cur.execute(sentencia)
            creados.append(nombre)
        except Exception as e:
            errores.append(f'{nombre}: {e}')

    return creados, omitidos, errores


# =============================================================================
# Programa principal
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description='Aplicación de índices (Sprint 2 - PB-05)')
    parser.add_argument('--sqlite', default=os.path.join('instance', 'asplot_database.db'),
                        help='Ruta de la BD SQLite')
    parser.add_argument('--motor', choices=['sqlite', 'mysql'], default='sqlite',
                        help='Motor destino (por defecto: sqlite)')
    parser.add_argument('--listar', action='store_true', help='Solo listar índices existentes')
    args = parser.parse_args()

    print('=' * 66)
    print(' ASPLOT CENTER - Índices de rendimiento (Sprint 2 / PB-05)')
    print('=' * 66)

    conn, motor = conectar_mysql() if args.motor == 'mysql' else conectar_sqlite(args.sqlite)
    try:
        if args.listar:
            listar_indices(conn, motor)
            return

        existentes = indices_existentes(conn, motor)
        print(f'\n[Motor] {motor.upper()}')
        print(f'[Índices definidos en models.py] {len(INDICES)}')

        creados, omitidos, errores = crear_indices(conn, motor, existentes)

        if creados:
            print(f'\n[Creados] {len(creados)}:')
            for c in creados:
                print(f'   + {c}')
        if omitidos:
            print(f'\n[Ya existían] {len(omitidos)} (omitidos)')
        if errores:
            print(f'\n[Errores] {len(errores)}:')
            for e in errores:
                print(f'   ! {e}')
            sys.exit(1)

        print('\n' + '=' * 66)
        print(' Índices aplicados correctamente.')
        print('=' * 66)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
