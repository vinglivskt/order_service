"""Prometheus-метрики (единая точка регистрации). Экспорт — через GET /metrics в app.main."""

from prometheus_client import Counter, Gauge, Histogram

# Метрики для DLQ
DLQ_METRICS = {
    "total_messages": Counter(
        "dlq_total_messages", "Общее количество сообщений, отправленных в DLQ"
    ),
    "retry_attempts": Counter(
        "dlq_retry_attempts", "Общее количество попыток повторной отправки из DLQ"
    ),
    "failed_messages": Gauge(
        "dlq_failed_messages", "Текущее количество сообщений, находящихся в DLQ"
    ),
}

HTTP_REQUESTS_COUNT = Counter(
    "http_requests_total",
    "Общее количество HTTP-запросов",
    ["method", "path", "status"],
)
HTTP_REQUESTS_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Задержка обработки HTTP-запросов",
    ["method", "path", "status"],
)

KAFKA_PUBLISHED_TOTAL = Counter(
    "kafka_published_total",
    "Количество опубликованных сообщений в Kafka",
    ["topic"],
)
KAFKA_CONSUMED_TOTAL = Counter(
    "kafka_consumed_total",
    "Количество потребленных сообщений из Kafka",
    ["topic"],
)

OUTBOX_PENDING_EVENTS = Gauge(
    "outbox_pending_events",
    "Количество outbox-событий, ожидающих публикации (в текущем батче publisher-а)",
)

CELERY_TASK_SUCCESS_TOTAL = Counter(
    "celery_task_success_total",
    "Успешные Celery задачи",
    ["task_name"],
)
CELERY_TASK_FAILURE_TOTAL = Counter(
    "celery_task_failure_total",
    "Неуспешные Celery задачи",
    ["task_name"],
)

CACHE_HIT_TOTAL = Counter(
    "cache_hit_total",
    "Cache hits",
)
CACHE_MISS_TOTAL = Counter(
    "cache_miss_total",
    "Cache misses",
)
