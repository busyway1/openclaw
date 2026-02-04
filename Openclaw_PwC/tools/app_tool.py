"""
Application control tools.

Reference: openclaw bash-tools.exec.ts patterns
- Cross-platform application launching
- Process management with psutil
"""

from langchain_core.tools import tool
import subprocess
import platform
from typing import Optional

# Common application aliases (cross-platform)
APP_ALIASES = {
    # Windows aliases
    "notepad": {"windows": "notepad.exe"},
    "calculator": {"windows": "calc.exe", "darwin": "Calculator", "linux": "gnome-calculator"},
    "calc": {"windows": "calc.exe", "darwin": "Calculator", "linux": "gnome-calculator"},
    "explorer": {"windows": "explorer.exe", "darwin": "Finder", "linux": "nautilus"},
    "browser": {"windows": "start", "darwin": "Safari", "linux": "firefox"},
    "terminal": {"windows": "cmd.exe", "darwin": "Terminal", "linux": "gnome-terminal"},
    "paint": {"windows": "mspaint.exe"},
    "word": {"windows": "WINWORD.EXE"},
    "excel": {"windows": "EXCEL.EXE"},
    "powerpoint": {"windows": "POWERPNT.EXE"},
    "outlook": {"windows": "OUTLOOK.EXE"},
    "vscode": {"windows": "code", "darwin": "Visual Studio Code", "linux": "code"},
    "code": {"windows": "code", "darwin": "Visual Studio Code", "linux": "code"},
    # macOS aliases
    "textedit": {"darwin": "TextEdit"},
    "safari": {"darwin": "Safari"},
    "finder": {"darwin": "Finder"},
    "preview": {"darwin": "Preview"},
    "notes": {"darwin": "Notes", "windows": "notepad.exe"},
}

# Protected processes that should not be killed
PROTECTED_PROCESSES = {
    "system",
    "systemd",
    "init",
    "kernel",
    "launchd",
    "loginwindow",
    "windowserver",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "explorer.exe",
    "dwm.exe",
}


def _get_platform() -> str:
    """Get normalized platform name."""
    system = platform.system().lower()
    if system == "darwin":
        return "darwin"
    elif system == "windows":
        return "windows"
    else:
        return "linux"


def _resolve_app_name(app_name: str) -> str:
    """Resolve app alias to actual app name."""
    app_lower = app_name.lower().strip()
    current_platform = _get_platform()

    if app_lower in APP_ALIASES:
        platform_apps = APP_ALIASES[app_lower]
        if current_platform in platform_apps:
            return platform_apps[current_platform]

    return app_name


@tool
def open_application(app_name: str) -> str:
    """
    Open an application by name or path.

    Args:
        app_name: Application name or full path

    Returns:
        Success message or error

    Windows examples:
        - "notepad" -> Opens Notepad
        - "calc" or "calculator" -> Opens Calculator
        - "explorer" -> Opens File Explorer
        - "code" or "vscode" -> Opens VS Code
        - "C:\\Program Files\\..." -> Full path

    macOS examples:
        - "TextEdit" -> Opens TextEdit
        - "Safari" -> Opens Safari
        - "Calculator" -> Opens Calculator
        - "/Applications/..." -> Full path

    Linux examples:
        - "firefox" -> Opens Firefox
        - "nautilus" -> Opens Files
        - "gnome-terminal" -> Opens Terminal
    """
    try:
        resolved_name = _resolve_app_name(app_name)
        current_platform = _get_platform()

        if current_platform == "windows":
            # Windows: use 'start' command
            # For .exe files or full paths, run directly
            if resolved_name.lower().endswith(".exe") or "\\" in resolved_name or "/" in resolved_name:
                subprocess.Popen(resolved_name, shell=True)
            else:
                subprocess.Popen(f'start "" "{resolved_name}"', shell=True)

        elif current_platform == "darwin":
            # macOS: use 'open -a' command
            if resolved_name.startswith("/"):
                # Full path
                subprocess.Popen(["open", resolved_name])
            else:
                subprocess.Popen(["open", "-a", resolved_name])

        else:
            # Linux: run directly or use xdg-open
            subprocess.Popen(resolved_name, shell=True)

        return f"Opened application: {app_name}" + (f" (resolved to: {resolved_name})" if resolved_name != app_name else "")

    except FileNotFoundError:
        return f"Error: Application not found: {app_name}"
    except Exception as e:
        return f"Error opening application: {type(e).__name__}: {str(e)}"


