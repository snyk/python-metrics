import logging
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

from prometheus_client import REGISTRY, CollectorRegistry

from .clients.base import BaseClient
from .clients.dogstatsd import DogstatsdClient
from .clients.prometheus import PrometheusClient
from .exceptions import (
    MetricAlreadyRegisteredError,
    MetricLabelMismatchError,
    MetricNotRegisteredError,
    MetricTypeMismatchError,
    RegistryLockedError,
)

logger = logging.getLogger(__name__)


class MetricTypes(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    metric_type: MetricTypes
    name: str
    documentation: str
    label_names: Optional[Tuple[str, ...]]


class Singleton(type):
    _instances: Dict[Any, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        else:
            logger.warning(f"{cls.__name__} already initialised.")
        return cls._instances[cls]


def _exception_handler(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def inner_func(*args: Any, **kwargs: Any) -> Any:
        try:
            func(*args, **kwargs)
        except Exception as exc:
            # NOTE: args[0] is the object
            if args[0]._raise_exceptions:
                raise
            logger.warning(f"{(exc.__class__.__name__)}: {str(exc)}", stack_info=True)

    return inner_func


class MetricsClient(metaclass=Singleton):
    def __init__(
        self,
        *,
        metrics: Optional[List[Metric]] = None,
        prometheus_enabled: bool = False,
        pushgateway_enabled: bool = False,
        pushgateway_host: str = "prometheus-pushgateway",
        pushgateway_port: int = 9091,
        pushgateway_job_name: str = "snyk-metrics-client",
        pushgateway_username: Optional[str] = None,
        pushgateway_password: Optional[str] = None,
        dogstatsd_enabled: bool = False,
        dogstatsd_agent_host: str = "datadog",
        dogstatsd_port: int = 8125,
        prometheus_registry: CollectorRegistry = REGISTRY,
        raise_exceptions: bool = True,
        lock_registry: bool = False,
    ):
        self._raise_exceptions = raise_exceptions
        self._prometheus_client = (
            PrometheusClient(
                pushgateway_enabled=pushgateway_enabled,
                pushgateway_host=pushgateway_host,
                pushgateway_port=pushgateway_port,
                pushgateway_job_name=pushgateway_job_name,
                pushgateway_username=pushgateway_username,
                pushgateway_password=pushgateway_password,
                registry=prometheus_registry,
            )
            if prometheus_enabled
            else None
        )
        self._dogstatsd_client = (
            DogstatsdClient(dogstatsd_agent_host, dogstatsd_port) if dogstatsd_enabled else None
        )
        self._enabled_clients: List[BaseClient] = list(
            filter(None, (self._prometheus_client, self._dogstatsd_client))
        )

        self.registry: Dict[str, Metric] = {}
        self.lock_registry = False
        for metric in metrics or []:
            self.register_metric(metric)
        self.lock_registry = lock_registry

    @_exception_handler
    def _validate_metric(
        self, metric: Metric, metric_type: MetricTypes, labels: Optional[Dict[str, Any]]
    ) -> None:
        registered_metric = self.registry.get(metric.name)
        label_names = tuple(labels.keys()) if labels else None

        if registered_metric is None:
            raise MetricNotRegisteredError(metric.name)

        if registered_metric.metric_type is not metric_type:
            raise MetricTypeMismatchError(
                f"{registered_metric.name} type is {registered_metric.metric_type.value}, "
                f"not {metric_type.value}."
            )

        sorted_registered_label_names = sorted(
            registered_metric.label_names if registered_metric.label_names else []
        )
        sorted_label_names = sorted(label_names if label_names else [])
        if sorted_registered_label_names != sorted_label_names:
            raise MetricLabelMismatchError(
                f"{registered_metric.name} required labels: {registered_metric.label_names}"
            )

    @_exception_handler
    def register_metric(self, metric: Metric) -> None:
        if self.lock_registry:
            raise RegistryLockedError(
                "metrics can't be registered after initialising the registry."
            )

        if metric.name in self.registry:
            raise MetricAlreadyRegisteredError(metric.name)

        for client in self._enabled_clients:
            client.register_metric(
                metric.metric_type.value,
                metric.name,
                metric.documentation,
                metric.label_names,
            )
        self.registry[metric.name] = metric
        return

    @_exception_handler
    def increment_counter(
        self, metric: Metric, labels: Optional[Dict[str, Any]] = None, value: int = 1
    ) -> None:
        self._validate_metric(metric, MetricTypes.COUNTER, labels)
        for client in self._enabled_clients:
            client.increment_counter(metric.name, labels, value)

    @_exception_handler
    def set_gauge_value(
        self, metric: Metric, labels: Optional[Dict[str, Any]] = None, value: float = 0.0
    ) -> None:
        self._validate_metric(metric, MetricTypes.GAUGE, labels)
        for client in self._enabled_clients:
            client.set_gauge_value(metric.name, labels, value)

    @_exception_handler
    def set_histogram_value(
        self, metric: Metric, labels: Optional[Dict[str, Any]] = None, value: float = 0.0
    ) -> None:
        self._validate_metric(metric, MetricTypes.HISTOGRAM, labels)
        for client in self._enabled_clients:
            client.set_histogram_value(metric.name, labels, value)
