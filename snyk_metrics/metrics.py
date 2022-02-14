import logging
from typing import Any, Dict, Optional, Tuple

from snyk_metrics import get_client

from .client import Metric, MetricsClient, MetricTypes
from .exceptions import ClientNotInitialisedError

logger = logging.getLogger(__name__)


class Counter(Metric):
    def __init__(
        self, name: str, documentation: str, label_names: Optional[Tuple[str, ...]] = None
    ):

        super().__init__(
            metric_type=MetricTypes.COUNTER,
            name=name,
            documentation=documentation,
            label_names=label_names,
        )

        self._client: Optional[MetricsClient] = None

        try:
            self._client = get_client()
            self._client.register_metric(self)
        except ClientNotInitialisedError:
            pass

    def increment(self, value: int = 1, labels: Optional[Dict[str, Any]] = None) -> None:
        if not self._client:
            self._client = get_client()

        self._client.increment_counter(self, value=value, labels=labels)
