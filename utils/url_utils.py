"""
URL 处理工具。

提供从输入中解析 URL 列表与校验 URL 格式的能力。
"""

import re


def parse_urls_from_input(urls_input: str | list[str] | None) -> list[str]:
    """
    从输入中解析 URL 列表。

    Args:
        urls_input: 输入内容，可以是包含 URL 的字符串或 URL 字符串列表

    Returns:
        解析出的 URL 列表；无法解析时返回空列表
    """
    if isinstance(urls_input, str):
        # 如果是字符串，尝试解析为 URL 列表
        # 提取所有 HTTP/HTTPS URL
        url_pattern = r"https?://[^\s\],]+"
        urls = re.findall(url_pattern, urls_input)
        if not urls:
            # 如果没有找到标准 URL，将整个字符串作为单个 URL
            if urls_input.strip().startswith(("http://", "https://")):
                urls = [urls_input.strip()]
            else:
                return []
    elif isinstance(urls_input, list):
        urls = [url.strip() for url in urls_input if isinstance(url, str) and url.strip()]
    else:
        return []

    return urls


def validate_urls(urls: list[str]) -> list[str]:
    """
    验证 URL 格式，返回有效的 URL 列表。

    Args:
        urls: 待校验的 URL 列表

    Returns:
        格式有效的 URL 列表（仅保留 http/https 前缀的条目）
    """
    return [url for url in urls if url.startswith(("http://", "https://"))]
