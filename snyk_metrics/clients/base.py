from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Optional, Tuple


class BaseClient(metaclass=ABCMeta):
    @abstractmethod
    def increment_counter(
        self, name: str, labels: Optional[Dict[str, Any]] = None, value: int = 1
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def register_metric(
        self,
        metric_type: str,
        name: str,
        documentation: str,
        label_names: Optional[Tuple[str, ...]] = None,
    ) -> None:
        raise NotImplementedError
