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
import uuid
from typing import Any, AsyncGenerator, Optional

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route
from starlette.requests import Request
import uvicorn

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
    """FHL Bible MCP Server with Streamable HTTP Transport for Smithery.ai"""
    
    def __init__(self):
        """Initialize FHL Bible HTTP Server"""
        self.endpoints = FHLAPIEndpoints()
        self.resource_router = ResourceRouter(self.endpoints)
        self.prompt_manager = PromptManager()
        self.tools = self._build_tools_list()
        self.tool_handlers = self._build_tool_handlers()
        self.sessions = {}  # Session management
        
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
            {
                "name": "search_bible_advanced",
                "description": "進階聖經搜尋，支援自訂書卷範圍。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜尋內容"},
                        "search_type": {
                            "type": "string",
                            "enum": ["keyword", "greek_number", "hebrew_number"],
                            "description": "搜尋類型：keyword(關鍵字)/greek_number(希臘文編號)/hebrew_number(希伯來文編號)"
                        },
                        "range_start": {"type": "integer", "description": "起始書卷編號 (1-66)"},
                        "range_end": {"type": "integer", "description": "結束書卷編號 (1-66)"},
                        "version": {"type": "string", "description": "聖經版本代碼"},
                        "limit": {"type": "integer", "description": "最多返回筆數"},
                        "offset": {"type": "integer", "description": "跳過筆數"},
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
                "name": "search_available_versions",
                "description": "搜尋符合條件的聖經版本。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "testament": {
                            "type": "string",
                            "enum": ["OT", "NT", "both"],
                            "description": "約別"
                        },
                        "has_strongs": {"type": "boolean", "description": "是否包含 Strong's Number"},
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
            "search_bible_advanced": search_bible_advanced,
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

    def _create_jsonrpc_response(self, request_id: Any, result: Any) -> dict:
        """Create a JSON-RPC response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    def _create_jsonrpc_error(self, request_id: Any, code: int, message: str) -> dict:
        """Create a JSON-RPC error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

    async def handle_initialize(self, request_id: Any) -> tuple[dict, str]:
        """Handle MCP initialize request"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {"initialized": True}
        
        return self._create_jsonrpc_response(request_id, {
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
        }), session_id

    async def handle_tools_list(self, request_id: Any) -> dict:
        """Handle tools/list request"""
        return self._create_jsonrpc_response(request_id, {
            "tools": self.tools
        })

    async def handle_tool_call(self, request_id: Any, params: dict) -> dict:
        """Handle tools/call request"""
        try:
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name not in self.tool_handlers:
                return self._create_jsonrpc_error(
                    request_id, -32601, f"Unknown tool: {tool_name}"
                )
            
            handler = self.tool_handlers[tool_name]
            result = await handler(**arguments)
            
            return self._create_jsonrpc_response(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2)
                    }
                ]
            })
            
        except Exception as e:
            logger.error(f"Error handling tool call: {e}", exc_info=True)
            return self._create_jsonrpc_error(request_id, -32603, str(e))

    async def handle_resources_list(self, request_id: Any) -> dict:
        """Handle resources/list request"""
        return self._create_jsonrpc_response(request_id, {"resources": []})

    async def handle_prompts_list(self, request_id: Any) -> dict:
        """Handle prompts/list request"""
        prompts = self.prompt_manager.list_prompts()
        return self._create_jsonrpc_response(request_id, {"prompts": prompts})

    async def process_jsonrpc_message(self, message: dict) -> tuple[Optional[dict], Optional[str]]:
        """Process a single JSON-RPC message"""
        method = message.get("method", "")
        request_id = message.get("id")
        params = message.get("params", {})
        
        logger.info(f"Processing MCP method: {method}")
        
        # Notifications (no id) don't need responses
        if request_id is None and method in ["notifications/initialized", "initialized"]:
            return None, None
        
        # Handle methods
        if method == "initialize":
            return await self.handle_initialize(request_id)
        elif method == "tools/list":
            return await self.handle_tools_list(request_id), None
        elif method == "tools/call":
            return await self.handle_tool_call(request_id, params), None
        elif method == "resources/list":
            return await self.handle_resources_list(request_id), None
        elif method == "prompts/list":
            return await self.handle_prompts_list(request_id), None
        elif method in ["notifications/initialized", "initialized"]:
            return None, None
        else:
            return self._create_jsonrpc_error(
                request_id, -32601, f"Method not found: {method}"
            ), None


# Create server instance
http_server = FHLBibleHTTPServer()


async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy", 
        "server": "fhl-bible-mcp", 
        "version": "0.1.2"
    })


def format_sse_event(data: dict, event_id: Optional[str] = None) -> str:
    """Format a Server-Sent Event"""
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


async def mcp_post_endpoint(request: Request) -> Response:
    """
    Main MCP endpoint for Smithery - POST handler
    Implements Streamable HTTP transport
    """
    try:
        body = await request.json()
        logger.info(f"MCP POST request received: {json.dumps(body, ensure_ascii=False)[:500]}")
        
        # Check Accept header
        accept = request.headers.get("accept", "")
        supports_sse = "text/event-stream" in accept
        
        # Handle batch requests
        if isinstance(body, list):
            messages = body
        else:
            messages = [body]
        
        # Check if all are notifications/responses (no id)
        all_notifications = all(msg.get("id") is None for msg in messages)
        
        if all_notifications:
            # Process notifications silently
            for msg in messages:
                await http_server.process_jsonrpc_message(msg)
            return Response(status_code=202)
        
        # Process requests and collect responses
        responses = []
        session_id = None
        
        for msg in messages:
            response, new_session_id = await http_server.process_jsonrpc_message(msg)
            if new_session_id:
                session_id = new_session_id
            if response:
                responses.append(response)
        
        # Build response headers
        headers = {}
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        
        # Return response
        if supports_sse and len(responses) > 0:
            # Return as SSE stream
            async def generate_sse() -> AsyncGenerator[str, None]:
                for i, resp in enumerate(responses):
                    yield format_sse_event(resp, event_id=str(i))
            
            return StreamingResponse(
                generate_sse(),
                media_type="text/event-stream",
                headers=headers
            )
        else:
            # Return as JSON
            if len(responses) == 1:
                result = responses[0]
            else:
                result = responses
            
            return JSONResponse(result, headers=headers)
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return JSONResponse(
            http_server._create_jsonrpc_error(None, -32700, "Parse error"),
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}", exc_info=True)
        return JSONResponse(
            http_server._create_jsonrpc_error(None, -32603, str(e)),
            status_code=500
        )


async def mcp_get_endpoint(request: Request) -> Response:
    """
    MCP endpoint GET handler - for SSE streaming from server
    """
    accept = request.headers.get("accept", "")
    
    if "text/event-stream" not in accept:
        return JSONResponse(
            {"error": "Must accept text/event-stream"},
            status_code=406
        )
    
    # Return empty SSE stream (server doesn't initiate messages)
    async def generate_sse() -> AsyncGenerator[str, None]:
        # Keep connection alive with periodic comments
        while True:
            yield ": keepalive\n\n"
            await asyncio.sleep(30)
    
    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream"
    )


# Create Starlette app
app = Starlette(
    debug=False,
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Route("/mcp", mcp_post_endpoint, methods=["POST"]),
        Route("/mcp", mcp_get_endpoint, methods=["GET"]),
        Route("/", health_check, methods=["GET"]),
    ]
)


def main():
    """Main entry point for HTTP server"""
    logger.info("Starting FHL Bible MCP HTTP Server...")
    logger.info("Server capabilities:")
    logger.info("  - Tools: 24 functions")
    logger.info("  - Endpoint: /mcp (POST/GET)")
    logger.info("  - Health: /health (GET)")
    logger.info("  - Transport: Streamable HTTP with SSE support")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
