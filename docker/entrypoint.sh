#!/bin/sh
set -e

# 确保数据目录存在（bind mount 不会自动创建）
mkdir -p /app/data

# 运行数据库迁移（建表）
cd /app
flask db upgrade

# 启动传入的命令
exec "$@"