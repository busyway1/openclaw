"""
Shell command execution tool.

Reference: openclaw bash-tools.exec.ts patterns
- Environment variable validation
- Timeout handling
- Cross-platform support
"""

from langchain_core.tools import tool
import subprocess
import platform
import shlex
from typing import Optional

# Security: dangerous commands to block
BLOCKED_COMMANDS = {
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",  # fork bomb
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
}

# Default timeout in seconds
DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 300


def _is_blocked_command(command: str) -> bool:
    """Check if command contains blocked patterns."""
    command_lower = command.lower().strip()
    for blocked in BLOCKED_COMMANDS:
        if blocked in command_lower:
            return True
    return False


@tool
def execute_command(
    command: str,
    timeout: Optional[int] = None,
    shell: bool = True,
) -> str:
    """
    Execute a shell command and return the output.

    Args:
        command: The shell command to execute
        timeout: Timeout in seconds (default: 30, max: 300)
        shell: Whether to use shell execution (default: True)

    Returns:
        Command output (stdout + stderr) or error message

    Examples:
        - "dir" (Windows) / "ls -la" (Unix)
        - "echo Hello World"
        - "python --version"

    Security:
        - Dangerous commands are blocked
        - Timeout prevents hanging
    """
    # Validate timeout
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    timeout = min(max(1, timeout), MAX_TIMEOUT)

    # Security check
    if _is_blocked_command(command):
        return f"Error: Command blocked for security reasons: {command[:50]}..."

    try:
        # Execute command
        if platform.system() == "Windows":
            # Windows: use cmd.exe
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        else:
            # Unix: use default shell
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"

        if result.returncode != 0:
            output += f"\n[exit code]: {result.returncode}"

        return output.strip() if output.strip() else "(no output)"

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return f"Error: Command not found: {command.split()[0] if command else 'empty'}"
    except PermissionError:
        return "Error: Permission denied"
    except Exception as e:
        return f"Error executing command: {type(e).__name__}: {str(e)}"
