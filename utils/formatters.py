"""
搜索结果格式化工具。

将原始搜索结果统一格式化为可供 LLM 阅读的文本，并提供结果去重能力。
"""

from typing import Any


def format_search_results(results: list[dict[str, Any]]) -> str:
    """
    将搜索结果列表格式化为字符串。

    Args:
        results: 搜索结果列表，每个结果包含 title、url、snippet、provider 等字段

    Returns:
        格式化后的搜索摘要文本；结果为空时返回提示语
    """
    if not results:
        return "没有找到相关的网络信息。"

    formatted_string = "根据网络搜索结果：\n\n"
    for i, res in enumerate(results, 1):
        title = res.get("title", "无标题")
        url = res.get("url", "#")
        snippet = res.get("snippet", "无摘要")
        provider = res.get("provider", "未知来源")
        content = res.get("content", "")  # 完整网页内容

        formatted_string += f"{i}. **{title}** (来自: {provider})\n"
        formatted_string += f"   - 摘要: {snippet}\n"

        # 如果有完整内容，则显示完整内容而不仅仅是摘要
        if content:
            formatted_string += f"   - 页面内容:\n{content}\n"

        formatted_string += f"   - 来源: {url}\n\n"

    return formatted_string


def format_url_parse_results(results: list[dict[str, Any]]) -> str:
    """
    将成功解析的 URL 结果列表格式化为一段简洁的文本。

    Args:
        results: URL 解析结果列表，每个结果包含 title、url、snippet、source 等字段

    Returns:
        格式化后的 URL 解析文本
    """
    formatted_parts = []
    for res in results:
        title = res.get("title", "无标题")
        url = res.get("url", "#")
        snippet = res.get("snippet", "无摘要")
        source = res.get("source", "未知")

        formatted_string = f"**{title}**\n"
        formatted_string += f"**内容摘要**:\n{snippet}\n"
        formatted_string += f"**来源**: {url} (由 {source} 解析)\n"
        formatted_parts.append(formatted_string)

    return "\n---\n".join(formatted_parts)


def deduplicate_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    根据 URL 去重搜索结果。

    Args:
        results: 搜索结果列表

    Returns:
        去重后的搜索结果列表
    """
    unique_urls = set()
    unique_results = []
    for res in results:
        if isinstance(res, dict) and res.get("url") and res["url"] not in unique_urls:
            unique_urls.add(res["url"])
            unique_results.append(res)
    return unique_results
