"""
Web 搜索工具实现。

提供两个独立工具：
- ``web_search``：多引擎结构化搜索（Exa/Tavily/DuckDuckGo/Bing/SearXNG/Serper）
- ``deepseek_web_search``：DeepSeek 服务端联网搜索，返回完整自然语言回答
"""

import asyncio
from typing import TYPE_CHECKING, Annotated, Any

from src.app.plugin_system.api import log_api
from src.app.plugin_system.base import BaseTool
from src.app.plugin_system.types import ChatType

from ..config import WebSearchConfig
from ..engines.base import BaseSearchEngine
from ..engines.bing_engine import BingSearchEngine
from ..engines.ddg_engine import DDGSearchEngine
from ..engines.deepseek_engine import DeepSeekSearchEngine
from ..engines.exa_engine import ExaSearchEngine
from ..engines.searxng_engine import SearXNGSearchEngine
from ..engines.serper_engine import SerperSearchEngine
from ..engines.tavily_engine import TavilySearchEngine
from ..utils.formatters import deduplicate_results, format_search_results

if TYPE_CHECKING:
    from src.app.plugin_system.base import BasePlugin

logger = log_api.get_logger("web_search_tool")

# 多引擎结构化搜索工具描述（给 LLM 看的提示词）
_STRUCTURED_DESCRIPTION = (
    "联网搜索工具。当用户当前的问题或话题涉及以下情形时，无需用户明确要求，应主动调用：\n"
    "1. 时效性内容：近期新闻、时事动态、热点事件、赛事结果\n"
    "2. 快速变化的信息：产品价格、软件版本、近期发布或更新\n"
    "3. 具体数据、统计数字、排名等需要事实支撑的回答\n"
    "4. 你不确定或知识可能已过时的领域\n"
    "5. 用户提到某个具体人物、作品、事件，需要了解最新情况\n"
    "注意：\n"
    "- 仅根据用户当前正在询问的内容决定是否搜索，不要因历史对话中出现过某个话题就无关联地去搜索。\n"
    "- query 参数必须使用完整、详细的自然语言句子表达，严禁使用空格分隔的关键词、标签词拼凑或搜索引擎语法。\n"
    "返回的是多条搜索结果摘要，请将这些信息消化吸收后，用你自己的口吻自然表达出来。"
)

# DeepSeek 联网搜索工具描述（给 LLM 看的提示词）
_DEEPSEEK_DESCRIPTION = (
    "DeepSeek 联网搜索工具。使用 DeepSeek 模型自带的服务端联网搜索能力，"
    "会实时检索网络信息并整理成一段完整回答。\n"
    "当用户当前的问题或话题涉及以下情形时，无需用户明确要求，应主动调用：\n"
    "1. 时效性内容：近期新闻、时事动态、热点事件、赛事结果\n"
    "2. 快速变化的信息：产品价格、软件版本、近期发布或更新\n"
    "3. 具体数据、统计数字、排名等需要事实支撑的回答\n"
    "4. 你不确定或知识可能已过时的领域\n"
    "5. 用户提到某个具体人物、作品、事件，需要了解最新情况\n"
    "注意：\n"
    "- 仅根据用户当前正在询问的内容决定是否搜索，不要因历史对话中出现过某个话题就无关联地去搜索。\n"
    "- query 参数必须是完整、详细且富有上下文的自然语言提问句子（就像向真人对话提问一样），严禁使用空格分隔的关键词/标签词或加引号的短语。\n"
    "返回内容为整理后的联网信息，请将这些信息消化吸收后，用你自己的口吻自然表达出来。"
)


