import uvicorn
from fastapi import FastAPI
from prometheus_client import Counter, Gauge, generate_latest

app = FastAPI()

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


@app.get("/metrics")
async def metrics():
    """Экспортировать метрики Prometheus."""
    return generate_latest()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
