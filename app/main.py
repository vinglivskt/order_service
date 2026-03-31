import asyncio
from contextlib import asynccontextmanager, suppress
import time
import uuid

from fastapi.responses import Response

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import from_url as redis_from_url
from sqlalchemy import text
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.auth import router as auth_router
from app.api.orders import router as orders_router
from app.core.config import settings
from app.core.monitoring import (
    DLQ_METRICS,  # noqa: F401
    HTTP_REQUESTS_COUNT,
    HTTP_REQUESTS_LATENCY,
)
from app.core.rate_limit import limiter
from app.core.log_context import clear_context, ensure_uuid_str, set_request_context
from app.core.structured_logging import setup_structured_logging
from app.db.session import AsyncSessionLocal
from app.messaging.outbox_publisher import OutboxPublisherService
from app.messaging.producer import KafkaProducerService


setup_structured_logging(service="api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis_from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    kafka_producer = KafkaProducerService()
    await kafka_producer.start()
    app.state.kafka_producer = kafka_producer
    outbox_task: asyncio.Task | None = None

    if settings.ENABLE_OUTBOX_PUBLISHER:
        outbox_publisher = OutboxPublisherService(kafka_producer)
        outbox_task = asyncio.create_task(outbox_publisher.run())

    yield

    if outbox_task:
        outbox_task.cancel()
        with suppress(asyncio.CancelledError):
            await outbox_task

    await kafka_producer.stop()
    await app.state.redis.close()


app = FastAPI(
    title="Order Service",
    version="1.0.0",
    default_response_class=JSONResponse,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    start = time.perf_counter()
    raw_request_id = request.headers.get("X-Request-Id")
    raw_correlation_id = request.headers.get("X-Correlation-Id")
    request_id = ensure_uuid_str(raw_request_id) or str(uuid.uuid4())
    correlation_id = ensure_uuid_str(raw_correlation_id) or request_id

    set_request_context(request_id=request_id, correlation_id=correlation_id)

    status_code = 500
    try:
        response: Response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-Id"] = request_id
        return response
    finally:
        latency = time.perf_counter() - start
        status_label = str(status_code)
        HTTP_REQUESTS_COUNT.labels(
            method=request.method, path=request.url.path, status=status_label
        ).inc()
        HTTP_REQUESTS_LATENCY.labels(
            method=request.method, path=request.url.path, status=status_label
        ).observe(latency)
        clear_context()


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Обработчик ошибки RateLimitExceeded."""

    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@app.get("/liveness", tags=["health"])
async def liveness():
    """Liveness: процесс жив."""
    return {"status": "ok"}


async def _is_kafka_ready(app: FastAPI) -> bool:
    kafka_prod = getattr(app.state, "kafka_producer", None)
    return kafka_prod is not None and getattr(kafka_prod, "_producer", None) is not None


@app.get("/readiness", tags=["health"])
async def readiness(request: Request):
    """Readiness: Postgres/Redis/Kafka доступны."""
    postgres_ok = False
    redis_ok = False
    kafka_ok = False

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception:
        postgres_ok = False

    try:
        redis_ok = bool(await request.app.state.redis.ping())
    except Exception:
        redis_ok = False

    try:
        kafka_ok = await _is_kafka_ready(request.app)
    except Exception:
        kafka_ok = False

    ok = postgres_ok and redis_ok and kafka_ok
    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ok" if ok else "not_ready",
            "postgres": postgres_ok,
            "redis": redis_ok,
            "kafka": kafka_ok,
        },
    )


@app.get("/health", tags=["health"])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def health(request: Request):
    """Health: общий статус (liveness + readiness)."""
    return await readiness(request)


@app.get("/metrics")
async def metrics():
    """Экспортировать метрики Prometheus."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(auth_router)
app.include_router(orders_router)
