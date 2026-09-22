"""统一客户端与环境配置模块

遵循 KISS 原则与依赖注入理念：
- 单点管理凭证读取与客户端实例化
- 封装 TypeSafeClient（Jev 快速判断 System One）
- 封装基于 OpenAI 协议的 LLM Client（System Two 慢思考）
"""

import os

from dotenv import load_dotenv
from openai import OpenAI
from typesafe_sdk import TypeSafeClient

# 加载 .env 环境变量
load_dotenv()


def get_typesafe_client(api_key: str | None = None) -> TypeSafeClient:
    """获取 TypeSafe Jev 客户端实例。

    优先使用传入的 api_key，其次从 TYPESAFE_API_KEY 环境变量读取。
    """
    key = api_key or os.getenv("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError("未检测到 TYPESAFE_API_KEY，请在 .env 中配置或导出环境变量")
    return TypeSafeClient(api_key=key)


def get_llm_client(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> tuple[OpenAI, str]:
    """获取大语言模型客户端实例和模型名称

    返回:
        tuple[OpenAI, str]: (OpenAI客户端实例, 模型名称)
    """
    key = api_key or os.getenv("API_KEY")
    if not key:
        raise RuntimeError("未检测到 API 密钥")

    url = base_url or os.getenv("BASE_URL")
    if not url:
        raise RuntimeError("未检测到 base_url")

    model_id = model or os.getenv("MODEL_ID")
    if not model_id:
        raise RuntimeError("未检测到 model_id")

    client = OpenAI(
        api_key=key,
        base_url=url,
    )
    return client, model_id
