from typing import Any, Dict, Optional, Tuple, Union

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    push_to_gateway,
)
from prometheus_client.exposition import basic_auth_handler

from snyk_metrics.exceptions import MetricNotRegisteredError

from .base import BaseClient

PrometheusMetric = Union[Counter, Gauge, Histogram, Summary]

PROMETHEUS_METRIC_CLASS_MAP = {
    "counter": Counter,
    "gauge": Gauge,
    "histogram": Histogram,
    "summary": Summary,
}


class PrometheusClient(BaseClient):
    def __init__(
        self,
        pushgateway_enabled: bool = False,
        pushgateway_host: Optional[str] = None,
        pushgateway_port: Optional[int] = None,
        pushgateway_job_name: Optional[str] = None,
        pushgateway_username: Optional[str] = None,
        pushgateway_password: Optional[str] = None,
        registry: Optional[CollectorRegistry] = None,
    ):
        self.pushgateway_enabled = pushgateway_enabled
        self.pushgateway_host = pushgateway_host if pushgateway_enabled else None
        self.pushgateway_port = pushgateway_port
        self.pushgateway_job_name = pushgateway_job_name if pushgateway_enabled else None
        self.pushgateway_username = pushgateway_username
        self.pushgateway_password = pushgateway_password
        self._registry = registry or REGISTRY

    def _push_to_gateway(self) -> None:
        if not self.pushgateway_username and not self.pushgateway_password:
            push_to_gateway(
                f"{self.pushgateway_host}:{self.pushgateway_port}",
                self.pushgateway_job_name,
                self._registry,
            )
            return None

        def authenticated_handler(
            url: Any, method: Any, timeout: Any, headers: Any, data: Any
        ) -> Any:
            return basic_auth_handler(
                url,
                method,
                timeout,
                headers,
                data,
                self.pushgateway_username,
                self.pushgateway_password,
            )

        push_to_gateway(
            f"{self.pushgateway_host}:{self.pushgateway_port}",
            self.pushgateway_job_name,
            self._registry,
            handler=authenticated_handler,
        )

        return None

    def _get_registered_metric(
        self, metric_type: str, name: str, label_names: Optional[Tuple[str, ...]] = None
    ) -> PrometheusMetric:
        metric = self._registry._names_to_collectors.get(name)
        # TODO: add checks about type and labels
        if metric is None:
            raise MetricNotRegisteredError
        return metric

    def register_metric(
        self,
        metric_type: str,
        name: str,
        documentation: str,
        label_names: Optional[Tuple[str, ...]] = None,
    ) -> PrometheusMetric:

        metric = PROMETHEUS_METRIC_CLASS_MAP[metric_type](
            name=name,
            documentation=documentation,
            labelnames=label_names or (),
            registry=self._registry,
        )
        if self.pushgateway_enabled:
            self._push_to_gateway()

        return metric

    def increment_counter(
        self, name: str, labels: Optional[Dict[str, Any]] = None, value: int = 1
    ) -> None:
        label_names: Optional[Tuple[str, ...]] = tuple(labels.keys()) if labels else None
        counter = self._get_registered_metric("counter", name, label_names)
        counter.labels(**labels).inc(value) if labels else counter.inc(value)

        if self.pushgateway_enabled:
            self._push_to_gateway()

        return
