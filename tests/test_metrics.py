from unittest import TestCase
from unittest.mock import MagicMock, patch

import pytest

from snyk_metrics import _destroy_client, initialise
from snyk_metrics.exceptions import (
    ClientNotInitialisedError,
    MetricAlreadyRegisteredError,
    RegistryLockedError,
)
from snyk_metrics.metrics import Counter


class TestCounter(TestCase):
    def tearDown(self):
        _destroy_client()

    def test_initialise_must_be_called_first(self):
        counter = Counter("foo", "foo")
        with pytest.raises(ClientNotInitialisedError) as exc:
            counter.increment()
        assert str(exc.value) == "initialise() must be called before creating metrics"

    def test_counter_name_must_be_unique(self):
        initialise(lock_registry=False)
        Counter("foo", "foo")
        with pytest.raises(MetricAlreadyRegisteredError) as exc:
            Counter("foo", "duplicate counter")
        assert str(exc.value) == "foo"

    def test_counter_cant_be_registered_if_registry_is_locked(self):
        initialise()
        with pytest.raises(RegistryLockedError) as exc:
            Counter("foo", "foo")
        assert str(exc.value) == "metrics can't be registered after initialising the registry."

    def test_counter_is_incremented_by_one_by_default(self):
        initialise(lock_registry=False)
        counter = Counter("foo", "foo", label_names=("label",))
        with patch.object(counter._client, "increment_counter", MagicMock()) as increment_counter:
            counter.increment()
        increment_counter.assert_called_once_with(counter, value=1, labels=None)

    def test_counter_is_incremented_by_the_specified_amount(self):
        initialise(lock_registry=False)
        counter = Counter("foo", "foo", label_names=("label",))
        with patch.object(counter._client, "increment_counter", MagicMock()) as increment_counter:
            counter.increment(5)
        increment_counter.assert_called_once_with(counter, value=5, labels=None)

    def test_counter_with_labels_is_incremented(self):
        initialise(lock_registry=False)
        counter = Counter("foo", "foo", label_names=("label",))
        with patch.object(counter._client, "increment_counter", MagicMock()) as increment_counter:
            counter.increment(labels={"label": "test"})
        increment_counter.assert_called_once_with(counter, value=1, labels={"label": "test"})

    def test_counter_is_registered_automatically(self):
        initialise(lock_registry=False)
        counter = Counter("foo", "foo", label_names=("label",))
        counter.increment(labels={"label": "test"})
        assert len(counter._client.registry) == 1
        assert counter is counter._client.registry.get("foo")
