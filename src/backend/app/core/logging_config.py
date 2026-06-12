# src/backend/app/core/logging_config.py
"""JSON logging to stdout, ported from the original (python-json-logger replaced by a
stdlib formatter to keep the dependency list short). ASCII-safe output only.

Deviation (documented in the phase plan): the level is configurable via LOG_LEVEL;
the original silently fixed the root level at WARNING, muting its own logger.info calls.
"""
from __future__ import annotations

import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": record.created,
            "level": record.levelname.upper(),
            "severity": record.levelname.upper(),  # original: Google Cloud Logging key
            "name": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in ("args", "msg", "exc_info", "exc_text", "stack_info", "levelname",
                       "levelno", "pathname", "filename", "module", "lineno", "funcName",
                       "created", "msecs", "relativeCreated", "thread", "threadName",
                       "processName", "process", "name", "taskName"):
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers = []
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
