# Changelog - DevTeam AI

Todos los cambios notables en este proyecto serán documentados en este archivo.

---

## [2.0.0] - 2024-XX-XX

### 🎉 Nuevas Funcionalidades Principales

#### Gestión de Sesiones Completa
- **SessionManager mejorado** con funcionalidad completa
  - Crear sesiones con metadata personalizada
  - Listar sesiones con filtros avanzados
  - Obtener resumen detallado de sesiones
  - Recuperar historial completo de mensajes
  - Eliminar sesiones con cascada
  - Soporte dual SQLite/PostgreSQL

#### Memoria Vectorizada con IA
- **VectorMemory** con pgvector
  - 4 tablas vectorizadas (conversaciones, requisitos, diseños, código)
  - Modelo de embeddings: all-MiniLM-L6-v2 (384 dimensiones)
  - Índices HNSW para búsqueda rápida
  - Búsqueda semántica por similitud de coseno

- **MemoryIntegration** como capa de abstracción
  - Almacenamiento automático de conversaciones
  - Extracción inteligente de requisitos (RF, RNF, HU)
  - Extracción de componentes de diseño y ADRs
  - Almacenamiento de código generado
  - Búsqueda multi-categoría
  - Contexto relevante por fase del pipeline

- **ArtifactMonitor** para código generado
  - Monitoreo automático de carpeta artifacts/
  - Detección de archivos nuevos
  - Almacenamiento automático en memoria vectorizada
  - Clasificación de tipo de código

#### Nuevas Páginas de Streamlit

- **📚 Sesiones** (`pages/1_📚_Sesiones.py`)
  - Explorar sesiones con filtros
  - Ver historial completo de mensajes
  - Continuar conversaciones anteriores
  - Exportar sesiones a TXT
  - Eliminar sesiones con confirmación
  - Estadísticas y gráficos de actividad
  - Panel de configuración

- **🔍 Búsqueda Semántica** (`pages/2_🔍_Búsqueda_Semántica.py`)
  - Búsqueda inteligente por significado
  - Filtros avanzados (sesión, categorías)
  - Resultados organizados por tabs
  - Scores de similitud
  - Documentación integrada
  - Ejemplos de uso

### 🔧 Mejoras en App Principal

- Inicialización automática de MemoryIntegration
- Inicialización automática de SessionManager
- Inicialización automática de ArtifactMonitor
- Almacenamiento automático de mensajes en memoria vectorizada
- Detección y almacenamiento automático de requisitos
- Detección y almacenamiento automático de diseños
- Escaneo automático de artefactos generados
- Indicador de estado de memoria vectorizada en sidebar

### 📚 Nueva Documentación

- **docs/INTEGRACION_MEMORIA.md** - Guía técnica completa de integración
- **INTEGRACION_COMPLETADA.md** - Resumen ejecutivo de la integración
- **INICIO_RAPIDO.md** - Guía de inicio rápido
- **CHANGELOG.md** - Este archivo

### 🛠️ Nuevos Scripts de Utilidad

- **init_vector_memory.py** - Inicialización de tablas vectorizadas
  - Crea extensión pgvector
  - Crea 4 tablas vectorizadas
  - Crea índices HNSW
  - Verificación de conexión

- **verify_integration.py** - Verificación completa del sistema
  - Verifica imports
  - Verifica base de datos
  - Verifica SessionManager
  - Verifica MemoryIntegration
  - Verifica páginas
  - Verifica documentación

### 📦 Dependencias Actualizadas

```
sentence-transformers>=2.0.0  # Nuevo
numpy>=1.24.0                 # Nuevo
pgvector>=0.3.0               # Nuevo
```

### 🔄 Cambios en Archivos Existentes

#### `src/storage/session_manager.py`
- ✅ Implementación completa de todos los métodos
- ✅ Queries optimizadas con JOINs
- ✅ Soporte para SQLite y PostgreSQL
- ✅ Manejo de errores robusto
- ✅ Logging detallado

#### `src/storage/__init__.py`
- ✅ Exporta MemoryIntegration
- ✅ Exporta ArtifactMonitor

