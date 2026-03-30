import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import from_url as redis_from_url
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.auth import router as auth_router
from app.api.orders import router as orders_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.messaging.outbox_publisher import OutboxPublisherService
from app.messaging.producer import KafkaProducerService


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


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Обработчик ошибки RateLimitExceeded."""

    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@app.get("/health", tags=["health"])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def health(request: Request):
    """Проверка работоспособности сервиса."""

    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(orders_router)
