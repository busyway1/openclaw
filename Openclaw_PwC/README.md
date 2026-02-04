# PWC AI Assistant PoC

Comprehensive PC control tools for AI assistant, built with LangChain.

## Features

| Category | Tools | Description |
|----------|-------|-------------|
| **Shell** | `execute_command` | Run shell commands with timeout & security |
| **File** | `read_file`, `write_file`, `list_directory`, `delete_file`, `create_directory` | File system operations |
| **Web** | `fetch_webpage`, `web_search`, `clear_web_cache` | Web fetching & DuckDuckGo search |
| **Browser** | `open_url`, `take_screenshot`, `get_browser_bookmarks` | Browser control |
| **Office** | `read_excel`, `write_excel`, `read_word`, `write_word`, `list_excel_sheets` | Excel & Word manipulation |
| **App** | `open_application`, `list_processes`, `kill_process`, `get_system_info` | Application & process control |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key
export OPENAI_API_KEY=your-api-key

# Run example
python example_agent.py
```

## Usage with LangChain

```python
from tools import TOOLS
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Create agent with all tools
llm = ChatOpenAI(model="gpt-4o-mini")
agent = create_react_agent(llm, TOOLS)

# Run
result = agent.invoke({"messages": [("user", "Downloads 폴더 파일 목록 보여줘")]})
```

## Security Features

- **Path validation**: Blocks system directories (`/etc`, `C:\Windows`)
- **SSRF protection**: Blocks internal IPs (localhost, 10.x, 192.168.x)
- **Process protection**: Prevents killing critical system processes
- **File size limits**: 10MB max for file operations
- **Timeout handling**: Commands timeout after 30s (configurable)

## Tool Reference

### File Tools

```python
# Read file
read_file("~/Documents/report.txt")

# Write file
write_file("~/Desktop/memo.txt", "Hello World")

# List directory
list_directory("~/Downloads")
```

### Web Tools

```python
# Fetch webpage (with caching)
fetch_webpage("https://python.org")

# Search web
web_search("Python LangChain tutorial", num_results=5)
```

### Office Tools

```python
# Read Excel
read_excel("data.xlsx", sheet_name="Sheet1")

# Write Excel (CSV format input)
write_excel("output.xlsx", "Name,Age\nAlice,30\nBob,25")

# Read/Write Word
read_word("document.docx")
write_word("memo.docx", "Meeting notes...", title="Meeting")
```

### App Tools

```python
# Open application
open_application("notepad")  # or "calculator", "vscode", etc.

# List processes
list_processes("chrome")

# Kill process
kill_process("notepad")
```

## Reference

Based on [openclaw](https://github.com/openclaw/openclaw) patterns:
- `web-fetch.ts`: Caching, SSRF protection
- `web-search.ts`: Provider abstraction
- `browser-tool.ts`: Action-based dispatch
- `bash-tools.exec.ts`: Environment validation, timeout
