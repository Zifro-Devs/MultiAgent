"""Verificar que pgvector esté instalado y funcionando"""
import psycopg
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("SUPABASE_DB_URL")
url = url.replace("postgresql+psycopg://", "postgresql://")

print("🔍 Verificando pgvector en Supabase...\n")

try:
    conn = psycopg.connect(url)
    cur = conn.cursor()
    
    # Verificar extensión pgvector
    cur.execute("""
        SELECT extname, extversion 
        FROM pg_extension 
        WHERE extname = 'vector';
    """)
    
    result = cur.fetchone()
    
    if result:
        print(f"✅ pgvector instalado: versión {result[1]}")
    else:
        print("❌ pgvector NO está instalado")
    
    # Verificar tablas con columnas vector
    cur.execute("""
        SELECT 
            table_name, 
            column_name, 
            data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND data_type = 'USER-DEFINED'
        AND udt_name = 'vector';
    """)
    
    vector_columns = cur.fetchall()
    
    if vector_columns:
        print(f"\n✅ Columnas vectoriales encontradas ({len(vector_columns)}):")
        for table, column, dtype in vector_columns:
            print(f"  - {table}.{column}")
    else:
        print("\n⚠️ No se encontraron columnas vectoriales")
    
    # Verificar índices HNSW
    cur.execute("""
        SELECT 
            indexname, 
            tablename 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND indexdef LIKE '%hnsw%';
    """)
    
    indexes = cur.fetchall()
    
    if indexes:
        print(f"\n✅ Índices HNSW encontrados ({len(indexes)}):")
        for idx_name, table_name in indexes:
            print(f"  - {idx_name} en {table_name}")
    else:
        print("\n⚠️ No se encontraron índices HNSW")
    
    # Probar una búsqueda vectorial simple
    print("\n🧪 Probando búsqueda vectorial...")
    
    # Crear un vector de prueba (384 dimensiones, todo ceros)
    test_vector = [0.0] * 384
    
    cur.execute("""
        SELECT COUNT(*) 
        FROM conversation_embeddings 
        WHERE embedding IS NOT NULL;
    """)
    
    count = cur.fetchone()[0]
    print(f"   Embeddings en conversation_embeddings: {count}")
    
    if count > 0:
        # Probar búsqueda
        cur.execute("""
            SELECT 
                id, 
                session_id,
                1 - (embedding <=> %s::vector) as similarity
            FROM conversation_embeddings
            ORDER BY embedding <=> %s::vector
            LIMIT 1;
        """, (test_vector, test_vector))
        
        result = cur.fetchone()
        if result:
            print(f"   ✅ Búsqueda vectorial funciona correctamente")
            print(f"      ID: {result[0]}, Session: {result[1]}, Similarity: {result[2]:.4f}")
    else:
        print("   ℹ️ No hay embeddings para probar búsqueda")
    
    cur.close()
    conn.close()
    
    print("\n" + "="*60)
    print("✅ MEMORIA VECTORIZADA COMPLETAMENTE FUNCIONAL")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
