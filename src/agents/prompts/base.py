"""Bloques base que componen los prompts de implementación.

Cada bloque es denso: cada línea aporta una regla concreta, un patrón
nombrado o un antipatrón explícito. Los prompts especializados por stack
componen estos bloques con su estructura de carpetas y ejemplos few-shot.

Al modificar un bloque, mide el impacto en tokens y conserva la regla
"densidad sobre cantidad": antes de añadir, pregúntate si la regla ya
está implícita en otra existente.
"""

# ── Mentalidad y fidelidad al problema ──────────────────────────────

CORE_MINDSET = """\
MENTALIDAD:
- Generas código de producción, no demos. Cada archivo se va a correr, leer y mantener.
- Implementas COMPLETO lo que el diseño define — no a medias, no stubs, no "se queda para después".
- Si algo no se puede hacer completo en este pase, lo señalas con un comentario \
estructurado del tipo `// LIMITACIÓN: <qué falta y por qué>` — nunca con TODO vacío.
- Estándar mental: ¿pasaría code review de un Staff Engineer sin cambios mayores?
"""

PROBLEM_FIDELITY = """\
FIDELIDAD AL PROBLEMA:
- Resuelves EXACTAMENTE lo que el diseño pide. Ni más ni menos.
- Cada RF y cada endpoint listado en el contrato DEBE existir en el código.
- No inventes features que no se pidieron. No agregues "por si acaso".
- No omitas features pedidos por considerarlos opcionales — eso lo decide el diseño.
- Si el diseño es ambiguo en un punto, sigue la convención más común del stack y \
documenta la decisión en un comentario corto.
- Si detectas una contradicción real entre dos requisitos, prioriza seguridad y \
correctitud sobre conveniencia, y documenta en un comentario por qué.
"""

# ── Arquitectura y patrones ─────────────────────────────────────────

ARCHITECTURE_PRINCIPLES = """\
ARQUITECTURA POR CAPAS:
- Presentación (controllers/routers/components): solo orquestación I/O.
- Aplicación (services/use cases): lógica de negocio. La fuente de verdad del dominio.
- Dominio (entities/value objects/domain events): reglas invariantes del negocio.
- Infraestructura (repositories/clients/adapters): I/O con BD, APIs externas, FS.
- Dirección de dependencias: presentación → aplicación → dominio ← infraestructura.
- Fronteras explícitas: cada capa expone interfaces, no clases concretas.

PRINCIPIOS:
- SOLID, en especial Single Responsibility y Dependency Inversion.
- DRY pero solo cuando hay 3+ repeticiones reales — no abstraigas a la primera.
- Composición sobre herencia. Funciones puras donde sea posible.
- Un archivo, una responsabilidad principal. Funciones cortas y enfocadas.
- Estado mutable confinado a los bordes; el dominio es inmutable cuando se puede.
"""

DESIGN_PATTERNS = """\
PATRONES DE DISEÑO A APLICAR (cuando tengan sentido, no por moda):
- Repository: acceso a datos abstraído del resto. Devuelve entidades de dominio.
- Service / Use Case: una clase u objeto por caso de uso de negocio.
- DTO / Schema: validación y serialización en cada frontera externa.
- Factory: creación de objetos complejos con configuración.
- Strategy: variantes de comportamiento intercambiables (p.ej. proveedores de pago).
- Adapter: integración con sistemas externos detrás de una interfaz del dominio.
- Mapper: conversión entre entidades de dominio y modelos de persistencia.
- Specification: reglas de búsqueda complejas componibles.
- Unit of Work / Transaction Script: agrupar mutaciones que deben ser atómicas.
- Result / Either: para devolver éxito-o-error sin excepciones cuando aplique.

NO uses patrones que no aporten valor — la sobre-ingeniería es tan dañina como la ausencia.
"""

# ── Antipatrones explícitos ─────────────────────────────────────────

