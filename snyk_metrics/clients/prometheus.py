from typing import Union

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    push_to_gateway,
)

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
        pushgateway_host: str = None,
        pushgateway_port: int = None,
        pushgateway_job_name: str = None,
        registry: CollectorRegistry = None,
    ):
        self.pushgateway_enabled = pushgateway_enabled
        self.pushgateway_host = pushgateway_host if pushgateway_enabled else None
        self.pushgateway_port = pushgateway_port
        self.pushgateway_job_name = pushgateway_job_name if pushgateway_enabled else None
        self._registry = registry or REGISTRY

    def _push_to_gateway(self) -> None:
        return push_to_gateway(
            f"{self.pushgateway_host}:{self.pushgateway_port}",
            self.pushgateway_job_name,
            self._registry,
        )

    def _get_registered_metric(self, metric_type: str, name: str, label_names: tuple = None):
        metric = self._registry._names_to_collectors.get(name)
        # TODO: add checks about type and labels
        return metric

    def register_metric(
        self, metric_type: str, name: str, documentation: str, label_names: tuple = None
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

    def increment_counter(self, name: str, labels: dict = None, value: int = 1) -> None:
        counter = self._get_registered_metric(
            "counter", name, tuple(labels.keys()) if labels else None
        )
        counter.labels(**labels).inc(value) if labels else counter.inc(value)

        if self.pushgateway_enabled:
            self._push_to_gateway()

        return
