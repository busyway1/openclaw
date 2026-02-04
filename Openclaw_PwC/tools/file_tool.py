"""
File system control tools.

Reference: openclaw bash-tools patterns
- Path validation
- Cross-platform path handling
- File size limits
"""

from langchain_core.tools import tool
from pathlib import Path
from datetime import datetime
from typing import Optional
import os
import stat

# Limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_LINES_DISPLAY = 1000

# Dangerous paths to block (cross-platform)
BLOCKED_PATHS = {
    "/",
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/var",
    "/root",
    "C:\\Windows",
    "C:\\Windows\\System32",
    "C:\\Program Files",
}


def _resolve_path(file_path: str) -> Path:
    """Resolve and validate file path."""
    path = Path(file_path).expanduser().resolve()
    return path


def _is_blocked_path(path: Path) -> bool:
    """Check if path is in blocked list."""
    path_str = str(path)
    for blocked in BLOCKED_PATHS:
        if path_str == blocked or path_str.startswith(blocked + os.sep):
            # Allow subdirectories of blocked paths for reading (but not the root itself)
            if path_str == blocked:
                return True
    return False


def _detect_encoding(file_path: Path) -> str:
    """Detect file encoding, fallback to utf-8."""
    try:
        import chardet
        with open(file_path, "rb") as f:
            raw = f.read(min(10000, file_path.stat().st_size))
            result = chardet.detect(raw)
            return result.get("encoding") or "utf-8"
    except ImportError:
        return "utf-8"
    except Exception:
        return "utf-8"


def _format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _format_permissions(mode: int) -> str:
    """Format file permissions."""
    perms = ""
    for who in ["USR", "GRP", "OTH"]:
        for perm, char in [("R", "r"), ("W", "w"), ("X", "x")]:
            attr = getattr(stat, f"S_I{perm}{who}", 0)
            perms += char if mode & attr else "-"
    return perms


@tool
def read_file(file_path: str, encoding: Optional[str] = None) -> str:
    """
    Read file contents and return as text.

    Args:
        file_path: Full path to the file to read
        encoding: File encoding (auto-detected if not specified)

    Returns:
        File contents as text

    Examples:
        - "C:\\Users\\user\\Documents\\report.txt"
        - "/home/user/documents/report.txt"
        - "~/Desktop/memo.txt"

    Limits:
        - Maximum file size: 10MB
        - Maximum display: 1000 lines
    """
    try:
        path = _resolve_path(file_path)

        if not path.exists():
            return f"Error: File not found: {path}"

        if not path.is_file():
            return f"Error: Not a file: {path}"

        # Check file size
        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return f"Error: File too large ({_format_size(file_size)}). Maximum: {_format_size(MAX_FILE_SIZE)}"

        # Detect or use provided encoding
        enc = encoding or _detect_encoding(path)

        # Read file
        try:
            content = path.read_text(encoding=enc)
        except UnicodeDecodeError:
            # Fallback to latin-1 (accepts all bytes)
            content = path.read_text(encoding="latin-1")

        # Limit lines
        lines = content.split("\n")
        if len(lines) > MAX_LINES_DISPLAY:
            content = "\n".join(lines[:MAX_LINES_DISPLAY])
            content += f"\n\n... (truncated, showing {MAX_LINES_DISPLAY} of {len(lines)} lines)"

        return content

    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error reading file: {type(e).__name__}: {str(e)}"


@tool
def write_file(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """
    Write content to a file. Creates the file if it doesn't exist.

    Args:
        file_path: Full path to the file to write
        content: Content to write to the file
        encoding: File encoding (default: utf-8)

    Returns:
        Success message with file path and size

    Examples:
        - write_file("C:\\Users\\user\\Desktop\\memo.txt", "Hello World")
        - write_file("~/notes.txt", "My notes here")
    """
    try:
        path = _resolve_path(file_path)

        # Security check
        if _is_blocked_path(path):
            return f"Error: Writing to this location is blocked: {path}"

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        path.write_text(content, encoding=encoding)

        file_size = path.stat().st_size
        return f"Successfully wrote {_format_size(file_size)} to: {path}"

    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error writing file: {type(e).__name__}: {str(e)}"


@tool
def list_directory(path: str = ".") -> str:
    """
    List files and folders in a directory with detailed information.

    Args:
        path: Directory path (default: current directory)

    Returns:
        Formatted list of files/folders with size, date, and permissions

    Examples:
        - list_directory("C:\\Users\\user\\Documents")
        - list_directory("/home/user")
        - list_directory("~/Downloads")
        - list_directory(".") or list_directory() for current directory
    """
    try:
        dir_path = _resolve_path(path)

        if not dir_path.exists():
            return f"Error: Directory not found: {dir_path}"

        if not dir_path.is_dir():
            return f"Error: Not a directory: {dir_path}"

        entries = []
        total_files = 0
        total_dirs = 0
        total_size = 0

        for item in sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                stat_info = item.stat()
                modified = datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M")
                size = stat_info.st_size
                perms = _format_permissions(stat_info.st_mode)

                if item.is_dir():
                    type_indicator = "[DIR]"
                    size_str = "-"
                    total_dirs += 1
                else:
                    type_indicator = ""
                    size_str = _format_size(size)
                    total_files += 1
                    total_size += size

                entries.append(f"{perms}  {size_str:>10}  {modified}  {type_indicator}{item.name}")

            except (PermissionError, OSError):
                entries.append(f"?????????  {'?':>10}  {'?':>16}  {item.name} (access denied)")

        # Summary
        header = f"Directory: {dir_path}\n"
        header += f"Total: {total_dirs} folders, {total_files} files ({_format_size(total_size)})\n"
        header += "-" * 70 + "\n"

        return header + "\n".join(entries) if entries else header + "(empty directory)"

    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error listing directory: {type(e).__name__}: {str(e)}"


@tool
def delete_file(file_path: str) -> str:
    """
    Delete a file.

    Args:
        file_path: Full path to the file to delete

    Returns:
        Success or error message

    Warning:
        This action cannot be undone. Use with caution.
    """
    try:
        path = _resolve_path(file_path)

        if not path.exists():
            return f"Error: File not found: {path}"

        if not path.is_file():
            return f"Error: Not a file (use different method for directories): {path}"

        # Security check
        if _is_blocked_path(path):
            return f"Error: Deleting from this location is blocked: {path}"

        # Delete
        path.unlink()
        return f"Successfully deleted: {path}"

    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error deleting file: {type(e).__name__}: {str(e)}"


@tool
def create_directory(path: str) -> str:
    """
    Create a new directory (including parent directories if needed).

    Args:
        path: Full path of the directory to create

    Returns:
        Success or error message

    Examples:
        - create_directory("C:\\Users\\user\\Documents\\NewFolder")
        - create_directory("~/projects/my-project")
    """
    try:
        dir_path = _resolve_path(path)

        if dir_path.exists():
            if dir_path.is_dir():
                return f"Directory already exists: {dir_path}"
            else:
                return f"Error: A file with this name already exists: {dir_path}"

        # Security check
        if _is_blocked_path(dir_path):
            return f"Error: Creating directories in this location is blocked: {dir_path}"

        # Create directory
        dir_path.mkdir(parents=True, exist_ok=True)
        return f"Successfully created directory: {dir_path}"

    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error creating directory: {type(e).__name__}: {str(e)}"
