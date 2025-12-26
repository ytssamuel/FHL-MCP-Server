"""
FHL Bible MCP Server - HTTP Server for Smithery.ai

This module provides a Streamable HTTP transport for the MCP server,
compatible with Smithery.ai deployment using FastMCP.

Based on Smithery requirements:
https://smithery.ai/docs/migrations/python-custom-container
"""

import os
import logging
import json
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

# Import all tool functions
from fhl_bible_mcp.tools.verse import (
    get_bible_verse,
    get_bible_chapter,
    query_verse_citation,
)
from fhl_bible_mcp.tools.search import (
    search_bible,
    search_bible_advanced,
)
from fhl_bible_mcp.tools.strongs import (
    get_word_analysis,
    lookup_strongs,
    search_strongs_occurrences,
)
from fhl_bible_mcp.tools.commentary import (
    get_commentary,
    list_commentaries,
    search_commentary,
    get_topic_study,
)
from fhl_bible_mcp.tools.info import (
    list_bible_versions,
    get_book_list,
    get_book_info,
    search_available_versions,
)
from fhl_bible_mcp.tools.audio import (
    get_audio_bible,
    list_audio_versions,
    get_audio_chapter_with_text,
)
from fhl_bible_mcp.tools.apocrypha import (
    handle_get_apocrypha_verse,
    handle_search_apocrypha,
    handle_list_apocrypha_books,
)
from fhl_bible_mcp.tools.apostolic_fathers import (
    handle_get_apostolic_fathers_verse,
    handle_search_apostolic_fathers,
    handle_list_apostolic_fathers_books,
)
from fhl_bible_mcp.tools.footnotes import (
    handle_get_bible_footnote,
)
from fhl_bible_mcp.tools.articles import (
    handle_search_articles,
    handle_list_article_columns,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(name="FHL Bible MCP Server")


# ============================================================================
# Smithery Config Middleware
# ============================================================================

class SmitheryConfigMiddleware:
    """
    Middleware for extracting Smithery session configuration from URL parameters.
    Uses the Smithery SDK's dot+bracket notation parser.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope.get('type') == 'http':
            try:
                # Try to use smithery SDK for config parsing
                from smithery.utils.config import parse_config_from_asgi_scope
                scope['smithery_config'] = parse_config_from_asgi_scope(scope)
            except ImportError:
                # Fallback: simple query parameter parsing
                scope['smithery_config'] = self._parse_query_params(scope)
            except Exception as e:
                logger.warning(f"SmitheryConfigMiddleware: Error parsing config: {e}")
                scope['smithery_config'] = {}
        
        await self.app(scope, receive, send)
    
    def _parse_query_params(self, scope) -> dict:
        """Fallback query parameter parser."""
        from urllib.parse import parse_qs
        query_string = scope.get('query_string', b'').decode('utf-8')
        params = parse_qs(query_string)
        # Convert single-value lists to values
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}


# ============================================================================
# Configuration Helpers
# ============================================================================

def get_request_config() -> dict:
    """Get full config from current request context."""
    try:
        import contextvars
        request = contextvars.copy_context().get('request')
        if hasattr(request, 'scope') and request.scope:
            return request.scope.get('smithery_config', {})
    except Exception:
        pass
    return {}


def get_config_value(key: str, default=None):
    """Get a specific config value from current request."""
    config = get_request_config()
    return config.get(key, default)


# ============================================================================
# Verse Query Tools
# ============================================================================

@mcp.tool()
async def get_bible_verse_tool(
    book: str,
    chapter: int,
    verse: str = None,
    version: str = "unv",
    include_strong: bool = False,
    use_simplified: bool = False
) -> str:
    """查詢指定的聖經經文。支援單節、多節、節範圍查詢。
    
    Args:
        book: 經卷名稱（中文或英文縮寫，如：約、John、創世記、Genesis）
        chapter: 章數
        verse: 節數（支援格式：'1', '1-5', '1,3,5', '1-2,5,8-10'）。若不提供則返回整章
        version: 聖經版本代碼（預設：unv）
        include_strong: 是否包含 Strong's Number（預設：false）
        use_simplified: 是否使用簡體中文（預設：false）
    """
    result = await get_bible_verse(
        book=book,
        chapter=chapter,
        verse=verse,
        version=version,
        include_strong=include_strong,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_bible_chapter_tool(
    book: str,
    chapter: int,
    version: str = "unv",
    use_simplified: bool = False
) -> str:
    """查詢整章聖經經文。
    
    Args:
        book: 經卷名稱
        chapter: 章數
        version: 聖經版本代碼（預設：unv）
        use_simplified: 是否使用簡體中文
    """
    result = await get_bible_chapter(
        book=book,
        chapter=chapter,
        version=version,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def query_verse_citation_tool(
    citation: str,
    version: str = "unv",
    include_strong: bool = False,
    use_simplified: bool = False
) -> str:
    """解析並查詢經文引用字串（如：'約 3:16', '太 5:3-10'）。
    
    Args:
        citation: 經文引用字串
        version: 聖經版本代碼
        include_strong: 是否包含 Strong's Number
        use_simplified: 是否使用簡體中文
    """
    result = await query_verse_citation(
        citation=citation,
        version=version,
        include_strong=include_strong,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Search Tools
# ============================================================================

@mcp.tool()
async def search_bible_tool(
    query: str,
    search_type: str = "keyword",
    scope: str = "all",
    version: str = "unv",
    limit: int = 50,
    use_simplified: bool = False
) -> str:
    """在聖經中搜尋關鍵字或原文編號。
    
    Args:
        query: 搜尋內容
        search_type: 搜尋類型（keyword=關鍵字, greek_number=希臘文編號, hebrew_number=希伯來文編號）
        scope: 搜尋範圍（all=全部, ot=舊約, nt=新約）
        version: 聖經版本代碼
        limit: 最多返回筆數
        use_simplified: 是否使用簡體中文
    """
    result = await search_bible(
        query=query,
        search_type=search_type,
        scope=scope,
        version=version,
        limit=limit,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def search_bible_advanced_tool(
    query: str,
    search_type: str = "keyword",
    range_start: int = None,
    range_end: int = None,
    version: str = "unv",
    limit: int = 50,
    offset: int = 0,
    use_simplified: bool = False
) -> str:
    """進階聖經搜尋，支援自訂書卷範圍。
    
    Args:
        query: 搜尋內容
        search_type: 搜尋類型（keyword/greek_number/hebrew_number）
        range_start: 起始書卷編號 (1-66)
        range_end: 結束書卷編號 (1-66)
        version: 聖經版本代碼
        limit: 最多返回筆數
        offset: 跳過筆數
        use_simplified: 是否使用簡體中文
    """
    result = await search_bible_advanced(
        query=query,
        search_type=search_type,
        range_start=range_start,
        range_end=range_end,
        version=version,
        limit=limit,
        offset=offset,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Strong's Tools
# ============================================================================

@mcp.tool()
async def get_word_analysis_tool(
    book: str,
    chapter: int,
    verse: int,
    use_simplified: bool = False
) -> str:
    """取得經文的原文字彙分析（希臘文/希伯來文）。
    
    Args:
        book: 經卷名稱
        chapter: 章數
        verse: 節數
        use_simplified: 是否使用簡體中文
    """
    result = await get_word_analysis(
        book=book,
        chapter=chapter,
        verse=verse,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def lookup_strongs_tool(
    number: str,
    testament: str = None,
    use_simplified: bool = False
) -> str:
    """查詢 Strong's 原文字典。支援多種格式：整數+testament (3056, 'NT')、G前綴 ('G3056')、H前綴 ('H430')。
    
    Args:
        number: Strong's Number (整數、字串數字、或帶 G/H 前綴，如 'G3056' 或 'H430')
        testament: 約別（OT=舊約, NT=新約）。當 number 包含 G/H 前綴時可省略。
        use_simplified: 是否使用簡體中文
    """
    result = await lookup_strongs(
        number=number,
        testament=testament,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def search_strongs_occurrences_tool(
    number: str,
    testament: str = None,
    limit: int = 50,
    use_simplified: bool = False
) -> str:
    """搜尋 Strong's Number 在聖經中的出現位置。
    
    Args:
        number: Strong's Number（如 'G1344' 或 'H430'）
        testament: 約別（當 number 包含 G/H 前綴時可省略）
        limit: 最多返回筆數
        use_simplified: 是否使用簡體中文
    """
    result = await search_strongs_occurrences(
        number=number,
        testament=testament,
        limit=limit,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Commentary Tools
# ============================================================================

@mcp.tool()
async def get_commentary_tool(
    book: str,
    chapter: int,
    verse: int = None,
    use_simplified: bool = False
) -> str:
    """查詢經文註釋。
    
    Args:
        book: 書卷名稱
        chapter: 章數
        verse: 節數（可選）
        use_simplified: 是否使用簡體中文
    """
    result = await get_commentary(
        book=book,
        chapter=chapter,
        verse=verse,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_commentaries_tool(
    use_simplified: bool = False
) -> str:
    """列出所有可用的註釋書。
    
    Args:
        use_simplified: 是否使用簡體中文
    """
    result = await list_commentaries(use_simplified=use_simplified)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_topic_study_tool(
    keyword: str,
    source: str = "all",
    count_only: bool = False,
    use_simplified: bool = False
) -> str:
    """查詢主題查經資料（Torrey, Naves）。
    
    Args:
        keyword: 主題關鍵字
        source: 資料來源（all/torrey_en/naves_en/torrey_zh/naves_zh）
        count_only: 是否只返回總數
        use_simplified: 是否使用簡體中文
    """
    result = await get_topic_study(
        keyword=keyword,
        source=source,
        count_only=count_only,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Info Tools
# ============================================================================

@mcp.tool()
async def list_bible_versions_tool(
    use_simplified: bool = False
) -> str:
    """列出所有可用的聖經版本。
    
    Args:
        use_simplified: 是否使用簡體中文
    """
    result = await list_bible_versions(use_simplified=use_simplified)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def search_available_versions_tool(
    testament: str = None,
    has_strongs: bool = None,
    use_simplified: bool = False
) -> str:
    """搜尋符合條件的聖經版本。
    
    Args:
        testament: 約別（OT/NT/both）
        has_strongs: 是否包含 Strong's Number
        use_simplified: 是否使用簡體中文
    """
    result = await search_available_versions(
        testament=testament,
        has_strongs=has_strongs,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_book_list_tool(
    testament: str = "all",
    use_simplified: bool = False
) -> str:
    """取得聖經書卷列表。
    
    Args:
        testament: 約別（all/OT/NT）
        use_simplified: 是否使用簡體中文
    """
    result = await get_book_list(
        testament=testament,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_book_info_tool(
    book: str,
    use_simplified: bool = False
) -> str:
    """取得特定書卷的詳細資訊。
    
    Args:
        book: 書卷名稱
        use_simplified: 是否使用簡體中文
    """
    result = await get_book_info(
        book=book,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Audio Tools
# ============================================================================

@mcp.tool()
async def get_audio_bible_tool(
    book: str,
    chapter: int,
    version: str = None
) -> str:
    """取得有聲聖經連結。
    
    Args:
        book: 書卷名稱
        chapter: 章數
        version: 有聲聖經版本代碼
    """
    result = await get_audio_bible(
        book=book,
        chapter=chapter,
        version=version
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_audio_versions_tool() -> str:
    """列出所有可用的有聲聖經版本。"""
    result = await list_audio_versions()
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Apocrypha Tools
# ============================================================================

@mcp.tool()
async def get_apocrypha_verse_tool(
    book: str,
    chapter: int,
    verse: str = None
) -> str:
    """查詢次經 (Apocrypha) 經文內容。支援書卷 101-115。
    包含：多俾亞傳、友弟德傳、瑪加伯上下、智慧篇、德訓篇(便西拉智訓)、巴錄書等。
    
    Args:
        book: 次經書卷名稱（支援多種格式）。
              中文縮寫：'多', '友', '加上', '加下', '智', '德', '巴', '耶信', '但補'
              中文全名：'多俾亞傳', '友弟德傳', '瑪加伯上', '瑪加伯下', '智慧篇', '德訓篇', '便西拉智訓', '巴錄書' 等
              英文：'Tob', 'Jdt', '1Mac', '2Mac', 'Wis', 'Sir', 'Bar', 'Tobit', 'Judith', 'Sirach' 等
        chapter: 章數
        verse: 節數（可選）。支援多種格式：
              - 單節：'1'
              - 範圍：'1-5'
              - 多節：'1,3,5'
              - 混合：'1-2,5,8-10'
              若不提供則返回整章
    """
    result = await handle_get_apocrypha_verse(
        book=book,
        chapter=chapter,
        verse=verse
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_apocrypha_books_tool() -> str:
    """列出所有可用的次經書卷及其資訊。"""
    result = await handle_list_apocrypha_books()
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Apostolic Fathers Tools
# ============================================================================

@mcp.tool()
async def get_apostolic_fathers_verse_tool(
    book: str,
    chapter: int,
    verse: str = None
) -> str:
    """查詢使徒教父文獻經文內容。
    
    Args:
        book: 使徒教父書卷名稱
        chapter: 章數
        verse: 節數（可選）
    """
    result = await handle_get_apostolic_fathers_verse(
        book=book,
        chapter=chapter,
        verse=verse
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_apostolic_fathers_books_tool() -> str:
    """列出所有可用的使徒教父書卷及其資訊"""
    result = await handle_list_apostolic_fathers_books()
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Footnotes Tools
# ============================================================================

@mcp.tool()
async def get_bible_footnote_tool(
    book_id: int,
    footnote_id: int,
    use_simplified: bool = False
) -> str:
    """查詢聖經經文註腳（僅限 TCV 現代中文譯本）。
    註腳提供原文翻譯的不同選擇、古卷差異說明、或其他重要補充資訊。

    **重要提示**: 僅台灣聖經公會現代中文譯本 (TCV) 有註腳功能。
    
    Args:
        book_id: 書卷編號 (1-66)。例如：1=創世記, 19=詩篇, 43=約翰福音, 45=羅馬書
        footnote_id: 註腳編號（每個書卷有自己的編號系統）。從 1 開始遞增。若編號不存在，會返回空結果。
        use_simplified: 是否使用簡體中文（預設：否）
    """
    result = await handle_get_bible_footnote(
        book_id=book_id,
        footnote_id=footnote_id,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Articles Tools
# ============================================================================

@mcp.tool()
async def search_fhl_articles_tool(
    title: str = None,
    author: str = None,
    content: str = None,
    abstract: str = None,
    column: str = None,
    pub_date: str = None,
    limit: int = 50,
    include_content: bool = False,
    use_simplified: bool = False
) -> str:
    """搜尋信望愛站的文章。

    可以依據標題、作者、內容、摘要、專欄、發表日期等條件搜尋。
    **至少需要提供一個搜尋條件**。

    **回傳內容**：
    - 預設模式 (include_content=false): 返回摘要和內容預覽（約 200 字）
    - 完整模式 (include_content=true): 返回完整 HTML 內容

    回傳文章列表，包含：
    - 標題 (title)
    - 作者 (author)
    - 發表日期 (pubtime)
    - 專欄 (column)
    - 摘要 (abst)
    - 內容預覽 (content_preview) 或完整內容 (content, HTML 格式)

    ⚠️ **注意**: FHL API 不支援通過 ID 直接獲取文章，因此若需要完整內容，
    請在搜尋時設定 include_content=true。
    
    Args:
        title: 標題關鍵字
        author: 作者名稱
        content: 內文關鍵字
        abstract: 摘要關鍵字
        column: 專欄英文代碼（如 women3）。使用 list_fhl_article_columns 工具查看可用專欄
        pub_date: 發表日期，格式為 YYYY.MM.DD（如 2025.10.19）
        limit: 最多回傳結果數（預設：50，範圍：1-200）
        include_content: 是否包含完整 HTML 內容（預設：false，只返回預覽）。設為 true 會返回完整文章內容，但輸出較大。
        use_simplified: 是否使用簡體中文（預設：false，使用繁體）
    """
    result = await handle_search_articles(
        title=title,
        author=author,
        content=content,
        abstract=abstract,
        column=column,
        pub_date=pub_date,
        limit=limit,
        include_content=include_content,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_fhl_article_columns_tool() -> str:
    """列出信望愛站可用的文章專欄。

    回傳所有可搜尋的專欄，包含：
    - 專欄代碼 (code): 用於 search_fhl_articles 的 column 參數
    - 專欄名稱 (name): 中文名稱
    - 專欄說明 (description): 專欄內容簡介

    使用專欄代碼可以精確搜尋特定專欄的文章。

    範例：
    - 查看所有專欄：list_fhl_article_columns()
    - 然後使用代碼搜尋：search_fhl_articles(column="women3")
    """
    result = await handle_list_article_columns()
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Well-Known Endpoints for Smithery Discovery
# ============================================================================

# MCP Server Card - provides server metadata for Smithery discovery
MCP_SERVER_CARD = {
    "name": "FHL Bible MCP Server",
    "description": "信望愛聖經工具 MCP 伺服器 - 提供聖經查詢、原文分析、註釋、有聲聖經等功能。",
    "version": "0.1.2",
    "vendor": "Ytssamuel",
    "homepage": "https://github.com/ytssamuel/FHL_MCP_SERVER",
}

# MCP Config Schema - defines session configuration options
MCP_CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "MCP Session Configuration",
    "description": "Schema for the /mcp endpoint configuration",
    "x-query-style": "dot+bracket",
    "type": "object",
    "required": [],
    "properties": {
        "use_simplified": {
            "type": "boolean",
            "default": False,
            "description": "Whether to use Simplified Chinese for responses"
        }
    }
}


async def well_known_mcp_json(request):
    """MCP Server Card endpoint for Smithery discovery."""
    return JSONResponse(MCP_SERVER_CARD)


async def well_known_mcp_config(request):
    """MCP configuration schema endpoint for Smithery."""
    return JSONResponse(MCP_CONFIG_SCHEMA)


# ============================================================================
# Main Entry Point
# ============================================================================

def create_http_app():
    """
    Create and configure the Starlette app for HTTP deployment.
    Returns the app wrapped with all necessary middleware.
    """
    # Get the streamable HTTP app from FastMCP
    # The /mcp endpoint is automatically provided by FastMCP
    app = mcp.streamable_http_app()
    
    # Add well-known routes for Smithery discovery
    # These must be added before middleware wrapping
    app.routes.insert(0, Route("/.well-known/mcp.json", well_known_mcp_json, methods=["GET"]))
    app.routes.insert(0, Route("/.well-known/mcp-config", well_known_mcp_config, methods=["GET"]))
    
    # Add CORS middleware for browser-based clients
    # IMPORTANT: CORS must be added before other middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id", "mcp-protocol-version"],
        max_age=86400,
    )
    
    # Apply Smithery config middleware for per-request configuration
    app = SmitheryConfigMiddleware(app)
    
    return app


def main():
    """Main entry point for HTTP server"""
    transport_mode = os.getenv("TRANSPORT", "http")
    
    if transport_mode == "http":
        logger.info("FHL Bible MCP Server starting in HTTP mode...")
        
        # Create the HTTP app with all middleware
        app = create_http_app()
        
        # Use Smithery-required PORT environment variable
        port = int(os.environ.get("PORT", 8081))
        
        logger.info(f"Listening on port {port}")
        logger.info(f"MCP endpoint: /mcp (Streamable HTTP)")
        
        # Run with uvicorn
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    
    else:
        # STDIO mode for local development and backward compatibility
        logger.info("FHL Bible MCP Server starting in STDIO mode...")
        mcp.run()


# Export for Smithery deployment
# When deployed, Smithery will import and use this app directly
http_app = None


def get_app():
    """Get the HTTP app for ASGI deployment (e.g., with Gunicorn or Hypercorn)."""
    global http_app
    if http_app is None:
        http_app = create_http_app()
    return http_app


if __name__ == "__main__":
    main()
