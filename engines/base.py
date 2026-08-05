"""
搜索引擎抽象基类。

定义所有搜索引擎的统一接口与输出形态约定。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config import WebSearchConfig


class BaseSearchEngine(ABC):
    """
    搜索引擎基类。

    子类需实现 ``search`` 与 ``is_available``，可选覆盖 ``read_url``。
    """

    # 引擎输出形态：
    # - "summary": 返回完整自然语言总结（如 DeepSeek、Metaso），供 LLM 直接采用
    # - "results": 返回结构化结果列表（title/url/snippet），供 LLM 整合
    output_kind: str = "results"

    def __init__(self, config: "WebSearchConfig | None" = None):
        """
        初始化搜索引擎。

        Args:
            config: 插件配置对象（可选）
        """
        self.config = config

    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 3,
        time_range: str = "any"
    ) -> list[dict[str, Any]]:
        """
        执行搜索。

        Args:
            query: 搜索查询关键词
            num_results: 返回结果数量，默认为 3
            time_range: 时间范围，可选值："any"、"week"、"month"，默认为 "any"

        Returns:
            搜索结果列表，每个结果包含 title、url、snippet、provider 字段；
            搜索失败时返回空列表
        """
        pass

    async def read_url(self, url: str) -> str | None:
        """
        读取 URL 内容。

        Args:
            url: 待读取的 URL 地址

        Returns:
            URL 的文本内容；引擎不支持时返回 None
        """
        return None

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查搜索引擎是否可用。

        Returns:
            True 表示引擎可用，否则为 False
        """
        pass
