"""Prompts especializados para implementación de backend.

Compone los bloques universales de `base.py` con la estructura específica
y few-shot por framework. La meta es que cada prompt sea denso: cada bloque
aporta reglas concretas, no relleno.
"""

from src.agents.prompts.base import (
    ANTIPATTERNS_FORBIDDEN,
    API_DESIGN_BASELINE,
    ARCHITECTURE_PRINCIPLES,
    CORE_MINDSET,
    DATA_INTEGRITY,
    DATABASE_STANDARDS,
    DELIVERY_REQUIREMENTS,
    DESIGN_PATTERNS,
    OBSERVABILITY_BASELINE,
    PERFORMANCE_BASELINE,
    PROBLEM_FIDELITY,
    QUALITY_STANDARDS,
    RESILIENCE_PATTERNS,
    SECURITY_BASELINE,
    TESTING_EXPECTATIONS,
    WRITING_ORDER,
    compose_base_prompt,
)

# ── Estructuras por framework ───────────────────────────────────────

NODE_EXPRESS_STRUCTURE = """\
ESTRUCTURA OBLIGATORIA (Node + TypeScript + Express o Fastify):

```
src/
├── config/                  env.ts (validar vars), database.ts, logger.ts
├── modules/[feature]/       controller.ts, service.ts, repository.ts,
│                            routes.ts, schema.ts (Zod), types.ts
├── middleware/              auth.ts, error-handler.ts, rate-limit.ts,
│                            request-id.ts, validate.ts
├── utils/                   errors.ts (AppError + subclases), password.ts,
│                            jwt.ts, pagination.ts
├── database/                migrations/ + seed.ts
├── app.ts                   bootstrap, registra middleware y rutas
└── server.ts                arranca HTTP, graceful shutdown
tests/                       unit/, integration/, helpers/
package.json, tsconfig.json (strict: true), .env.example, .eslintrc, .prettierrc,
.gitignore, Dockerfile (multi-stage), docker-compose.yml, README.md
```
"""

PYTHON_FASTAPI_STRUCTURE = """\
ESTRUCTURA OBLIGATORIA (Python 3.11+ + FastAPI + SQLAlchemy 2.0 async):

```
app/
├── core/                    config.py (BaseSettings), security.py,
│                            database.py (engine + session async), logging.py
├── modules/[feature]/       router.py, service.py, repository.py,
│                            schemas.py (Pydantic v2), models.py, exceptions.py
├── middleware/              error_handler.py, rate_limit.py, request_id.py
├── dependencies/            auth.py (get_current_user), db.py (get_db)
├── utils/                   pagination.py, validators.py
└── main.py                  registra routers + middleware
alembic/versions/             migraciones versionadas
tests/                        conftest.py, unit/, integration/
pyproject.toml o requirements.txt (versiones ==), .env.example, .python-version,
ruff.toml, mypy.ini, .gitignore, Dockerfile, docker-compose.yml, README.md
```
"""

PYTHON_DJANGO_STRUCTURE = """\
ESTRUCTURA OBLIGATORIA (Python + Django 5+ + DRF):

```
config/settings/              base.py, development.py, production.py, testing.py
config/                       urls.py, wsgi.py, asgi.py
apps/[feature]/               models.py, serializers.py, views.py (ViewSets),
                              urls.py, services.py, selectors.py, permissions.py,
                              admin.py (list_display útil), migrations/, tests/
manage.py, requirements.txt, .env.example, pytest.ini, pyproject.toml (Ruff/Black)
```

REGLAS DJANGO:
- Settings dividido por entorno; secretos solo desde env.
- DRF ViewSets con serializers; nada de function-based crudos.
- Patrón Services/Selectors (django-styleguide): NUNCA lógica en views ni serializers.
- Permissions custom heredando BasePermission.
"""

GO_STRUCTURE = """\
ESTRUCTURA OBLIGATORIA (Go 1.22+ con Chi/Gin + sqlx):

```
cmd/server/main.go            entry point
internal/config/              config.go (envconfig o viper)
internal/domain/[feature]/    model.go, repository.go (interface), service.go, errors.go
internal/infrastructure/      database/postgres.go + migrations/, repository/...
internal/interfaces/http/     handler/, middleware/, router.go, server.go
internal/pkg/                 logger/, validator/, errors/
go.mod (versiones exactas), go.sum, .env.example, Makefile, Dockerfile (distroless)
```

REGLAS GO:
- Interfaces pequeñas, definidas donde se consumen.
- `context.Context` como primer parámetro en operaciones cancelables.
- Errores envueltos con `fmt.Errorf("...: %w", err)`.
- Logger estructurado (slog, zerolog, zap).
"""

