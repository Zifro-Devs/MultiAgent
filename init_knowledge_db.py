"""Inicializa la tabla knowledge_base en Supabase."""
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)

from src.config.settings import get_settings
from src.storage.knowledge_memory import KnowledgeMemory

settings = get_settings()

if not settings.supabase_db_url:
    print("ERROR: SUPABASE_DB_URL no configurada en .env")
    exit(1)

km = KnowledgeMemory(settings.supabase_db_url)
km.ensure_table()

stats = km.get_knowledge_stats()
print(f"\nBase de conocimiento lista.")
print(f"Insights guardados: {stats['total_insights']}")
print(f"Por categoría: {stats['by_category']}")
km.close()