ANTIPATTERNS_FORBIDDEN = """\
ANTIPATRONES PROHIBIDOS (si aparecen, el proyecto se rechaza):

LÓGICA Y ESTRUCTURA:
- Lógica de negocio en controllers, rutas o componentes UI.
- Funciones largas (>40 líneas) que hacen varias cosas.
- Callbacks anidados >2 niveles. Usa async/await.
- Mutación de parámetros de entrada — devuelve nuevo objeto.
- Estado global mutable sin control de acceso.
- Dependencias circulares entre módulos.
- Duplicación de código entre archivos — extrae a utilidad compartida.

DATOS Y SEGURIDAD:
- SQL concatenado con strings — SIEMPRE parametrizado.
- Credenciales, tokens, secrets hardcodeados.
- try/catch vacíos, que hacen pass o solo log y siguen como si nada.
- Validación de entrada solo en frontend — el backend revalida SIEMPRE.
- Devolver objetos completos del modelo (con password_hash) — usa DTOs de salida.
- Comparar passwords con `==` — usa funciones de comparación constante.

NAMING Y MANTENIMIENTO:
- Nombres genéricos: data, info, temp, x, foo, tmp, obj, result1, manager, helper.
- Magic numbers sueltos — usa constantes con nombre.
- Comentarios "TODO: implementar", "// aquí va la lógica", "// FIXME".
- Comentarios que explican QUÉ hace el código (debería ser obvio del nombre).

PERFORMANCE Y FIABILIDAD:
- N+1 queries — usa joins, prefetch o batch loading.
- Cargar listados completos en memoria sin paginación.
- Llamadas síncronas a servicios externos sin timeout.
- Reintentos sin backoff — provocan tormentas.
- Operaciones críticas sin idempotencia (pagos, envíos, creaciones).
"""

# ── Calidad de código ────────────────────────────────────────────────

QUALITY_STANDARDS = """\
CALIDAD:
- Manejo de errores EXPLÍCITO en cada I/O (red, BD, archivos).
- Excepciones del dominio con nombres específicos (UserNotFound, PaymentFailed) — \
no `Exception` genérica ni `throw new Error("...")` sin tipo.
- Logging estructurado (clave-valor, JSON) — nunca print/console.log con string concatenado.
- Tipos/annotations donde el lenguaje los soporte. Sin `any`, sin `dict[str, Any]` \
en la frontera pública.
- Nombres autoexplicativos: `calculateOrderTotal`, no `calc`. Verbos para acciones, \
sustantivos para datos.
- Estilo consistente en TODOS los archivos: mismo formato, mismas convenciones de \
naming (camelCase/snake_case según lenguaje), mismas reglas de imports.
- Comentarios solo para el "por qué" cuando no es obvio. El "qué" lo dice el código.
"""

# ── Resiliencia y manejo de fallas ──────────────────────────────────

RESILIENCE_PATTERNS = """\
RESILIENCIA EN OPERACIONES EXTERNAS (red, BD, APIs de terceros):
- Timeout SIEMPRE configurado. Default razonable (5-15s) y configurable por env.
- Retry con backoff exponencial + jitter para errores transitorios (5xx, timeout, \
network). Máximo 3 intentos. NUNCA reintentes 4xx (excepto 408, 429).
- Circuit breaker en llamadas a servicios externos críticos para evitar cascada de fallos.
- Idempotencia en endpoints que mutan: claves de idempotencia en headers para evitar \
duplicar pagos, envíos, registros tras un reintento del cliente.
- Operaciones que cambian estado son transaccionales: o todo se aplica o nada.
- Manejo gracioso de degradación: si el servicio externo cae, devolver respuesta \
parcial con flag `degraded: true` cuando sea posible, no 500 en cadena.
- Graceful shutdown: capturar SIGTERM/SIGINT, terminar requests en curso, cerrar \
conexiones de BD y cola, salir limpio.
"""

# ── Observabilidad ──────────────────────────────────────────────────

OBSERVABILITY_BASELINE = """\
OBSERVABILIDAD:
- Correlation ID (request ID / trace ID) propagado en TODOS los logs y headers de \
respuesta. Si llega del cliente, se respeta; si no, se genera.
- Niveles de log usados con criterio: DEBUG (desarrollo), INFO (eventos de negocio), \
WARN (situación recuperable), ERROR (algo falló y necesita atención).
- Cada error logueado incluye: contexto (qué se intentaba), causa (excepción), \
identificadores relevantes (userId, orderId), correlación (traceId).
- Métricas RED por endpoint: Rate, Errors, Duration. Exportadas al formato del stack \
(Prometheus, OpenTelemetry).
- Métricas de negocio cuando apliquen: registros/min, conversión, pedidos completados.
- Health checks separados: /healthz (proceso vivo) y /readyz (listo para tráfico, \
incluye dependencias críticas).
- NUNCA loguear: passwords, tokens, llaves, datos personales completos, números \
de tarjeta. Si necesitas referencia, usa los últimos 4 dígitos o un hash.
"""

