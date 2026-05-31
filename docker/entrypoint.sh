#!/bin/bash
set -e

# 运行数据库迁移
flask db upgrade

# ─── 创建初始管理员账号 ─────────────────────────────────
# 策略：
#   1. 若设置了 ADMIN_PASSWORD 环境变量 → 使用该密码
#   2. 否则 → 随机生成 16 字符密码，打印到日志一次
# 仅在无管理员账号存在时生效（已有 admin 时跳过 seed）
# 初始 admin 默认归 default 租户，且 is_superuser=true（保证有人能管 tenants）
python3 - <<'PYEOF'
import os
import secrets
import sys

from app import create_app
from app.models.user import User
from app.models.tenant import Tenant
from app.models.role import Role
from app.models.tenant_membership import TenantMembership
from app.services.auth_service import seed_admin

app = create_app()
with app.app_context():
    # 确保系统租户存在（migration 已 seed，这里是兜底）
    for slug, name in [("default", "默认组织"), ("guest", "访客租户")]:
        if not Tenant.query.filter_by(slug=slug).first():
            print(f"[seed-tenant] 创建系统租户 {slug}")
            t = Tenant(slug=slug, name=name, plan="free", is_system=True)
            from app import db
            db.session.add(t)
            db.session.commit()

    admin_role = Role.query.filter_by(name="admin").first()
    if admin_role and (
        User.query
        .join(TenantMembership, TenantMembership.user_id == User.id)
        .filter(TenantMembership.role_id == admin_role.id)
        .first()
    ):
        print("[seed-admin] 检测到已有管理员账号，跳过初始化")
        sys.exit(0)

    username = os.getenv("ADMIN_USERNAME", "admin")
    email = os.getenv("ADMIN_EMAIL", "admin@taiji.local")
    password = os.getenv("ADMIN_PASSWORD")
    generated = False

    if not password:
        password = secrets.token_urlsafe(12)  # 约 16 字符
        generated = True

    # 初始 admin 归 default 租户，自动获得 superuser 权限
    seed_admin(username, email, password, tenant_slug="default", is_superuser=True)

    if generated:
        bar = "=" * 60
        print(f"\n{bar}", flush=True)
        print(f"  🔐 首次部署：已创建管理员账号", flush=True)
        print(f"  username: {username}", flush=True)
        print(f"  password: {password}", flush=True)
        print(f"  tenant:   default", flush=True)
        print(f"  is_superuser: true (可管理所有租户)", flush=True)
        print(f"  请立即保存此密码，登录后修改！本提示仅显示一次。", flush=True)
        print(f"  （如需自定义，可设置 ADMIN_PASSWORD 环境变量后重新部署）", flush=True)
        print(f"{bar}\n", flush=True)
    else:
        print(f"[seed-admin] 已创建管理员 {username}（密码来自 ADMIN_PASSWORD，superuser=true）", flush=True)
PYEOF

# 启动传入的命令
exec "$@"
