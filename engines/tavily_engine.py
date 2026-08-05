"""
Tavily 搜索引擎实现。

使用 tavily-python 客户端调用 Tavily 搜索接口。
"""

import asyncio
import functools
from typing import TYPE_CHECKING, Any

from tavily import TavilyClient

from src.app.plugin_system.api import log_api

from ..utils.api_key_manager import create_api_key_manager_from_config
from .base import BaseSearchEngine

if TYPE_CHECKING:
    from ..config import WebSearchConfig

logger = log_api.get_logger("tavily_engine")


class TavilySearchEngine(BaseSearchEngine):
    """
    Tavily 搜索引擎实现。
    """

    def __init__(self, config: "WebSearchConfig | None" = None):
        """
        初始化 Tavily 搜索引擎。

        Args:
            config: 插件配置对象（可选）
        """
        super().__init__(config)
        self._initialize_clients()

    def _initialize_clients(self) -> None:
        """初始化 Tavily 客户端与 API 密钥管理器。"""
        # 从配置对象读取 API 密钥
        tavily_api_key = self.config.api_keys.tavily_api_key if self.config else ""

        # 创建 API 密钥管理器
        self.api_manager = create_api_key_manager_from_config(
            tavily_api_key, "Tavily"
        )

    def is_available(self) -> bool:
        """
        检查 Tavily 搜索引擎是否可用。

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
        执行 Tavily 搜索。

        Args:
            query: 搜索查询关键词
            num_results: 返回结果数量，默认为 3
            time_range: 时间范围，可选值："any"、"week"、"month"，默认为 "any"

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
                logger.error("无法获取 Tavily API 密钥")
                return []

            # 创建客户端
            tavily_client = TavilyClient(api_key=api_key)

            # 构建 Tavily 搜索参数
            search_params = {
                "query": query,
                "max_results": num_results,
                "search_depth": "basic",
                "include_answer": False,
                "include_raw_content": False,
            }

            # 根据时间范围调整搜索参数
            if time_range == "week":
                search_params["days"] = 7
            elif time_range == "month":
                search_params["days"] = 30

            loop = asyncio.get_running_loop()
            func = functools.partial(tavily_client.search, **search_params)
            search_response = await loop.run_in_executor(None, func)

            results: list[dict[str, Any]] = []
            if search_response and "results" in search_response:
                results.extend(
                    {
                        "title": res.get("title", "无标题"),
                        "url": res.get("url", ""),
                        "snippet": res.get("content", "")[:300] + "..." if res.get("content") else "无摘要",
                        "provider": "Tavily",
                    }
                    for res in search_response["results"]
                )

            return results

        except Exception as e:
            logger.error(f"Tavily 搜索失败: {e}")
            return []
