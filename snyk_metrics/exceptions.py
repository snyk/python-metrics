class MetricsClientException(Exception):
    pass


class MetricNotRegisteredError(MetricsClientException):
    pass


class MetricNotSupportedError(MetricsClientException):
    pass


class MetricTypeMismatchError(MetricsClientException):
    pass


class MetricLabelMismatchError(MetricsClientException):
    pass


class MetricAlreadyRegisteredError(MetricsClientException):
    pass


class ClientNotInitialisedError(MetricsClientException):
    pass


class RegistryNotInitialisedError(MetricsClientException):
    pass


class RegistryLockedError(MetricsClientException):
    pass
