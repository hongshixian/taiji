"""IAM event processing and authoritative projection reconciliation."""

from datetime import datetime, timezone
import uuid

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.iam_event_receipt import IamAggregateCursor, IamEventReceipt
from app.models.tenant import Tenant
from app.services.audit_log_service import record_audit_log
from app.services.iam_client import IamClient
from app.services.iam_projection_service import (
    project_platform_admins,
    reconcile_iam_members,
    reconcile_iam_tenants,
)
from app.utils.decorators import bypass_tenant_filter


SUPPORTED_PREFIX = "iam."


class InvalidIamEvent(ValueError):
    """Terminal schema or routing error for an IAM event."""


def reconcile_all(client: IamClient | None = None, *, source: str = "scheduled") -> dict:
    iam = client or IamClient()
    tenant_payloads = iam.reconciliation_tenants()
    tenants = reconcile_iam_tenants(tenant_payloads)
    member_count = 0
    for tenant in tenants:
        members = iam.reconciliation_members(tenant.iam_tenant_id)
        member_count += len(reconcile_iam_members(tenant, members))
    admins = project_platform_admins(iam.reconciliation_platform_admins())
    result = {
        "tenants": len(tenants),
        "memberships": member_count,
        "platform_admins": len(admins),
    }
    record_audit_log(
        action="iam.reconciliation.completed",
        resource_type="iam_projection",
        result="success",
        metadata={"source": source, **result},
    )
    db.session.commit()
    return result


def reconcile_tenant(tenant_id: str, client: IamClient | None = None) -> dict:
    iam = client or IamClient()
    payloads = iam.reconciliation_tenants()
    tenants = reconcile_iam_tenants(payloads)
    tenant = next((item for item in tenants if item.iam_tenant_id == tenant_id), None)
    if tenant is None:
        return {"tenants": 0, "memberships": 0, "platform_admins": 0}
    members = iam.reconciliation_members(tenant_id)
    projected = reconcile_iam_members(tenant, members)
    return {"tenants": 1, "memberships": len(projected), "platform_admins": 0}


def process_event(payload: dict, client: IamClient | None = None) -> str:
    event = _validate_event(payload)
    if event["realm"] != current_app.config["IAM_REALM"]:
        raise InvalidIamEvent("IAM event belongs to a different realm")
    receipt = _begin_receipt(event)
    if receipt.status in {"processed", "ignored"}:
        return "duplicate"

    cursor = IamAggregateCursor.query.filter_by(
        aggregate_kind=event["aggregate_kind"],
        aggregate_id=event["aggregate_id"],
    ).first()
    if cursor and event["aggregate_version"] < cursor.aggregate_version:
        _complete(receipt, event, "ignored", cursor)
        return "ignored"

    try:
        _reconcile_for_event(event, client or IamClient())
        _complete(receipt, event, "processed", cursor)
    except Exception as exc:
        db.session.rollback()
        failed = IamEventReceipt.query.filter_by(event_id=event["event_id"]).first()
        if failed is not None:
            failed.status = "failed"
            failed.last_error = str(exc)[:500]
            db.session.commit()
        raise
    return "processed"


def _reconcile_for_event(event: dict, client: IamClient) -> None:
    kind = event["aggregate_kind"]
    if kind == "invitation":
        return
    if kind == "platform_admin":
        project_platform_admins(client.reconciliation_platform_admins())
        return
    if kind == "tenant":
        reconcile_tenant(event["aggregate_id"], client)
        return
    if kind == "membership":
        tenant_id = event["data"].get("tenant_id")
        if tenant_id:
            reconcile_tenant(str(tenant_id), client)
            return
    reconcile_all(client, source="event")


def _begin_receipt(event: dict) -> IamEventReceipt:
    with bypass_tenant_filter():
        receipt = IamEventReceipt.query.filter_by(event_id=event["event_id"]).first()
        if receipt is not None:
            if receipt.status not in {"processed", "ignored"}:
                receipt.status = "processing"
                receipt.attempts += 1
                receipt.last_error = None
                db.session.commit()
            return receipt

        receipt = IamEventReceipt(
            event_id=event["event_id"],
            event_type=event["event_type"],
            aggregate_kind=event["aggregate_kind"],
            aggregate_id=event["aggregate_id"],
            aggregate_version=event["aggregate_version"],
            occurred_at=event["occurred_at"],
            status="processing",
            attempts=1,
        )
        db.session.add(receipt)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            receipt = IamEventReceipt.query.filter_by(event_id=event["event_id"]).one()
        return receipt


def _complete(
    receipt: IamEventReceipt,
    event: dict,
    status: str,
    cursor: IamAggregateCursor | None,
) -> None:
    now = datetime.now(timezone.utc)
    receipt.status = status
    receipt.processed_at = now
    receipt.last_error = None
    if cursor is None:
        cursor = IamAggregateCursor(
            aggregate_kind=event["aggregate_kind"],
            aggregate_id=event["aggregate_id"],
            aggregate_version=event["aggregate_version"],
            last_event_id=event["event_id"],
        )
        db.session.add(cursor)
    elif event["aggregate_version"] >= cursor.aggregate_version:
        cursor.aggregate_version = event["aggregate_version"]
        cursor.last_event_id = event["event_id"]
    db.session.commit()


def _validate_event(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise InvalidIamEvent("IAM event must be a JSON object")
    required = {
        "event_id", "event_type", "occurred_at", "realm",
        "aggregate_id", "aggregate_version", "data",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise InvalidIamEvent(f"IAM event is missing fields: {', '.join(missing)}")
    try:
        event_id = str(uuid.UUID(str(payload["event_id"])))
        occurred_at = datetime.fromisoformat(
            str(payload["occurred_at"]).replace("Z", "+00:00")
        )
        aggregate_version = int(payload["aggregate_version"])
    except (TypeError, ValueError) as exc:
        raise InvalidIamEvent(
            "IAM event contains invalid identifiers or timestamps"
        ) from exc
    event_type = str(payload["event_type"])
    aggregate_id = str(payload["aggregate_id"]).strip()
    parts = event_type.split(".")
    if (
        not event_type.startswith(SUPPORTED_PREFIX)
        or len(event_type) > 100
        or len(parts) < 4
        or parts[-1] != "v1"
    ):
        raise InvalidIamEvent("unsupported IAM event type")
    if not aggregate_id or len(aggregate_id) > 100 or aggregate_version < 0:
        raise InvalidIamEvent("IAM event contains an invalid aggregate")
    if not isinstance(payload["data"], dict):
        raise InvalidIamEvent("IAM event data must be an object")
    return {
        **payload,
        "event_id": event_id,
        "event_type": event_type,
        "aggregate_kind": parts[1],
        "aggregate_id": aggregate_id,
        "aggregate_version": aggregate_version,
        "occurred_at": occurred_at,
    }
