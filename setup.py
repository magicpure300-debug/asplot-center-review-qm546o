#!/usr/bin/env python3
"""
Script de inicialización para As Plot Center
Este script configura el entorno y ejecuta la aplicación por primera vez
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path

def check_python_version():
    """Verificar que la versión de Python sea compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} detectado")

def create_virtual_environment():
    """Crear entorno virtual si no existe"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("📦 Creando entorno virtual...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Entorno virtual creado")
    else:
        print("✅ Entorno virtual ya existe")

def install_dependencies():
    """Instalar dependencias del proyecto"""
    print("📦 Instalando dependencias...")
    
    # Determinar el ejecutable de pip según el sistema operativo
    if os.name == 'nt':  # Windows
        pip_executable = "venv\\Scripts\\pip"
    else:  # Linux/Mac
        pip_executable = "venv/bin/pip"
    
    try:
        subprocess.run([pip_executable, "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencias instaladas correctamente")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        sys.exit(1)

def create_directories():
    """Crear directorios necesarios"""
    directories = [
        "static/uploads/planos",
        "static/images",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directorios creados")

def initialize_database():
    """Inicializar la base de datos"""
    print("🗄️ Inicializando base de datos...")
    
    # Importar y ejecutar la aplicación para crear las tablas
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from models import db
            db.create_all()
        
        print("✅ Base de datos inicializada")
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        sys.exit(1)

def create_sample_data():
    """Crear datos de ejemplo"""
    print("📊 Creando datos de ejemplo...")
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from models import db, Usuario, Cliente, Proyecto, TipoPlano, Material, Inventario
            
            # Verificar si ya existen datos
            if Usuario.query.count() > 1:  # Más que solo el admin
                print("✅ Datos de ejemplo ya existen")
                return
            
            # Crear cliente de ejemplo
            cliente_ejemplo = Cliente(
                nombre="María",
                apellido="González",
                email="maria.gonzalez@constructora.com",
                telefono="0414699854",
                direccion="AV. Bolívar, Maturín"
            )
            db.session.add(cliente_ejemplo)
            
            # Crear proyecto de ejemplo
            proyecto_ejemplo = Proyecto(
                id_cliente=cliente_ejemplo.id_cliente,
                nombre_proyecto="Edificio Residencial Los Alamos",
                descripcion="Proyecto residencial de 12 pisos con 48 apartamentos",
                fecha_inicio="2025-01-01",
                fecha_fin="2025-12-31",
                estado="en_progreso"
            )
            db.session.add(proyecto_ejemplo)
            
            db.session.commit()
            print("✅ Datos de ejemplo creados")
            
    except Exception as e:
        print(f"⚠️ Advertencia: No se pudieron crear datos de ejemplo: {e}")

def show_credentials():
    """Mostrar credenciales de acceso"""
    print("\n" + "="*50)
    print("🎉 ¡As Plot Center está listo!")
    print("="*50)
    print("\n📋 Credenciales de acceso:")
    print("   Email: admin@asplot.com")
    print("   Contraseña: admin123")
    print("\n🌐 Para acceder a la aplicación:")
    print("   1. Ejecuta: python app.py")
    print("   2. Abre tu navegador en: http://localhost:5000")
    print("   3. Usa las credenciales mostradas arriba")
    print("\n📚 Para más información, consulta el archivo README.md")
    print("="*50)

def main():
    """Función principal"""
    print("🚀 Inicializando As Plot Center...")
    print("="*50)
    
    try:
        check_python_version()
        create_virtual_environment()
        install_dependencies()
        create_directories()
        initialize_database()
        create_sample_data()
        show_credentials()
        
    except KeyboardInterrupt:
        print("\n❌ Instalación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error durante la instalación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()