#### `app.py`
- ✅ Imports de nuevos módulos
- ✅ Inicialización de gestores de memoria
- ✅ Almacenamiento automático en pipeline
- ✅ Indicador de estado de memoria
- ✅ Reinicio de memoria en nueva conversación

#### `README.md`
- ✅ Sección de nuevas features
- ✅ Estructura de proyecto actualizada
- ✅ Instrucciones de Supabase mejoradas
- ✅ Documentación de memoria vectorizada

---

## [1.0.0] - 2024-XX-XX (Versión Original)

### Funcionalidades Iniciales

#### Pipeline Multi-Agente
- Orquestador con Team de Agno
- 4 agentes especializados:
  - Agente de Análisis (requisitos)
  - Agente de Diseño (arquitectura)
  - Agente de Implementación (código)
  - Agente de Validación (QA + seguridad)

#### Generación de Código
- ArtifactTools con sandbox seguro
- Protección contra path traversal
- Límite de 500KB por archivo
- Operaciones: write_file, read_file, list_files

#### Persistencia Básica
- Soporte para SQLite (desarrollo)
- Soporte para PostgreSQL/Supabase (producción)
- Tablas relacionales de Agno (sessions, runs, messages)

#### Interfaz de Usuario
- Streamlit con chat conversacional
- Configuración dinámica de modelos
- Visualización de artefactos generados
- Gestión básica de sesiones

#### Seguridad
- Sandbox de I/O de archivos
- Sin secretos hardcodeados
- Validación OWASP en prompts
- Principio de mínimo privilegio

#### Testing
- Suite pytest completa
- Tests de seguridad (path traversal)
- Tests de funcionalidad
- Tests de integración

#### Documentación
- README.md completo
- docs/MEMORIA_Y_PERSISTENCIA.md
- Comentarios en código
- Docstrings

---

## Comparación de Versiones

| Feature | v1.0.0 | v2.0.0 |
|---------|--------|--------|
| Pipeline Multi-Agente | ✅ | ✅ |
| Generación de Código | ✅ | ✅ |
| Persistencia Básica | ✅ | ✅ |
| Gestión de Sesiones | ⚪ Básica | ✅ Completa |
| Memoria Vectorizada | ❌ | ✅ |
| Búsqueda Semántica | ❌ | ✅ |
| Indexación Automática | ❌ | ✅ |
| Páginas Adicionales | ❌ | ✅ (2 páginas) |
| Estadísticas | ❌ | ✅ |
| Exportación | ❌ | ✅ |
| Scripts de Utilidad | ⚪ Básicos | ✅ Completos |

---

## Roadmap Futuro

### v2.1.0 (Próximo)
- [ ] Panel de estadísticas de memoria vectorizada
- [ ] Exportación masiva de sesiones
- [ ] Limpieza automática de sesiones antiguas
- [ ] Filtros temporales en búsqueda

### v2.2.0
- [ ] Recomendaciones automáticas basadas en proyectos similares
- [ ] Detección de patrones recurrentes
- [ ] Sugerencias de mejora de código
- [ ] Análisis de tendencias

### v3.0.0
- [ ] Fine-tuning del modelo de embeddings
- [ ] Soporte para embeddings multimodales
- [ ] Clustering automático de proyectos
- [ ] Knowledge graph de conceptos
- [ ] API REST para integración externa

---

## Notas de Migración

### De v1.0.0 a v2.0.0

#### Requisitos Nuevos
```bash
pip install sentence-transformers numpy pgvector
```

#### Configuración Opcional (Memoria Vectorizada)
1. Configura `SUPABASE_DB_URL` en `.env`
2. Ejecuta `python init_vector_memory.py`
3. Reinicia la aplicación

#### Compatibilidad
- ✅ 100% compatible con v1.0.0
- ✅ No requiere cambios en código existente
- ✅ Funciona sin Supabase (SQLite)
- ✅ Memoria vectorizada es opcional

#### Datos Existentes
- ✅ Sesiones existentes se mantienen
- ✅ Historial se preserva
- ✅ No se pierde información

