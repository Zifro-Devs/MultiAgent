"""Prueba el ciclo completo de aprendizaje autónomo."""
from dotenv import load_dotenv
load_dotenv()
import logging
logging.basicConfig(level=logging.WARNING)

from src.config.settings import get_settings
from src.storage.knowledge_memory import KnowledgeMemory
from src.agents.learning import LearningAgent

settings = get_settings()
km = KnowledgeMemory(settings.supabase_db_url)
km.ensure_table()

agent = LearningAgent(settings, km)

print("Simulando aprendizaje de un proyecto de e-commerce...")
saved = agent.learn_from_project(
    project_name="tienda-amazfit",
    project_type="web",
    user_request="Quiero una página informativa de relojes Amazfit con comparativas, características y sección de contacto para público general",
    analysis_doc="""RF-001: Mostrar catálogo de relojes con filtros por precio y características
RF-002: Comparar hasta 3 relojes simultáneamente
RF-003: Formulario de contacto con validación
RNF-001: Tiempo de carga < 2 segundos
RNF-002: Responsive para móvil""",
    design_doc="""Stack: React + TypeScript (frontend), FastAPI (backend), PostgreSQL
Componentes: ProductCard, CompareTable, ContactForm, FilterSidebar
API endpoints: GET /products, GET /products/{id}, POST /contact
Base de datos: tabla products (id, name, price, specs JSONB)""",
    implementation_summary="Archivos generados (12): frontend/src/App.tsx, frontend/src/components/ProductCard.tsx, frontend/src/components/CompareTable.tsx, backend/main.py, backend/models.py, backend/routes/products.py",
    validation_result="Código válido. Seguridad: sin vulnerabilidades críticas. Cobertura de requisitos: 100%",
)

print(f"Insights guardados: {saved}")

stats = km.get_knowledge_stats()
print(f"\nEstado de la base de conocimiento:")
print(f"  Total insights: {stats['total_insights']}")
print(f"  Por categoría: {stats['by_category']}")

if stats['total_insights'] > 0:
    print("\nBuscando conocimiento relevante para un nuevo proyecto web...")
    results = km.search_relevant_knowledge("quiero una tienda online de productos tecnológicos", limit=3)
    for r in results:
        print(f"\n  [{r['category']}] {r['title']}")
        print(f"  → {r['insight']}")
        print(f"  Similitud: {r['similarity']:.2f}")

km.close()
