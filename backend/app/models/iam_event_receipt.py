"""Durable idempotency ledger for IAM projection events."""

from datetime import datetime, timezone

from app import db


class IamEventReceipt(db.Model):
    __tablename__ = "iam_event_receipts"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(100), nullable=False, index=True)
    aggregate_kind = db.Column(db.String(32), nullable=False)
    aggregate_id = db.Column(db.String(100), nullable=False, index=True)
    aggregate_version = db.Column(db.BigInteger, nullable=False)
    occurred_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="processing", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=1)
    last_error = db.Column(db.String(500), nullable=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class IamAggregateCursor(db.Model):
    __tablename__ = "iam_aggregate_cursors"
    __table_args__ = (
        db.UniqueConstraint(
            "aggregate_kind", "aggregate_id", name="uq_iam_aggregate_cursor"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    aggregate_kind = db.Column(db.String(32), nullable=False)
    aggregate_id = db.Column(db.String(100), nullable=False)
    aggregate_version = db.Column(db.BigInteger, nullable=False)
    last_event_id = db.Column(db.String(36), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
