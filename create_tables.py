"""Crear tablas (relacionales + vectorizadas) en Supabase"""
import psycopg
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("SUPABASE_DB_URL").replace("postgresql+psycopg://", "postgresql://")

print("Creando tablas en Supabase...")
print("  - Tablas relacionales (sesiones, runs, mensajes)")
print("  - Tablas vectorizadas (embeddings para búsqueda semántica)")

# SQL para crear las tablas que Agno necesita + tablas vectorizadas
CREATE_TABLES_SQL = """
-- ============================================================
-- TABLAS RELACIONALES (para Agno)
-- ============================================================

-- Tabla de sesiones
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de runs (ejecuciones)
CREATE TABLE IF NOT EXISTS runs (
    id SERIAL PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    session_id TEXT REFERENCES sessions(session_id),
    agent_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de mensajes
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    run_id TEXT REFERENCES runs(run_id),
    role TEXT NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de sesiones de agentes
CREATE TABLE IF NOT EXISTS agent_sessions (
    id SERIAL PRIMARY KEY,
    agent_id TEXT NOT NULL,
    session_id TEXT REFERENCES sessions(session_id),
    data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- EXTENSIÓN PGVECTOR (para búsqueda semántica)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- TABLAS VECTORIZADAS (embeddings)
-- ============================================================

-- Embeddings de conversaciones
CREATE TABLE IF NOT EXISTS conversation_embeddings (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_id INTEGER,
    content TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings de requisitos
CREATE TABLE IF NOT EXISTS requirement_embeddings (
    id SERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    requirement_id TEXT NOT NULL,
    requirement_type TEXT,
    content TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings de diseño
CREATE TABLE IF NOT EXISTS design_embeddings (
    id SERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    component_name TEXT NOT NULL,
    design_type TEXT,
    content TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings de código
CREATE TABLE IF NOT EXISTS code_embeddings (
    id SERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    code_type TEXT,
    content TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- ÍNDICES (rendimiento)
-- ============================================================

-- Índices relacionales
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_runs_session_id ON runs(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_run_id ON messages(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_session_id ON agent_sessions(session_id);

-- Índices vectoriales (HNSW para búsqueda rápida)
CREATE INDEX IF NOT EXISTS conversation_embeddings_idx 
ON conversation_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS requirement_embeddings_idx 
ON requirement_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS design_embeddings_idx 
ON design_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS code_embeddings_idx 
ON code_embeddings USING hnsw (embedding vector_cosine_ops);
"""

try:
    conn = psycopg.connect(url)
    cur = conn.cursor()
    
    cur.execute(CREATE_TABLES_SQL)
    conn.commit()
    
    print("\n✅ Tablas creadas exitosamente")
    
    # Verificar
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    
    tables = cur.fetchall()
    print(f"\nTablas en Supabase ({len(tables)}):")
    
    relational = []
    vectorized = []
    
    for table in tables:
        name = table[0]
        if 'embedding' in name:
            vectorized.append(name)
        else:
            relational.append(name)
    
    if relational:
        print("\n📊 Tablas relacionales:")
        for t in relational:
            print(f"  ✓ {t}")
    
    if vectorized:
        print("\n🧠 Tablas vectorizadas:")
        for t in vectorized:
            print(f"  ✓ {t}")
    
    # Verificar extensión pgvector
    cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
    vector_ext = cur.fetchone()
    if vector_ext:
        print(f"\n✅ pgvector instalado: versión {vector_ext[1]}")
    else:
        print("\n⚠️  pgvector NO está instalado")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
