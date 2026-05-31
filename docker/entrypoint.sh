#!/bin/bash
set -e

# 运行数据库迁移
flask db upgrade

# ─── 创建初始管理员账号 ─────────────────────────────────
# 策略：
#   1. 若设置了 ADMIN_PASSWORD 环境变量 → 使用该密码
#   2. 否则 → 随机生成 16 字符密码，打印到日志一次
# 仅在无管理员账号存在时生效（已有 admin 时跳过 seed）
python3 - <<'PYEOF'
import os
import secrets
import sys

from app import create_app
from app.models.user import User
from app.services.auth_service import seed_admin

app = create_app()
with app.app_context():
    if User.query.filter_by(role="admin").first():
        print("[seed-admin] 检测到已有管理员账号，跳过初始化")
        sys.exit(0)

    username = os.getenv("ADMIN_USERNAME", "admin")
    email = os.getenv("ADMIN_EMAIL", "admin@taiji.local")
    password = os.getenv("ADMIN_PASSWORD")
    generated = False

    if not password:
        password = secrets.token_urlsafe(12)  # 约 16 字符
        generated = True

    seed_admin(username, email, password)

    if generated:
        bar = "=" * 60
        print(f"\n{bar}", flush=True)
        print(f"  🔐 首次部署：已创建管理员账号", flush=True)
        print(f"  username: {username}", flush=True)
        print(f"  password: {password}", flush=True)
        print(f"  请立即保存此密码，登录后修改！本提示仅显示一次。", flush=True)
        print(f"  （如需自定义，可设置 ADMIN_PASSWORD 环境变量后重新部署）", flush=True)
        print(f"{bar}\n", flush=True)
    else:
        print(f"[seed-admin] 已创建管理员 {username}（密码来自 ADMIN_PASSWORD）", flush=True)
PYEOF

# 启动传入的命令
exec "$@"
