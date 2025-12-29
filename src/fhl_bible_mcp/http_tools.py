"""
FHL Bible MCP Server - HTTP Tool Wrappers

This module provides tool wrapper functions for HTTP deployment.
These wrappers adapt the existing tool handlers to work with FastMCP's
decorator-based tool registration.

The key difference from the original server.py is that HTTP tools receive
direct keyword arguments, while the original handlers expect
(api_client, arguments) signature.
"""

import json
import logging
from typing import Any, Optional

from fhl_bible_mcp.api.endpoints import FHLAPIEndpoints

# Import existing tool modules for their helper data
from fhl_bible_mcp.tools.apocrypha import APOCRYPHA_BOOKS
from fhl_bible_mcp.tools.apostolic_fathers import APOSTOLIC_FATHERS_BOOKS

logger = logging.getLogger(__name__)


# ============================================================================
# Info Tools (Fixed signatures)
# ============================================================================

async def http_get_book_list(
    testament: str = "all",
) -> dict[str, Any]:
    """
    取得聖經書卷列表 (HTTP version)
    
    Args:
        testament: 約別（all/OT/NT）
    
    Note: use_simplified is not supported by the underlying function
    """
    from fhl_bible_mcp.tools.info import get_book_list
    return await get_book_list(testament=testament)


async def http_get_book_info(
    book: str,
) -> dict[str, Any]:
    """
    取得特定書卷的詳細資訊 (HTTP version)
    
    Args:
        book: 書卷名稱
    
    Note: use_simplified is not supported by the underlying function
    """
    from fhl_bible_mcp.tools.info import get_book_info
    return await get_book_info(book=book)


# ============================================================================
# Audio Tools (Fixed parameter name)
# ============================================================================

async def http_get_audio_bible(
    book: str,
    chapter: int,
    audio_version: str = "unv",
) -> dict[str, Any]:
    """
    取得有聲聖經連結 (HTTP version)
    
    Args:
        book: 書卷名稱
        chapter: 章數
        audio_version: 有聲聖經版本代碼 (not 'version')
    """
    from fhl_bible_mcp.tools.audio import get_audio_bible
    return await get_audio_bible(
        book=book,
        chapter=chapter,
        audio_version=audio_version,
    )


# ============================================================================
# Apocrypha Tools (Adapted from handler signature)
# ============================================================================

async def http_get_apocrypha_verse(
    book: str,
    chapter: int,
    verse: Optional[str] = None,
) -> dict[str, Any]:
    """
    查詢次經經文 (HTTP version)
    
    Adapts handle_get_apocrypha_verse(api_client, arguments) to direct kwargs.
    """
    async with FHLAPIEndpoints() as api:
        # Get book info for display name
        book_info = APOCRYPHA_BOOKS.get(book)
        display_name = book_info["name_zh"] if book_info else book
        
        result = await api.get_apocrypha_verse(
            book=book,
            chapter=chapter,
            verse=verse,
        )
        
        if result.get("status") == "success":
            record_count = result.get("record_count", 0)
            v_name = result.get("v_name", "1933年聖公會出版")
            v_code = result.get("version", "c1933")
            
            records = result.get("record", [])
            bid = records[0].get("bid", "未知") if records else "未知"
            
            verses = []
            for verse_obj in records:
                verses.append({
                    "book": display_name,
                    "book_id": verse_obj.get("bid", bid),
                    "chapter": chapter,
                    "verse": verse_obj.get("sec", ""),
                    "text": verse_obj.get("bible_text", "")
                })
            
            return {
                "status": "success",
                "query_type": "apocrypha_verse",
                "book": display_name,
                "book_id": bid,
                "chapter": chapter,
                "verse": verse,
                "version": {
                    "code": v_code,
                    "name": v_name
                },
                "verse_count": record_count,
                "verses": verses
            }
        else:
            return {
                "status": "error",
                "error": result.get("error", "未知錯誤")
            }


async def http_search_apocrypha(
    query: str,
    limit: int = 10,
    offset: int = 0,
) -> dict[str, Any]:
    """
    搜尋次經 (HTTP version)
    """
    # Build bid to name mapping
    bid_to_name = {}
    for abbr, info in APOCRYPHA_BOOKS.items():
        bid_to_name[info["id"]] = info["name_zh"]
    
    async with FHLAPIEndpoints() as api:
        result = await api.search_apocrypha(
            query=query,
            limit=limit,
            offset=offset,
        )
        
        if result.get("status") == "success":
            record_count = result.get("record_count", 0)
            
            results = []
            for verse_obj in result.get("record", []):
                bid = verse_obj.get("bid", "")
                book_name = bid_to_name.get(int(bid), verse_obj.get("chineses", "")) if bid else ""
                
                results.append({
                    "book": book_name,
                    "book_id": bid,
                    "chapter": verse_obj.get("chap", ""),
                    "verse": verse_obj.get("sec", ""),
                    "text": verse_obj.get("bible_text", "")
                })
            
            return {
                "status": "success",
                "query_type": "apocrypha_search",
                "keyword": query,
                "total_count": record_count,
                "returned_count": len(results),
                "offset": offset,
                "results": results
            }
        else:
            return {
                "status": "error",
                "error": result.get("error", "未知錯誤")
            }


