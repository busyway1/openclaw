"""
Browser control tools.

Reference: openclaw browser-tool.ts patterns
- Action-based dispatch
- Cross-platform support
"""

from langchain_core.tools import tool
import webbrowser
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional


def _get_desktop_path() -> Path:
    """Get user's Desktop path cross-platform."""
    home = Path.home()

    if platform.system() == "Windows":
        desktop = home / "Desktop"
        if not desktop.exists():
            # Try OneDrive Desktop
            onedrive_desktop = home / "OneDrive" / "Desktop"
            if onedrive_desktop.exists():
                return onedrive_desktop
    else:
        desktop = home / "Desktop"

    return desktop if desktop.exists() else home


@tool
def open_url(url: str, browser: Optional[str] = None) -> str:
    """
    Open a URL in the default web browser.

    Args:
        url: The URL to open
        browser: Optional browser name ('chrome', 'firefox', 'edge', 'safari')

    Returns:
        Success message or error

    Examples:
        - open_url("https://www.google.com")
        - open_url("https://github.com", browser="chrome")
    """
    try:
        # Ensure URL has protocol
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url

        # Browser mapping
        browser_map = {
            "chrome": "google-chrome" if platform.system() == "Linux" else "chrome",
            "firefox": "firefox",
            "edge": "microsoft-edge" if platform.system() == "Linux" else "edge",
            "safari": "safari",
        }

        if browser:
            browser_key = browser.lower()
            if browser_key in browser_map:
                try:
                    browser_controller = webbrowser.get(browser_map[browser_key])
                    browser_controller.open(url)
                    return f"Opened {url} in {browser}"
                except webbrowser.Error:
                    # Fallback to default
                    pass

        # Default browser
        webbrowser.open(url)
        return f"Opened {url} in default browser"

    except Exception as e:
        return f"Error opening URL: {type(e).__name__}: {str(e)}"


@tool
def take_screenshot(output_path: Optional[str] = None) -> str:
    """
    Take a screenshot of the current screen.

    Args:
        output_path: Where to save the screenshot (default: Desktop/screenshot_TIMESTAMP.png)

    Returns:
        Path to the saved screenshot or error message

    Note:
        - Windows: Uses PIL/Pillow
        - macOS: Uses screencapture command
        - Linux: Uses scrot or gnome-screenshot
    """
    try:
        # Generate default filename if not provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            desktop = _get_desktop_path()
            output_path = str(desktop / f"screenshot_{timestamp}.png")

        output_path = str(Path(output_path).expanduser().resolve())

        # Ensure parent directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        system = platform.system()

        if system == "Windows":
            try:
                from PIL import ImageGrab
                screenshot = ImageGrab.grab()
                screenshot.save(output_path)
                return f"Screenshot saved to: {output_path}"
            except ImportError:
                return "Error: Pillow not installed. Run: pip install pillow"

        elif system == "Darwin":  # macOS
            result = subprocess.run(
                ["screencapture", "-x", output_path],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return f"Screenshot saved to: {output_path}"
            else:
                return f"Error: screencapture failed: {result.stderr}"

        elif system == "Linux":
            # Try scrot first, then gnome-screenshot
            for cmd in [["scrot", output_path], ["gnome-screenshot", "-f", output_path]]:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        return f"Screenshot saved to: {output_path}"
                except FileNotFoundError:
                    continue
            return "Error: No screenshot tool found. Install scrot or gnome-screenshot."

        else:
            return f"Error: Unsupported platform: {system}"

    except Exception as e:
        return f"Error taking screenshot: {type(e).__name__}: {str(e)}"


@tool
def get_browser_bookmarks() -> str:
    """
    Get bookmarks from the default browser (Chrome).

    Returns:
        List of bookmarks with names and URLs

    Note:
        Currently supports Chrome on Windows and macOS
    """
    try:
        import json

        system = platform.system()
        home = Path.home()

        # Chrome bookmarks paths
        if system == "Windows":
            bookmarks_path = home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Bookmarks"
        elif system == "Darwin":
            bookmarks_path = home / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "Bookmarks"
        else:
            bookmarks_path = home / ".config" / "google-chrome" / "Default" / "Bookmarks"

        if not bookmarks_path.exists():
            return f"Chrome bookmarks not found at: {bookmarks_path}"

        # Parse bookmarks
        with open(bookmarks_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        def extract_bookmarks(node, path=""):
            results = []
            if node.get("type") == "url":
                results.append(f"{path}/{node['name']}: {node['url']}")
            elif node.get("type") == "folder":
                folder_path = f"{path}/{node['name']}" if path else node['name']
                for child in node.get("children", []):
                    results.extend(extract_bookmarks(child, folder_path))
            return results

        bookmarks = []
        for root_name, root_node in data.get("roots", {}).items():
            if isinstance(root_node, dict):
                bookmarks.extend(extract_bookmarks(root_node))

        if not bookmarks:
            return "No bookmarks found"

        return "Chrome Bookmarks:\n" + "\n".join(bookmarks[:100])  # Limit to 100

    except Exception as e:
        return f"Error reading bookmarks: {type(e).__name__}: {str(e)}"
