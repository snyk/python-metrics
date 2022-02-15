from typing import Dict, Optional, Tuple

from datadog import initialize, statsd

from .base import BaseClient


class DogstatsdClient(BaseClient):
    def __init__(self, agent_host: str, port: int) -> None:
        initialize(statsd_host=agent_host, statsd_port=port)

    def increment_counter(
        self, name: str, labels: Optional[Dict[str, str]] = None, value: int = 1
    ) -> None:
        tags = [f"{key}:{value}" for key, value in labels.items()] if labels else None
        statsd.increment(metric=name, tags=tags, value=value)

    def register_metric(
        self,
        metric_type: str,
        name: str,
        documentation: str,
        label_names: Optional[Tuple[str, ...]] = None,
    ) -> None:
        pass
