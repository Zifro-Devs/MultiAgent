"""Script de inicialización de memoria vectorizada.

Crea las tablas necesarias para pgvector en Supabase.
Ejecutar: python init_vector_memory.py
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

from src.config.settings import get_settings
from src.storage.vector_memory import VectorMemory


def main():
    """Inicializa las tablas de memoria vectorizada."""
    print("=" * 80)
    print("🚀 Inicialización de Memoria Vectorizada")
    print("=" * 80)
    
    settings = get_settings()
    
    if not settings.supabase_db_url:
        print("\n❌ ERROR: SUPABASE_DB_URL no está configurado en .env")
        print("\nPara usar memoria vectorizada necesitas:")
        print("1. Crear un proyecto en Supabase (https://supabase.com)")
        print("2. Obtener la URL de conexión PostgreSQL")
        print("3. Configurarla en .env como SUPABASE_DB_URL")
        print("\nEjemplo:")
        print("SUPABASE_DB_URL=postgresql+psycopg://postgres:PASSWORD@db.xxx.supabase.co:6543/postgres")
        return 1
    
    print(f"\n📡 Conectando a Supabase...")
    print(f"   Host: {settings.supabase_db_url.split('@')[1].split('/')[0] if '@' in settings.supabase_db_url else 'N/A'}")
    
    try:
        vm = VectorMemory(settings.supabase_db_url)
        
        print("\n🔧 Creando tablas y extensiones...")
        vm.create_tables()
        
        print("\n✅ Inicialización completada exitosamente!")
        print("\nTablas creadas:")
        print("  ✓ conversation_embeddings - Conversaciones con embeddings")
        print("  ✓ requirement_embeddings  - Requisitos funcionales/no funcionales")
        print("  ✓ design_embeddings       - Componentes de diseño y ADRs")
        print("  ✓ code_embeddings         - Código fuente generado")
        
        print("\nÍndices HNSW creados para búsqueda vectorial rápida")
        
        print("\n🧠 Modelo de embeddings:")
        print(f"   {vm.embedding_model_name} (384 dimensiones)")
        
        print("\n🎉 ¡Todo listo! Ahora puedes usar la búsqueda semántica.")
        print("\nPróximos pasos:")
        print("1. Ejecuta: streamlit run app.py")
        print("2. Ve a la página 'Búsqueda Semántica' en el menú lateral")
        print("3. Comienza a crear proyectos - se indexarán automáticamente")
        
        vm.close()
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        print("\nDetalles del error:")
        traceback.print_exc()
        
        print("\n💡 Posibles soluciones:")
        print("1. Verifica que la URL de Supabase sea correcta")
        print("2. Asegúrate de que la contraseña no tenga caracteres especiales sin escapar")
        print("3. Verifica que tu proyecto de Supabase esté activo")
        print("4. Comprueba tu conexión a internet")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
