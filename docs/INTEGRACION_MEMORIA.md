# Integración de Memoria Vectorizada y Gestión de Sesiones

## 🎉 ¿Qué se ha integrado?

Este documento describe la integración completa de memoria vectorizada y gestión de sesiones en DevTeam AI.

---

## ✅ Componentes Integrados

### 1. SessionManager Mejorado (`src/storage/session_manager.py`)

**Funcionalidades:**
- ✅ Crear nuevas sesiones con metadata
- ✅ Listar sesiones activas con filtros
- ✅ Obtener resumen detallado de sesiones
- ✅ Recuperar mensajes de sesiones anteriores
- ✅ Eliminar sesiones completas
- ✅ Soporte para SQLite y PostgreSQL

**Métodos principales:**
```python
session_mgr = SessionManager(db)

# Crear sesión
session_id = session_mgr.create_session(user_id="usuario123")

# Listar sesiones
sessions = session_mgr.get_active_sessions(user_id="usuario123", limit=50)

# Obtener resumen
summary = session_mgr.get_session_summary(session_id)

# Obtener mensajes
messages = session_mgr.get_session_messages(session_id, limit=100)

# Eliminar sesión
success = session_mgr.delete_session(session_id)
```

---

### 2. MemoryIntegration (`src/storage/memory_integration.py`)

**Funcionalidades:**
- ✅ Almacenamiento automático de conversaciones
- ✅ Extracción y almacenamiento de requisitos (RF, RNF, HU)
- ✅ Extracción y almacenamiento de componentes de diseño
- ✅ Almacenamiento de código generado
- ✅ Búsqueda semántica en todas las categorías
- ✅ Contexto relevante por fase del pipeline

**Uso:**
```python
memory = MemoryIntegration(settings, project_id="proyecto-123")

# Verificar si está habilitada
if memory.is_enabled():
    # Almacenar conversación
    memory.store_conversation_message(
        session_id="session-123",
        role="user",
        content="Quiero crear una API REST"
    )
    
    # Almacenar requisitos
    memory.store_requirements(session_id, requirements_doc)
    
    # Almacenar diseño
    memory.store_design_components(session_id, design_doc)
    
    # Almacenar código
    memory.store_code_artifact(session_id, "src/main.py", code_content)
    
    # Buscar contexto similar
    results = memory.search_similar_context(
        query="autenticación JWT",
        session_id="session-123",
        limit=5
    )
```

---

### 3. ArtifactMonitor (`src/storage/artifact_monitor.py`)

**Funcionalidades:**
- ✅ Monitoreo automático de la carpeta `artifacts/`
- ✅ Detección de archivos nuevos
- ✅ Almacenamiento automático en memoria vectorizada
- ✅ Clasificación de tipo de código

**Uso:**
```python
monitor = ArtifactMonitor(artifacts_path, memory)

# Escanear y almacenar archivos nuevos
monitor.scan_and_store(session_id="session-123")

# Reiniciar (para nueva sesión)
monitor.reset()
```

---

### 4. Página de Gestión de Sesiones (`pages/1_📚_Sesiones.py`)

**Funcionalidades:**
- ✅ Explorar todas las sesiones guardadas
- ✅ Ver detalles y estadísticas de cada sesión
- ✅ Continuar conversaciones anteriores
- ✅ Ver historial completo de mensajes
- ✅ Exportar sesiones a TXT
- ✅ Eliminar sesiones con confirmación
- ✅ Estadísticas generales (gráficos, top usuarios)
- ✅ Panel de configuración

**Acceso:**
- Ejecuta `streamlit run app.py`
- Ve al menú lateral → **📚 Sesiones**

---

### 5. Página de Búsqueda Semántica (`pages/2_🔍_Búsqueda_Semántica.py`)

**Funcionalidades:**
- ✅ Búsqueda inteligente por significado (no solo palabras clave)
- ✅ Búsqueda en conversaciones, requisitos, diseños y código
- ✅ Filtros avanzados (sesión, categorías)
- ✅ Resultados con score de similitud
- ✅ Vista organizada por tabs
- ✅ Documentación integrada

