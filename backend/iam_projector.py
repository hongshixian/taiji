"""Long-running NATS JetStream consumer for IAM projection repair."""

import argparse
import asyncio
import json
import logging
import time

import nats
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js.api import ConsumerConfig, StorageType
from nats.js.errors import BadRequestError, NotFoundError

from app import create_app
from app.services.iam_client import IamClient
from app.services.iam_reconciliation_service import (
    InvalidIamEvent,
    process_event,
    reconcile_all,
)


LOGGER = logging.getLogger("taiji.iam_projector")


async def ensure_stream(jetstream, *, name: str, subject: str) -> None:
    try:
        await jetstream.stream_info(name)
        return
    except NotFoundError:
        pass

    try:
        await jetstream.add_stream(
            name=name,
            subjects=[subject],
            storage=StorageType.FILE,
        )
    except BadRequestError:
        # Keycloak may create the stream concurrently while the projector starts.
        await jetstream.stream_info(name)


async def run_projector(app, *, once: bool = False) -> None:
    config = app.config
    connection = await nats.connect(
        servers=[config["NATS_URL"]],
        name="taiji-iam-projector",
        connect_timeout=2,
        max_reconnect_attempts=-1,
    )
    jetstream = connection.jetstream()
    await ensure_stream(
        jetstream,
        name=config["IAM_EVENT_STREAM"],
        subject=config["IAM_EVENT_SUBJECT"],
    )
    subscription = await jetstream.pull_subscribe(
        config["IAM_EVENT_SUBJECT"],
        durable=config["IAM_EVENT_CONSUMER"],
        stream=config["IAM_EVENT_STREAM"],
        config=ConsumerConfig(
            durable_name=config["IAM_EVENT_CONSUMER"],
            filter_subject=config["IAM_EVENT_SUBJECT"],
            ack_wait=config["IAM_EVENT_ACK_WAIT_SECONDS"],
            max_ack_pending=config["IAM_EVENT_BATCH_SIZE"] * 2,
        ),
    )
    client = None
    next_reconciliation = 0.0
    try:
        while True:
            if time.monotonic() >= next_reconciliation:
                with app.app_context():
                    client = client or IamClient()
                    result = reconcile_all(client, source="scheduled")
                    LOGGER.info("IAM full reconciliation completed: %s", result)
                next_reconciliation = (
                    time.monotonic() + config["IAM_RECONCILE_INTERVAL_SECONDS"]
                )

            try:
                messages = await subscription.fetch(
                    batch=config["IAM_EVENT_BATCH_SIZE"], timeout=1
                )
            except (NatsTimeoutError, asyncio.TimeoutError):
                if once:
                    return
                continue

            for message in messages:
                try:
                    await message.in_progress()
                    payload = json.loads(message.data)
                    with app.app_context():
                        client = client or IamClient()
                        result = process_event(payload, client)
                    await message.ack()
                    LOGGER.info(
                        "IAM event %s: id=%s type=%s",
                        result,
                        payload.get("event_id"),
                        payload.get("event_type"),
                    )
                except (json.JSONDecodeError, UnicodeDecodeError, InvalidIamEvent) as exc:
                    LOGGER.error("Discarding invalid IAM event: %s", exc)
                    await message.term()
                except Exception:
                    LOGGER.exception("IAM event processing failed; message will be retried")
                    await message.nak()
            if once:
                return
    finally:
        await connection.drain()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Process at most one batch")
    parser.add_argument(
        "--reconcile-only", action="store_true", help="Run one full reconciliation"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    if args.reconcile_only:
        with app.app_context():
            print(json.dumps(reconcile_all(), ensure_ascii=True, sort_keys=True))
        return
    asyncio.run(run_projector(app, once=args.once))


if __name__ == "__main__":
    main()
