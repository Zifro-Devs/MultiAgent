"""Test de conexión a Supabase"""
from dotenv import load_dotenv
load_dotenv()

from src.config.settings import get_settings
from src.storage.database import get_database

settings = get_settings()
print(f"SUPABASE_DB_URL configurado: {bool(settings.supabase_db_url)}")
print(f"URL (primeros 50 chars): {settings.supabase_db_url[:50] if settings.supabase_db_url else 'NO CONFIGURADO'}")

db = get_database(settings)
print(f"\nTipo de base de datos: {type(db).__name__}")

# Crear el equipo (esto crea las tablas automáticamente)
try:
    from src.orchestrator.team import create_dev_team
    print("\nCreando equipo...")
    team = create_dev_team()
    print("✅ Equipo creado")
    
    print("\nEnviando mensaje de prueba (esto crea las tablas)...")
    result = team.run("Hola, solo estoy probando la conexión")
    print("✅ Mensaje enviado - Las tablas AHORA SÍ están en Supabase")
    print("\nVe a Supabase → Table Editor y refresca la página")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
