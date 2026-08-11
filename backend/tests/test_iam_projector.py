"""Runtime behavior tests for the IAM JetStream projector."""

import asyncio

import iam_projector


class _TimeoutSubscription:
    def __init__(self):
        self.fetch_calls = 0

    async def fetch(self, **_kwargs):
        self.fetch_calls += 1
        raise asyncio.TimeoutError


class _JetStream:
    def __init__(self, subscription):
        self.subscription = subscription

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
