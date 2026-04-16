# Memoria y Persistencia en DevTeam AI

## Resumen

El sistema ahora tiene **memoria de largo plazo** mejorada con:

✅ **Sesiones persistentes** - Cada conversación se guarda con un ID único  
✅ **Historial completo** - Los agentes recuerdan hasta 20 interacciones anteriores  
✅ **Contexto compartido** - Todos los agentes ven las últimas 10 ejecuciones del equipo  
✅ **Base de datos** - SQLite (desarrollo) o PostgreSQL (producción)

---

## Configuración Actual

### Nivel 1: SQLite (Desarrollo) ✅ YA ACTIVO

**Ubicación:** `data/devteam.db`

**Qué guarda:**
- Todas las sesiones de conversación
- Historial completo de mensajes
- Estado de cada agente
- Trazas de ejecución
- Metadata de runs

**Ventajas:**
- ✅ Cero configuración
- ✅ Funciona offline
- ✅ Perfecto para desarrollo local
- ✅ Portátil (un solo archivo)

**Limitaciones:**
- ❌ No soporta múltiples usuarios concurrentes
- ❌ No escalable para producción
- ❌ Sin backups automáticos

---

## Migración a PostgreSQL (Producción)

### Opción A: Supabase (Recomendado - Gratis)

**Paso 1: Crear cuenta en Supabase**

1. Ve a https://supabase.com
2. Crea una cuenta gratuita
3. Crea un nuevo proyecto
4. Espera 2-3 minutos a que se aprovisione

**Paso 2: Obtener URL de conexión**

1. En tu proyecto, ve a `Settings` → `Database`
2. Baja hasta la sección **"Connection string"**
3. Selecciona la pestaña **"URI"** (no "Session mode" ni "Transaction mode")
4. Verás algo como:
   ```
   postgresql://postgres.[ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
5. **IMPORTANTE:** Si dice `[YOUR-PASSWORD]`, necesitas tu contraseña real

**Paso 2.1: Obtener tu contraseña (si no la recuerdas)**

1. En la misma página (Settings → Database)
2. Busca **"Database password"** o **"Reset database password"**
3. Haz clic en **"Reset database password"**
4. **COPIA Y GUARDA** la nueva contraseña que aparezca (solo se muestra una vez)

**Ejemplo con tu proyecto:**

Si tu proyecto es `vxrdwigjhonnsbifbjws`, la URL se verá así:
```
postgresql://postgres.vxrdwigjhonnsbifbjws:tu_password_aqui@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

**Paso 3: Configurar en tu proyecto**

Edita tu archivo `.env` (copia desde `.env.example` si no existe):

```bash
# Agrega esta línea con TU contraseña real
# Nota: Agrega "+psycopg" después de "postgresql" (importante para Python)
SUPABASE_DB_URL=postgresql+psycopg://postgres.vxrdwigjhonnsbifbjws:tu_password_real@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

**⚠️ IMPORTANTE:**
- Reemplaza `tu_password_real` con la contraseña que copiaste
- NO uses `[YOUR-PASSWORD]` literalmente
- Asegúrate de que diga `postgresql+psycopg://` (con el `+psycopg`)
- La región (`us-west-1`) puede variar, verifica en tu dashboard

**❌ NO uses estas variables (son para frontend Next.js):**
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY`

Solo necesitas `SUPABASE_DB_URL` para la conexión directa a PostgreSQL.

**Paso 4: Reiniciar la aplicación**

```bash
streamlit run app.py
```

¡Listo! Agno creará automáticamente todas las tablas necesarias en PostgreSQL.

---

### Opción B: PostgreSQL Local

**Paso 1: Instalar PostgreSQL**

Windows:
```powershell
# Con Chocolatey
choco install postgresql

# O descarga desde: https://www.postgresql.org/download/windows/
```

**Paso 2: Crear base de datos**

```bash
# Conectar a PostgreSQL
psql -U postgres

# Crear base de datos
CREATE DATABASE devteam_ai;

# Crear usuario
CREATE USER devteam WITH PASSWORD 'tu_password_seguro';
GRANT ALL PRIVILEGES ON DATABASE devteam_ai TO devteam;
```

**Paso 3: Configurar conexión**

En tu `.env`:

```bash
SUPABASE_DB_URL=postgresql+psycopg://devteam:tu_password_seguro@localhost:5432/devteam_ai
```

---

## Configuración de Memoria

### Parámetros Actuales (Ya Configurados)

**En el Team (Orquestador):**
```python
add_history_to_context=True        # ← Carga historial completo
num_team_history_runs=10           # ← Últimas 10 ejecuciones del equipo
create_session=True                # ← Crea sesiones persistentes
session_id=session_id              # ← ID único por conversación
```

**En cada Agente:**
```python
add_history_to_context=True        # ← Carga historial del agente
num_history_responses=20           # ← Últimas 20 respuestas
```

### Ajustar Memoria (Opcional)

Si necesitas **más contexto** (consume más tokens):

```python
# En src/orchestrator/team.py
num_team_history_runs=20  # ← Aumentar de 10 a 20