**Acceso:**
- Ejecuta `streamlit run app.py`
- Ve al menú lateral → **🔍 Búsqueda Semántica**

---

### 6. Integración en App Principal (`app.py`)

**Cambios realizados:**
- ✅ Inicialización automática de `MemoryIntegration`
- ✅ Inicialización automática de `SessionManager`
- ✅ Inicialización automática de `ArtifactMonitor`
- ✅ Almacenamiento automático de mensajes
- ✅ Detección y almacenamiento de requisitos
- ✅ Detección y almacenamiento de diseños
- ✅ Escaneo automático de artefactos generados
- ✅ Indicador de estado de memoria vectorizada

---

## 🚀 Cómo Usar

### Paso 1: Configurar Supabase (Opcional pero Recomendado)

**Si quieres usar memoria vectorizada:**

1. Crea una cuenta en [Supabase](https://supabase.com)
2. Crea un nuevo proyecto
3. Obtén la URL de conexión:
   - Ve a `Settings` → `Database`
   - Copia la **Connection string** (URI)
   - Formato: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`

4. Configura en `.env`:
   ```bash
   SUPABASE_DB_URL=postgresql+psycopg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```

5. Inicializa las tablas:
   ```bash
   python init_vector_memory.py
   ```

**Si usas SQLite (desarrollo local):**
- No necesitas configurar nada
- La memoria vectorizada estará deshabilitada
- La gestión de sesiones funcionará normalmente

---

### Paso 2: Ejecutar la Aplicación

```bash
streamlit run app.py
```

---

### Paso 3: Usar las Nuevas Funcionalidades

#### Gestión de Sesiones

1. Ve a **📚 Sesiones** en el menú lateral
2. Explora tus conversaciones anteriores
3. Haz clic en **▶️ Continuar** para retomar una conversación
4. Usa **📥 Exportar** para descargar el historial
5. Usa **🗑️ Eliminar** para borrar sesiones

#### Búsqueda Semántica (requiere Supabase)

1. Ve a **🔍 Búsqueda Semántica** en el menú lateral
2. Escribe lo que buscas en lenguaje natural:
   - "autenticación con JWT"
   - "validación de formularios"
   - "arquitectura hexagonal"
3. Ajusta filtros si es necesario
4. Haz clic en **🔍 Buscar**
5. Explora los resultados por categoría

#### Memoria Automática

La memoria funciona automáticamente:
- ✅ Cada mensaje se almacena con embedding
- ✅ Los requisitos se extraen y almacenan
- ✅ Los diseños se extraen y almacenan
- ✅ El código generado se almacena
- ✅ Todo es buscable semánticamente

---

## 📊 Arquitectura de la Integración

```
┌─────────────────────────────────────────────────────────────┐
│                      app.py (Streamlit)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │MemoryInteg.  │  │SessionMgr    │  │ArtifactMon.  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │VectorMemory  │  │Database      │  │Artifacts/    │      │
│  │(pgvector)    │  │(Agno)        │  │              │      │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘      │
└─────────┼──────────────────┼─────────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQL (Supabase)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Tablas Relacionales:                                  │   │
│  │  - sessions, runs, messages, agent_sessions          │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ Tablas Vectorizadas (pgvector):                      │   │
│  │  - conversation_embeddings (384D)                    │   │
│  │  - requirement_embeddings (384D)                     │   │
│  │  - design_embeddings (384D)                          │   │
│  │  - code_embeddings (384D)                            │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ Índices HNSW para búsqueda rápida                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔬 Tecnologías Utilizadas

| Componente | Tecnología | Propósito |
|------------|-----------|-----------|
| Embeddings | sentence-transformers | Convertir texto a vectores |
| Modelo | all-MiniLM-L6-v2 | 384 dimensiones, rápido y preciso |
| Base de datos vectorial | pgvector | Extensión PostgreSQL para vectores |
| Índice | HNSW | Búsqueda aproximada de vecinos más cercanos |
| Métrica | Cosine similarity | Medir similitud entre vectores |
| ORM | Agno DB | Gestión de sesiones y runs |

---

## 📈 Rendimiento

### Embeddings
- **Modelo:** all-MiniLM-L6-v2
- **Dimensiones:** 384
- **Velocidad:** ~1000 textos/segundo (CPU)
- **Tamaño:** ~80MB en disco

### Búsqueda Vectorial
- **Índice:** HNSW (Hierarchical Navigable Small World)
- **Complejidad:** O(log n) en promedio
- **Precisión:** >95% recall@10
- **Latencia:** <50ms para 1M vectores

---

## 🔒 Seguridad y Privacidad

- ✅ Todos los embeddings se almacenan en tu base de datos
- ✅ No se envían datos a servicios externos de embeddings
- ✅ El modelo corre localmente (descarga automática)
- ✅ Las sesiones están aisladas por `session_id`
- ✅ Soporte para multi-usuario con `user_id`

---

## 🐛 Troubleshooting

### "Memoria vectorizada deshabilitada"

**Causa:** No hay `SUPABASE_DB_URL` configurado o estás usando SQLite.

**Solución:**
1. Configura Supabase en `.env`
2. Ejecuta `python init_vector_memory.py`
3. Reinicia la aplicación

---

### "Error al conectar con Supabase"

**Causa:** URL incorrecta o credenciales inválidas.

**Solución:**
1. Verifica que la URL tenga el formato correcto
2. Asegúrate de que la contraseña sea correcta
3. Verifica que el proyecto de Supabase esté activo
4. Prueba la conexión con `python test_supabase_connection.py`

---

### "No se encuentran resultados en búsqueda"

**Causa:** No hay datos indexados todavía.

**Solución:**
1. Crea algunos proyectos primero
2. Espera a que se indexen automáticamente
3. Verifica que la memoria vectorizada esté habilitada
4. Ve a **Sesiones** → **Configuración** para verificar

---

### "Error: module 'sentence_transformers' not found"

**Causa:** Falta instalar dependencias.

**Solución:**
```bash
pip install sentence-transformers
```

---

## 🚀 Próximas Mejoras

### Corto Plazo
- [ ] Panel de estadísticas de memoria vectorizada
- [ ] Exportación masiva de sesiones
- [ ] Limpieza automática de sesiones antiguas
- [ ] Búsqueda con filtros temporales

### Mediano Plazo
- [ ] Recomendaciones automáticas basadas en proyectos similares
- [ ] Detección de patrones recurrentes
- [ ] Sugerencias de mejora de código
- [ ] Análisis de tendencias en proyectos

### Largo Plazo
- [ ] Fine-tuning del modelo de embeddings
- [ ] Soporte para embeddings multimodales (código + docs)
- [ ] Clustering automático de proyectos
- [ ] Knowledge graph de conceptos

---

## 📚 Referencias

- [Agno Documentation](https://docs.agno.com/)
- [pgvector](https://github.com/pgvector/pgvector)
- [sentence-transformers](https://www.sbert.net/)
- [Supabase](https://supabase.com/docs)
- [HNSW Algorithm](https://arxiv.org/abs/1603.09320)

---

## 🤝 Contribuir

Si encuentras bugs o tienes sugerencias:
1. Abre un issue en el repositorio
2. Describe el problema o mejora
3. Incluye logs si es un error
4. Propón una solución si es posible

---

## ✅ Checklist de Integración

- [x] SessionManager con funcionalidad completa
- [x] VectorMemory integrado en el pipeline
- [x] MemoryIntegration como capa de abstracción
- [x] ArtifactMonitor para código generado
- [x] Página de gestión de sesiones
- [x] Página de búsqueda semántica
- [x] Almacenamiento automático de conversaciones
- [x] Extracción automática de requisitos
- [x] Extracción automática de diseños
- [x] Almacenamiento automático de código
- [x] Script de inicialización
- [x] Documentación completa
- [x] Soporte para SQLite y PostgreSQL
- [x] Manejo de errores robusto
- [x] Logging detallado

---

**¡La integración está completa y lista para usar!** 🎉