async def http_list_apocrypha_books() -> dict[str, Any]:
    """
    列出所有次經書卷 (HTTP version)
    """
    # Group by book ID
    books_by_id: dict[int, dict[str, Any]] = {}
    for abbr, info in APOCRYPHA_BOOKS.items():
        book_id = info["id"]
        if book_id not in books_by_id:
            books_by_id[book_id] = info.copy()
            books_by_id[book_id]["abbrs"] = []
        books_by_id[book_id]["abbrs"].append(abbr)
    
    # Build books list
    books_list = []
    for book_id in sorted(books_by_id.keys()):
        info = books_by_id[book_id]
        books_list.append({
            "id": book_id,
            "name_zh": info["name_zh"],
            "name_en": info["name_en"],
            "abbreviations": info["abbrs"]
        })
    
    return {
        "status": "success",
        "query_type": "list_apocrypha_books",
        "id_range": "101-115",
        "book_count": len(books_list),
        "books": books_list
    }


# ============================================================================
# Apostolic Fathers Tools (Adapted from handler signature)
# ============================================================================

async def http_get_apostolic_fathers_verse(
    book: str,
    chapter: int,
    verse: Optional[str] = None,
) -> dict[str, Any]:
    """
    查詢使徒教父文獻經文 (HTTP version)
    """
    async with FHLAPIEndpoints() as api:
        # Get book info for display name
        book_info = APOSTOLIC_FATHERS_BOOKS.get(book)
        display_name = book_info["name_zh"] if book_info else book
        
        result = await api.get_apostolic_fathers_verse(
            book=book,
            chapter=chapter,
            verse=verse,
        )
        
        if result.get("status") == "success":
            record_count = result.get("record_count", 0)
            v_name = result.get("v_name", "黃錫木主編《使徒教父著作》")
            v_code = result.get("version", "af")
            
            records = result.get("record", [])
            bid = records[0].get("bid", "未知") if records else "未知"
            
            verses = []
            for verse_obj in records:
                verses.append({
                    "book": display_name,
                    "book_id": verse_obj.get("bid", bid),
                    "chapter": chapter,
                    "verse": verse_obj.get("sec", ""),
                    "text": verse_obj.get("bible_text", "")
                })
            
            return {
                "status": "success",
                "query_type": "apostolic_fathers_verse",
                "book": display_name,
                "book_id": bid,
                "chapter": chapter,
                "verse": verse,
                "version": {
                    "code": v_code,
                    "name": v_name
                },
                "verse_count": record_count,
                "verses": verses
            }
        else:
            return {
                "status": "error",
                "error": result.get("error", "未知錯誤")
            }


async def http_search_apostolic_fathers(
    query: str,
    limit: int = 10,
    offset: int = 0,
) -> dict[str, Any]:
    """
    搜尋使徒教父文獻 (HTTP version)
    """
    # Build bid to name mapping
    bid_to_name = {}
    for abbr, info in APOSTOLIC_FATHERS_BOOKS.items():
        bid_to_name[info["id"]] = info["name_zh"]
    
    async with FHLAPIEndpoints() as api:
        result = await api.search_apostolic_fathers(
            query=query,
            limit=limit,
            offset=offset,
        )
        
        if result.get("status") == "success":
            record_count = result.get("record_count", 0)
            
            results = []
            for verse_obj in result.get("record", []):
                bid = verse_obj.get("bid", "")
                book_name = bid_to_name.get(int(bid), verse_obj.get("chineses", "")) if bid else ""
                
                results.append({
                    "book": book_name,
                    "book_id": bid,
                    "chapter": verse_obj.get("chap", ""),
                    "verse": verse_obj.get("sec", ""),
                    "text": verse_obj.get("bible_text", "")
                })
            
            return {
                "status": "success",
                "query_type": "apostolic_fathers_search",
                "keyword": query,
                "total_count": record_count,
                "returned_count": len(results),
                "offset": offset,
                "results": results
            }
        else:
            return {
                "status": "error",
                "error": result.get("error", "未知錯誤")
            }


async def http_list_apostolic_fathers_books() -> dict[str, Any]:
    """
    列出所有使徒教父書卷 (HTTP version)
    """
    # Group by book ID
    books_by_id: dict[int, dict[str, Any]] = {}
    for abbr, info in APOSTOLIC_FATHERS_BOOKS.items():
        book_id = info["id"]
        if book_id not in books_by_id:
            books_by_id[book_id] = info.copy()
            books_by_id[book_id]["abbrs"] = []
        books_by_id[book_id]["abbrs"].append(abbr)
    
    # Build books list
    books_list = []
    for book_id in sorted(books_by_id.keys()):
        info = books_by_id[book_id]
        books_list.append({
            "id": book_id,
            "name_zh": info["name_zh"],
            "name_en": info["name_en"],
            "abbreviations": info["abbrs"]
        })
    
    return {
        "status": "success",
        "query_type": "list_apostolic_fathers_books",
        "id_range": "201-217",
        "book_count": len(books_list),
        "books": books_list
    }