@tool
def list_processes(filter_name: Optional[str] = None) -> str:
    """
    List running processes.

    Args:
        filter_name: Optional filter to show only matching process names

    Returns:
        Formatted list of processes with PID, name, CPU%, and memory

    Examples:
        - list_processes() -> All processes
        - list_processes("chrome") -> Only Chrome-related processes
        - list_processes("python") -> Only Python processes
    """
    try:
        import psutil

        processes = []

        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                name = info["name"] or "(unknown)"

                # Apply filter
                if filter_name and filter_name.lower() not in name.lower():
                    continue

                processes.append({
                    "pid": info["pid"],
                    "name": name,
                    "cpu": info["cpu_percent"] or 0,
                    "memory": info["memory_percent"] or 0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by memory usage (descending)
        processes.sort(key=lambda x: x["memory"], reverse=True)

        # Limit to top 50
        processes = processes[:50]

        if not processes:
            return f"No processes found" + (f" matching '{filter_name}'" if filter_name else "")

        # Format output
        output = [f"Running Processes" + (f" (filter: {filter_name})" if filter_name else "")]
        output.append(f"{'PID':>8}  {'CPU%':>6}  {'MEM%':>6}  Name")
        output.append("-" * 60)

        for proc in processes:
            output.append(f"{proc['pid']:>8}  {proc['cpu']:>6.1f}  {proc['memory']:>6.1f}  {proc['name']}")

        output.append(f"\nTotal: {len(processes)} processes shown")

        return "\n".join(output)

    except ImportError:
        return "Error: 'psutil' not installed. Run: pip install psutil"
    except Exception as e:
        return f"Error listing processes: {type(e).__name__}: {str(e)}"


@tool
def kill_process(process_name: str, force: bool = False) -> str:
    """
    Kill processes by name.

    Args:
        process_name: Name of the process to kill (partial match)
        force: If True, force kill (SIGKILL). Default: graceful (SIGTERM)

    Returns:
        Number of processes killed or error message

    Examples:
        - kill_process("notepad")
        - kill_process("chrome", force=True)

    Warning:
        System-critical processes are protected and cannot be killed.
    """
    try:
        import psutil

        process_lower = process_name.lower()

        # Security check
        if process_lower in PROTECTED_PROCESSES:
            return f"Error: Cannot kill protected system process: {process_name}"

        killed = 0
        errors = []

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if process_lower in (proc.info["name"] or "").lower():
                    proc_name = proc.info["name"]
                    pid = proc.info["pid"]

                    # Double-check protection
                    if proc_name.lower() in PROTECTED_PROCESSES:
                        continue

                    if force:
                        proc.kill()
                    else:
                        proc.terminate()

                    killed += 1

            except psutil.NoSuchProcess:
                continue
            except psutil.AccessDenied:
                errors.append(f"Access denied for PID {proc.info['pid']}")
            except Exception as e:
                errors.append(f"Error killing PID {proc.info['pid']}: {str(e)}")

        result = []
        if killed > 0:
            result.append(f"Successfully {'killed' if force else 'terminated'} {killed} process(es) matching '{process_name}'")
        else:
            result.append(f"No processes found matching '{process_name}'")

        if errors:
            result.append(f"Errors: {'; '.join(errors)}")

        return "\n".join(result)

    except ImportError:
        return "Error: 'psutil' not installed. Run: pip install psutil"
    except Exception as e:
        return f"Error killing process: {type(e).__name__}: {str(e)}"


@tool
def get_system_info() -> str:
    """
    Get system information (OS, CPU, memory, disk).

    Returns:
        Formatted system information
    """
    try:
        import psutil

        # OS info
        uname = platform.uname()

        # CPU info
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory info
        memory = psutil.virtual_memory()

        # Disk info
        disk = psutil.disk_usage("/")

        output = [
            "System Information",
            "=" * 40,
            f"OS: {uname.system} {uname.release}",
            f"Machine: {uname.machine}",
            f"Hostname: {uname.node}",
            "",
            "CPU",
            f"  Cores: {cpu_count}",
            f"  Usage: {cpu_percent}%",
            "",
            "Memory",
            f"  Total: {memory.total / (1024**3):.1f} GB",
            f"  Used: {memory.used / (1024**3):.1f} GB ({memory.percent}%)",
            f"  Available: {memory.available / (1024**3):.1f} GB",
            "",
            "Disk",
            f"  Total: {disk.total / (1024**3):.1f} GB",
            f"  Used: {disk.used / (1024**3):.1f} GB ({disk.percent}%)",
            f"  Free: {disk.free / (1024**3):.1f} GB",
        ]

        return "\n".join(output)

    except ImportError:
        return "Error: 'psutil' not installed. Run: pip install psutil"
    except Exception as e:
        return f"Error getting system info: {type(e).__name__}: {str(e)}"