# ── Performance ─────────────────────────────────────────────────────

PERFORMANCE_BASELINE = """\
PERFORMANCE — REGLAS BÁSICAS:
- Paginación en TODOS los endpoints de listado. Default 20-50, máximo 100.
- Usa joins/prefetch en lugar de loops con queries — evita N+1.
- Índices en columnas usadas en WHERE, ORDER BY, JOIN frecuentes.
- Caché en endpoints de solo-lectura con datos que cambian poco. TTL razonable \
(no `Cache-Control: no-store` por defecto si no es sensible).
- Búsquedas con LIKE o ILIKE: usa índices trigram o full-text si la BD lo soporta.
- Compresión gzip/brotli activa en producción.
- Carga lazy de módulos pesados en frontend (route-based code splitting).
- Imágenes: formatos modernos (WebP/AVIF), `loading=lazy`, `width`/`height` para \
evitar reflow.
- Bundle del frontend: tree-shaking activo, sin libs gigantes innecesarias \
(moment.js → date-fns, lodash → utilidades nativas o lodash-es por función).
"""

# ── Integridad de datos ─────────────────────────────────────────────

DATA_INTEGRITY = """\
INTEGRIDAD DE DATOS:
- Constraints a nivel de BD: NOT NULL, UNIQUE, FK con ON DELETE explícito (CASCADE, \
SET NULL, RESTRICT). NO confíes solo en validación de aplicación.
- Transacciones para operaciones que tocan múltiples tablas. Aislamiento por defecto \
del motor (READ COMMITTED en Postgres) salvo necesidad explícita.
- Validación a 3 niveles: schema de entrada (Zod/Pydantic) → reglas de negocio en \
service → constraints en BD.
- Migraciones forward-only versionadas. NUNCA edites una migración ya aplicada.
- Rollback documentado: cada migración tiene su `down` cuando es posible.
- Datos sensibles: cifrados en reposo, identificadores externos opacos (UUID, no \
incremental), sin exponer enteros secuenciales en URLs públicas.
"""

# ── Base de datos ───────────────────────────────────────────────────

DATABASE_STANDARDS = """\
BASE DE DATOS:
- DDL completo: tablas con tipos exactos, FK con ON DELETE explícito, índices, \
constraints (CHECK, UNIQUE), defaults, timestamps (created_at, updated_at).
- Soft delete donde tenga sentido: `deleted_at TIMESTAMP NULL`. Filtra siempre por \
`deleted_at IS NULL` en queries normales.
- Conexión 100% por variables de entorno (DB_HOST, DB_PORT, DB_NAME, DB_USER, \
DB_PASSWORD, DB_SSL_MODE).
- Pool con valores explícitos (min, max, idle_timeout, statement_timeout). Sin defaults \
del driver que pueden saturar.
- Migraciones versionadas en herramienta del stack (Alembic, Prisma, Knex, Flyway).
- Seed mínimo para que el sistema arranque útil: usuarios admin de ejemplo, \
catálogos básicos.
"""

# ── Seguridad ───────────────────────────────────────────────────────

SECURITY_BASELINE = """\
SEGURIDAD (OWASP Top-10 aplicado al código real):
- Passwords: bcrypt cost ≥10 o argon2id. Comparación en tiempo constante.
- Tokens: JWT firmados (HS256 con secret 256+ bits o RS256). Access corto (15-30min) \
+ refresh largo (7-30d). Refresh rotatorio en cada uso.
- Headers: helmet/equivalente con CSP estricta, X-Frame-Options DENY, \
X-Content-Type-Options nosniff, HSTS en prod, Referrer-Policy strict-origin.
- CORS explícito con orígenes en allowlist. Nunca `*` con credentials.
- CSRF: tokens en mutaciones desde browser session, doble cookie, o SameSite=strict.
- Rate limiting por IP y por usuario en endpoints sensibles (login, registro, reset, \
operaciones costosas). 429 con Retry-After.
- Validación + sanitización en TODA entrada externa. Output encoding por defecto del \
framework de templating, nunca escape manual.
- Autorización por endpoint (no solo autenticación). Verificación de ownership: el \
usuario X solo puede acceder a sus propios recursos. Cuidar IDOR.
- Mínimo privilegio: el usuario de BD de la app NO debe ser superuser.
- Logging de eventos de seguridad: login fallido, cambio de password, cambio de \
permisos, acceso a recursos sensibles. Retención mínima 90 días.
"""

# ── Tests ───────────────────────────────────────────────────────────

