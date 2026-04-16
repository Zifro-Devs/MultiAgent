# DevTeam AI — Multi-Agent Software Development Platform

A production-grade multi-agent system that replicates a complete software development team.  Built with **[Agno](https://docs.agno.com/)** and **Python 3.12+**.

---

## Architecture

```
         ┌──────────────┐
         │   Streamlit   │  ← User Interface
         │    (Chat)     │
         └──────┬───────┘
                │
         ┌──────▼───────┐
         │  Orchestrator │  ← Team Leader (coordinates pipeline)
         │  (Agno Team)  │
         └──┬──┬──┬──┬──┘
            │  │  │  │
   ┌────────┘  │  │  └────────┐
   ▼           ▼  ▼           ▼
┌──────┐  ┌──────┐ ┌──────┐ ┌──────┐
│Analy-│  │Desi- │ │Imple-│ │Valid-│
│sis   │  │gn    │ │ment  │ │ation │
│Agent │  │Agent │ │Agent │ │Agent │
└──────┘  └──────┘ └──┬───┘ └──┬───┘
                      │        │
                      ▼        ▼
                  ┌──────────────┐
                  │  Artifacts   │  ← Generated source code
                  │  (Local FS)  │
                  └──────────────┘
                        │
              ┌─────────▼─────────┐
              │  Supabase / SQLite │  ← Sessions, memory, traces
              └───────────────────┘
```

### Agent Roles

| Agent | Role | Output |
|-------|------|--------|
| **Analysis Agent** | Senior Requirements Analyst | Requirements Specification Document |
| **Design Agent** | Senior Software Architect | Architecture & Design Document |
| **Implementation Agent** | Senior Software Engineer | Production source code (files) |
| **Validation Agent** | Senior QA Engineer & Security Auditor | Validation Report + Unit Tests |

### Pipeline

```
User Request → Analysis → Design → Implementation → Validation → Final Delivery
```

The **Orchestrator** (Agno `Team` with `TeamMode.coordinate`) ensures the strict sequential pipeline while sharing context across all phases.

---

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Ollama** installed locally
- `qwen3:4b` model available locally (`ollama pull qwen3:4b`)
- **(Optional)** Supabase account for vector memory and production database

### Setup (Windows)

```powershell
cd MultiAgentesApp

# Automated setup
.\setup.ps1

# Ensure Ollama is running
ollama serve

# Activate & launch
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

### Setup (Manual)

```bash
python -m venv .venv

# Windows:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt

cp .env.example .env
# Edit .env (defaults to Ollama + qwen3:4b)

streamlit run app.py
```

---

## Configuration

All settings via environment variables or `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | — |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `GOOGLE_API_KEY` | Google API key | — |
| `LLM_PROVIDER` | `ollama`, `openai`, `anthropic`, or `google` | `ollama` |
| `LLM_MODEL` | Model ID for agents | `qwen3:4b` |
| `ORCHESTRATOR_MODEL` | Model ID for the orchestrator | `qwen3:4b` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `SUPABASE_DB_URL` | Supabase PostgreSQL URL | — (SQLite) |
| `ARTIFACTS_DIR` | Output directory | `artifacts` |
| `DEBUG` | Enable debug logging | `false` |

### Supabase (Production)

Set `SUPABASE_DB_URL` in `.env`:

```
SUPABASE_DB_URL=postgresql+psycopg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

Then initialize vector memory tables:

```bash
python init_vector_memory.py
```

Without it, the system automatically uses a local SQLite database — zero config needed for development.

**New Features with Supabase:**
- 🧠 **Vector Memory** - Semantic search across conversations, requirements, designs, and code
- 🔍 **Smart Search** - Find similar projects using AI embeddings
- 📊 **Session Management** - Full session history and analytics
- 💾 **Production Ready** - Multi-user support with persistent storage

---

## Project Structure

```
MultiAgentesApp/
├── app.py                          # Streamlit UI entry point
├── pages/                          # Streamlit pages
│   ├── 1_📚_Sesiones.py            # Session management UI
│   └── 2_🔍_Búsqueda_Semántica.py  # Semantic search UI
├── init_vector_memory.py           # Vector memory initialization script
├── setup.ps1                       # Automated Windows setup
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── src/
│   ├── config/
│   │   └── settings.py             # Pydantic-settings config & model factory
│   ├── agents/
│   │   ├── analysis.py             # Requirements Analysis Agent
│   │   ├── design.py               # System Design Agent
│   │   ├── implementation.py       # Code Implementation Agent
│   │   └── validation.py           # QA & Security Validation Agent
│   ├── orchestrator/
│   │   └── team.py                 # Agno Team assembly & pipeline
│   ├── storage/
│   │   ├── database.py             # Supabase/SQLite adapter
│   │   ├── session_manager.py      # Session management (NEW)
│   │   ├── vector_memory.py        # Vector embeddings with pgvector (NEW)
│   │   ├── memory_integration.py   # Memory integration layer (NEW)
│   │   └── artifact_monitor.py     # Artifact monitoring (NEW)
│   └── tools/
│       └── artifact_tools.py       # Sandboxed file I/O toolkit
├── artifacts/                      # Generated project files (gitignored)
├── data/                           # Local SQLite DB (auto-created)
├── docs/
│   ├── MEMORIA_Y_PERSISTENCIA.md   # Memory & persistence guide
│   └── INTEGRACION_MEMORIA.md      # Integration documentation (NEW)
└── tests/
    └── test_pipeline.py            # Unit & integration tests
```

---

## Features

### Core Pipeline
- **Conversational Discovery** — Guides users through project requirements with clarifying questions
- **4-Phase Development** — Analysis → Design → Implementation → Validation
- **Real Code Generation** — Produces actual, runnable source code files
- **Security-First** — OWASP-aware validation and sandboxed file operations
- **Multi-LLM Support** — Works with OpenAI, Anthropic, Google, or local Ollama

### Memory & Persistence (NEW)
- **Session Management** — Continue conversations across sessions
- **Vector Memory** — Semantic search using AI embeddings (pgvector)
- **Smart Search** — Find similar projects, requirements, designs, and code
- **Automatic Indexing** — All conversations and artifacts indexed automatically
- **Session Analytics** — View statistics and activity graphs

### User Interface
- **Main Chat** — Interactive conversation with the development team
- **Session Manager** — Browse, continue, export, or delete previous sessions
- **Semantic Search** — AI-powered search across all your projects
- **Artifact Viewer** — Preview generated code directly in the UI

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --tb=short
```

Tests include:
- Configuration loading
- Artifact tools security (path traversal blocking)
- Artifact tools functionality (read/write/list)
- Database adapter fallback
- Team assembly (requires API key)

---

## Security

- **Sandboxed I/O** — All file operations confined to `artifacts/` with path-traversal protection.
- **No hardcoded secrets** — Everything via environment variables / `.env`.
- **OWASP-aware agents** — Prompts enforce OWASP Top-10 compliance in generated code.
- **Input validation** — System boundaries validate all external input.
- **Least privilege** — Each agent has only the tools it needs.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | Agno 2.5+ | Multi-agent orchestration runtime |
| **Frontend** | Streamlit | Interactive chat UI |
| **LLM** | OpenAI / Anthropic / Google | AI reasoning & code generation |
| **Database** | Supabase (PostgreSQL) / SQLite | Session & memory persistence |
| **Config** | pydantic-settings | Type-safe configuration |
| **Testing** | pytest | Automated test suite |

---

## License

MIT