---

## Créditos

### v2.0.0
- Integración de memoria vectorizada
- Gestión de sesiones completa
- Búsqueda semántica con IA
- Nuevas páginas de Streamlit
- Documentación exhaustiva

### v1.0.0
- Arquitectura multi-agente original
- Pipeline de desarrollo
- Generación de código
- Sistema de seguridad

---

## Licencia

MIT License - Ver LICENSE para más detalles


---

## [3.0.0] - 2026-05-11

### 🚀 Rediseño del sistema de generación — Pipeline especializado

Refactor mayor para mejorar la calidad de los proyectos generados. Los
cambios se concentran en prompts especializados, quality gates, detección
de stack y validación real de código.

### ✨ Nuevos módulos

#### Sistema modular de prompts (`src/agents/prompts/`)
- **base.py** — bloques compartidos (mentalidad, antipatrones, seguridad, entrega)
- **backend.py** — prompts específicos para FastAPI, Django, Express/Fastify y Go
- **frontend.py** — prompts específicos para React+Vite, Next.js y Vue 3 con estados obligatorios
- **fullstack.py** — prompts coordinados con contratos API compartidos
- **mobile.py** — React Native + Expo con reglas de UX nativa
- **cli.py** — CLIs con UX tipo gh/kubectl
- **data.py** — pipelines de datos y ML reproducibles
- **analysis.py**, **design.py**, **testing.py**, **validation.py**, **documentation.py** — prompts mejorados con few-shot examples y formato estricto
- **selector.py** — enruta al prompt correcto según el stack detectado

Cada prompt incluye:
- Estructura obligatoria de carpetas por framework
- Few-shot examples reales (repository, service, controller, hook, página)
- Checklist de seguridad OWASP aplicado
- Lista de antipatrones prohibidos explícitos

#### Pipeline de producción (`src/orchestrator/pipeline.py`)
- Flujo 6 fases: análisis → diseño → testing (TDD) → implementación → validación → documentación
- Los tests se generan ANTES de la implementación desde criterios de aceptación
- Re-intentos automáticos con feedback del quality gate
- Validador de código real integrado con auto-corrección
- `ProgressReporter` como interfaz para UI (desacoplado de Streamlit)

#### Detector de stack (`src/orchestrator/stack_detector.py`)
- Extrae el "Contrato de Implementación" (sección 11) del diseño
- Heurística de keywords como fallback
- Produce un `StackProfile` que el selector de prompts consume

#### Quality gates (`src/orchestrator/quality_gates.py`)
- `gate_analysis` — exige IEEE 830 completo, RF/RNF/HU mínimos, criterios testables
- `gate_design` — exige secciones obligatorias, diagramas, ADRs, contrato
- `gate_implementation` — detecta archivos faltantes, TODOs, secretos hardcoded
- `gate_testing` — exige presencia de suite de tests
- Cada gate renderiza feedback accionable para auto-corrección

#### Validador de código real (`src/tools/code_validator.py`)
- Detecta lenguaje predominante y corre herramientas instaladas
- Python: `py_compile` + `ruff` (opcional)
- TypeScript/JavaScript: `tsc --noEmit`
- Go: `go vet` + `go build`
- Rust: `cargo check`
- Devuelve issues estructurados con archivo, línea y severidad
- Feedback formateado para re-pedir corrección al agente

### 🔧 Cambios en agentes existentes

- **Analysis Agent** — usa prompt con criterios de aceptación Given/When/Then testables
- **Design Agent** — exige sección 11 "CONTRATO DE IMPLEMENTACIÓN" con PROJECT_TYPE, LANGUAGE, etc.
- **Implementation Agent** — factory adaptativa que recibe un `StackProfile` y selecciona el prompt especializado
- **Validation Agent** — ya no genera tests (eso lo hace el agente de testing dedicado); solo audita
- **Testing Agent** — nuevo agente TDD que escribe tests desde criterios de aceptación
- **Documentation Agent** — produce README, ARCHITECTURE, CONTRIBUTING y PROYECTO