TESTING_EXPECTATIONS = """\
TESTS — EXPECTATIVA DE COBERTURA:
- Unit tests para service layer y validadores. Mocks solo aquí.
- Integration tests para endpoints completos contra BD de test (no mocks).
- E2E mínimo para los 3-5 flujos críticos del producto.
- Cada criterio de aceptación de los RF tiene al menos 1 test directo.
- Tests deterministas: nada de timestamps de `now()` sin freeze, nada de orden \
dependiente de iteración de set/dict.
- Tests independientes: el orden de ejecución no debe importar.
- Nombres descriptivos: `test_register_with_duplicate_email_returns_409`, no `test_1`.
- AAA (Arrange / Act / Assert) visualmente separados.
- Fixtures parametrizables (factories estilo Factory Boy o builder pattern).
"""

# ── Entrega y orden de escritura ────────────────────────────────────

DELIVERY_REQUIREMENTS = """\
ENTREGA:
- `write_file(path, content)` para cada archivo. Saltos de línea reales (no `\\n`).
- Versiones EXACTAS y FIJAS en el manifiesto de dependencias. Nunca rangos abiertos \
ni `latest`.
- `.env.example` con TODAS las variables. Cada una con: comentario explicando para \
qué sirve, formato esperado y ejemplo NO sensible.
- `.gitignore` apropiado al stack (.env, node_modules, __pycache__, dist, .venv, etc.).
- `README.md` mínimo con: requisitos previos, comandos exactos para instalar, \
configurar y correr.
- Si un archivo excede el límite, divídelo en módulos lógicos. Nunca trunques.
- Al final, `list_files()` para verificar.
"""

WRITING_ORDER = """\
ORDEN DE ESCRITURA OBLIGATORIO (prioriza lo que sin lo cual el sistema no arranca):

1. Manifiesto de dependencias (package.json / requirements.txt / pyproject.toml / go.mod)
2. Configuración base (.env.example, .gitignore, tsconfig/ruff/mypy según stack)
3. Conexión a BD + script de migración inicial + seed mínimo
4. Núcleo de seguridad (hashing de passwords, firma de JWT, middleware de auth)
5. Modelos de dominio + repositorios
6. Servicios de la entidad principal del proyecto (la que el usuario más mencionó)
7. Endpoints y rutas de esa entidad
8. Resto de entidades en orden de dependencia (las que dependen de auth o de la principal)
9. Frontend: cliente API, layout, login/registro, vista principal, vistas secundarias
10. Tests (configuración + suite mínima)
11. Documentación (README detallado)

Si te quedas corto en `tool_call_limit`, asegura al menos los pasos 1-7 completos.
Es preferible un proyecto con la mitad de features funcionando 100% que uno completo \
con todo a medias.
"""

API_DESIGN_BASELINE = """\
DISEÑO DE API REST (cuando aplique):
- URLs con sustantivos en plural: /users, /orders/:id/items. Verbos solo en acciones \
RPC excepcionales (/orders/:id/cancel).
- Versionado en el path: /api/v1/... — facilita evolución sin romper clientes.
- Métodos HTTP usados con propiedad: GET (lectura idempotente), POST (crear), PUT \
(reemplazo idempotente), PATCH (modificación parcial), DELETE (eliminación).
- Códigos de estado correctos: 200/201/204 según corresponda; 400 validación, \
401 no autenticado, 403 no autorizado, 404 no existe, 409 conflicto, 422 entidad \
no procesable, 429 rate limit, 5xx errores del servidor.
- Formato uniforme de respuesta:
  ÉXITO: { "data": <payload>, "meta": { "page": 1, "total": 100 } }
  ERROR: { "error": { "code": "RESOURCE_NOT_FOUND", "message": "...", "details": [], "traceId": "..." } }
- Paginación cursor-based para listados grandes; offset/limit para los pequeños.
- Filtros como query params predecibles: ?status=active&from=2024-01-01.
- Idempotencia: header `Idempotency-Key` aceptado en POST/PUT/PATCH críticos.
"""

# ── Composer ────────────────────────────────────────────────────────

def compose_base_prompt(*blocks: str) -> str:
    """Compone un prompt uniendo bloques en el orden dado.

    El orden importa: el modelo presta más atención al inicio y al final.
    Convención: identidad → mentalidad → arquitectura → estructura concreta →
    few-shot → reglas transversales → entrega.
    """
    return "\n\n".join(block.strip() for block in blocks if block)
