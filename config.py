"""Web Search Tool 插件的配置定义。"""
from __future__ import annotations

from typing import ClassVar

from src.core.components.base.config import BaseConfig, Field, SectionBase, config_section


class WebSearchConfig(BaseConfig):
    """网络搜索工具插件配置"""

    name: ClassVar[str] = "config"
    description: ClassVar[str] = "网络搜索工具插件配置"

    @config_section("plugin", title="插件设置", tag="plugin")
    class PluginSection(SectionBase):
        """插件基本配置"""

        enabled: bool = Field(
            default=True,
            description="是否启用插件",
            label="启用插件",
            tag="plugin",
            order=0
        )
        version: str = Field(
            default="1.0.0",
            description="插件版本",
            label="插件版本",
            disabled=True,
            tag="general",
            order=1
        )

    @config_section("components", title="组件配置", tag="plugin")
    class ComponentsSection(SectionBase):
        """组件启用配置"""

        enable_web_search_tool: bool = Field(
            default=True,
            description="是否启用网络搜索工具（多引擎结构化搜索）",
            label="启用搜索工具",
            tag="plugin",
            order=0
        )
        enable_deepseek_tool: bool = Field(
            default=False,
            description="是否启用 DeepSeek 联网搜索工具（独立工具，返回完整自然语言回答）",
            label="启用 DeepSeek 工具",
            tag="plugin",
            order=1
        )
        enable_web_search_service: bool = Field(
            default=True,
            description="是否启用网络搜索服务",
            label="启用搜索服务",
            tag="plugin",
            order=2
        )

    @config_section("proxy", title="代理配置", tag="network")
    class ProxySection(SectionBase):
        """代理配置"""

        enable_proxy: bool = Field(
            default=False,
            description="是否启用代理",
            label="启用代理",
            tag="network",
            order=0
        )
        http_proxy: str | None = Field(
            default=None,
            description="HTTP代理地址，格式如: http://proxy.example.com:8080",
            label="HTTP 代理",
            placeholder="http://proxy.example.com:8080",
            tag="network",
            depends_on="enable_proxy",
            depends_value=True,
            order=1
        )
        https_proxy: str | None = Field(
            default=None,
            description="HTTPS代理地址，格式如: http://proxy.example.com:8080",
            label="HTTPS 代理",
            placeholder="http://proxy.example.com:8080",
            tag="network",
            depends_on="enable_proxy",
            depends_value=True,
            order=2
        )
        socks5_proxy: str | None = Field(
            default=None,
            description="SOCKS5代理地址，格式如: socks5://proxy.example.com:1080",
            label="SOCKS5 代理",
            placeholder="socks5://proxy.example.com:1080",
            tag="network",
            depends_on="enable_proxy",
            depends_value=True,
            order=3
        )

    @config_section("api_keys", title="API 密钥", tag="security")
    class ApiKeysSection(SectionBase):
        """API密钥配置"""

        exa_api_keys: list[str] = Field(
            default=[],
            description="Exa搜索引擎API密钥列表（支持轮询）",
            label="Exa API Keys",
            input_type="list",
            item_type="str",
            placeholder="输入 Exa API Key",
            tag="security",
            order=0
        )
        tavily_api_key: str = Field(
            default="",
            description="Tavily搜索引擎API密钥",
            label="Tavily API Key",
            input_type="password",
            placeholder="输入 Tavily API Key",
            tag="security",
            order=1
        )
        metaso_api_key: str = Field(
            default="",
            description="Metaso搜索引擎API密钥",
            label="Metaso API Key",
            input_type="password",
            placeholder="输入 Metaso API Key",
            tag="security",
            order=2
        )
        serper_api_key: str = Field(
            default="",
            description="Serper搜索引擎API密钥",
            label="Serper API Key",
            input_type="password",
            placeholder="输入 Serper API Key",
            tag="security",
            order=3
        )

    @config_section("search", title="搜索配置", tag="general")
    class SearchSection(SectionBase):
        """搜索配置"""

        default_engine: str = Field(
            default="bing",
            description="默认搜索引擎 (exa/tavily/metaso/ddg/bing/searxng/serper)",
            label="默认引擎",
            input_type="select",
            choices=["exa", "tavily", "metaso", "ddg", "bing", "searxng", "serper"],
            tag="general",
            order=0
        )
        enabled_engines: list[str] = Field(
            default=["bing"],
            description="启用的搜索引擎列表",
            label="启用的引擎",
            input_type="list",
            item_type="str",
            tag="list",
            hint="可选：exa, tavily, metaso, ddg, bing, searxng, serper",
            order=1
        )
        search_strategy: str = Field(
            default="single",
            description="搜索策略：single(单引擎)/parallel(并行)/fallback(回退)",
            label="搜索策略",
            input_type="select",
            choices=["single", "parallel", "fallback"],
            tag="performance",
            order=2
        )
        max_results: int = Field(
            default=10,
            description="搜索返回的最大结果数",
            label="最大结果数",
            ge=1,
            le=50,
            input_type="slider",
            tag="performance",
            order=3
        )
        timeout: int = Field(
            default=30,
            description="搜索超时时间（秒）",
            label="超时时间",
            ge=5,
            le=120,
            input_type="slider",
            tag="network",
            order=4
        )

    @config_section("searxng", title="SearXNG 配置", tag="network")
    class SearXNGSection(SectionBase):
        """SearXNG搜索引擎配置"""

        base_url: str = Field(
            default="http://localhost:8080",
            description="SearXNG实例地址",
            label="实例地址",
            placeholder="http://localhost:8080",
            tag="network",
            order=0
        )

    @config_section("bing", title="Bing 配置", tag="network")
    class BingSection(SectionBase):
        """Bing搜索引擎配置"""

        fetch_page_content: bool = Field(
            default=True,
            description="是否抓取搜索结果页面的完整内容",
            label="抓取页面内容",
            tag="general",
            order=0
        )
        content_max_length: int = Field(
            default=3000,
            description="抓取的页面内容最大长度（字符数）",
            label="内容最大长度",
            ge=500,
            le=10000,
            input_type="slider",
            tag="performance",
            depends_on="fetch_page_content",
            depends_value=True,
            order=1
        )
        max_concurrent_fetches: int = Field(
            default=3,
            description="并发抓取页面内容的最大数量",
            label="最大并发抓取",
            ge=1,
            le=10,
            tag="performance",
            depends_on="fetch_page_content",
            depends_value=True,
            order=2
        )
        abstract_max_length: int = Field(
            default=300,
            description="搜索结果摘要的最大长度（字符数）",
            label="摘要最大长度",
            ge=100,
            le=1000,
            tag="text",
            order=3
        )
        request_timeout: int = Field(
            default=10,
            description="请求超时时间（秒）",
            label="请求超时",
            ge=3,
            le=60,
            input_type="slider",
            tag="network",
            order=4
        )
        content_fetch_timeout: int = Field(
            default=8,
            description="抓取页面内容的超时时间（秒）",
            label="内容抓取超时",
            ge=3,
            le=30,
            input_type="slider",
            tag="network",
            depends_on="fetch_page_content",
            depends_value=True,
            order=5
        )

    @config_section("deepseek", title="DeepSeek 配置", tag="network")
    class DeepSeekSection(SectionBase):
        """DeepSeek 联网搜索配置"""

        enabled: bool = Field(
            default=False,
            description="是否启用 DeepSeek 联网搜索",
            label="启用 DeepSeek",
            tag="plugin",
            order=0
        )
        api_key: str = Field(
            default="",
            description="DeepSeek API 密钥",
            label="DeepSeek API Key",
            input_type="password",
            placeholder="输入 DeepSeek API Key",
            tag="security",
            order=1
        )
        base_url: str = Field(
            default="https://api.deepseek.com",
            description="DeepSeek Responses API 基础地址",
            label="API 基础地址",
            placeholder="https://api.deepseek.com",
            tag="network",
            order=2
        )
        model: str = Field(
            default="deepseek-v4-flash",
            description="DeepSeek 模型名称（当前仅支持 deepseek-v4-flash）",
            label="模型",
            tag="network",
            order=3
        )
        max_output_tokens: int = Field(
            default=4096,
            description="联网搜索总结的最大输出 token 数",
            label="最大输出 token",
            ge=64,
            le=8192,
            input_type="slider",
            tag="performance",
            order=4
        )
        instructions: str = Field(
            default="你是一个联网搜索助手。请基于实时搜索结果，用简体中文简洁准确地回答用户的问题，并在回答末尾列出信息来源链接。",
            description="发送给模型的指令（instructions）",
            label="模型指令",
            tag="general",
            order=5
        )

    # 配置节实例
    plugin: PluginSection = Field(default_factory=PluginSection)
    components: ComponentsSection = Field(default_factory=ComponentsSection)
    proxy: ProxySection = Field(default_factory=ProxySection)
    api_keys: ApiKeysSection = Field(default_factory=ApiKeysSection)
    search: SearchSection = Field(default_factory=SearchSection)
    deepseek: DeepSeekSection = Field(default_factory=DeepSeekSection)
    searxng: SearXNGSection = Field(default_factory=SearXNGSection)
    bing: BingSection = Field(default_factory=BingSection)