class WebSearchTool(BaseTool):
    """
    多引擎结构化网络搜索工具。
    """

    chat_type = ChatType.ALL
    name: str = "web_search"
    description: str = _STRUCTURED_DESCRIPTION

    # 结构化引擎映射（不含 summary 类型引擎）
    _ENGINE_CLASSES: dict[str, type[BaseSearchEngine]] = {
        "exa": ExaSearchEngine,
        "tavily": TavilySearchEngine,
        "ddg": DDGSearchEngine,
        "bing": BingSearchEngine,
        "searxng": SearXNGSearchEngine,
        "serper": SerperSearchEngine,
    }

    def __init__(self, plugin: "BasePlugin") -> None:
        """
        初始化多引擎搜索工具。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)

        # 获取配置对象
        self.config = (
            self.plugin.config
            if isinstance(self.plugin.config, WebSearchConfig)
            else None
        )

        # 初始化搜索引擎
        self.engines: dict[str, BaseSearchEngine] = {
            name: engine_cls(self.config)
            for name, engine_cls in self._ENGINE_CLASSES.items()
        }

    async def execute(
        self,
        query: Annotated[str, "要搜索的内容。必须使用完整详细的自然语言句子提问，严禁使用空格分隔的关键词/标签词拼凑或搜索引擎语法"],
        num_results: Annotated[int, "期望每个搜索引擎返回的搜索结果数量"] = 5,
        time_range: Annotated[str, "搜索时间范围：'any', 'week', 'month'"] = "any"
    ) -> tuple[bool, str | dict[str, Any]]:
        """
        执行网络搜索。

        Args:
            query: 要搜索的内容，用自然语言完整描述你想了解的问题，不要拆成零散关键词
            num_results: 期望每个搜索引擎返回的搜索结果数量，默认为 5
            time_range: 指定搜索的时间范围，可以是 'any'、'week'、'month'。默认为 'any'

        Returns:
            tuple[bool, str | dict]: (是否成功, 搜索结果或错误信息)
        """
        if not query:
            return False, "搜索查询不能为空。"

        # 读取搜索配置（类型安全，直接访问类型化字段）
        if self.config:
            enabled_engines = list(self.config.search.enabled_engines)
            search_strategy = self.config.search.search_strategy
        else:
            enabled_engines = ["ddg"]
            search_strategy = "single"

        logger.info(f"开始搜索，策略: {search_strategy}, 启用引擎: {enabled_engines}, 查询: '{query}'")

        # 根据策略执行搜索
        try:
            if search_strategy == "parallel":
                result = await self._execute_parallel_search(query, num_results, time_range, enabled_engines)
            elif search_strategy == "fallback":
                result = await self._execute_fallback_search(query, num_results, time_range, enabled_engines)
            else:  # single
                result = await self._execute_single_search(query, num_results, time_range, enabled_engines)

            # 检查结果中是否有错误
            if isinstance(result, dict) and "error" in result:
                return False, result["error"]

            return True, result

        except Exception as e:
            logger.error(f"执行网络搜索时发生异常: {e}")
            return False, f"执行网络搜索时发生严重错误: {e!s}"

    async def _execute_parallel_search(
        self, query: str, num_results: int, time_range: str, enabled_engines: list[str]
    ) -> dict[str, Any]:
        """
        并行搜索策略：同时使用所有启用的搜索引擎。

        Args:
            query: 搜索查询关键词
            num_results: 返回结果数量
            time_range: 时间范围
            enabled_engines: 启用的引擎列表

        Returns:
            搜索结果的 dict；无可用引擎时返回错误 dict
        """
        search_tasks = []

        for engine_name in enabled_engines:
            engine = self.engines.get(engine_name)
            if engine and engine.is_available():
                search_tasks.append(engine.search(query, num_results, time_range))

        if not search_tasks:
            return {"error": "没有可用的搜索引擎。"}

        try:
            search_results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)

            all_results = []
            for result in search_results_lists:
                if isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"搜索时发生错误: {result}")

            # 去重并格式化
            unique_results = deduplicate_results(all_results)
            formatted_content = format_search_results(unique_results)

            return {
                "type": "web_search_result",
                "content": formatted_content,
            }

        except Exception as e:
            logger.error(f"执行并行网络搜索时发生异常: {e}")
            return {"error": f"执行网络搜索时发生严重错误: {e!s}"}

    async def _execute_fallback_search(
        self, query: str, num_results: int, time_range: str, enabled_engines: list[str]
    ) -> dict[str, Any]:
        """
        回退搜索策略：按顺序尝试搜索引擎，失败则尝试下一个。

        Args:
            query: 搜索查询关键词
            num_results: 返回结果数量
            time_range: 时间范围
            enabled_engines: 启用的引擎列表

        Returns:
            搜索结果的 dict；全部引擎失败时返回错误 dict
        """
        for engine_name in enabled_engines:
            engine = self.engines.get(engine_name)
            if not engine or not engine.is_available():
                continue

            try:
                results = await engine.search(query, num_results, time_range)

                if results:  # 如果有结果，直接返回
                    formatted_content = format_search_results(results)
                    return {
                        "type": "web_search_result",
                        "content": formatted_content,
                    }

            except Exception as e:
                logger.warning(f"{engine_name} 搜索失败，尝试下一个引擎: {e}")
                continue

        return {"error": "所有搜索引擎都失败了。"}

    async def _execute_single_search(
        self, query: str, num_results: int, time_range: str, enabled_engines: list[str]
    ) -> dict[str, Any]:
        """
        单一搜索策略：只使用第一个可用的搜索引擎。

        Args:
            query: 搜索查询关键词
            num_results: 返回结果数量
            time_range: 时间范围
            enabled_engines: 启用的引擎列表

        Returns:
            搜索结果的 dict；无可用引擎时返回错误 dict
        """
        for engine_name in enabled_engines:
            engine = self.engines.get(engine_name)
            if not engine or not engine.is_available():
                continue

            try:
                results = await engine.search(query, num_results, time_range)

                if results:
                    formatted_content = format_search_results(results)
                    return {
                        "type": "web_search_result",
                        "content": formatted_content,
                    }

            except Exception as e:
                logger.error(f"{engine_name} 搜索失败: {e}")
                return {"error": f"{engine_name} 搜索失败: {e!s}"}

        return {"error": "没有可用的搜索引擎。"}


class DeepSeekWebSearchTool(BaseTool):
    """
    DeepSeek 服务端联网搜索工具。

    使用 DeepSeek Responses API 的服务端 web_search 内置工具，返回完整自然语言回答。
    """

    chat_type = ChatType.ALL
    name: str = "deepseek_web_search"
    description: str = _DEEPSEEK_DESCRIPTION

    def __init__(self, plugin: "BasePlugin") -> None:
        """
        初始化 DeepSeek 联网搜索工具。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)

        # 获取配置对象
        self.config = (
            self.plugin.config
            if isinstance(self.plugin.config, WebSearchConfig)
            else None
        )
        self.engine = DeepSeekSearchEngine(self.config)

    async def execute(
        self,
        query: Annotated[str, "要搜索的问题。必须使用完整详细且富有上下文的自然语言提问句子（就像向真人对话提问一样），严禁拆成关键词、标签词或加引号短语"],
    ) -> tuple[bool, str | dict[str, Any]]:
        """
        执行 DeepSeek 服务端联网搜索。

        Args:
            query: 要搜索的问题，直接用自然语言完整描述

        Returns:
            tuple[bool, str | dict]: (是否成功, 搜索结果或错误信息)
        """
        if not query:
            return False, "搜索查询不能为空。"

        if not self.engine.is_available():
            logger.warning("DeepSeek 引擎未启用或未配置 API 密钥")
            return False, "DeepSeek 联网搜索未启用。"

        try:
            results = await self.engine.search(query)
            if not results:
                return False, "DeepSeek 联网搜索未返回结果。"

            return True, {
                "type": "final_answer",
                "content": results[0].get("snippet", ""),
            }

        except Exception as e:
            logger.error(f"执行 DeepSeek 联网搜索时发生异常: {e}")
            return False, f"执行 DeepSeek 联网搜索时发生严重错误: {e!s}"
