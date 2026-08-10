"""Persistent checkpoint for the one-time legacy IAM migration."""

from datetime import datetime, timezone

from app import db


class IamMigrationRecord(db.Model):
    __tablename__ = "iam_migration_records"
    __table_args__ = (
        db.UniqueConstraint("entity_type", "local_id", name="uq_iam_migration_entity"),
        db.UniqueConstraint("entity_type", "stable_id", name="uq_iam_migration_stable_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(24), nullable=False, index=True)
    local_id = db.Column(db.String(64), nullable=False)
    stable_id = db.Column(db.String(36), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    keycloak_id = db.Column(db.String(64), nullable=True)
    last_error = db.Column(db.String(500), nullable=True)
    last_attempted_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
