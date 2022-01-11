# snyk-python-metrics

Python library to interact transparently with Prometheus, Pushgateway and
Dogstatsd.

## Usage

The client can be used with two different approaches, one more opinionated and
structured, with all the metrics created and registered at the creation of the
client, and one more flexible, where metrics can be registered at any time.

The first approach should help keeping the application using this client cleaner
and the metrics management in a centralised place.

### Example 1 - "Locked Registry"

In this example all the metrics used by the application are registered as part
of the client initialisation.

Example:

```python
# my_app/settings.py
from snyk_metrics import initialise, Counter

counter_1 = Counter(
    name="my_app_counter",
    documentation="Simple example counter",
    label_names=None,
)
counter_2 = Counter(
    name="my_app_requests",
    documentation="Requests per endpoint and method",
    label_names=("endpoint", "method"),
)

metrics = [counter_1, counter_2]

initialise(metrics=metrics, prometheus_enabled=True)
```

```python
# my_app/api/endpoints.py
from my_app.metrics import counter_1, counter_2


def my_function():
    counter_1.increment()


def foo_get_endpoint():
    counter_2.increment()
```

### Example 2 - "Unstructured flexibility"

In this example metrics are created and used within the same file. It could make
it harder to keep track of all the metrics in the application, but it can also
help in keeping them closer to the part of the project where the metrics are
used.

```python
# my_app/settings.py
from snyk_metrics import initialise

initialise(prometheus_enabled=True, lock_registry=False)
```

```python
# my_app/api/endpoints.py
from snyk_metrics import Counter

counter_1 = Counter(
    name="my_app_counter",
    documentation="Simple example counter",
    label_names=None,
)
counter_2 = Counter(
    name="my_app_requests",
    documentation="Requests per endpoint and method",
    label_names=("endpoint", "method"),
)


def my_function():
    counter_1.increment()


def foo_get_endpoint():
    counter_2.increment()
```
