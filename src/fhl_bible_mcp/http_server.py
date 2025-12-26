"""
FHL Bible MCP Server - HTTP Server for Smithery.ai

This module provides a Streamable HTTP transport for the MCP server,
compatible with Smithery.ai deployment.

Based on MCP Specification:
https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http
"""

import asyncio
import json
import logging
import sys
from typing import Any

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route
from starlette.requests import Request
import uvicorn

from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    Prompt,
    PromptMessage,
    GetPromptResult,
)

from fhl_bible_mcp.api.endpoints import FHLAPIEndpoints
from fhl_bible_mcp.resources.handlers import ResourceRouter
from fhl_bible_mcp.prompts.templates import PromptManager

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


class FHLBibleHTTPServer:
    """FHL Bible MCP Server with HTTP Transport for Smithery.ai"""
    
    def __init__(self):
        """Initialize FHL Bible HTTP Server"""
        self.endpoints = FHLAPIEndpoints()
        self.resource_router = ResourceRouter(self.endpoints)
        self.prompt_manager = PromptManager()
        self.tools = self._build_tools_list()
        self.tool_handlers = self._build_tool_handlers()
        
    def _build_tools_list(self) -> list[dict]:
        """Build the list of available tools"""
        tools = [
            # Verse Tools
            {
                "name": "get_bible_verse",
                "description": "查詢聖經經文。支援多種格式：'約 3:16'、'John 3:16'、'約翰福音 3:16'",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "book": {"type": "string", "description": "書卷名稱"},
                        "chapter": {"type": "integer", "description": "章數"},
                        "verse": {"type": "string", "description": "節數（可選，支援範圍如 '1-5' 或 '1,3,5'）"},
                        "version": {"type": "string", "description": "聖經版本代碼（預設：unv）"},
                        "include_strong": {"type": "boolean", "description": "是否包含 Strong's Number"},
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": ["book", "chapter"]
                }
            },
            {
                "name": "get_bible_chapter",
                "description": "查詢整章聖經經文。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "book": {"type": "string", "description": "書卷名稱"},
                        "chapter": {"type": "integer", "description": "章數"},
                        "version": {"type": "string", "description": "聖經版本代碼"},
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": ["book", "chapter"]
                }
            },
            {
                "name": "query_verse_citation",
                "description": "解析並查詢經文引用字串（如：'約 3:16', '太 5:3-10'）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "citation": {"type": "string", "description": "經文引用字串"},
                        "version": {"type": "string", "description": "聖經版本代碼"},
                        "include_strong": {"type": "boolean", "description": "是否包含 Strong's Number"},
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": ["citation"]
                }
            },
            # Search Tools
            {
                "name": "search_bible",
                "description": "在聖經中搜尋關鍵字或原文編號。支援關鍵字搜尋、希臘文編號搜尋、希伯來文編號搜尋。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜尋內容"},
                        "search_type": {
                            "type": "string",
                            "enum": ["keyword", "greek_number", "hebrew_number"],
                            "description": "搜尋類型（keyword=關鍵字, greek_number=希臘文編號, hebrew_number=希伯來文編號）"
                        },
                        "scope": {
                            "type": "string",
                            "enum": ["all", "ot", "nt"],
                            "description": "搜尋範圍（all=全部, ot=舊約, nt=新約）"
                        },
                        "version": {"type": "string", "description": "聖經版本代碼"},
                        "limit": {"type": "integer", "description": "最多返回筆數"},
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": ["query"]
                }
            },
            # Strong's Tools
            {
                "name": "get_word_analysis",
                "description": "取得經文的原文字彙分析（希臘文/希伯來文）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "book": {"type": "string", "description": "書卷名稱"},
                        "chapter": {"type": "integer", "description": "章數"},
                        "verse": {"type": "integer", "description": "節數"},
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": ["book", "chapter", "verse"]
                }
            },
            {
                "name": "lookup_strongs",
                "description": "查詢 Strong's 原文字典。支援多種格式：整數+testament (3056, 'NT')、G前綴 ('G3056')、H前綴 ('H430')。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": ["string", "integer"],
                            "description": "Strong's Number (整數、字串數字、或帶 G/H 前綴，如 'G3056' 或 'H430')"
                        },
                        "testament": {
                            "type": "string",
                            "enum": ["OT", "NT"],
                            "description": "約別（OT=舊約, NT=新約）。當 number 包含 G/H 前綴時可省略。"
                        },
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": ["number"]
                }
            },
            {
                "name": "search_strongs_occurrences",
                "description": "搜尋 Strong's Number 在聖經中的出現位置。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": ["string", "integer"],
                            "description": "Strong's Number (整數、字串數字、或帶 G/H 前綴)"
                        },
                        "testament": {
                            "type": "string",
                            "enum": ["OT", "NT"],
                            "description": "約別（當 number 包含 G/H 前綴時可省略）"
                        },
                        "limit": {"type": "integer", "description": "最多返回筆數"},
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": ["number"]
                }
            },
            # Commentary Tools
            {
                "name": "get_commentary",
                "description": "查詢經文註釋。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "book": {"type": "string", "description": "書卷名稱"},
                        "chapter": {"type": "integer", "description": "章數"},
                        "verse": {"type": "integer", "description": "節數（可選）"},
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": ["book", "chapter"]
                }
            },
            {
                "name": "list_commentaries",
                "description": "列出所有可用的註釋書。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": []
                }
            },
            {
                "name": "get_topic_study",
                "description": "查詢主題查經資料（Torrey, Naves）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "主題關鍵字"},
                        "source": {
                            "type": "string",
                            "enum": ["all", "torrey_en", "naves_en", "torrey_zh", "naves_zh"],
                            "description": "資料來源"
                        },
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": ["keyword"]
                }
            },
            # Info Tools
            {
                "name": "list_bible_versions",
                "description": "列出所有可用的聖經版本。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": []
                }
            },
            {
                "name": "get_book_list",
                "description": "取得聖經書卷列表。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "testament": {
                            "type": "string",
                            "enum": ["all", "OT", "NT"],
                            "description": "約別"
                        },
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": []
                }
            },
            {
                "name": "get_book_info",
                "description": "取得特定書卷的詳細資訊。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "book": {"type": "string", "description": "書卷名稱"},
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": ["book"]
                }
            },
            # Audio Tools
            {
                "name": "get_audio_bible",
                "description": "取得有聲聖經連結。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "book": {"type": "string", "description": "書卷名稱"},
                        "chapter": {"type": "integer", "description": "章數"},
                        "version": {"type": "string", "description": "有聲聖經版本代碼"}
                    },
                    "required": ["book", "chapter"]
                }
            },
            {
                "name": "list_audio_versions",
                "description": "列出所有可用的有聲聖經版本。",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            # Apocrypha Tools
            {
                "name": "get_apocrypha_verse",
                "description": "查詢次經 (Apocrypha) 經文內容。支援書卷 101-115。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "book": {"type": "string", "description": "次經書卷名稱"},
                        "chapter": {"type": "integer", "description": "章數"},
                        "verse": {"type": "string", "description": "節數（可選）"}
                    },
                    "required": ["book", "chapter"]
                }
            },
            {
                "name": "list_apocrypha_books",
                "description": "列出所有可用的次經書卷及其資訊",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            # Apostolic Fathers Tools
            {
                "name": "get_apostolic_fathers_verse",
                "description": "查詢使徒教父文獻經文內容。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "book": {"type": "string", "description": "使徒教父書卷名稱"},
                        "chapter": {"type": "integer", "description": "章數"},
                        "verse": {"type": "string", "description": "節數（可選）"}
                    },
                    "required": ["book", "chapter"]
                }
            },
            {
                "name": "list_apostolic_fathers_books",
                "description": "列出所有可用的使徒教父書卷及其資訊",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            # Footnotes Tools
            {
                "name": "get_bible_footnote",
                "description": "查詢聖經經文註腳（僅限 TCV 現代中文譯本）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "book_id": {"type": "integer", "description": "書卷編號 (1-66)", "minimum": 1, "maximum": 66},
                        "footnote_id": {"type": "integer", "description": "註腳編號", "minimum": 1},
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": ["book_id", "footnote_id"]
                }
            },
            # Articles Tools
            {
                "name": "search_fhl_articles",
                "description": "搜尋信望愛站的文章。可以依據標題、作者、內容、摘要、專欄、發表日期等條件搜尋。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "標題關鍵字"},
                        "author": {"type": "string", "description": "作者名稱"},
                        "content": {"type": "string", "description": "內文關鍵字"},
                        "column": {"type": "string", "description": "專欄英文代碼"},
                        "limit": {"type": "integer", "description": "最多回傳結果數"},
                        "include_content": {"type": "boolean", "description": "是否包含完整 HTML 內容"},
                        "use_simplified": {"type": "boolean", "description": "是否使用簡體中文"}
                    },
                    "required": []
                }
            },
            {
                "name": "list_fhl_article_columns",
                "description": "列出信望愛站可用的文章專欄。",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
        return tools
    
    def _build_tool_handlers(self) -> dict:
        """Build mapping of tool names to handler functions"""
        return {
            "get_bible_verse": get_bible_verse,
            "get_bible_chapter": get_bible_chapter,
            "query_verse_citation": query_verse_citation,
            "search_bible": search_bible,
            "get_word_analysis": get_word_analysis,
            "lookup_strongs": lookup_strongs,
            "search_strongs_occurrences": search_strongs_occurrences,
            "get_commentary": get_commentary,
            "list_commentaries": list_commentaries,
            "search_commentary": search_commentary,
            "get_topic_study": get_topic_study,
            "list_bible_versions": list_bible_versions,
            "get_book_list": get_book_list,
            "get_book_info": get_book_info,
            "search_available_versions": search_available_versions,
            "get_audio_bible": get_audio_bible,
            "list_audio_versions": list_audio_versions,
            "get_audio_chapter_with_text": get_audio_chapter_with_text,
            "get_apocrypha_verse": handle_get_apocrypha_verse,
            "list_apocrypha_books": handle_list_apocrypha_books,
            "get_apostolic_fathers_verse": handle_get_apostolic_fathers_verse,
            "list_apostolic_fathers_books": handle_list_apostolic_fathers_books,
            "get_bible_footnote": handle_get_bible_footnote,
            "search_fhl_articles": handle_search_articles,
            "list_fhl_article_columns": handle_list_article_columns,
        }

    async def handle_initialize(self, request: Request) -> JSONResponse:
        """Handle MCP initialize request"""
        return JSONResponse({
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False}
            },
            "serverInfo": {
                "name": "fhl-bible-server",
                "version": "0.1.2"
            }
        })

    async def handle_tools_list(self, request: Request) -> JSONResponse:
        """Handle tools/list request"""
        return JSONResponse({
            "tools": self.tools
        })

    async def handle_tool_call(self, request: Request) -> JSONResponse:
        """Handle tools/call request"""
        try:
            body = await request.json()
            tool_name = body.get("params", {}).get("name")
            arguments = body.get("params", {}).get("arguments", {})
            
            if tool_name not in self.tool_handlers:
                return JSONResponse({
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }, status_code=400)
            
            handler = self.tool_handlers[tool_name]
            result = await handler(**arguments)
            
            return JSONResponse({
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2)
                    }
                ]
            })
            
        except Exception as e:
            logger.error(f"Error handling tool call: {e}", exc_info=True)
            return JSONResponse({
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }, status_code=500)

    async def handle_mcp_request(self, request: Request) -> Response:
        """Handle MCP JSON-RPC requests"""
        try:
            body = await request.json()
            method = body.get("method", "")
            request_id = body.get("id")
            
            logger.info(f"MCP Request: {method}")
            
            # Route based on method
            if method == "initialize":
                result = await self.handle_initialize(request)
            elif method == "tools/list":
                result = await self.handle_tools_list(request)
            elif method == "tools/call":
                result = await self.handle_tool_call(request)
            elif method == "resources/list":
                return JSONResponse({"resources": []})
            elif method == "prompts/list":
                prompts = self.prompt_manager.list_prompts()
                return JSONResponse({"prompts": prompts})
            else:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }, status_code=400)
            
            # Wrap response in JSON-RPC format
            response_data = result.body.decode() if hasattr(result, 'body') else "{}"
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": json.loads(response_data)
            })
            
        except json.JSONDecodeError:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }, status_code=400)
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}", exc_info=True)
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }, status_code=500)


# Create server instance
http_server = FHLBibleHTTPServer()


async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint"""
    return JSONResponse({"status": "healthy", "server": "fhl-bible-mcp", "version": "0.1.2"})


async def mcp_endpoint(request: Request) -> Response:
    """Main MCP endpoint for Smithery"""
    return await http_server.handle_mcp_request(request)


# Create Starlette app
app = Starlette(
    debug=False,
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Route("/mcp", mcp_endpoint, methods=["POST"]),
        Route("/", health_check, methods=["GET"]),  # Root health check
    ]
)


def main():
    """Main entry point for HTTP server"""
    logger.info("Starting FHL Bible MCP HTTP Server...")
    logger.info("Server capabilities:")
    logger.info("  - Tools: 24 functions")
    logger.info("  - Endpoint: /mcp (POST)")
    logger.info("  - Health: /health (GET)")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
