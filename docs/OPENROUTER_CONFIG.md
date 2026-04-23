# Configuración de OpenRouter

## ✅ Estado Actual

Tu proyecto está **100% configurado** para usar OpenRouter con GPT-4o-mini.

---

## 🔧 Configuración Aplicada

### 1. Variables de Entorno (`.env`)

```bash
# OpenRouter
OPENAI_API_KEY=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
OPENAI_API_BASE=https://openrouter.ai/api/v1

# Modelos
LLM_PROVIDER=openai
LLM_MODEL=openai/gpt-4o-mini
ORCHESTRATOR_MODEL=openai/gpt-4o-mini
DEFAULT_MODEL=openai/gpt-4o-mini
```

### 2. Código Modificado

**`src/config/settings.py`:**
- ✅ Agregado `openai_api_base` para soportar URLs personalizadas
- ✅ Agregado `default_model` para fallback
- ✅ Modificado `get_model()` para usar `base_url` cuando hay `OPENAI_API_BASE`

**Lógica:**
```python
if cfg.openai_api_base:
    # Usar OpenRouter
    return OpenAIChat(
        id=model_id,
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_api_base
    )
```

---

## 🚀 Cómo Funciona

### Flujo de Configuración

1. **Agno lee `.env`** → Carga `OPENAI_API_KEY` y `OPENAI_API_BASE`
2. **Settings detecta OpenRouter** → Si `OPENAI_API_BASE` existe, usa OpenRouter
3. **Todos los agentes usan OpenRouter** → Análisis, Diseño, Implementación, Validación
4. **Orquestador usa OpenRouter** → El Team leader también

### Modelos Usados

| Componente | Modelo |
|------------|--------|
| Agente de Análisis | `openai/gpt-4o-mini` |
| Agente de Diseño | `openai/gpt-4o-mini` |
| Agente de Implementación | `openai/gpt-4o-mini` |
| Agente de Validación | `openai/gpt-4o-mini` |
| Orquestador (Team) | `openai/gpt-4o-mini` |

**Todos usan tu API key de OpenRouter.**

---

## 🧪 Verificar Configuración

```bash
# Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# Probar OpenRouter
python test_openrouter.py
```

Deberías ver:
```
✅ Settings cargados
✅ Modelo creado: OpenAIChat
✅ Respuesta recibida
🎉 ¡OpenRouter funciona correctamente!
```

---

## 🎯 Modelos Disponibles en OpenRouter

Puedes cambiar el modelo editando `.env`:

### Modelos Recomendados

```bash
# GPT-4o mini (rápido y económico)
LLM_MODEL=openai/gpt-4o-mini

# GPT-4o (más potente)
LLM_MODEL=openai/gpt-4o

# Claude 3.5 Sonnet (excelente para código)
LLM_MODEL=anthropic/claude-3.5-sonnet

# Llama 3.1 70B (open source potente)
LLM_MODEL=meta-llama/llama-3.1-70b-instruct

# Mixtral 8x7B (rápido y bueno)
LLM_MODEL=mistralai/mixtral-8x7b-instruct
```

### Modelos Especializados

```bash
# Para código (mejor)
LLM_MODEL=anthropic/claude-3.5-sonnet
ORCHESTRATOR_MODEL=openai/gpt-4o-mini

# Para análisis (más económico)
LLM_MODEL=openai/gpt-4o-mini
ORCHESTRATOR_MODEL=openai/gpt-4o-mini

# Para máxima calidad (más caro)
LLM_MODEL=openai/gpt-4o
ORCHESTRATOR_MODEL=openai/gpt-4o
```

---

## 💰 Costos Aproximados

| Modelo | Input (1M tokens) | Output (1M tokens) |
|--------|-------------------|-------------------|
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |
| claude-3.5-sonnet | $3.00 | $15.00 |
| llama-3.1-70b | $0.35 | $0.40 |

