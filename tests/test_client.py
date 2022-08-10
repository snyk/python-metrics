from unittest import TestCase
from unittest.mock import patch

import pytest
from prometheus_client import CollectorRegistry

from snyk_metrics.client import Metric, MetricsClient, MetricTypes, Singleton
from snyk_metrics.exceptions import (
    MetricAlreadyRegisteredError,
    MetricLabelMismatchError,
    MetricNotRegisteredError,
    MetricTypeMismatchError,
    RegistryLockedError,
)


class TestMetricsClient(TestCase):
    def tearDown(self) -> None:
        Singleton._instances = {}

    def test_client_is_a_singleton(self) -> None:
        with patch("snyk_metrics.client.logger") as logger:
            client_1 = MetricsClient()
            client_2 = MetricsClient()
        assert client_1 is client_2
        logger.warning.assert_called_once_with("MetricsClient already initialised.")

    def test_metric_is_registered_correctly(self) -> None:
        client = MetricsClient()
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_counter",
            documentation="Test",
            label_names=None,
        )
        client.register_metric(metric)
        assert client.registry.get("test_counter") is not None

    def test_metric_already_registered_raise(self) -> None:
        client = MetricsClient()
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        client.register_metric(metric)
        with pytest.raises(MetricAlreadyRegisteredError) as exc:
            client.register_metric(metric)
        assert str(exc.value) == "test_metric"

    def test_prometheus_client_is_created_correctly(self) -> None:
        client = MetricsClient(prometheus_enabled=True)
        assert client._prometheus_client is not None

    def test_dogstatsd_client_is_created_correctly(self) -> None:
        client = MetricsClient(dogstatsd_enabled=True)
        assert client._dogstatsd_client is not None

    def test_multiple_clients_are_created_correctly(self) -> None:
        client = MetricsClient(prometheus_enabled=True, dogstatsd_enabled=True)
        assert len(client._enabled_clients) == 2

    def test_pushgateway_is_enabled_correctly(self) -> None:
        client = MetricsClient(prometheus_enabled=True, pushgateway_enabled=True)
        assert client._prometheus_client is not None
        assert client._prometheus_client.pushgateway_enabled is True

    def test_exceptions_are_silenced_and_logged_as_warning(self) -> None:
        client = MetricsClient(raise_exceptions=False)
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        client.register_metric(metric)
        with patch("snyk_metrics.client.logger") as logger:
            client.register_metric(metric)

        logger.warning.assert_called_once_with(
            "MetricAlreadyRegisteredError: test_metric", stack_info=True
        )

    def test_registry_is_initialised_correctly(self) -> None:

        metrics = [
            Metric(
                metric_type=MetricTypes.COUNTER,
                name="simple_metric",
                documentation="Metric",
                label_names=None,
            ),
            Metric(
                metric_type=MetricTypes.COUNTER,
                name="metric_with_labels",
                documentation="Metric with labels",
                label_names=(
                    "foo",
                    "bar",
                ),
            ),
        ]

        client = MetricsClient(metrics=metrics)
        assert len(client.registry) == 2

    def test_metrics_cant_be_registered_if_registry_is_locked(self) -> None:
        metrics = [
            Metric(
                metric_type=MetricTypes.COUNTER,
                name="simple_metric",
                documentation="Metric",
                label_names=None,
            ),
            Metric(
                metric_type=MetricTypes.COUNTER,
                name="metric_with_labels",
                documentation="Metric with labels",
                label_names=(
                    "foo",
                    "bar",
                ),
            ),
        ]

        client = MetricsClient(metrics=metrics, lock_registry=True)

        with pytest.raises(RegistryLockedError) as exc:
            client.register_metric(
                Metric(
                    metric_type=MetricTypes.COUNTER,
                    name="simple_metric",
                    documentation="Metric",
                    label_names=None,
                ),
            )
        assert str(exc.value) == "metrics can't be registered after initialising the registry."

    def test_not_registered_metric_raises_if_incremented(self) -> None:
        client = MetricsClient()
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        with pytest.raises(MetricNotRegisteredError) as exc:
            client.increment_counter(metric)

        assert str(exc.value) == "test_metric"

    def test_metrics_missmatch_raises(self) -> None:
        client = MetricsClient()
        metric = Metric(
            metric_type=MetricTypes.GAUGE,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        client.register_metric(metric)
        with pytest.raises(MetricTypeMismatchError) as exc:
            client.increment_counter(metric)

        assert str(exc.value) == "test_metric type is gauge, not counter."

    def test_counter_incremented_with_wrong_labels_raises(self) -> None:
        client = MetricsClient()
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=("foo",),
        )
        client.register_metric(metric)
        with pytest.raises(MetricLabelMismatchError) as exc:
            client.increment_counter(metric)

        assert str(exc.value) == "test_metric required labels: ('foo',)"

    def test_counter_with_labels_works(self) -> None:
        client = MetricsClient()
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=("foo",),
        )
        client.register_metric(metric)
        assert client.increment_counter(metric, labels={"foo": "bar"}) is None

    def test_counter_is_incremented_by_one_if_unspecified(self) -> None:
        # NOTE: to test the values we use Prometheus registry as the internal
        # registry only keeps track of the registered metrics, not their value.
        prometheus_registry = CollectorRegistry()
        client = MetricsClient(
            prometheus_enabled=True,
            prometheus_registry=prometheus_registry,
        )
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        client.register_metric(metric)
        client.increment_counter(metric)
        # NOTE: `_total` is added automatically by Prometheus
        assert prometheus_registry.get_sample_value("test_metric_total") == 1

    def test_counter_is_incremented_by_the_specified_amount(self) -> None:
        # NOTE: to test the values we use Prometheus registry as the internal
        # registry only keeps track of the registered metrics, not their value.
        prometheus_registry = CollectorRegistry()
        client = MetricsClient(
            prometheus_enabled=True,
            prometheus_registry=prometheus_registry,
        )
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        client.register_metric(metric)
        client.increment_counter(metric, value=5)
        # NOTE: `_total` is added automatically by Prometheus
        assert prometheus_registry.get_sample_value("test_metric_total") == 5

    def test_counter_can_be_incremented_multiple_times(self) -> None:
        # NOTE: to test the values we use Prometheus registry as the internal
        # registry only keeps track of the registered metrics, not their value.
        prometheus_registry = CollectorRegistry()
        client = MetricsClient(
            prometheus_enabled=True,
            prometheus_registry=prometheus_registry,
        )
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        client.register_metric(metric)
        client.increment_counter(metric, value=2)
        client.increment_counter(metric, value=5)
        # NOTE: `_total` is added automatically by Prometheus
        assert prometheus_registry.get_sample_value("test_metric_total") == 7

    def test_registered_metrics_are_sent_to_pushgateway(self) -> None:
        prometheus_registry = CollectorRegistry()
        client = MetricsClient(
            prometheus_enabled=True,
            pushgateway_enabled=True,
            pushgateway_job_name="pytest",
            pushgateway_host="localhost",
            pushgateway_port=9091,
            prometheus_registry=prometheus_registry,
        )
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        with patch("snyk_metrics.clients.prometheus.push_to_gateway") as push_to_gateway:
            client.register_metric(metric)

        push_to_gateway.assert_called_once_with("localhost:9091", "pytest", prometheus_registry)

    def test_counter_increment_is_sent_to_pushgateway(self) -> None:
        prometheus_registry = CollectorRegistry()
        client = MetricsClient(
            prometheus_enabled=True,
            pushgateway_enabled=True,
            pushgateway_job_name="pytest",
            pushgateway_host="localhost",
            pushgateway_port=9091,
            prometheus_registry=prometheus_registry,
        )
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        # NOTE: only want to test the increment_counter call, register_metric is already tested.
        with patch("snyk_metrics.clients.prometheus.push_to_gateway") as _:
            client.register_metric(metric)

        with patch("snyk_metrics.clients.prometheus.push_to_gateway") as push_to_gateway:
            client.increment_counter(metric)

        push_to_gateway.assert_called_once_with("localhost:9091", "pytest", prometheus_registry)

    def test_authenticated_pushgateway_called_correctly(self) -> None:
        prometheus_registry = CollectorRegistry()
        client = MetricsClient(
            prometheus_enabled=True,
            pushgateway_enabled=True,
            pushgateway_job_name="pytest",
            pushgateway_host="localhost",
            pushgateway_port=9091,
            pushgateway_username="bar",
            pushgateway_password="foo",
            prometheus_registry=prometheus_registry,
        )
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )

        with patch("snyk_metrics.clients.prometheus.push_to_gateway") as push_to_gateway:
            client.register_metric(metric)
        push_to_gateway.assert_called_once()
        _, kwargs = push_to_gateway.call_args
        assert "handler" in kwargs

    def test_dogstatsd_client_is_initialised_correctly(self) -> None:
        with patch("snyk_metrics.clients.dogstatsd.initialize") as initialize:
            MetricsClient(
                dogstatsd_enabled=True,
                dogstatsd_agent_host="localhost",
                dogstatsd_port=1234,
            )
        initialize.assert_called_once_with(statsd_host="localhost", statsd_port=1234)

    def test_counter_is_incremented_in_dogstatsd(self) -> None:
        client = MetricsClient(dogstatsd_enabled=True)
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        client.register_metric(metric)
        with patch("snyk_metrics.clients.dogstatsd.statsd") as statsd:
            client.increment_counter(metric)

        statsd.increment.assert_called_once_with(metric="test_metric", tags=None, value=1)

    def test_counter_with_labels_is_incremented_in_dogstatsd(self) -> None:
        client = MetricsClient(dogstatsd_enabled=True)
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=("foo",),
        )
        client.register_metric(metric)
        with patch("snyk_metrics.clients.dogstatsd.statsd") as statsd:
            client.increment_counter(metric, labels={"foo": "bar"})

        statsd.increment.assert_called_once_with(metric="test_metric", tags=["foo:bar"], value=1)

    def test_not_registered_metric_raises_when_setting_a_gauge_value(self) -> None:
        client = MetricsClient()
        metric = Metric(
            metric_type=MetricTypes.GAUGE,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        with pytest.raises(MetricNotRegisteredError) as exc:
            client.set_gauge_value(metric)

        assert str(exc.value) == "test_metric"

    def test_gauges_value_set_with_wrong_labels_raises(self) -> None:
        client = MetricsClient()
        metric = Metric(
            metric_type=MetricTypes.GAUGE,
            name="test_metric",
            documentation="Test",
            label_names=("foo",),
        )
        client.register_metric(metric)
        with pytest.raises(MetricLabelMismatchError) as exc:
            client.set_gauge_value(metric)

        assert str(exc.value) == "test_metric required labels: ('foo',)"

    def test_gauge_with_labels_works(self) -> None:
        client = MetricsClient()
        metric = Metric(
            metric_type=MetricTypes.GAUGE,
            name="test_metric",
            documentation="Test",
            label_names=("foo",),
        )
        client.register_metric(metric)
        assert client.set_gauge_value(metric, labels={"foo": "bar"}, value=2.0) is None

    def test_gauge_value_is_default_if_unspecified(self) -> None:
        # NOTE: to test the values we use Prometheus registry as the internal
        # registry only keeps track of the registered metrics, not their value.
        prometheus_registry = CollectorRegistry()
        client = MetricsClient(
            prometheus_enabled=True,
            prometheus_registry=prometheus_registry,
        )
        metric = Metric(
            metric_type=MetricTypes.GAUGE,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        client.register_metric(metric)
        client.set_gauge_value(metric)
        # NOTE: `_total` is added automatically by Prometheus
        assert prometheus_registry.get_sample_value("test_metric") == 0.0

    def test_gauge_set_value_works_properly(self) -> None:
        # NOTE: to test the values we use Prometheus registry as the internal
        # registry only keeps track of the registered metrics, not their value.
        prometheus_registry = CollectorRegistry()
        client = MetricsClient(
            prometheus_enabled=True,
            prometheus_registry=prometheus_registry,
        )
        metric = Metric(
            metric_type=MetricTypes.GAUGE,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        client.register_metric(metric)
        client.set_gauge_value(metric, value=5.0)
        # NOTE: `_total` is added automatically by Prometheus
        assert prometheus_registry.get_sample_value("test_metric") == 5.0

    def test_gauge_value_is_sent_to_pushgateway(self) -> None:
        prometheus_registry = CollectorRegistry()
        client = MetricsClient(
            prometheus_enabled=True,
            pushgateway_enabled=True,
            pushgateway_job_name="pytest",
            pushgateway_host="localhost",
            pushgateway_port=9091,
            prometheus_registry=prometheus_registry,
        )
        metric = Metric(
            metric_type=MetricTypes.GAUGE,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        # NOTE: only want to test the increment_counter call, register_metric is already tested.
        with patch("snyk_metrics.clients.prometheus.push_to_gateway") as _:
            client.register_metric(metric)

        with patch("snyk_metrics.clients.prometheus.push_to_gateway") as push_to_gateway:
            client.set_gauge_value(metric, value=15.0)

        push_to_gateway.assert_called_once_with("localhost:9091", "pytest", prometheus_registry)

    def test_gauge_value_is_set_in_dogstatsd(self) -> None:
        client = MetricsClient(dogstatsd_enabled=True)
        metric = Metric(
            metric_type=MetricTypes.GAUGE,
            name="test_metric",
            documentation="Test",
            label_names=None,
        )
        client.register_metric(metric)
        with patch("snyk_metrics.clients.dogstatsd.statsd") as statsd:
            client.set_gauge_value(metric, value=4.0)

        statsd.gauge.assert_called_once_with(metric="test_metric", tags=None, value=4.0)

    def test_labels_recognized_even_if_specified_in_different_order(self) -> None:
        client = MetricsClient()
        metric = Metric(
            metric_type=MetricTypes.COUNTER,
            name="test_metric",
            documentation="Test",
            label_names=("label_a", "label_b"),
        )
        client.register_metric(metric)

        try:
            client.increment_counter(metric, labels={"label_b": "luca", "label_a": "mike"})
        except MetricLabelMismatchError as exc:
            raise pytest.fail(f"MetricsClient.increment_counter() raised {exc}")
