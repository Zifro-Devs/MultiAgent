"""Script de verificación de integración.

Verifica que todos los componentes estén correctamente integrados.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que el root del proyecto esté en sys.path
_ROOT = str(Path(__file__).resolve().parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv()


def check_imports():
    """Verifica que todos los módulos se puedan importar."""
    print("🔍 Verificando imports...")
    
    try:
        from src.config.settings import get_settings
        print("  ✓ settings")
        
        from src.storage.database import get_database
        print("  ✓ database")
        
        from src.storage.session_manager import SessionManager
        print("  ✓ session_manager")
        
        from src.storage.vector_memory import VectorMemory
        print("  ✓ vector_memory")
        
        from src.storage.memory_integration import MemoryIntegration
        print("  ✓ memory_integration")
        
        from src.storage.artifact_monitor import ArtifactMonitor
        print("  ✓ artifact_monitor")
        
        from src.orchestrator.team import create_dev_team
        print("  ✓ team")
        
        print("\n✅ Todos los imports exitosos")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en imports: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_database():
    """Verifica la conexión a la base de datos."""
    print("\n🔍 Verificando base de datos...")
    
    try:
        from src.config.settings import get_settings
        from src.storage.database import get_database
        
        settings = get_settings()
        db = get_database(settings)
        
        if settings.supabase_db_url:
            print("  ✓ PostgreSQL (Supabase) configurado")
        else:
            print("  ✓ SQLite (desarrollo local)")
        
        print("\n✅ Base de datos accesible")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en base de datos: {e}")
        return False


def check_session_manager():
    """Verifica el SessionManager."""
    print("\n🔍 Verificando SessionManager...")
    
    try:
        from src.config.settings import get_settings
        from src.storage.database import get_database
        from src.storage.session_manager import SessionManager
        
        settings = get_settings()
        db = get_database(settings)
        session_mgr = SessionManager(db)
        
        # Crear sesión de prueba
        session_id = session_mgr.create_session(user_id="test-user")
        print(f"  ✓ Sesión creada: {session_id[:12]}...")
        
        # Listar sesiones
        sessions = session_mgr.get_active_sessions(limit=5)
        print(f"  ✓ Sesiones encontradas: {len(sessions)}")
        
        print("\n✅ SessionManager funcional")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en SessionManager: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_memory_integration():
    """Verifica MemoryIntegration."""
    print("\n🔍 Verificando MemoryIntegration...")
    
    try:
        from src.config.settings import get_settings
        from src.storage.memory_integration import MemoryIntegration
        
        settings = get_settings()
        memory = MemoryIntegration(settings, project_id="test-project")
        
        if memory.is_enabled():
            print("  ✓ Memoria vectorizada habilitada")
            print("  ℹ️ Requiere Supabase con pgvector")
        else:
            print("  ⚪ Memoria vectorizada deshabilitada")
            print("  ℹ️ Configura SUPABASE_DB_URL para habilitarla")
        
        print("\n✅ MemoryIntegration funcional")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en MemoryIntegration: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_pages():
    """Verifica que las páginas de Streamlit existan."""
    print("\n🔍 Verificando páginas de Streamlit...")
    
    pages = [
        "pages/1_📚_Sesiones.py",
        "pages/2_🔍_Búsqueda_Semántica.py",
    ]
    
    all_exist = True
    for page in pages:
        if Path(page).exists():
            print(f"  ✓ {page}")
        else:
            print(f"  ❌ {page} NO ENCONTRADO")
            all_exist = False
    
    if all_exist:
        print("\n✅ Todas las páginas existen")
    else:
        print("\n⚠️ Algunas páginas faltan")
    
    return all_exist


def check_documentation():
    """Verifica que la documentación exista."""
    print("\n🔍 Verificando documentación...")
    
    docs = [
        "README.md",
        "docs/MEMORIA_Y_PERSISTENCIA.md",
        "docs/INTEGRACION_MEMORIA.md",
    ]
    
    all_exist = True
    for doc in docs:
        if Path(doc).exists():
            print(f"  ✓ {doc}")
        else:
            print(f"  ❌ {doc} NO ENCONTRADO")
            all_exist = False
    
    if all_exist:
        print("\n✅ Toda la documentación existe")
    else:
        print("\n⚠️ Alguna documentación falta")
    
    return all_exist


def main():
    """Ejecuta todas las verificaciones."""
    print("=" * 80)
    print("🚀 Verificación de Integración - DevTeam AI")
    print("=" * 80)
    
    results = []
    
    results.append(("Imports", check_imports()))
    results.append(("Base de Datos", check_database()))
    results.append(("SessionManager", check_session_manager()))
    results.append(("MemoryIntegration", check_memory_integration()))
    results.append(("Páginas Streamlit", check_pages()))
    results.append(("Documentación", check_documentation()))
    
    print("\n" + "=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n🎉 ¡TODAS LAS VERIFICACIONES PASARON!")
        print("\n✅ La integración está completa y funcional")
        print("\nPróximos pasos:")
        print("1. Ejecuta: streamlit run app.py")
        print("2. Explora las nuevas páginas en el menú lateral")
        print("3. Si tienes Supabase, ejecuta: python init_vector_memory.py")
        return 0
    else:
        print("\n⚠️ ALGUNAS VERIFICACIONES FALLARON")
        print("\nRevisa los errores arriba y corrígelos antes de continuar")
        return 1


if __name__ == "__main__":
    sys.exit(main())