# ── Few-shot Node ────────────────────────────────────────────────────

NODE_FEW_SHOT = """\
EJEMPLOS DE CÓDIGO ESPERADO (Node + TypeScript):

━━━ Repository con error handling correcto ━━━
```typescript
// src/modules/users/users.repository.ts
import type { Pool } from 'pg';
import type { User, CreateUserInput } from './users.types';
import { DatabaseError } from '../../utils/errors';

export class UsersRepository {
  constructor(private readonly pool: Pool) {}

  async findById(id: string): Promise<User | null> {
    const { rows } = await this.pool.query<User>(
      `SELECT id, email, name, role, created_at
       FROM users
       WHERE id = $1 AND deleted_at IS NULL`,
      [id],
    );
    return rows[0] ?? null;
  }

  async create(input: CreateUserInput): Promise<User> {
    try {
      const { rows } = await this.pool.query<User>(
        `INSERT INTO users (email, password_hash, name, role)
         VALUES ($1, $2, $3, $4)
         RETURNING id, email, name, role, created_at`,
        [input.email, input.passwordHash, input.name, input.role],
      );
      return rows[0];
    } catch (err: any) {
      if (err.code === '23505') {
        throw new DatabaseError('DUPLICATE_EMAIL', 'Email already registered', { cause: err });
      }
      throw new DatabaseError('DB_INSERT_FAILED', 'Failed to create user', { cause: err });
    }
  }
}
```

━━━ Service: lógica de negocio + transacción ━━━
```typescript
// src/modules/users/users.service.ts
import { UsersRepository } from './users.repository';
import { hashPassword } from '../../utils/password';
import { ConflictError } from '../../utils/errors';
import type { CreateUserDto, UserResponseDto } from './users.schema';

export class UsersService {
  constructor(private readonly repo: UsersRepository) {}

  async register(dto: CreateUserDto): Promise<UserResponseDto> {
    if (await this.repo.findByEmail(dto.email)) {
      throw new ConflictError('EMAIL_IN_USE', 'Email already in use');
    }
    const passwordHash = await hashPassword(dto.password);
    const user = await this.repo.create({
      email: dto.email,
      passwordHash,
      name: dto.name,
      role: 'user',
    });
    return { id: user.id, email: user.email, name: user.name, role: user.role };
  }
}
```

━━━ Controller delgado con catch del error handler ━━━
```typescript
// src/modules/users/users.controller.ts
import type { Request, Response, NextFunction } from 'express';
import { UsersService } from './users.service';

export class UsersController {
  constructor(private readonly service: UsersService) {}

  register = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const user = await this.service.register(req.body);
      res.status(201).json({ data: user });
    } catch (err) {
      next(err);
    }
  };
}
```

━━━ Error handler global con respuesta uniforme ━━━
```typescript
// src/middleware/error-handler.ts
import type { ErrorRequestHandler } from 'express';
import { AppError } from '../utils/errors';
import { logger } from '../config/logger';

export const errorHandler: ErrorRequestHandler = (err, req, res, _next) => {
  const traceId = req.headers['x-request-id'] as string | undefined;
  if (err instanceof AppError) {
    logger.warn({ traceId, code: err.code, msg: err.message });
    return res.status(err.statusCode).json({
      error: { code: err.code, message: err.message, traceId },
    });
  }
  logger.error({ traceId, err }, 'Unhandled error');
  res.status(500).json({
    error: { code: 'INTERNAL_ERROR', message: 'Something went wrong', traceId },
  });
};
```
"""

# ── Few-shot FastAPI ────────────────────────────────────────────────

