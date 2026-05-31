"""JWT 黑名单 — Redis 单 token 撤销

配合 `users.tokens_revoked_at` 实现两种撤销渠道：
- 本模块：单 token 撤销（登出场景，jti 进黑名单）
- tokens_revoked_at：用户级全量撤销（改密 / 禁用 / 改角色场景）

Redis 键 TTL = token 剩余有效期，过期自动清理，零运维。

容错策略：Redis 暂时不可达时，is_jti_revoked 返回 False（fail-open）。
原因：用户级吊销机制（tokens_revoked_at）仍然生效，提供基础安全保证；
单 token 撤销失败仅意味着登出按钮无法立即让 token 失效，但 token 仍会自然过期（30 分钟）。
"""

import redis
from flask import current_app

from app.utils.logger import get_logger

logger = get_logger(__name__)

_redis_client = None


def _get_redis():
    """惰性单例 — 复用 Flask 配置的 REDIS_URL"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            current_app.config["REDIS_URL"], decode_responses=True
        )
    return _redis_client


def _key(jti: str) -> str:
    return f"jwt:blocklist:{jti}"


def revoke_jti(jti: str, ttl_seconds: int) -> bool:
    """把指定 jti 加入黑名单，ttl 秒后自动过期。

    Returns: True=成功，False=Redis 不可达（调用方应该提示用户）
    """
    if ttl_seconds <= 0:
        return True  # 已过期 token 无需进黑名单
    try:
        _get_redis().setex(_key(jti), ttl_seconds, "1")
        return True
    except redis.RedisError as e:
        logger.warning(f"撤销 jti 失败（Redis 不可达）：{e}")
        return False


def is_jti_revoked(jti: str) -> bool:
    """检查 jti 是否在黑名单。Redis 不可达时返回 False（fail-open）"""
    try:
        return _get_redis().exists(_key(jti)) > 0
    except redis.RedisError as e:
        logger.warning(f"查询黑名单失败（Redis 不可达），跳过检查：{e}")
        return False
