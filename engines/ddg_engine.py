"""
DuckDuckGo 搜索引擎实现。

使用 asyncddgs 库异步调用 DuckDuckGo 搜索接口，无需 API 密钥。
"""

from typing import TYPE_CHECKING, Any

from asyncddgs import aDDGS

from src.app.plugin_system.api import log_api

from .base import BaseSearchEngine

if TYPE_CHECKING:
    from ..config import WebSearchConfig

logger = log_api.get_logger("ddg_engine")


class DDGSearchEngine(BaseSearchEngine):
    """
    DuckDuckGo 搜索引擎实现。
    """

    def __init__(self, config: "WebSearchConfig | None" = None):
        """
        初始化 DuckDuckGo 搜索引擎。

        Args:
            config: 插件配置对象（可选）
        """
        super().__init__(config)

    def is_available(self) -> bool:
        """
        检查 DuckDuckGo 搜索引擎是否可用。

        Returns:
            DuckDuckGo 不需要 API 密钥，始终返回 True
        """
        return True

    async def search(
        self,
        query: str,
        num_results: int = 3,
        time_range: str = "any"
    ) -> list[dict[str, Any]]:
        """
        执行 DuckDuckGo 搜索。

        Args:
            query: 搜索查询关键词
            num_results: 返回结果数量，默认为 3
            time_range: 时间范围（DuckDuckGo 不支持，保留用于接口兼容）

        Returns:
            搜索结果列表，每个结果包含 title、url、snippet、provider 字段；
            异常时返回空列表
        """
        try:
            async with aDDGS() as ddgs:
                search_response = await ddgs.text(query, max_results=num_results)

            return [
                {"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body"), "provider": "DuckDuckGo"}
                for r in search_response
            ]
        except Exception as e:
            logger.error(f"DuckDuckGo 搜索失败: {e}")
            return []
