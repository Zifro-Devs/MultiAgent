"""Verificar tablas directamente en PostgreSQL"""
import psycopg
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("SUPABASE_DB_URL")
# Convertir de postgresql+psycopg a postgresql
url = url.replace("postgresql+psycopg://", "postgresql://")

print(f"Conectando a: {url[:50]}...")

try:
    conn = psycopg.connect(url)
    cur = conn.cursor()
    
    # Listar todas las tablas
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    
    tables = cur.fetchall()
    
    if tables:
        print(f"\n✅ Tablas encontradas ({len(tables)}):")
        for table in tables:
            print(f"  - {table[0]}")
    else:
        print("\n❌ NO hay tablas en el schema 'public'")
        
        # Verificar otros schemas
        cur.execute("""
            SELECT schema_name 
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema');
        """)
        schemas = cur.fetchall()
        print(f"\nSchemas disponibles: {[s[0] for s in schemas]}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ Error de conexión: {e}")
    import traceback
    traceback.print_exc()
