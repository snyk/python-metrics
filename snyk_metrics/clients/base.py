from abc import ABCMeta, abstractmethod


class BaseClient(metaclass=ABCMeta):
    @abstractmethod
    def increment_counter(self, name: str, labels: dict = None, value: int = 1) -> None:
        raise NotImplementedError

    @abstractmethod
    def register_metric(
        self, metric_type: str, name: str, documentation: str, label_names: tuple = None
    ) -> None:
        raise NotImplementedError
