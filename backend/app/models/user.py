"""用户模型"""

from datetime import datetime, timezone
from app import db


class User(db.Model):
    """太极平台用户"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # 关联分析任务
    analyze_tasks = db.relationship("AnalyzeTask", backref="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.username}>"