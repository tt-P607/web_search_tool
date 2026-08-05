"""
Metaso 搜索引擎实现（聊天补全模式）。

通过 Metaso 的 chat/completions 流式接口返回模型整理的自然语言总结。
"""

from typing import TYPE_CHECKING, Any

import httpx
import orjson

from src.app.plugin_system.api import log_api

from ..utils.api_key_manager import create_api_key_manager_from_config
from .base import BaseSearchEngine

if TYPE_CHECKING:
    from ..config import WebSearchConfig

logger = log_api.get_logger(__name__)


class MetasoClient:
    """
    用于与 Metaso API 交互的客户端。

    封装 Metaso 聊天补全接口的流式请求与响应解析。
    """

    def __init__(self, api_key: str):
        """
        初始化 Metaso 客户端。

        Args:
            api_key: Metaso API 密钥
        """
        self.api_key = api_key
        self.base_url = "https://metaso.cn/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """
        使用 Metaso 聊天补全 API 执行搜索。

        Args:
            query: 搜索查询关键词
            **kwargs: 预留的扩展参数

        Returns:
            包含单条结果的列表：title 为查询词、snippet 为模型整理后的总结；
            异常时返回空列表
        """
        payload = {"model": "fast", "stream": True, "messages": [{"role": "user", "content": query}]}
        search_url = f"{self.base_url}/chat/completions"
        full_response_content = ""

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                async with client.stream("POST", search_url, headers=self.headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_str = line[len("data:") :].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = orjson.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content_chunk = delta.get("content")
                                if content_chunk:
                                    full_response_content += content_chunk
                            except orjson.JSONDecodeError:
                                logger.warning(f"Metaso 流式响应：无法解码 JSON 行：{data_str}")
                                continue

                if not full_response_content:
                    logger.warning("Metaso 搜索返回了空的流式响应。")
                    return []

                return [
                    {
                        "title": query,
                        "url": "https://metaso.cn/",
                        "snippet": full_response_content,
                        "provider": "Metaso (Chat)",
                    }
                ]
            except httpx.HTTPStatusError as e:
                logger.error(f"使用 Metaso Chat 搜索时发生 HTTP 错误：{e.response.text}")
                return []
            except Exception as e:
                logger.error(f"使用 Metaso Chat 搜索时发生错误：{e}")
                return []


class MetasoSearchEngine(BaseSearchEngine):
    """
    Metaso 搜索引擎实现。
    """

    output_kind: str = "summary"

    def __init__(self, config: "WebSearchConfig | None" = None):
        """
        初始化 Metaso 搜索引擎。

        Args:
            config: 插件配置对象（可选）
        """
        super().__init__(config)
        self._initialize_clients()

    def _initialize_clients(self) -> None:
        """初始化 Metaso 客户端与 API 密钥管理器。"""
        # 从配置对象读取 API 密钥
        metaso_api_key = self.config.api_keys.metaso_api_key if self.config else ""

        # 创建 API 密钥管理器
        self.api_manager = create_api_key_manager_from_config(
            metaso_api_key, "Metaso"
        )

    def is_available(self) -> bool:
        """
        检查 Metaso 搜索引擎是否可用。

        Returns:
            True 表示存在可用 API 密钥，否则为 False
        """
        return self.api_manager.is_available()

    async def search(
        self,
        query: str,
        num_results: int = 3,
        time_range: str = "any"
    ) -> list[dict[str, Any]]:
        """
        执行 Metaso 搜索。

        Args:
            query: 搜索查询关键词
            num_results: 为兼容引擎接口保留；Metaso 由模型自行决定内容长度
            time_range: 为兼容引擎接口保留；Metaso 暂不支持时间过滤

        Returns:
            搜索结果列表，每个结果包含 title、url、snippet、provider 字段；
            异常或未配置密钥时返回空列表
        """
        if not self.is_available():
            return []
        try:
            # 使用 API 密钥管理器获取下一个 API 密钥
            api_key = self.api_manager.get_next_key()
            if not api_key:
                logger.error("无法获取 Metaso API 密钥。")
                return []

            # 创建客户端
            metaso_client = MetasoClient(api_key=api_key)

            return await metaso_client.search(query)
        except Exception as e:
            logger.error(f"Metaso 搜索失败：{e}")
            return []
