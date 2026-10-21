"""
Script de inicialización y migración de base de datos
As Plot Center - Refactor a Portal Cliente-Servicio
"""

from app import create_app
from models import db, Usuario, Cliente, TipoPlano, Proyecto

def init_database():
    """Inicializa la base de datos con datos básicos necesarios"""
    
    app = create_app()
    
    with app.app_context():
        print("🔄 Creando tablas de base de datos...")
        db.create_all()
        print("✅ Tablas creadas exitosamente\n")
        
        # Verificar si ya existe usuario admin
        admin_existente = Usuario.query.filter_by(email='admin@asplot.com').first()
        
        if not admin_existente:
            print("📝 Creando usuario administrador...")
            admin = Usuario(
                nombre_usuario='admin',
                email='admin@asplot.com',
                rol='admin',
                nombre_completo='Administrador del Sistema',
                activo=True
            )
            import os
            admin.set_password(os.environ.get('ADMIN_PASSWORD', 'admin123'))
            db.session.add(admin)
            print("✅ Usuario admin creado")
            print("   Email: admin@asplot.com")
            print("   Contraseña: admin123\n")
        else:
            print("ℹ️  Usuario admin ya existe\n")
        
        # Crear tipos de plano por defecto
        if TipoPlano.query.count() == 0:
            print("📝 Creando tipos de plano por defecto...")
            tipos_plano = [
                TipoPlano(nombre_tipo='Arquitectónico', descripcion='Planos arquitectónicos'),
                TipoPlano(nombre_tipo='Estructural', descripcion='Planos estructurales'),
                TipoPlano(nombre_tipo='Eléctrico', descripcion='Planos eléctricos'),
                TipoPlano(nombre_tipo='Plomería', descripcion='Planos de plomería'),
                TipoPlano(nombre_tipo='Mecánico', descripcion='Planos mecánicos'),
                TipoPlano(nombre_tipo='HVAC', descripcion='Planos de climatización'),
                TipoPlano(nombre_tipo='Topográfico', descripcion='Planos topográficos')
            ]
            
            for tipo in tipos_plano:
                db.session.add(tipo)
            print(f"✅ {len(tipos_plano)} tipos de plano creados\n")
        else:
            print("ℹ️  Tipos de plano ya existen\n")
        
        # Crear cliente de ejemplo
        cliente_ejemplo_existe = Cliente.query.filter_by(email='ejemplo.sistema@asplot.com').first()
        
        if not cliente_ejemplo_existe:
            print("📝 Creando cliente de ejemplo...")
            cliente_ejemplo = Cliente(
                nombre='Cliente',
                apellido='Ejemplo',
                email='ejemplo.sistema@asplot.com',
                telefono='555-0000',
                direccion='Dirección de ejemplo'
            )
            db.session.add(cliente_ejemplo)
            db.session.flush()
            
            # Crear proyecto de ejemplo
            proyecto_ejemplo = Proyecto(
                id_cliente=cliente_ejemplo.id_cliente,
                nombre_proyecto='Proyecto de Prueba',
                descripcion='Proyecto de ejemplo para subir planos de prueba',
                tipo_servicio='plano',
                estado='aprobado'
            )
            db.session.add(proyecto_ejemplo)
            print("✅ Cliente y proyecto de ejemplo creados\n")
        else:
            print("ℹ️  Cliente de ejemplo ya existe\n")
        
        # Guardar todos los cambios
        try:
            db.session.commit()
            print("✅ Base de datos inicializada correctamente!\n")
            print("=" * 60)
            print("CREDENCIALES DE ACCESO:")
            print("=" * 60)
            print("Administrador:")
            print("  Usuario: admin@asplot.com")
            print("  Contraseña: admin123")
            print("=" * 60)
            print("\n🚀 Puedes iniciar la aplicación ahora con: python run_dev.py\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al guardar cambios: {e}")
            return False
    
    return True


def crear_usuario_cliente_demo():
    """Crea un usuario de prueba con rol cliente"""
    
    app = create_app()
    
    with app.app_context():
        # Verificar si ya existe
        cliente_demo_existe = Cliente.query.filter_by(email='cliente@asplot.com').first()
        
        if cliente_demo_existe:
            print("ℹ️  Cliente demo ya existe")
            return
        
        print("📝 Creando cliente demo...")
        
        # Crear perfil de cliente
        cliente = Cliente(
            nombre='Cliente',
            apellido='Demo',
            email='cliente@asplot.com',
            telefono='555-1234',
            direccion='Dirección de prueba'
        )
        
        # Crear usuario con rol cliente
        usuario_cliente = Usuario(
            nombre_usuario='cliente',
            email='cliente@asplot.com',
            rol='cliente',
            nombre_completo='Cliente Demo',
            activo=True
        )
        usuario_cliente.set_password('cliente123')
        
        db.session.add(cliente)
        db.session.add(usuario_cliente)
        db.session.flush()
        
        # Vincular cliente con usuario
        cliente.id_usuario = usuario_cliente.id_usuario
        
        try:
            db.session.commit()
            print("✅ Cliente demo creado exitosamente!")
            print("=" * 60)
            print("CREDENCIALES DEL CLIENTE:")
            print("=" * 60)
            print("  Email: cliente@asplot.com")
            print("  Contraseña: cliente123")
            print("=" * 60)
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al crear cliente demo: {e}")


def crear_trabajador_demo():
    """Crea un usuario de prueba con rol trabajador"""
    
    app = create_app()
    
    with app.app_context():
        # Verificar si ya existe
        trabajador_existe = Usuario.query.filter_by(email='trabajador@asplot.com').first()
        
        if trabajador_existe:
            print("ℹ️  Trabajador demo ya existe")
            return
        
        print("📝 Creando trabajador demo...")
        
        usuario_trabajador = Usuario(
            nombre_usuario='trabajador',
            email='trabajador@asplot.com',
            rol='trabajador',
            nombre_completo='Trabajador Demo',
            activo=True
        )
        usuario_trabajador.set_password('trabajador123')
        
        db.session.add(usuario_trabajador)
        
        try:
            db.session.commit()
            print("✅ Trabajador demo creado exitosamente!")
            print("=" * 60)
            print("CREDENCIALES DEL TRABAJADOR:")
            print("=" * 60)
            print("  Email: trabajador@asplot.com")
            print("  Contraseña: trabajador123")
            print("=" * 60)
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al crear trabajador demo: {e}")


if __name__ == '__main__':
    import sys
    
    print("\n" + "=" * 60)
    print("AS PLOT CENTER - INICIALIZACIÓN DE BASE DE DATOS")
    print("=" * 60 + "\n")
    
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        if comando == 'cliente':
            crear_usuario_cliente_demo()
        elif comando == 'trabajador':
            crear_trabajador_demo()
        elif comando == 'todos':
            init_database()
            crear_usuario_cliente_demo()
            crear_trabajador_demo()
        else:
            print("Comandos disponibles:")
            print("  python init_db.py          - Inicializar BD y crear admin")
            print("  python init_db.py cliente  - Crear usuario cliente demo")
            print("  python init_db.py trabajador - Crear usuario trabajador demo")
            print("  python init_db.py todos    - Crear todos los usuarios demo")
    else:
        # Por defecto, solo inicializar BD básica
        init_database()
