"""
FHL Bible MCP Server - HTTP Server for Smithery.ai

This module provides a Streamable HTTP transport for the MCP server,
compatible with Smithery.ai deployment using FastMCP.

Based on Smithery requirements:
https://smithery.ai/docs/migrations/python-custom-container
"""

import os
import logging
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

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
# Verse Query Tools
# ============================================================================

@mcp.tool()
async def get_verse(
    book: str,
    chapter: int,
    verse: str = None,
    version: str = "unv",
    include_strong: bool = False,
    use_simplified: bool = False
) -> str:
    """查詢指定的聖經經文。支援單節、多節、節範圍查詢。
    
    Args:
        book: 經卷名稱（中文或英文縮寫，如：約、John、創世記）
        chapter: 章數
        verse: 節數（支援格式：'1', '1-5', '1,3,5'）
        version: 聖經版本代碼（預設：unv）
        include_strong: 是否包含 Strong's Number
        use_simplified: 是否使用簡體中文
    """
    import json
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
async def get_chapter(
    book: str,
    chapter: int,
    version: str = "unv",
    use_simplified: bool = False
) -> str:
    """查詢整章聖經經文。
    
    Args:
        book: 書卷名稱
        chapter: 章數
        version: 聖經版本代碼
        use_simplified: 是否使用簡體中文
    """
    import json
    result = await get_bible_chapter(
        book=book,
        chapter=chapter,
        version=version,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def parse_verse_citation(
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
    import json
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
async def search_bible_text(
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
    import json
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
async def search_bible_range(
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
    import json
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
async def get_original_word_analysis(
    book: str,
    chapter: int,
    verse: int,
    use_simplified: bool = False
) -> str:
    """取得經文的原文字彙分析（希臘文/希伯來文）。
    
    Args:
        book: 書卷名稱
        chapter: 章數
        verse: 節數
        use_simplified: 是否使用簡體中文
    """
    import json
    result = await get_word_analysis(
        book=book,
        chapter=chapter,
        verse=verse,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def lookup_strongs_number(
    number: str,
    testament: str = None,
    use_simplified: bool = False
) -> str:
    """查詢 Strong's 原文字典。支援多種格式：'G3056'、'H430'、整數。
    
    Args:
        number: Strong's Number（如 'G3056' 或 'H430'）
        testament: 約別（OT=舊約, NT=新約）。當 number 包含 G/H 前綴時可省略
        use_simplified: 是否使用簡體中文
    """
    import json
    result = await lookup_strongs(
        number=number,
        testament=testament,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def search_strongs(
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
    import json
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
async def get_verse_commentary(
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
    import json
    result = await get_commentary(
        book=book,
        chapter=chapter,
        verse=verse,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_available_commentaries(
    use_simplified: bool = False
) -> str:
    """列出所有可用的註釋書。
    
    Args:
        use_simplified: 是否使用簡體中文
    """
    import json
    result = await list_commentaries(use_simplified=use_simplified)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_topic_study_data(
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
    import json
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
async def list_versions(
    use_simplified: bool = False
) -> str:
    """列出所有可用的聖經版本。
    
    Args:
        use_simplified: 是否使用簡體中文
    """
    import json
    result = await list_bible_versions(use_simplified=use_simplified)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def search_versions(
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
    import json
    result = await search_available_versions(
        testament=testament,
        has_strongs=has_strongs,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_books(
    testament: str = "all",
    use_simplified: bool = False
) -> str:
    """取得聖經書卷列表。
    
    Args:
        testament: 約別（all/OT/NT）
        use_simplified: 是否使用簡體中文
    """
    import json
    result = await get_book_list(
        testament=testament,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_book_details(
    book: str,
    use_simplified: bool = False
) -> str:
    """取得特定書卷的詳細資訊。
    
    Args:
        book: 書卷名稱
        use_simplified: 是否使用簡體中文
    """
    import json
    result = await get_book_info(
        book=book,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Audio Tools
# ============================================================================

@mcp.tool()
async def get_audio_link(
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
    import json
    result = await get_audio_bible(
        book=book,
        chapter=chapter,
        version=version
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_audio(
) -> str:
    """列出所有可用的有聲聖經版本。"""
    import json
    result = await list_audio_versions()
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Apocrypha Tools
# ============================================================================

@mcp.tool()
async def get_apocrypha_verse(
    book: str,
    chapter: int,
    verse: str = None
) -> str:
    """查詢次經 (Apocrypha) 經文內容。支援書卷 101-115。
    
    Args:
        book: 次經書卷名稱（如：多、友、加上、加下、智、德）
        chapter: 章數
        verse: 節數（可選）
    """
    import json
    result = await handle_get_apocrypha_verse(
        book=book,
        chapter=chapter,
        verse=verse
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_apocrypha_books(
) -> str:
    """列出所有可用的次經書卷及其資訊。"""
    import json
    result = await handle_list_apocrypha_books()
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Apostolic Fathers Tools
# ============================================================================

@mcp.tool()
async def get_apostolic_fathers_verse(
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
    import json
    result = await handle_get_apostolic_fathers_verse(
        book=book,
        chapter=chapter,
        verse=verse
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_apostolic_fathers_books(
) -> str:
    """列出所有可用的使徒教父書卷及其資訊。"""
    import json
    result = await handle_list_apostolic_fathers_books()
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Footnotes Tools
# ============================================================================

@mcp.tool()
async def get_bible_footnote(
    book_id: int,
    footnote_id: int,
    use_simplified: bool = False
) -> str:
    """查詢聖經經文註腳（僅限 TCV 現代中文譯本）。
    
    Args:
        book_id: 書卷編號 (1-66)
        footnote_id: 註腳編號
        use_simplified: 是否使用簡體中文
    """
    import json
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
async def search_fhl_articles(
    title: str = None,
    author: str = None,
    content: str = None,
    column: str = None,
    limit: int = 20,
    include_content: bool = False,
    use_simplified: bool = False
) -> str:
    """搜尋信望愛站的文章。
    
    Args:
        title: 標題關鍵字
        author: 作者名稱
        content: 內文關鍵字
        column: 專欄英文代碼
        limit: 最多回傳結果數
        include_content: 是否包含完整 HTML 內容
        use_simplified: 是否使用簡體中文
    """
    import json
    result = await handle_search_articles(
        title=title,
        author=author,
        content=content,
        column=column,
        limit=limit,
        include_content=include_content,
        use_simplified=use_simplified
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_fhl_article_columns(
) -> str:
    """列出信望愛站可用的文章專欄。"""
    import json
    result = await handle_list_article_columns()
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for HTTP server"""
    transport_mode = os.getenv("TRANSPORT", "http")
    
    if transport_mode == "http":
        logger.info("FHL Bible MCP Server starting in HTTP mode...")
        
        # Get the streamable HTTP app from FastMCP
        app = mcp.streamable_http_app()
        
        # Add CORS middleware for browser-based clients
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id", "mcp-protocol-version"],
            max_age=86400,
        )
        
        # Use Smithery-required PORT environment variable
        port = int(os.environ.get("PORT", 8000))
        logger.info(f"Listening on port {port}")
        logger.info(f"MCP endpoint: /mcp")
        logger.info(f"Tools registered: 24")
        
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    
    else:
        # STDIO mode for local development
        logger.info("FHL Bible MCP Server starting in STDIO mode...")
        mcp.run()


if __name__ == "__main__":
    main()
