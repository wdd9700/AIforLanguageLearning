"""Prometheus 指标收集占位"""

from __future__ import annotations

from typing import Any

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class PrometheusMetricsCollector:
    """Prometheus 指标收集器"""

    def __init__(self) -> None:
        self._request_count: Any | None = None
        self._request_latency: Any | None = None
        self._error_count: Any | None = None
        if PROMETHEUS_AVAILABLE:
            self._request_count = Counter(
                "http_requests_total",
                "Total HTTP requests",
                ["method", "path", "status"],
            )
            self._request_latency = Histogram(
                "http_request_duration_ms",
                "HTTP request latency in ms",
                ["method", "path"],
            )
            self._error_count = Counter(
                "http_errors_total",
                "Total HTTP errors",
                ["error_type"],
            )

    def increment_request_count(self, method: str, path: str, status: int) -> None:
        if self._request_count is not None:
            self._request_count.labels(method=method, path=path, status=str(status)).inc()

    def observe_request_latency(self, method: str, path: str, duration_ms: float) -> None:
        if self._request_latency is not None:
            self._request_latency.labels(method=method, path=path).observe(duration_ms)

    def increment_error_count(self, error_type: str) -> None:
        if self._error_count is not None:
            self._error_count.labels(error_type=error_type).inc()


def get_metrics_response() -> tuple[bytes, str]:
    """生成 Prometheus 指标响应"""
    if not PROMETHEUS_AVAILABLE:
        return b"# prometheus_client not installed\n", "text/plain"
    return generate_latest(), CONTENT_TYPE_LATEST


_metrics_collector: PrometheusMetricsCollector | None = None


def get_metrics_collector() -> PrometheusMetricsCollector:
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = PrometheusMetricsCollector()
    return _metrics_collector