# ============================================================================
# Footnotes Tools (Adapted from handler signature)
# ============================================================================

async def http_get_bible_footnote(
    book_id: int,
    footnote_id: int,
    use_simplified: bool = False,
) -> dict[str, Any]:
    """
    查詢聖經經文註腳 (HTTP version)
    僅限 TCV 現代中文譯本
    """
    async with FHLAPIEndpoints() as api:
        result = await api.get_footnote(
            book_id=book_id,
            footnote_id=footnote_id,
            use_simplified=use_simplified
        )
        
        if result.get("status") == "success":
            record_count = result.get("record_count", 0)
            engs = result.get("engs", "")
            
            if record_count > 0:
                record = result["record"][0]
                return {
                    "status": "success",
                    "query_type": "bible_footnote",
                    "version": "TCV",
                    "version_name": "現代中文譯本",
                    "book_id": book_id,
                    "book_name": engs,
                    "footnote_id": record.get("id", footnote_id),
                    "text": record.get("text", "")
                }
            else:
                return {
                    "status": "not_found",
                    "message": f"找不到書卷 {book_id} 的註腳 #{footnote_id}"
                }
        else:
            return {
                "status": "error",
                "error": result.get("error", "未知錯誤")
            }


# ============================================================================
# Articles Tools (Adapted from handler signature)
# ============================================================================

async def http_search_articles(
    title: Optional[str] = None,
    author: Optional[str] = None,
    content: Optional[str] = None,
    abstract: Optional[str] = None,
    column: Optional[str] = None,
    pub_date: Optional[str] = None,
    limit: int = 50,
    include_content: bool = False,
    use_simplified: bool = False,
) -> dict[str, Any]:
    """
    搜尋信望愛站文章 (HTTP version)
    """
    async with FHLAPIEndpoints() as api:
        result = await api.search_articles(
            title=title,
            author=author,
            content=content,
            abstract=abstract,
            column=column,
            pub_date=pub_date,
            use_simplified=use_simplified,
            limit=limit
        )
        
        if result.get("status") == 1 and result.get("record_count", 0) > 0:
            articles = result.get("record", [])
            
            if not articles:
                return {
                    "status": "no_results",
                    "query_type": "article_search",
                    "message": "未找到符合條件的文章"
                }
            
            # Format articles
            formatted_articles = []
            for article in articles:
                formatted = {
                    "id": article.get("id", ""),
                    "title": article.get("title", ""),
                    "author": article.get("author", ""),
                    "pubtime": article.get("pubtime", ""),
                    "column": article.get("column", ""),
                    "abstract": article.get("abst", ""),
                }
                
                if include_content:
                    formatted["content"] = article.get("content", "")
                else:
                    # Content preview (first 200 chars)
                    full_content = article.get("content", "")
                    if full_content:
                        # Strip HTML tags for preview
                        import re
                        clean_text = re.sub(r'<[^>]+>', '', full_content)
                        formatted["content_preview"] = clean_text[:200] + "..." if len(clean_text) > 200 else clean_text
                
                formatted_articles.append(formatted)
            
            return {
                "status": "success",
                "query_type": "article_search",
                "total_count": result.get("record_count", len(formatted_articles)),
                "returned_count": len(formatted_articles),
                "include_full_content": include_content,
                "articles": formatted_articles
            }
        
        elif result.get("status") == 0:
            error_msg = result.get("result", "Unknown error")
            
            if "data too much" in error_msg.lower():
                return {
                    "status": "error",
                    "error": "資料量過大，請提供至少一個搜尋條件",
                    "hint": "請使用 title, author, content, abstract, column 或 pub_date 參數"
                }
            elif "no data" in error_msg.lower():
                return {
                    "status": "no_results",
                    "message": "未找到符合條件的文章"
                }
            else:
                return {
                    "status": "error",
                    "error": error_msg
                }
        else:
            return {
                "status": "no_results",
                "query_type": "article_search",
                "message": "未找到符合條件的文章"
            }


async def http_list_article_columns() -> dict[str, Any]:
    """
    列出信望愛站文章專欄 (HTTP version)
    """
    async with FHLAPIEndpoints() as api_client:
        columns = api_client.list_article_columns()
    
    return {
        "status": "success",
        "query_type": "list_article_columns",
        "column_count": len(columns),
        "columns": [
            {
                "code": col['code'],
                "name": col['name'],
                "description": col['description']
            }
            for col in columns
        ]
    }
