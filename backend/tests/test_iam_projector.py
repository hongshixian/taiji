"""Runtime behavior tests for the IAM JetStream projector."""

import asyncio

import iam_projector
from nats.js.errors import NotFoundError


class _TimeoutSubscription:
    def __init__(self):
        self.fetch_calls = 0

    async def fetch(self, **_kwargs):
        self.fetch_calls += 1
        raise asyncio.TimeoutError


class _JetStream:
    def __init__(self, subscription):
        self.subscription = subscription
        self.stream_exists = False
        self.added_stream = None

    async def stream_info(self, _name):
        if not self.stream_exists:
            raise NotFoundError()
        return object()

    async def add_stream(self, **params):
        self.stream_exists = True
        self.added_stream = params
        return object()

    async def pull_subscribe(self, *_args, **_kwargs):
        return self.subscription


class _Connection:
    def __init__(self, subscription):
        self._jetstream = _JetStream(subscription)
        self.drained = False

    def jetstream(self):
        return self._jetstream

    async def drain(self):
        self.drained = True


def test_builtin_timeout_is_a_normal_empty_poll(app, monkeypatch):
    subscription = _TimeoutSubscription()
    connection = _Connection(subscription)

    async def connect(**_kwargs):
        return connection

    monkeypatch.setattr(iam_projector.nats, "connect", connect)
    monkeypatch.setattr(iam_projector, "IamClient", object)
    monkeypatch.setattr(iam_projector, "reconcile_all", lambda *_args, **_kwargs: {})

    asyncio.run(iam_projector.run_projector(app, once=True))

    assert subscription.fetch_calls == 1
    assert connection.drained is True
    assert connection._jetstream.added_stream == {
        "name": app.config["IAM_EVENT_STREAM"],
        "subjects": [app.config["IAM_EVENT_SUBJECT"]],
        "storage": iam_projector.StorageType.FILE,
    }