# En src/agents/*.py
num_history_responses=50  # ← Aumentar de 20 a 50
```

Si necesitas **menos contexto** (más rápido, más barato):

```python
num_team_history_runs=5
num_history_responses=10
```

---

## Gestión de Sesiones

### Continuar una conversación anterior

**Opción 1: En Streamlit (Automático)**

El sistema ya guarda automáticamente cada sesión. Para continuar:
1. No hagas clic en "Nueva conversación"
2. Simplemente sigue escribiendo
3. El historial se mantiene automáticamente

**Opción 2: Programáticamente**

```python
from src.orchestrator.team import create_dev_team

# Crear equipo con session_id específico
team = create_dev_team(session_id="abc-123-def-456")

# Todas las interacciones se guardan bajo ese ID
team.run("Continúa con el proyecto anterior")
```

### Ver sesiones guardadas

```python
from src.storage import get_database, SessionManager
from src.config.settings import get_settings

settings = get_settings()
db = get_database(settings)
session_mgr = SessionManager(db)

# Listar sesiones activas
sessions = session_mgr.get_active_sessions()

# Ver resumen de una sesión
summary = session_mgr.get_session_summary("session-id-aqui")
```

---

## Qué se Guarda Automáticamente

### En la Base de Datos

| Tabla | Contenido |
|-------|-----------|
| `sessions` | Metadata de cada conversación |
| `runs` | Cada ejecución del equipo/agente |
| `messages` | Todos los mensajes (user + assistant) |
| `agent_sessions` | Estado de cada agente |
| `tool_calls` | Llamadas a herramientas (write_file, etc.) |

### En el Sistema de Archivos

| Ubicación | Contenido |
|-----------|-----------|
| `artifacts/` | Código generado por los agentes |
| `data/devteam.db` | Base de datos SQLite (si no usas PostgreSQL) |

---

## Ventajas de la Nueva Configuración

### Antes (Configuración Original)
- ❌ Solo 5 runs en memoria
- ❌ Historial desactivado (`add_history_to_context=False`)
- ❌ Sin gestión de sesiones
- ❌ Contexto limitado entre agentes

### Ahora (Configuración Mejorada)
- ✅ 10 runs del equipo + 20 respuestas por agente
- ✅ Historial completo activado
- ✅ Sesiones persistentes con IDs únicos
- ✅ Contexto compartido entre todos los agentes
- ✅ Memoria de largo plazo en base de datos
- ✅ Posibilidad de continuar conversaciones

---

## Próximos Pasos (Opcional)

### Nivel 2: Memoria Vectorizada (RAG)

Si necesitas buscar en proyectos anteriores o documentación:

```python
# Agregar a requirements.txt
chromadb>=0.4.0
sentence-transformers>=2.0.0

# O usar pgvector con PostgreSQL
pgvector>=0.2.0
```

Esto permitiría:
- 🔍 Buscar proyectos similares anteriores
- 📚 RAG sobre documentación técnica
- 🧠 Aprendizaje entre sesiones
- 💡 Sugerencias basadas en patrones históricos

**¿Necesitas esto?** Avísame y te ayudo a implementarlo.

---

## Troubleshooting

### "No se conecta a PostgreSQL"

1. Verifica que la URL esté correcta en `.env`
2. Asegúrate de que PostgreSQL esté corriendo
3. Revisa que el firewall permita la conexión
4. Prueba la conexión manualmente:
   ```bash
   psql "postgresql://user:pass@host:5432/dbname"
   ```

### "La base de datos está muy grande"

SQLite puede crecer con el tiempo. Para limpiar:

```bash
# Respaldar
cp data/devteam.db data/devteam.db.backup

# Eliminar sesiones antiguas (implementar query personalizado)
# O simplemente eliminar el archivo para empezar de cero
rm data/devteam.db
```

### "Quiero exportar mis conversaciones"

```python
# TODO: Implementar exportador
# Por ahora, puedes acceder directamente a la DB con:
import sqlite3
conn = sqlite3.connect('data/devteam.db')
# Hacer queries SQL directamente
```

---

## Resumen de Cambios Realizados

✅ `src/orchestrator/team.py` - Memoria mejorada + sesiones  
✅ `src/agents/*.py` - Historial de 20 respuestas por agente  
✅ `src/storage/session_manager.py` - Gestor de sesiones  
✅ `app.py` - Integración de session_id  
✅ Este documento de referencia

**Tu sistema ahora tiene memoria de largo plazo completa.** 🎉
