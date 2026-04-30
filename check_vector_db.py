"""Verifica el estado de la memoria vectorial en Supabase."""
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.WARNING)

from src.config.settings import get_settings
from src.storage.memory_integration import MemoryIntegration

settings = get_settings()

print("Inicializando MemoryIntegration...")
memory = MemoryIntegration(settings, project_id="test-proyecto")
print("is_enabled:", memory.is_enabled())

if memory.is_enabled():
    print("\nIntentando guardar un mensaje de prueba...")
    try:
        memory.store_conversation_message(
            session_id="test-session-001",
            role="user",
            content="Quiero una aplicación web de gestión de tareas con autenticación"
        )
        print("store_conversation_message: OK")
    except Exception as e:
        print("store_conversation_message ERROR:", e)
        import traceback; traceback.print_exc()

    print("\nVerificando que se guardó...")
    from src.storage.vector_memory import VectorMemory
    vm = VectorMemory(settings.supabase_db_url)
    conn = vm.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM conversation_embeddings;")
    print("Registros en conversation_embeddings:", cur.fetchone()[0])
    cur.close()
    conn.close()