### 📦 Cambios en la UI (`app.py`)

- La ejecución del pipeline se delega a `run_pipeline()` en lugar de orquestar inline
- Reporter integrado con la barra de progreso y status de Streamlit
- Aprendizaje autónomo sigue funcionando, ahora usa el `PipelineResult` estructurado

### 🛡️ Mejoras de calidad

- Antipatrones prohibidos enumerados explícitamente en cada prompt
- Headers de seguridad OWASP aplicados en cada capa
- Detección de credenciales hardcoded vía quality gate
- Accesibilidad WCAG AA exigida en prompts de frontend


## [3.1.0] - 2026-05-11

### 🧠 Sistema de aprendizaje continuo con refuerzo

Rediseño profundo del aprendizaje autónomo. El sistema ya no solo guarda
insights al terminar proyectos: aprende de múltiples señales en tiempo real,
deduplicar por similitud, aplica refuerzo positivo/negativo, olvida
selectivamente y consolida clusters.

### ✨ Nuevas capacidades en `KnowledgeMemory`

- **Deduplicación semántica** — si un insight tiene similitud ≥ 0.88 con uno
  existente en la misma categoría, refuerza el existente en lugar de crear
  otro duplicado. Evita que la base de conocimiento se llene de variantes
  de la misma idea.
- **Hybrid search** — la búsqueda combina similitud vectorial (60%),
  usefulness score (25%) y recencia (15%). Los insights más probados suben,
  los olvidados bajan.
- **Feedback loop explícito** — `apply_feedback(ids, positive)` refuerza o
  penaliza insights según si el proyecto donde se usaron terminó bien.
- **Decay temporal** — `apply_temporal_decay()` reduce el score de insights
  que llevan días sin recuperarse. Simula olvido selectivo.
- **Consolidación de clusters** — `consolidate_clusters()` encuentra grupos
  de insights muy similares (≥ 0.90) y los fusiona en el canónico.
- **Archivado automático** — insights con score < 0.1 se marcan como
  archivados y dejan de aparecer en búsquedas.
- **Esquema extendido** — nuevas columnas (`reinforcement_count`,
  `last_retrieved_at`, `positive_feedback`, `negative_feedback`, `archived`,
  `source_signal`) añadidas de forma no-destructiva con ADD COLUMN IF NOT
  EXISTS.

### ✨ Nuevas capacidades en `LearningAgent`

- **Aprendizaje multi-señal** — cinco métodos especializados para aprender
  de distintas fuentes de evidencia:
  - `learn_from_project()` — al terminar un proyecto (compatible con la API anterior)
  - `learn_from_compiler_errors()` — cuando el code validator detecta errores
  - `learn_from_gate_failures()` — cuando los quality gates fallan
  - `learn_from_validation_findings()` — de hallazgos críticos del auditor
  - `learn_from_user_preferences()` — preferencias explícitas del diálogo
- **Feedback hooks** — `mark_used_insights_success()` y
  `mark_used_insights_failure()` para que el pipeline informe cómo terminaron
  los proyectos que consumieron cada insight.
- **Mantenimiento periódico** — `periodic_maintenance()` aplica decay +
  consolidación. Se ejecuta una vez por sesión automáticamente.

### 🔗 Integración en el pipeline

- `run_pipeline()` ahora acepta `learning_agent` y `prior_knowledge_ids`.
- Durante la ejecución captura feedback real: errores del compilador, gates
  fallidos y hallazgos del validador.
- Al terminar, dispara las señales de aprendizaje correspondientes y aplica
  feedback positivo/negativo a los insights que se inyectaron.

### 📊 UI mejorada

- El sidebar muestra ahora el estado de la memoria de conocimiento: total de
  insights activos/archivados, distribución por categoría, top insights por
  score y número de refuerzos.

### 🧹 Nuevas categorías de conocimiento

- `error_compilador` — patrones que el compilador rechaza
- `hallazgo_validacion` — problemas reales de auditorías de código
- `falla_quality_gate` — patrones que hacen fallar gates de calidad
- `convencion_nombres` — preferencias de naming del usuario
