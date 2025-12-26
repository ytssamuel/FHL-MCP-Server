"""
FHL Bible MCP Server - Smithery Python Runtime Entry Point

This module provides the server creation function required by Smithery's
Python runtime mode using the @smithery.server() decorator.

Based on Smithery requirements:
https://smithery.ai/docs/build/deployments/python
"""

import json
from mcp.server.fastmcp import FastMCP, Context
from smithery.decorators import smithery
from pydantic import BaseModel, Field
from typing import Optional

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


# ============================================================================
# Session Configuration Schema
# ============================================================================

class ConfigSchema(BaseModel):
    """Schema for session configuration options."""
    use_simplified: bool = Field(
        default=False,
        description="Whether to use Simplified Chinese for responses"
    )


# ============================================================================
# Smithery Server Creation Function
# ============================================================================

@smithery.server(config_schema=ConfigSchema)
def create_server():
    """
    Create and return a FastMCP server instance.
    This function is called by Smithery to create the server.
    """
    
    server = FastMCP(
        name="FHL Bible MCP Server",
        instructions="信望愛聖經工具 MCP 伺服器 - 提供聖經查詢、原文分析、註釋、有聲聖經等功能。"
    )
    
    # ========================================================================
    # Verse Query Tools
    # ========================================================================
    
    @server.tool()
    async def get_bible_verse_tool(
        book: str,
        chapter: int,
        verse: Optional[str] = None,
        version: str = "unv",
        include_strong: bool = False,
        use_simplified: bool = False,
        ctx: Context = None
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
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
        
        result = await get_bible_verse(
            book=book,
            chapter=chapter,
            verse=verse,
            version=version,
            include_strong=include_strong,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def get_bible_chapter_tool(
        book: str,
        chapter: int,
        version: str = "unv",
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """查詢整章聖經經文。
        
        Args:
            book: 經卷名稱
            chapter: 章數
            version: 聖經版本代碼（預設：unv）
            use_simplified: 是否使用簡體中文
        """
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await get_bible_chapter(
            book=book,
            chapter=chapter,
            version=version,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def query_verse_citation_tool(
        citation: str,
        version: str = "unv",
        include_strong: bool = False,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """解析並查詢經文引用字串（如：'約 3:16', '太 5:3-10'）。
        
        Args:
            citation: 經文引用字串
            version: 聖經版本代碼
            include_strong: 是否包含 Strong's Number
            use_simplified: 是否使用簡體中文
        """
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await query_verse_citation(
            citation=citation,
            version=version,
            include_strong=include_strong,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ========================================================================
    # Search Tools
    # ========================================================================

    @server.tool()
    async def search_bible_tool(
        query: str,
        testament: str = "both",
        version: str = "unv",
        limit: int = 50,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """在聖經中搜尋關鍵字。
        
        Args:
            query: 搜尋內容
            testament: 約別範圍 (OT=舊約, NT=新約, both=全部)
            version: 聖經版本代碼
            limit: 最多返回筆數
            use_simplified: 是否使用簡體中文
        """
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await search_bible(
            query=query,
            testament=testament,
            version=version,
            limit=limit,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def search_bible_advanced_tool(
        query: str,
        search_type: str = "keyword",
        range_start: Optional[int] = None,
        range_end: Optional[int] = None,
        version: str = "unv",
        limit: int = 50,
        offset: int = 0,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """進階聖經搜尋，支援自訂書卷範圍。
        
        Args:
            query: 搜尋內容
            search_type: 搜尋類型：keyword(關鍵字)/greek_number(希臘文編號)/hebrew_number(希伯來文編號)
            range_start: 起始書卷編號 (1-66)
            range_end: 結束書卷編號 (1-66)
            version: 聖經版本代碼
            limit: 最多返回筆數
            offset: 跳過筆數
            use_simplified: 是否使用簡體中文
        """
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
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

    # ========================================================================
    # Strong's Number Tools
    # ========================================================================

    @server.tool()
    async def get_word_analysis_tool(
        book: str,
        chapter: int,
        verse: int,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """取得經文的原文字彙分析（希臘文/希伯來文）。
        
        Args:
            book: 經卷名稱
            chapter: 章數
            verse: 節數
            use_simplified: 是否使用簡體中文
        """
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await get_word_analysis(
            book=book,
            chapter=chapter,
            verse=verse,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def lookup_strongs_tool(
        number: str,
        testament: Optional[str] = None,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """查詢 Strong's 原文字典。
        
        Args:
            number: Strong's Number (整數、字串數字、或帶 G/H 前綴)
            testament: 約別（OT=舊約, NT=新約）
            use_simplified: 是否使用簡體中文
        """
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await lookup_strongs(
            number=number,
            testament=testament,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def search_strongs_occurrences_tool(
        strongs_number: str,
        testament: Optional[str] = None,
        limit: int = 100,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """搜尋包含特定 Strong's Number 的經文。
        
        Args:
            strongs_number: Strong's Number（如 'G3056' 或 'H430'）
            testament: 約別限制（OT/NT，可選）
            limit: 最多返回筆數
            use_simplified: 是否使用簡體中文
        """
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await search_strongs_occurrences(
            strongs_number=strongs_number,
            testament=testament,
            limit=limit,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ========================================================================
    # Commentary Tools
    # ========================================================================

    @server.tool()
    async def get_commentary_tool(
        book: str,
        chapter: int,
        verse: Optional[int] = None,
        commentary_id: Optional[str] = None,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """取得經文的註釋。
        
        Args:
            book: 經卷名稱
            chapter: 章數
            verse: 節數（可選）
            commentary_id: 註釋書 ID（可選）
            use_simplified: 是否使用簡體中文
        """
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await get_commentary(
            book=book,
            chapter=chapter,
            verse=verse,
            commentary_id=commentary_id,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def list_commentaries_tool(
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """列出所有可用的註釋書。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await list_commentaries(use_simplified=use_simplified)
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def search_commentary_tool(
        keyword: str,
        commentary_id: Optional[str] = None,
        limit: int = 50,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """在註釋書中搜尋關鍵字。
        
        Args:
            keyword: 搜尋關鍵字
            commentary_id: 指定註釋書 ID（可選）
            limit: 最多返回筆數
            use_simplified: 是否使用簡體中文
        """
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await search_commentary(
            keyword=keyword,
            commentary_id=commentary_id,
            limit=limit,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def get_topic_study_tool(
        keyword: str,
        source: str = "all",
        count_only: bool = False,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """查詢主題查經資料（Torrey, Naves）。
        
        Args:
            keyword: 主題關鍵字
            source: 資料來源
            count_only: 是否只返回總數
            use_simplified: 是否使用簡體中文
        """
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await get_topic_study(
            keyword=keyword,
            source=source,
            count_only=count_only,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ========================================================================
    # Bible Info Tools
    # ========================================================================

    @server.tool()
    async def list_bible_versions_tool(
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """列出所有可用的聖經版本。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await list_bible_versions(use_simplified=use_simplified)
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def search_available_versions_tool(
        testament: str = "both",
        has_strongs: Optional[bool] = None,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """搜尋符合條件的聖經版本。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await search_available_versions(
            testament=testament,
            has_strongs=has_strongs,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def get_book_list_tool(
        category: str = "bible",
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """取得書卷列表。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await get_book_list(
            category=category,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def get_book_info_tool(
        book: str,
        category: str = "bible",
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """取得特定書卷的詳細資訊。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await get_book_info(
            book=book,
            category=category,
            use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ========================================================================
    # Audio Bible Tools
    # ========================================================================

    @server.tool()
    async def get_audio_bible_tool(
        book: str,
        chapter: int,
        version: str = "unv"
    ) -> str:
        """取得有聲聖經音訊連結。"""
        result = await get_audio_bible(book=book, chapter=chapter, version=version)
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def list_audio_versions_tool() -> str:
        """列出所有可用的有聲聖經版本。"""
        result = await list_audio_versions()
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def get_audio_chapter_with_text_tool(
        book: str,
        chapter: int,
        version: str = "unv",
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """取得有聲聖經章節及對應經文。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await get_audio_chapter_with_text(
            book=book, chapter=chapter, version=version, use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ========================================================================
    # Apocrypha Tools
    # ========================================================================

    @server.tool()
    async def get_apocrypha_verse_tool(
        book: str,
        chapter: int,
        verse: Optional[str] = None,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """查詢次經 (Apocrypha) 經文內容。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await handle_get_apocrypha_verse(
            book=book, chapter=chapter, verse=verse, use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def search_apocrypha_tool(
        keyword: str,
        book: Optional[str] = None,
        limit: int = 50,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """在次經中搜尋關鍵字。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await handle_search_apocrypha(
            keyword=keyword, book=book, limit=limit, use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def list_apocrypha_books_tool(
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """列出所有次經書卷。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await handle_list_apocrypha_books(use_simplified=use_simplified)
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ========================================================================
    # Apostolic Fathers Tools
    # ========================================================================

    @server.tool()
    async def get_apostolic_fathers_verse_tool(
        book: str,
        chapter: int,
        verse: Optional[str] = None,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """查詢使徒教父文獻。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await handle_get_apostolic_fathers_verse(
            book=book, chapter=chapter, verse=verse, use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def search_apostolic_fathers_tool(
        keyword: str,
        book: Optional[str] = None,
        limit: int = 50,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """在使徒教父文獻中搜尋關鍵字。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await handle_search_apostolic_fathers(
            keyword=keyword, book=book, limit=limit, use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def list_apostolic_fathers_books_tool(
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """列出所有使徒教父文獻書卷。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await handle_list_apostolic_fathers_books(use_simplified=use_simplified)
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ========================================================================
    # Footnotes Tool
    # ========================================================================

    @server.tool()
    async def get_bible_footnote_tool(
        book_id: int,
        footnote_id: int,
        use_simplified: bool = False,
        ctx: Context = None
    ) -> str:
        """查詢聖經經文註腳（僅限 TCV 現代中文譯本）。"""
        if ctx and hasattr(ctx, 'session_config') and ctx.session_config:
            use_simplified = getattr(ctx.session_config, 'use_simplified', use_simplified)
            
        result = await handle_get_bible_footnote(
            book_id=book_id, footnote_id=footnote_id, use_simplified=use_simplified
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ========================================================================
    # FHL Articles Tools
    # ========================================================================

    @server.tool()
    async def search_fhl_articles_tool(
        keyword: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        column: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> str:
        """搜尋信望愛網站文章。"""
        result = await handle_search_articles(
            keyword=keyword, title=title, author=author,
            column=column, limit=limit, offset=offset
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @server.tool()
    async def list_fhl_article_columns_tool() -> str:
        """列出信望愛網站所有文章專欄。"""
        result = await handle_list_article_columns()
        return json.dumps(result, ensure_ascii=False, indent=2)

    return server
