import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.log_context import get_context, set_service


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ctx = get_context()
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": ctx.get("service") or record.name,
            "request_id": ctx.get("request_id"),
            "correlation_id": ctx.get("correlation_id"),
            "event_id": ctx.get("event_id"),
            "order_id": ctx.get("order_id"),
            "user_id": ctx.get("user_id"),
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Добавим любые extra-поля, если они пришли в record.__dict__
        # (например, из logger.warning(..., extra={...})).
        reserved = set(payload.keys()) | {"args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName", "levelname",
                                         "levelno", "lineno", "module", "msecs", "message", "msg", "name", "pathname", "process", "processName",
                                         "relativeCreated", "root", "request_id", "correlation_id", "event_id", "order_id", "user_id", "service", "thread",
                                         "threadName", "taskName"}
        for k, v in record.__dict__.items():
            if k in reserved or k.startswith("_"):
                continue
            if k not in payload:
                payload[k] = v

        return json.dumps(payload, ensure_ascii=False)


def setup_structured_logging(*, service: str, level: int = logging.INFO) -> None:
    set_service(service)

    root = logging.getLogger()
    root.setLevel(level)

    if not any(isinstance(h.formatter, JsonLogFormatter) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        root.addHandler(handler)