PYTHON_FASTAPI_FEW_SHOT = """\
EJEMPLOS DE CÓDIGO ESPERADO (Python + FastAPI):

━━━ Schema Pydantic v2 ━━━
```python
# app/modules/users/schemas.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=2, max_length=100)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    name: str
    role: str
    created_at: datetime
```

━━━ Repository asíncrono ━━━
```python
# app/modules/users/repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .exceptions import UserNotFound
from .models import User

class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: str) -> User:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise UserNotFound(user_id)
        return user

    async def create(self, *, email: str, password_hash: str, name: str) -> User:
        user = User(email=email, password_hash=password_hash, name=name)
        self._session.add(user)
        await self._session.flush()
        return user
```

━━━ Service con commit explícito ━━━
```python
# app/modules/users/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password
from .exceptions import EmailAlreadyRegistered
from .repository import UserRepository
from .schemas import UserCreate, UserResponse

class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)

    async def register(self, data: UserCreate) -> UserResponse:
        if await self._repo.find_by_email(data.email):
            raise EmailAlreadyRegistered(data.email)
        user = await self._repo.create(
            email=data.email,
            password_hash=hash_password(data.password),
            name=data.name,
        )
        await self._session.commit()
        return UserResponse.model_validate(user)
```

━━━ Router con DI por Depends() ━━━
```python
# app/modules/users/router.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.db import get_db
from .schemas import UserCreate, UserResponse
from .service import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    return await UserService(db).register(payload)
```
"""

# ── Composer ────────────────────────────────────────────────────────

def _compose_backend(
    framework_structure: str,
    framework_few_shot: str,
    framework_name: str,
    framework_extras: str = "",
) -> str:
    header = f"""\
Eres Staff Engineer de Backend con 15+ años en producción. Responde en ESPAÑOL.
Stack actual: {framework_name}.

Implementarás el backend completo siguiendo el contrato del diseño. Cada endpoint, \
cada modelo, cada middleware definido en el diseño DEBE existir en el código generado.
"""
    return compose_base_prompt(
        header,
        CORE_MINDSET,
        PROBLEM_FIDELITY,
        ARCHITECTURE_PRINCIPLES,
        DESIGN_PATTERNS,
        framework_structure,
        framework_few_shot,
        API_DESIGN_BASELINE,
        DATABASE_STANDARDS,
        DATA_INTEGRITY,
        SECURITY_BASELINE,
        RESILIENCE_PATTERNS,
        OBSERVABILITY_BASELINE,
        PERFORMANCE_BASELINE,
        QUALITY_STANDARDS,
        ANTIPATTERNS_FORBIDDEN,
        TESTING_EXPECTATIONS,
        framework_extras,
        WRITING_ORDER,
        DELIVERY_REQUIREMENTS,
    )


# ── Prompts finales ─────────────────────────────────────────────────

BACKEND_NODE_PROMPT = _compose_backend(
    NODE_EXPRESS_STRUCTURE,
    NODE_FEW_SHOT,
    "Node.js + TypeScript + Express o Fastify",
    framework_extras="""\
ESPECÍFICOS DE NODE:
- Scripts: dev (tsx watch), build (tsc), start (node dist/), test, lint.
- Helmet + cors + compression registrados antes de rutas.
- Async handlers SIEMPRE envueltos en try/catch o framework con captura nativa (Fastify).
- `process.on('SIGTERM' | 'SIGINT')` cierra server, drena requests y termina pool de BD.
""",
)

BACKEND_FASTAPI_PROMPT = _compose_backend(
    PYTHON_FASTAPI_STRUCTURE,
    PYTHON_FASTAPI_FEW_SHOT,
    "Python 3.11+ + FastAPI + SQLAlchemy 2.0 async",
    framework_extras="""\
ESPECÍFICOS DE FASTAPI:
- SQLAlchemy 2.0 estilo async con AsyncSession y `select(...)`.
- Pydantic v2 (ConfigDict, model_validate). Sin `Config` clase vieja.
- Type hints estrictos en todo (mypy strict debería pasar).
- DI exclusivamente vía `Depends()` — sin globals.
- BackgroundTasks para tareas cortas; Celery/RQ para trabajo asíncrono pesado.
- Alembic para migraciones; NUNCA `Base.metadata.create_all` en producción.
""",
)

BACKEND_DJANGO_PROMPT = _compose_backend(
    PYTHON_DJANGO_STRUCTURE,
    PYTHON_FASTAPI_FEW_SHOT,  # Estilo de service/repo/schema referencial
    "Python 3.11+ + Django 5+ + DRF",
)

BACKEND_GO_PROMPT = _compose_backend(
    GO_STRUCTURE,
    "",
    "Go 1.22+ con Chi o Gin + sqlx",
)