**Proyecto típico (análisis + diseño + código):**
- Con gpt-4o-mini: ~$0.10 - $0.50
- Con gpt-4o: ~$1.00 - $5.00
- Con claude-3.5-sonnet: ~$1.50 - $6.00

---

## 🔍 Verificar que Todo Use OpenRouter

### En la App

1. Ejecuta `streamlit run app.py`
2. En el sidebar verás: **Proveedor LLM: openai**
3. En el sidebar verás: **Modelo: openai/gpt-4o-mini**
4. Cuando converses, verás en logs: `Using OpenRouter with model: openai/gpt-4o-mini`

### En Logs

```bash
# Ejecutar con logs visibles
streamlit run app.py --logger.level=debug
```

Busca líneas como:
```
INFO:src.config.settings:Using OpenRouter with model: openai/gpt-4o-mini
```

---

## 🐛 Troubleshooting

### "Error: Invalid API key"

**Causa:** La API key de OpenRouter es incorrecta.

**Solución:**
1. Ve a https://openrouter.ai/keys
2. Copia tu API key
3. Actualiza `OPENAI_API_KEY` en `.env`

---

### "Error: Model not found"

**Causa:** El nombre del modelo es incorrecto.

**Solución:**
- Verifica el nombre en https://openrouter.ai/models
- Formato correcto: `proveedor/modelo`
- Ejemplo: `openai/gpt-4o-mini` (no `gpt-4o-mini`)

---

### "No usa OpenRouter, usa OpenAI directo"

**Causa:** Falta `OPENAI_API_BASE` en `.env`.

**Solución:**
```bash
OPENAI_API_BASE=https://openrouter.ai/api/v1
```

---

### "Respuestas muy lentas"

**Causa:** Modelo muy grande o saturación de OpenRouter.

**Solución:**
- Cambia a `openai/gpt-4o-mini` (más rápido)
- O usa `meta-llama/llama-3.1-8b-instruct` (muy rápido)

---

## 📊 Monitoreo de Uso

### En OpenRouter Dashboard

1. Ve a https://openrouter.ai/activity
2. Verás todas las llamadas en tiempo real
3. Puedes ver:
   - Tokens usados
   - Costo por llamada
   - Modelo usado
   - Latencia

### En la App

Los logs muestran:
```
INFO:agno:Running agent: Agente de Analisis
INFO:src.config.settings:Using OpenRouter with model: openai/gpt-4o-mini
```

---

## 🎛️ Configuración Avanzada

### Usar Diferentes Modelos por Agente

Edita `src/agents/*.py` y pasa el modelo específico:

```python
# En src/agents/implementation.py
def create_implementation_agent(settings: Settings, db=None) -> Agent:
    # Usar Claude para implementación (mejor para código)
    from agno.models.openai import OpenAIChat
    
    model = OpenAIChat(
        id="anthropic/claude-3.5-sonnet",
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base
    )
    
    return Agent(
        name="Agente de Implementacion",
        model=model,  # ← Modelo específico
        ...
    )
```

### Fallback a Otro Modelo

Si OpenRouter falla, puedes configurar fallback:

```python
# En src/config/settings.py
try:
    return OpenAIChat(
        id=model_id,
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_api_base
    )
except Exception as e:
    logger.warning(f"OpenRouter failed, using fallback: {e}")
    # Fallback a Ollama local
    from agno.models.ollama import Ollama
    return Ollama(id="qwen3:4b")
```

---

## ✅ Resumen

- ✅ OpenRouter está **100% configurado**
- ✅ Todos los agentes usan **tu API key**
- ✅ Modelo actual: **openai/gpt-4o-mini**
- ✅ Puedes cambiar modelos en `.env`
- ✅ Funciona con memoria vectorizada
- ✅ Funciona con gestión de sesiones

**Solo ejecuta `streamlit run app.py` y todo funcionará con OpenRouter.**
