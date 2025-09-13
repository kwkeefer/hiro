"""Target management tools for the unified HTTP MCP server.

IMPORTANT: This is NOT a separate server!

These tools work alongside HTTP tools in the serve-http command.
When DATABASE_URL is configured, both HTTP and target management
tools are automatically available in the same server instance.

The 'ai_logging' name refers to logging AI reconnaissance activities,
not a separate AI server. All tools run in the unified HTTP server.

Available tools when database is configured:
- create_target: Register new targets for testing
- update_target_status: Update target status and metadata
- get_target_summary: Get comprehensive target information
- search_targets: Search and filter targets

These tools integrate seamlessly with HTTP tools:
- HTTP requests auto-create targets if they don't exist
- HTTP requests auto-log to the database
- Target tools let you manage and query this data
"""

from .providers import AiLoggingToolProvider
from .tools import (
    CreateTargetTool,
    GetTargetSummaryTool,
    SearchTargetsTool,
    UpdateTargetStatusTool,
)

__all__ = [
    "AiLoggingToolProvider",
    "CreateTargetTool",
    "UpdateTargetStatusTool",
    "GetTargetSummaryTool",
    "SearchTargetsTool",
]
