"""Path resolution utilities for Windows with OneDrive support."""

import os
import sys
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Cache for user directories
_USER_DIRS: Dict[str, str] = {}

# Allowed roots for file operations (user directories + configured workspace)
_ALLOWED_ROOTS: List[str] = []


def _resolve_user_dirs() -> Dict[str, str]:
    """Read real Desktop/Documents/Downloads paths from Windows registry, fall back to default."""
    if _USER_DIRS:
        return _USER_DIRS

    home = os.path.expanduser("~")
    defaults = {
        "desktop": os.path.join(home, "Desktop"),
        "documents": os.path.join(home, "Documents"),
        "downloads": os.path.join(home, "Downloads"),
        "pictures": os.path.join(home, "Pictures"),
        "music": os.path.join(home, "Music"),
        "videos": os.path.join(home, "Videos"),
    }

    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            registry_map = {
                "desktop": "Desktop",
                "documents": "Personal",
                "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
                "pictures": "My Pictures",
                "music": "My Music",
                "videos": "My Video",
            }
            for folder_key, reg_name in registry_map.items():
                try:
                    val, _ = winreg.QueryValueEx(key, reg_name)
                    if val and os.path.isdir(val):
                        defaults[folder_key] = val
                except (FileNotFoundError, OSError):
                    pass
            winreg.CloseKey(key)

            # Also check User Shell Folders for redirected paths
            try:
                key2 = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
                for folder_key, reg_name in registry_map.items():
                    try:
                        val, _ = winreg.QueryValueEx(key2, reg_name)
                        if val:
                            # Expand environment variables like %USERPROFILE%
                            expanded = os.path.expandvars(val)
                            if os.path.isdir(expanded):
                                defaults[folder_key] = expanded
                    except (FileNotFoundError, OSError):
                        pass
                winreg.CloseKey(key2)
            except (ImportError, OSError, FileNotFoundError):
                pass

        except (ImportError, OSError, FileNotFoundError):
            pass

    # Also check common OneDrive locations
    onedrive = os.environ.get("OneDrive")
    if onedrive and os.path.isdir(onedrive):
        for folder in ["Desktop", "Documents", "Pictures"]:
            path = os.path.join(onedrive, folder)
            if os.path.isdir(path):
                defaults[folder.lower()] = path

    _USER_DIRS.update(defaults)
    return _USER_DIRS


def get_user_dir(name: str) -> str:
    """Get a user directory by common name (desktop, documents, downloads, etc.)."""
    dirs = _resolve_user_dirs()
    return dirs.get(name.lower(), os.path.join(os.path.expanduser("~"), name))


def get_allowed_roots() -> List[str]:
    """Get the list of allowed root directories for file operations."""
    global _ALLOWED_ROOTS
    if not _ALLOWED_ROOTS:
        _ALLOWED_ROOTS = [
            get_user_dir("desktop"),
            get_user_dir("documents"),
            get_user_dir("downloads"),
            get_user_dir("pictures"),
            get_user_dir("music"),
            get_user_dir("videos"),
            os.path.join(os.path.expanduser("~"), "ACO_Output"),
        ]
        # Deduplicate
        seen = set()
        unique = []
        for root in _ALLOWED_ROOTS:
            norm = os.path.normpath(root)
            if norm not in seen:
                seen.add(norm)
                unique.append(norm)
        _ALLOWED_ROOTS = unique
    return _ALLOWED_ROOTS


def is_path_allowed(path: str) -> bool:
    """Check if a path is within allowed roots."""
    try:
        normalized = os.path.normpath(os.path.abspath(path))
        for root in get_allowed_roots():
            norm_root = os.path.normpath(os.path.abspath(root))
            if normalized.startswith(norm_root + os.sep) or normalized == norm_root:
                return True
    except Exception:
        pass
    return False


def resolve_path(raw: str) -> str:
    """Resolve a path with tilde, environment variables, and user directory shortcuts."""
    p = raw.strip()
    p = os.path.expanduser(p)
    p = os.path.expandvars(p)

    # Handle shortcuts like "desktop:file.txt" or "documents:folder/file.txt"
    if ":" in p and not (len(p) >= 2 and p[1] == ":"):  # Not a drive letter
        parts = p.split(":", 1)
        prefix = parts[0].lower()
        rest = parts[1]
        if prefix in ("desktop", "documents", "downloads", "pictures", "music", "videos", "home"):
            base = get_user_dir(prefix)
            p = os.path.join(base, rest)

    return os.path.normpath(p)


def find_file(filename: str) -> Optional[str]:
    """Find a file by name in the allowed roots (non-recursive first, then recursive)."""
    if not filename:
        return None

    # First check if it's already an absolute path that exists
    if os.path.isabs(filename) and os.path.exists(filename):
        return os.path.normpath(filename)

    # Search in allowed roots
    for root in get_allowed_roots():
        # Non-recursive search first
        direct = os.path.join(root, filename)
        if os.path.exists(direct):
            return os.path.normpath(direct)

    # Recursive search in allowed roots
    for root in get_allowed_roots():
        try:
            for dirpath, _, filenames in os.walk(root):
                for fname in filenames:
                    if fname.lower() == filename.lower():
                        return os.path.normpath(os.path.join(dirpath, fname))
        except (OSError, PermissionError):
            continue

    return None


def is_safe_path(path: str) -> tuple[bool, Optional[str]]:
    """Check if a path is safe (within allowed roots, not system directory).

    Returns (is_safe, error_message).
    """
    normalized = os.path.normpath(os.path.abspath(os.path.expanduser(os.path.expandvars(path))))

    # System directories that must never be written/deleted
    system_dirs = [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\ProgramData",
        "C:\\System Volume Information",
        "/etc", "/usr", "/bin", "/sbin", "/lib", "/boot", "/dev", "/proc", "/sys", "/root",
    ]

    for sys_dir in system_dirs:
        sys_norm = os.path.normpath(sys_dir)
        if normalized.startswith(sys_norm + os.sep) or normalized == sys_norm:
            return False, f"Path '{path}' is inside blocked system directory: {sys_dir}"

    # Check if within allowed roots
    if not is_path_allowed(normalized):
        return False, f"Path '{path}' is outside allowed directories. Allowed: {', '.join(get_allowed_roots())}"

    return True, None