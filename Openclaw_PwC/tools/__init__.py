"""
PWC AI Assistant Tools

Comprehensive PC control tools for AI assistant.
Based on openclaw patterns: caching, error handling, security validation.
"""

# Shell execution
from .exec_tool import execute_command

# File system
from .file_tool import (
    read_file,
    write_file,
    list_directory,
    delete_file,
    create_directory,
)

# Web
from .web_tool import (
    fetch_webpage,
    web_search,
    clear_web_cache,
)

# Browser
from .browser_tool import (
    open_url,
    take_screenshot,
    get_browser_bookmarks,
)

# Office (Excel/Word)
from .office_tool import (
    read_excel,
    write_excel,
    read_word,
    write_word,
    list_excel_sheets,
)

# Application control
from .app_tool import (
    open_application,
    list_processes,
    kill_process,
    get_system_info,
)

# All tools list for LangChain agent
TOOLS = [
    # Shell
    execute_command,
    # File system
    read_file,
    write_file,
    list_directory,
    delete_file,
    create_directory,
    # Web
    fetch_webpage,
    web_search,
    clear_web_cache,
    # Browser
    open_url,
    take_screenshot,
    get_browser_bookmarks,
    # Office
    read_excel,
    write_excel,
    read_word,
    write_word,
    list_excel_sheets,
    # Application
    open_application,
    list_processes,
    kill_process,
    get_system_info,
]

__all__ = [
    # Shell
    "execute_command",
    # File system
    "read_file",
    "write_file",
    "list_directory",
    "delete_file",
    "create_directory",
    # Web
    "fetch_webpage",
    "web_search",
    "clear_web_cache",
    # Browser
    "open_url",
    "take_screenshot",
    "get_browser_bookmarks",
    # Office
    "read_excel",
    "write_excel",
    "read_word",
    "write_word",
    "list_excel_sheets",
    # Application
    "open_application",
    "list_processes",
    "kill_process",
    "get_system_info",
    # All tools list
    "TOOLS",
]
