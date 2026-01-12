#!/usr/bin/env python3
"""
Codebeamer MCP Server
Exposes the Codebeamer Smart Tool as an MCP (Model Context Protocol) server
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from codebeamer_smart_tool import CodebeamerSmartTool


# Initialize the Codebeamer Smart Tool
# Configuration from environment variables
CODEBEAMER_URL = os.getenv("CODEBEAMER_URL", "https://your-codebeamer.com")
CODEBEAMER_API_KEY = os.getenv("CODEBEAMER_API_KEY", "")
MAX_CALLS_PER_MINUTE = int(os.getenv("CODEBEAMER_MAX_CALLS", "60"))
CACHE_TTL = int(os.getenv("CODEBEAMER_CACHE_TTL", "300"))
SSL_VERIFY_ENV = os.getenv("CODEBEAMER_SSL_VERIFY", "True")

# Parse SSL verify setting
if SSL_VERIFY_ENV.lower() == "false":
    SSL_VERIFY = False
elif SSL_VERIFY_ENV.lower() == "true":
    SSL_VERIFY = True
else:
    # Treat as path to certificate
    SSL_VERIFY = SSL_VERIFY_ENV

# Global tool instance
codebeamer_tool = None


def initialize_tool():
    """Initialize the Codebeamer Smart Tool"""
    global codebeamer_tool
    if not CODEBEAMER_API_KEY:
        raise ValueError("CODEBEAMER_API_KEY environment variable is required")
    
    codebeamer_tool = CodebeamerSmartTool(
        base_url=CODEBEAMER_URL,
        api_key=CODEBEAMER_API_KEY,
        max_calls_per_minute=MAX_CALLS_PER_MINUTE,
        default_cache_ttl=CACHE_TTL,
        ssl_verify=SSL_VERIFY
    )
    return codebeamer_tool


# Define MCP Tools
MCP_TOOLS = [
    Tool(
        name="codebeamer_query_items",
        description="""
        Query Codebeamer items efficiently using CbQL. This is the MOST EFFICIENT method.
        Replaces multiple get_projects -> get_trackers -> get_items calls with a single CbQL query.
        Use this for 90% of search operations.
        
        Efficiency: Reduces 10-25 API calls to just 1 call (96% reduction).
        
        Examples:
        - Find all open bugs in projects 123, 456
        - Get high-priority tasks assigned to specific user
        - Search items by custom field filters
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "project_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Optional: Filter by project IDs"
                },
                "tracker_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Optional: Filter by tracker IDs"
                },
                "tracker_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: Filter by tracker names (e.g., ['Bugs', 'Tasks'])"
                },
                "item_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: Filter by item types (e.g., ['Bug', 'Task'])"
                },
                "statuses": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: Filter by statuses (e.g., ['Open', 'In Progress'])"
                },
                "custom_filters": {
                    "type": "object",
                    "description": "Optional: Custom field filters (e.g., {'priority': 'High', 'assignee.name': 'John'})"
                },
                "include_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: Specific fields to include (e.g., ['summary', 'description', 'assignee'])"
                },
                "max_results": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of results to return"
                }
            }
        }
    ),
    
    Tool(
        name="codebeamer_get_project_complete",
        description="""
        Get complete project data including trackers and items in optimized calls.
        
        Instead of: get_project() -> get_trackers() -> get_items() for each tracker (50+ calls)
        This does: get_project() + get_trackers() + single CbQL for all items (3 calls)
        
        Efficiency: 94% reduction in API calls.
        """,
        inputSchema={
            "type": "object",
            "required": ["project_id"],
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The project ID to retrieve"
                },
                "include_trackers": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include tracker information"
                },
                "include_items": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include all items (may be slow for large projects)"
                },
                "include_wiki": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include wiki pages"
                }
            }
        }
    ),
    
    Tool(
        name="codebeamer_get_tracker_complete",
        description="""
        Get complete tracker data including all items and field metadata.
        
        Efficiency: 92% reduction in API calls (2 calls vs 20+).
        """,
        inputSchema={
            "type": "object",
            "required": ["tracker_id"],
            "properties": {
                "tracker_id": {
                    "type": "integer",
                    "description": "The tracker ID to retrieve"
                },
                "include_items": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include all tracker items"
                },
                "include_fields_metadata": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include field metadata (useful for test cases)"
                },
                "max_items": {
                    "type": "integer",
                    "default": 500,
                    "description": "Maximum number of items to retrieve"
                }
            }
        }
    ),
    
    Tool(
        name="codebeamer_get_items_batch",
        description="""
        Get multiple items by IDs efficiently in a single API call.
        
        Instead of: get_item(1), get_item(2), get_item(3)... (N calls)
        This does: Single CbQL query (1 call)
        
        Efficiency: 90% reduction for batch retrieval.
        """,
        inputSchema={
            "type": "object",
            "required": ["item_ids"],
            "properties": {
                "item_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of item IDs to retrieve"
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: Specific fields to include"
                }
            }
        }
    ),
    
    Tool(
        name="codebeamer_get_item_with_context",
        description="""
        Get a single item with all context (children, relations, parent) in optimized calls.
        
        Efficiency: 75% reduction (2-4 calls vs 4+).
        """,
        inputSchema={
            "type": "object",
            "required": ["item_id"],
            "properties": {
                "item_id": {
                    "type": "integer",
                    "description": "The item ID to retrieve"
                },
                "include_children": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include child items"
                },
                "include_relations": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include related items/associations"
                },
                "include_parent": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include parent item"
                }
            }
        }
    ),
    
    Tool(
        name="codebeamer_create_item",
        description="""
        Create a new tracker item in Codebeamer.
        """,
        inputSchema={
            "type": "object",
            "required": ["tracker_id", "summary"],
            "properties": {
                "tracker_id": {
                    "type": "integer",
                    "description": "The tracker ID where the item will be created"
                },
                "summary": {
                    "type": "string",
                    "description": "Item summary/title"
                },
                "description": {
                    "type": "string",
                    "description": "Optional: Item description"
                },
                "fields": {
                    "type": "object",
                    "description": "Optional: Additional fields (e.g., {'priority': 'High', 'assignee': {'id': 123}})"
                },
                "parent_id": {
                    "type": "integer",
                    "description": "Optional: Parent item ID to create as child"
                }
            }
        }
    ),
    
    Tool(
        name="codebeamer_update_item",
        description="""
        Update specific fields of an existing tracker item.
        """,
        inputSchema={
            "type": "object",
            "required": ["item_id", "fields"],
            "properties": {
                "item_id": {
                    "type": "integer",
                    "description": "The item ID to update"
                },
                "fields": {
                    "type": "object",
                    "description": "Fields to update (e.g., {'status': 'Done', 'resolution': 'Fixed'})"
                },
                "clear_cache": {
                    "type": "boolean",
                    "default": True,
                    "description": "Clear cached data for this item"
                }
            }
        }
    ),
    
    Tool(
        name="codebeamer_bulk_update_items",
        description="""
        Bulk update multiple items efficiently in a single API call.
        
        Efficiency: 95% reduction (1 call vs N calls).
        """,
        inputSchema={
            "type": "object",
            "required": ["updates"],
            "properties": {
                "updates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "itemId": {"type": "integer"},
                            "fields": {"type": "object"}
                        }
                    },
                    "description": "Array of updates [{'itemId': 123, 'fields': {'status': 'Done'}}, ...]"
                }
            }
        }
    ),
    
    Tool(
        name="codebeamer_manage_associations",
        description="""
        Create, get, or delete associations between items.
        """,
        inputSchema={
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "get", "delete"],
                    "description": "Action to perform: create, get, or delete"
                },
                "from_item_id": {
                    "type": "integer",
                    "description": "Source item ID (for create/get)"
                },
                "to_item_id": {
                    "type": "integer",
                    "description": "Target item ID (for create)"
                },
                "association_id": {
                    "type": "integer",
                    "description": "Association ID (for delete)"
                },
                "association_type": {
                    "type": "string",
                    "description": "Optional: Type of association (e.g., 'depends_on', 'related')"
                }
            }
        }
    ),
    
    Tool(
        name="codebeamer_get_hierarchy_tree",
        description="""
        Get the complete hierarchy tree for a tracker.
        
        Efficiency: 80% reduction in API calls.
        """,
        inputSchema={
            "type": "object",
            "required": ["tracker_id"],
            "properties": {
                "tracker_id": {
                    "type": "integer",
                    "description": "The tracker ID to get hierarchy for"
                },
                "max_depth": {
                    "type": "integer",
                    "default": 3,
                    "description": "Maximum depth to traverse (prevents infinite recursion)"
                }
            }
        }
    ),
    
    Tool(
        name="codebeamer_get_stats",
        description="""
        Get usage statistics for the Codebeamer tool including API calls, cache hits, and performance metrics.
        """,
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    
    Tool(
        name="codebeamer_clear_cache",
        description="""
        Clear the cache, optionally by pattern. Useful after bulk updates or when data needs to be refreshed.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Optional: Pattern to match cache keys (e.g., '/items/' to clear all item caches)"
                }
            }
        }
    )
]


# Create the MCP server
app = Server("codebeamer-mcp-server")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return MCP_TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls"""
    
    # Ensure tool is initialized
    if codebeamer_tool is None:
        initialize_tool()
    
    try:
        # Route to appropriate method
        if name == "codebeamer_query_items":
            result = codebeamer_tool.query_items(**arguments)
        
        elif name == "codebeamer_get_project_complete":
            result = codebeamer_tool.get_project_complete(**arguments)
        
        elif name == "codebeamer_get_tracker_complete":
            result = codebeamer_tool.get_tracker_complete(**arguments)
        
        elif name == "codebeamer_get_items_batch":
            result = codebeamer_tool.get_items_batch(**arguments)
        
        elif name == "codebeamer_get_item_with_context":
            result = codebeamer_tool.get_item_with_context(**arguments)
        
        elif name == "codebeamer_create_item":
            result = codebeamer_tool.create_item(**arguments)
        
        elif name == "codebeamer_update_item":
            result = codebeamer_tool.update_item_fields(**arguments)
        
        elif name == "codebeamer_bulk_update_items":
            result = codebeamer_tool.bulk_update_items(**arguments)
        
        elif name == "codebeamer_manage_associations":
            result = codebeamer_tool.manage_associations(**arguments)
        
        elif name == "codebeamer_get_hierarchy_tree":
            result = codebeamer_tool.get_hierarchy_tree(**arguments)
        
        elif name == "codebeamer_get_stats":
            result = codebeamer_tool.get_stats()
        
        elif name == "codebeamer_clear_cache":
            pattern = arguments.get("pattern")
            codebeamer_tool.clear_cache(pattern)
            result = {"message": f"Cache cleared{' for pattern: ' + pattern if pattern else ''}"}
        
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        # Format response
        return [
            TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )
        ]
    
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "tool": name,
                    "arguments": arguments
                }, indent=2)
            )
        ]


async def main():
    """Run the MCP server"""
    # Force UTF-8 encoding for stdout/stdin/stderr
    if sys.platform == 'win32':
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    # Initialize the tool on startup
    try:
        initialize_tool()
        print(f"Codebeamer MCP Server initialized")
        print(f"   URL: {CODEBEAMER_URL}")
        print(f"   Max calls/min: {MAX_CALLS_PER_MINUTE}")
        print(f"   Cache TTL: {CACHE_TTL}s")
        print(f"   SSL Verify: {SSL_VERIFY}")
        print(f"   Tools: {len(MCP_TOOLS)}")
    except Exception as e:
        print(f"Failed to initialize: {e}")
        print(f"   Make sure CODEBEAMER_API_KEY environment variable is set")
        return
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
