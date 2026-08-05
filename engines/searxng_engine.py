"""
SearXNG 搜索引擎实现。

通过 SearXNG 的公开 JSON 接口执行元搜索，支持多实例轮询。

参考: https://docs.searxng.org/dev/search_api.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from src.app.plugin_system.api import log_api

from .base import BaseSearchEngine

if TYPE_CHECKING:
    from ..config import WebSearchConfig

logger = log_api.get_logger("searxng_engine")


class SearXNGSearchEngine(BaseSearchEngine):
    """
    SearXNG 元搜索引擎实现。

    通过配置提供 SearXNG 实例地址。
    """

    def __init__(self, config: "WebSearchConfig | None" = None):
        """
        初始化 SearXNG 搜索引擎。

        Args:
            config: 插件配置对象（可选）
        """
        super().__init__(config)
        self._load_config()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))

    def _load_config(self) -> None:
        """
        从配置加载 SearXNG 实例地址。

        Returns:
            None
        """
        # 从配置对象读取 SearXNG 实例地址
        if self.config:
            base_url = self.config.searxng.base_url
            self.instances: list[str] = [base_url.rstrip("/")] if base_url else []
        else:
            self.instances = []

        # SearXNG 通常不需要 API 密钥，这里保留为空列表
        self.api_keys: list[str | None] = []

        # 与实例列表对齐（若 keys 少则补 None）
        if self.api_keys and len(self.api_keys) < len(self.instances):
            self.api_keys.extend([None] * (len(self.instances) - len(self.api_keys)))

        logger.debug(f"SearXNG 引擎配置: instances={self.instances}, api_keys={'有' if any(self.api_keys) else '无'}")

    def is_available(self) -> bool:
        """
        检查 SearXNG 搜索引擎是否可用。

        Returns:
            True 表示已配置至少一个实例，否则为 False
        """
        return bool(self.instances)

    async def search(
        self,
        query: str,
        num_results: int = 3,
        time_range: str = "any"
    ) -> list[dict[str, Any]]:
        """
        执行 SearXNG 搜索。

        Args:
            query: 搜索查询关键词
            num_results: 返回结果数量，默认为 3
            time_range: 时间范围，可选值："any"、"week"、"month"，默认为 "any"

        Returns:
            搜索结果列表，每个结果包含 title、url、snippet、provider 字段；
            未配置实例时返回空列表
        """
        if not self.is_available():
            return []

        # SearXNG 的时间范围参数: day / week / month / year
        searx_time = None
        if time_range == "week":
            searx_time = "week"
        elif time_range == "month":
            searx_time = "month"

        # 轮询实例：简单使用循环尝试，直到获得结果或全部失败
        results: list[dict[str, Any]] = []
        for idx, base_url in enumerate(self.instances):
            token = self.api_keys[idx] if idx < len(self.api_keys) else None
            try:
                instance_results = await self._search_one_instance(base_url, query, num_results, searx_time, token)
                if instance_results:
                    results.extend(instance_results)
                if len(results) >= num_results:
                    break
            except Exception as e:
                logger.warning(f"SearXNG 实例 {base_url} 调用失败: {e}")
                continue

        # 截断到需要的数量
        return results[:num_results]

    async def _search_one_instance(
        self, base_url: str, query: str, num_results: int, searx_time: str | None, api_key: str | None
    ) -> list[dict[str, Any]]:
        """
        向单个 SearXNG 实例发起搜索请求。

        Args:
            base_url: SearXNG 实例地址
            query: 搜索查询关键词
            num_results: 返回结果数量
            searx_time: SearXNG 时间范围参数，可为 None
            api_key: 实例访问令牌，可为 None

        Returns:
            搜索结果列表，每个结果包含 title、url、snippet、provider 字段
        """
        # 构造 URL & 参数
        url = f"{base_url}/search"
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
            "language": "zh-CN",
            "safesearch": 1,
        }
        if searx_time:
            params["time_range"] = searx_time

        headers = {}
        if api_key:
            # SearXNG 可通过 Authorization 或 X-Token (取决于实例配置)，尝试常见方案
            headers["Authorization"] = f"Token {api_key}"

        # 发送异步 HTTP 请求
        try:
            resp = await self._client.get(url, params=params, headers=headers)
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"请求失败: {e}") from e

        try:
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"解析 JSON 失败: {e}") from e

        raw_results = data.get("results", []) if isinstance(data, dict) else []

        parsed: list[dict[str, Any]] = []
        for item in raw_results:
            title = item.get("title") or item.get("url", "无标题")
            url_item = item.get("url") or item.get("link", "")
            snippet = item.get("content") or item.get("snippet") or ""
            snippet = (snippet[:300] + "...") if len(snippet) > 300 else snippet
            parsed.append({"title": title, "url": url_item, "snippet": snippet, "provider": "SearXNG"})
            if len(parsed) >= num_results:  # 单实例限量
                break

        return parsed

    async def __aenter__(self) -> "SearXNGSearchEngine":
        """
        异步上下文管理器入口。

        Returns:
            当前实例
        """
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """
        异步上下文管理器出口，关闭底层 HTTP 客户端。

        Args:
            exc_type: 异常类型
            exc: 异常实例
            tb: 回溯对象
        """
        await self._client.aclose()
