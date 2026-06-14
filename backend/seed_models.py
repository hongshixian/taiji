"""
Seed model configs from benchmark_data.json model list into the guest tenant.
Run from backend/: python seed_models.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app import db
from app.models.model_config import ModelConfig
from app.models.tenant import Tenant, GUEST_TENANT_SLUG

MODELS = [
    {
        "display_name": "Claude Opus 4.7",
        "model_name": "claude-opus-4-7",
        "api_base_url": "https://api.anthropic.com",
        "api_protocol": "anthropic",
        "description": "Anthropic Claude Opus 4.7",
    },
    {
        "display_name": "Claude Sonnet 4.6",
        "model_name": "claude-sonnet-4-6",
        "api_base_url": "https://api.anthropic.com",
        "api_protocol": "anthropic",
        "description": "Anthropic Claude Sonnet 4.6",
    },
    {
        "display_name": "DeepSeek V3.2 Thinking",
        "model_name": "deepseek-reasoner",
        "api_base_url": "https://api.deepseek.com/v1",
        "api_protocol": "openai",
        "description": "DeepSeek V3.2 Thinking (deepseek-reasoner)",
    },
    {
        "display_name": "DeepSeek V4 Pro",
        "model_name": "deepseek-chat",
        "api_base_url": "https://api.deepseek.com/v1",
        "api_protocol": "openai",
        "description": "DeepSeek V4 Pro (deepseek-chat)",
    },
    {
        "display_name": "GLM-4.7",
        "model_name": "glm-4-air",
        "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_protocol": "openai",
        "description": "智谱 GLM-4.7",
    },
    {
        "display_name": "GLM-5",
        "model_name": "glm-4-plus",
        "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_protocol": "openai",
        "description": "智谱 GLM-5",
    },
    {
        "display_name": "GLM-5.1",
        "model_name": "glm-4-long",
        "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_protocol": "openai",
        "description": "智谱 GLM-5.1",
    },
    {
        "display_name": "GPT-5.4",
        "model_name": "gpt-4o",
        "api_base_url": "https://api.openai.com/v1",
        "api_protocol": "openai",
        "description": "OpenAI GPT-5.4",
    },
    {
        "display_name": "GPT-5.5",
        "model_name": "gpt-4o-mini",
        "api_base_url": "https://api.openai.com/v1",
        "api_protocol": "openai",
        "description": "OpenAI GPT-5.5",
    },
    {
        "display_name": "Kimi K2.5",
        "model_name": "moonshot-v1-8k",
        "api_base_url": "https://api.moonshot.cn/v1",
        "api_protocol": "openai",
        "description": "Moonshot Kimi K2.5",
    },
    {
        "display_name": "Kimi K2.6",
        "model_name": "moonshot-v1-32k",
        "api_base_url": "https://api.moonshot.cn/v1",
        "api_protocol": "openai",
        "description": "Moonshot Kimi K2.6",
    },
    {
        "display_name": "MiniMax M2.5",
        "model_name": "abab6.5s-chat",
        "api_base_url": "https://api.minimax.chat/v1",
        "api_protocol": "openai",
        "description": "MiniMax M2.5",
    },
    {
        "display_name": "MiniMax M2.7",
        "model_name": "abab6.5-chat",
        "api_base_url": "https://api.minimax.chat/v1",
        "api_protocol": "openai",
        "description": "MiniMax M2.7",
    },
    {
        "display_name": "Qwen3 235B",
        "model_name": "qwen-max",
        "api_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_protocol": "openai",
        "description": "阿里云 Qwen3 235B",
    },
    {
        "display_name": "Qwen3 235B Instruct",
        "model_name": "qwen-plus",
        "api_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_protocol": "openai",
        "description": "阿里云 Qwen3 235B Instruct",
    },
]


def seed():
    app = create_app()
    with app.app_context():
        tenant = Tenant.query.filter_by(slug=GUEST_TENANT_SLUG).first()
        if not tenant:
            print(f"ERROR: tenant '{GUEST_TENANT_SLUG}' not found")
            sys.exit(1)

        created = 0
        skipped = 0
        for m in MODELS:
            exists = ModelConfig.query.filter_by(
                tenant_id=tenant.id,
                display_name=m["display_name"],
            ).first()
            if exists:
                print(f"  skip (already exists): {m['display_name']}")
                skipped += 1
                continue

            config = ModelConfig(
                tenant_id=tenant.id,
                display_name=m["display_name"],
                model_name=m["model_name"],
                api_base_url=m["api_base_url"],
                api_protocol=m["api_protocol"],
                description=m.get("description"),
                is_active=True,
            )
            db.session.add(config)
            print(f"  create: {m['display_name']}")
            created += 1

        db.session.commit()
        print(f"\nDone — created {created}, skipped {skipped}")


if __name__ == "__main__":
    seed()
