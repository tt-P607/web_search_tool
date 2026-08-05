"""
Exa 搜索引擎实现。

使用 exa-py 客户端调用 Exa 的 search_and_contents 接口，支持多 API 密钥轮询。
"""

import asyncio
import functools
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from exa_py import Exa

from src.app.plugin_system.api import log_api

from ..utils.api_key_manager import create_api_key_manager_from_config
from .base import BaseSearchEngine

if TYPE_CHECKING:
    from ..config import WebSearchConfig

logger = log_api.get_logger("exa_engine")


class ExaSearchEngine(BaseSearchEngine):
    """
    Exa 搜索引擎实现。
    """

    def __init__(self, config: "WebSearchConfig | None" = None):
        """
        初始化 Exa 搜索引擎。

        Args:
            config: 插件配置对象（可选）
        """
        super().__init__(config)
        self._initialize_clients()

    def _initialize_clients(self) -> None:
        """初始化 Exa 客户端与 API 密钥管理器。"""
        # 从配置对象读取 API 密钥列表
        exa_api_keys = self.config.api_keys.exa_api_keys if self.config else []

        # 创建 API 密钥管理器
        self.api_manager = create_api_key_manager_from_config(exa_api_keys, "Exa")

    def is_available(self) -> bool:
        """
        检查 Exa 搜索引擎是否可用。

        Returns:
            True 表示存在可用 API 密钥，否则为 False
        """
        return self.api_manager.is_available()

    async def search(
        self,
        query: str,
        num_results: int = 5,
        time_range: str = "any"
    ) -> list[dict[str, Any]]:
        """
        执行 Exa 搜索（使用 search_and_contents 接口）。

        Args:
            query: 搜索查询关键词
            num_results: 返回结果数量，默认为 5（最多 5 条）
            time_range: 时间范围，可选值："any"、"week"、"month"，默认为 "any"

        Returns:
            搜索结果列表，每个结果包含 title、url、snippet、provider 字段；
            异常或未配置密钥时返回空列表
        """
        if not self.is_available():
            return []

        num_results = min(num_results, 5)  # 限制最多 5 个结果

        # 使用 search_and_contents 的参数格式
        exa_args = {
            "query": query,
            "num_results": num_results,
            "type": "auto",
        }

        # 时间范围过滤
        if time_range != "any":
            today = datetime.now()
            start_date = today - timedelta(days=7 if time_range == "week" else 30)
            exa_args["start_published_date"] = start_date.strftime("%Y-%m-%d")

        try:
            # 使用 API 密钥管理器获取下一个 API 密钥
            api_key = self.api_manager.get_next_key()
            if not api_key:
                logger.error("无法获取 Exa API 密钥")
                return []

            # 创建客户端
            exa_client = Exa(api_key=api_key)

            loop = asyncio.get_running_loop()
            # 使用 search_and_contents 方法
            func = functools.partial(exa_client.search_and_contents, **exa_args)
            search_response = await loop.run_in_executor(None, func)

            # 优化结果处理 - 更注重答案质量
            results = []
            for res in search_response.results:
                # 获取高亮内容或文本
                highlights = getattr(res, "highlights", [])
                text = getattr(res, "text", "")

                # 智能内容选择：高亮 > 文本开头
                if highlights and len(highlights) > 0:
                    snippet = " ".join(highlights[:3]).strip()
                elif text:
                    snippet = text[:300] + "..." if len(text) > 300 else text
                else:
                    snippet = "内容获取失败"

                # 只保留有意义的摘要
                if len(snippet) < 30:
                    snippet = text[:200] + "..." if text and len(text) > 200 else snippet

                results.append({
                    "title": res.title,
                    "url": res.url,
                    "snippet": snippet,
                    "provider": "Exa",
                    "answer_focused": True,  # 标记为答案导向的搜索
                })

            return results
        except Exception as e:
            logger.error(f"Exa搜索失败: {e}")
            return []
