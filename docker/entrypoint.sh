#!/bin/bash
set -e

# 运行数据库迁移
flask db upgrade

# 确保管理员用户存在
python3 -c "
from app import create_app
from app.services.auth_service import seed_admin
app = create_app()
with app.app_context():
    seed_admin('admin', 'admin@taiji.local', 'admin123')
    print('Admin seed OK')
"

# 启动传入的命令
exec "$@"
