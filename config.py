# -*- coding: utf-8 -*-
"""
ASPLOT CENTER - Configuración de la aplicación
Sprint 1 (PB-01): soporte de MySQL mediante variables de entorno,
manteniendo SQLite como opción de respaldo mientras MySQL no esté
disponible en producción (Patrón Strangler Fig).

Variables de entorno para activar MySQL:
    MYSQL_HOST      (ej: localhost)
    MYSQL_PORT      (ej: 3306)
    MYSQL_USER      (ej: root)
    MYSQL_PASSWORD  (ej: secret)
    MYSQL_DATABASE  (ej: asplot_center)

Si MYSQL_HOST y MYSQL_PASSWORD NO están definidas, la aplicación
continúa operando sobre SQLite (compatibilidad hacia atrás).
"""

import os


def get_database_url():
    """
    Construye la URL de conexión a la base de datos.
    - Si las variables de entorno MySQL están presentes -> MySQL.
    - En caso contrario                      -> SQLite (respaldo).
    """
    host = os.environ.get('MYSQL_HOST')
    password = os.environ.get('MYSQL_PASSWORD')

    # Criterio de conmutación (Strangler Fig): MySQL solo cuando está configurado
    if host and password is not None and os.environ.get('MYSQL_USER'):
        user = os.environ.get('MYSQL_USER', 'root')
        port = os.environ.get('MYSQL_PORT', '3306')
        database = os.environ.get('MYSQL_DATABASE', 'asplot_center')
        return f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4'

    return 'sqlite:///asplot_database.db'


def es_mysql():
    """Indica si la aplicación apunta a MySQL o a SQLite."""
    return get_database_url().startswith('mysql')


class Config:
    """Configuración base para la aplicación Flask"""

    # Configuración de la base de datos (SQLite por defecto, MySQL por env vars)
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuración de seguridad
    SECRET_KEY = os.environ.get('SECRET_KEY', 'asplot-center-secret-key-2025')

    # Configuración de archivos
    UPLOAD_FOLDER = os.path.join('static', 'uploads', 'planos')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB máximo por archivo

    # Tipos de archivos permitidos para planos
    ALLOWED_EXTENSIONS = {'pdf', 'dwg', 'dxf', 'jpg', 'jpeg', 'png'}

    # Configuración de sesión
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora

    @staticmethod
    def init_app(app):
        """Inicializar configuración específica de la aplicación"""
        pass


class MySQLConfig(Config):
    """
    Configuración que fuerza el uso de MySQL.
    Detecta automáticamente las variables de entorno MYSQL_USER,
    MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT y MYSQL_DATABASE.
    """
    SQLALCHEMY_DATABASE_URI = get_database_url()

    @staticmethod
    def validar():
        """Verifica que las variables de entorno MySQL estén completas."""
        faltantes = [v for v in ('MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD')
                     if v not in os.environ]
        if faltantes:
            raise RuntimeError(
                'MySQLConfig requiere las variables de entorno definidas: '
                + ', '.join(faltantes)
            )


class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True


class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'mysql': MySQLConfig,
    'default': DevelopmentConfig
}
