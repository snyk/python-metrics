import logging
from typing import List, Optional

from prometheus_client import REGISTRY, CollectorRegistry

from .client import Metric, MetricsClient, Singleton
from .exceptions import ClientNotInitialisedError

__all__ = [
    "Metric",
    "MetricsClient",
    "MetricTypes",
]

logger = logging.getLogger(__name__)
_metrics_client: Optional[MetricsClient] = None


def initialise(
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
    lock_registry: bool = True,
) -> None:
    global _metrics_client
    if _metrics_client is not None:
        logger.warning("MetricsClient already initialised. Different settings will be ignored.")
    _metrics_client = _metrics_client or MetricsClient(
        metrics=metrics,
        prometheus_enabled=prometheus_enabled,
        pushgateway_enabled=pushgateway_enabled,
        pushgateway_host=pushgateway_host,
        pushgateway_port=pushgateway_port,
        pushgateway_job_name=pushgateway_job_name,
        pushgateway_username=pushgateway_username,
        pushgateway_password=pushgateway_password,
        dogstatsd_enabled=dogstatsd_enabled,
        dogstatsd_agent_host=dogstatsd_agent_host,
        dogstatsd_port=dogstatsd_port,
        prometheus_registry=prometheus_registry,
        raise_exceptions=raise_exceptions,
        lock_registry=lock_registry,
    )


def get_client() -> MetricsClient:
    global _metrics_client
    if not _metrics_client:
        raise ClientNotInitialisedError("initialise() must be called before creating metrics")

    return _metrics_client


def _destroy_client() -> None:
    # NOTE: used in unittest, probably a better approach is needed
    global _metrics_client
    _metrics_client = None
    Singleton._instances = {}
