"""
DeepSeek 联网搜索引擎实现。

通过 DeepSeek Responses API 的服务端 web_search 内置工具完成联网搜索，
DeepSeek 服务端负责网页检索与内容整理，返回模型生成的自然语言总结。
"""

from typing import TYPE_CHECKING, Any

from src.app.plugin_system.api import log_api

from .base import BaseSearchEngine

if TYPE_CHECKING:
    from ..config import WebSearchConfig

logger = log_api.get_logger("deepseek_engine")


class DeepSeekSearchEngine(BaseSearchEngine):
    """
    基于 DeepSeek Responses API 服务端 web_search 的搜索实现。

    调用一次 ``responses.create`` 并携带 ``tools=[{"type": "web_search"}]``，
    由 DeepSeek 服务端完成网页检索与内容整理，``output_text`` 即为可直接
    使用的自然语言总结，而非结构化链接列表。
    """

    output_kind: str = "summary"

    def __init__(self, config: "WebSearchConfig | None" = None) -> None:
        """
        初始化 DeepSeek 搜索实现。

        Args:
            config: 插件配置对象（可选）
        """
        super().__init__(config)

    def is_available(self) -> bool:
        """
        检查 DeepSeek 引擎是否可用（需要配置 API 密钥）。

        Returns:
            bool: 配置了非空 API 密钥时为 True
        """
        return bool(self.config and self.config.deepseek.api_key.strip())

    async def search(
        self,
        query: str,
        num_results: int = 5,
        time_range: str = "any"
    ) -> list[dict[str, Any]]:
        """
        执行 DeepSeek 服务端联网搜索，返回自然语言总结。

        Args:
            query: 搜索查询关键词
            num_results: 为兼容引擎接口保留；DeepSeek 服务端自行决定检索条数
            time_range: 为兼容引擎接口保留；DeepSeek 服务端暂不支持时间过滤

        Returns:
            包含单条结果的列表：title 为查询词、snippet 为模型整理后的总结。
            异常或未配置密钥时返回空列表。
        """
        if not self.is_available():
            logger.warning("DeepSeek API 密钥未配置，无法使用 DeepSeek 引擎")
            return []
        if self.config is None:
            return []

        try:
            from openai import AsyncOpenAI

            section = self.config.deepseek
            client = AsyncOpenAI(
                api_key=section.api_key,
                base_url=section.base_url,
            )
            response = await client.responses.create(
                model=section.model,
                instructions=section.instructions,
                input=query,
                tools=[{"type": "web_search"}],
                max_output_tokens=section.max_output_tokens,
            )

            output_text = getattr(response, "output_text", "")
            if not output_text or not output_text.strip():
                logger.warning("DeepSeek 返回空的 output_text")
                return []

            return [{
                "title": query,
                "url": "",
                "snippet": output_text.strip(),
                "provider": "DeepSeek",
            }]
        except Exception as e:
            logger.error(f"DeepSeek 搜索失败: {e}")
            return []
