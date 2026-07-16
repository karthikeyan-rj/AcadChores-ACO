import os
import re
import sys
import json
import shlex
import logging
import asyncio
import subprocess
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional, List, Set
from urllib.parse import urlparse
from playwright.async_api import async_playwright

from app.core.security import permission_guard
from app.services.desktop_service import desktop_service
from app.services.vision_engine import vision_engine
from app.services.indexer import file_indexer
from app.services.process_manager import register_process, unregister_process
from app.ai import llm_service
from app.utils.paths import resolve_path, get_allowed_roots, find_file, is_safe_path
from app.utils.paths import resolve_path, get_allowed_roots, find_file

logger = logging.getLogger(__name__)

BROWSER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".aco_browser_data")

# --- Safety constants ---

# Destructive terminal commands that must never be executed
BLOCKED_TERMINAL_PATTERNS: List[str] = [
    r'\brm\s+-rf\s+/',
    r'\bformat\s+[cCdD]:',
    r'\bdel\s+/[sS]\s+/[qQ]',
    r'\bshutdown\s',
    r'\breboot\b',
    r'\bmkfs\b',
    r'\bdd\s+if=',
    r':\(\)\s*\{',         # fork bomb
    r':\(\)\{',            # fork bomb (no space)
    r'\bsudo\s+rm\s+-rf\s+/',
    r'\btaskkill\s+/F\s+/IM\s+explorer',
    r'\bwevtutil\s+cl\s+',
    r'\bcd\s+\.\.',           # no escaping to parent from sandbox
    r'\bcacls\b',
    r'\bicacls\b.*\b/\w*\s*remov',  # remove permissions
    r'\breg\s+delete\b',
    r'\bnet\s+user\b.*/delete',  # net user ... /delete
]

# Compiled regex for performance
_BLOCKED_TERMINAL_RE = re.compile('|'.join(BLOCKED_TERMINAL_PATTERNS), re.IGNORECASE)

# Maximum output size from terminal commands (1 MB)
MAX_TERMINAL_OUTPUT_BYTES: int = 1_000_000

# Allowed URL schemes for browser navigation
ALLOWED_URL_SCHEMES: Set[str] = {"http", "https"}

# Maximum scraped text size (500 KB)
MAX_SCRAPED_TEXT_BYTES: int = 500_000

# System directories that file agent must not write/delete
BLOCKED_FILE_PATHS: List[str] = [
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
    "C:\\System Volume Information",
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/lib",
    "/boot",
    "/dev",
    "/proc",
    "/sys",
    "/root",
]

# Task execution timeout (5 minutes)
TASK_EXECUTION_TIMEOUT: float = 300.0


def _needs_shell(cmd: str) -> bool:
    """Check if a command requires shell interpretation (pipes, redirects, &&, etc.)."""
    shell_indicators = ['|', '&&', '||', '>', '<', '>>', '<<', '`', '$(']
    for indicator in shell_indicators:
        if indicator in cmd:
            return True
    return False

SESSION_MARKER = os.path.join(BROWSER_DATA_DIR, ".session_active")


def _is_terminal_command_blocked(command: str) -> Optional[str]:
    """Check if a terminal command matches any blocked destructive pattern.
    Returns the matched pattern description if blocked, None if safe."""
    match = _BLOCKED_TERMINAL_RE.search(command)
    if match:
        return f"Blocked destructive pattern: {match.group()}"
    return None


def _validate_url_scheme(url: str) -> bool:
    """Validate that a URL uses only allowed schemes (http/https)."""
    try:
        parsed = urlparse(url)
        return parsed.scheme.lower() in ALLOWED_URL_SCHEMES
    except Exception:
        return False


def _is_path_blocked(path: str, action: str = "write") -> Optional[str]:
    """Check if a file path is in a blocked system directory.
    Returns the blocking reason if blocked, None if safe."""
    normalized = os.path.normpath(os.path.expanduser(os.path.expandvars(path)))
    for blocked in BLOCKED_FILE_PATHS:
        blocked_norm = os.path.normpath(blocked)
        if normalized.startswith(blocked_norm + os.sep) or normalized == blocked_norm:
            return f"Path '{path}' is inside blocked system directory: {blocked}"
    return None


def _truncate_output(text: str, max_bytes: int = MAX_TERMINAL_OUTPUT_BYTES) -> str:
    """Truncate output to max_bytes, preserving the end (most relevant part)."""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[-max_bytes:]
    return truncated.decode("utf-8", errors="replace")


def _sanitize_js_string(value: str) -> str:
    """Escape a string for safe interpolation inside a JavaScript string literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")

class BaseAgent(ABC):
    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any], progress_cb: Callable[[int, str], Any]) -> Dict[str, Any]:
        """Runs the action with validation and progress tracking."""
        pass


class DesktopAgent(BaseAgent):
    async def execute(self, action: str, params: Dict[str, Any], progress_cb: Callable[[int, str], Any]) -> Dict[str, Any]:
        await progress_cb(10, f"Starting desktop action: {action}")
        
        # Intercept action validation through permission guard
        authorized = await permission_guard.authorize_action("desktop", action, params)
        if not authorized:
            raise PermissionError(f"User denied execution of desktop action: {action}")

        await progress_cb(30, "Action authorized by Permission Guard.")

        if action == "click":
            x, y = params["x"], params["y"]
            double = params.get("double", False)
            await progress_cb(60, f"Simulating mouse click at ({x}, {y})")
            desktop_service.click(x, y, double=double)
        elif action == "type":
            text = params["text"]
            await progress_cb(60, "Typing text payload")
            desktop_service.type_text(text)
        elif action == "press":
            key = params["key"]
            await progress_cb(60, f"Pressing key: {key}")
            desktop_service.press_key(key)
        else:
            raise ValueError(f"Unknown desktop agent action: {action}")

        await progress_cb(100, f"Desktop action {action} completed successfully.")
        return {"success": True}


class BrowserAgent(BaseAgent):
    def __init__(self):
        self._playwright = None
        self._user_contexts: Dict[str, Any] = {}  # user_id -> {"context": ..., "page": ...}

    def _user_data_dir(self, user_id: str) -> str:
        return os.path.join(BROWSER_DATA_DIR, f"user_{user_id}")

    def _session_saved(self, user_id: str) -> bool:
        return os.path.exists(os.path.join(self._user_data_dir(user_id), ".session_active"))

    async def _ensure_browser(self, user_id: str = "default"):
        if user_id in self._user_contexts:
            entry = self._user_contexts[user_id]
            if entry["context"] and entry["page"]:
                try:
                    await entry["page"].evaluate("1 + 1")
                    return
                except Exception:
                    logger.warning(f"Stale browser context for user {user_id}, relaunching.")
                    try:
                        await entry["context"].close()
                    except Exception:
                        pass
                    del self._user_contexts[user_id]

        if not self._playwright:
            self._playwright = await async_playwright().start()

        data_dir = self._user_data_dir(user_id)
        os.makedirs(data_dir, exist_ok=True)
        headless = self._session_saved(user_id)

        if not headless:
            logger.info(f"No saved session for user {user_id} — launching headed mode for login.")
            logger.info("Please sign into Google in the browser window that opens.")
            logger.info("Once logged in, the session will be saved for future headless runs.")

        try:
            context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=data_dir,
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                    '--no-first-run',
                    '--no-default-browser-check',
                ],
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                ignore_default_args=['--enable-automation'],
            )
        except Exception as e:
            logger.warning(f"Browser launch failed (possibly corrupted profile), retrying with fresh profile: {e}")
            import shutil
            try:
                shutil.rmtree(data_dir, ignore_errors=True)
                os.makedirs(data_dir, exist_ok=True)
            except Exception:
                pass
            context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=data_dir,
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                ],
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                ignore_default_args=['--enable-automation'],
            )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.add_init_script('delete Object.getPrototypeOf(navigator).webdriver')

        self._user_contexts[user_id] = {"context": context, "page": page, "headless": headless}

        if not headless:
            await self._wait_for_login(page, user_id)

    async def _relaunch_headed(self, user_id: str):
        """Close current context and relaunch in headed mode for interactive login."""
        entry = self._user_contexts.get(user_id)
        if entry and entry.get("context"):
            try:
                await entry["context"].close()
            except Exception:
                pass

        data_dir = self._user_data_dir(user_id)
        logger.info(f"Relaunching browser in HEADED mode for user {user_id} to complete login...")

        context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=data_dir,
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-gpu',
                '--no-first-run',
            ],
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            ignore_default_args=['--enable-automation'],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.add_init_script('delete Object.getPrototypeOf(navigator).webdriver')
        self._user_contexts[user_id] = {"context": context, "page": page, "headless": False}
        return page

    async def _wait_for_login(self, page, user_id: str):
        """Navigate to Google sign-in and wait for user to complete authentication."""
        logger.info("Opening Google sign-in in browser window...")
        await page.goto("https://accounts.google.com/signin", timeout=60000, wait_until="domcontentloaded")
        logger.info(">>> PLEASE SIGN INTO GOOGLE IN THE BROWSER WINDOW <<<")
        logger.info("Waiting for sign-in to complete (timeout: 5 minutes)...")

        for i in range(300):  # 5 minutes, 1 second intervals
            await asyncio.sleep(1)
            try:
                url = page.url
                # Check if navigated away from sign-in page
                if "accounts.google.com" not in url:
                    logger.info(f"Navigated to: {url} — sign-in likely complete")
                    await asyncio.sleep(3)  # Let final page settle
                    break
                # Check for Google cookies (session established)
                cookies = await page.context.cookies("https://accounts.google.com")
                has_session = any(c["name"] in ("SID", "SSID", "HSID", "LSID") for c in cookies)
                if has_session and i > 5:
                    logger.info("Google session cookies detected — sign-in complete")
                    # Navigate away from sign-in page to confirm
                    try:
                        await page.goto("https://myaccount.google.com", timeout=15000)
                    except Exception:
                        pass
                    await asyncio.sleep(2)
                    break
            except Exception as e:
                logger.debug(f"Login check iteration {i}: {e}")
        else:
            logger.warning("Login wait timed out after 5 minutes. Proceeding anyway.")

        marker = os.path.join(self._user_data_dir(user_id), ".session_active")
        with open(marker, "w") as f:
            f.write("active")
        logger.info(f"Session saved for user {user_id}. Future runs will be headless.")
        try:
            await page.goto("about:blank")
        except Exception:
            pass

    async def _handle_account_chooser(self, page, progress_cb=None):
        """Detect Google account chooser or login pages and auto-select the user's account.
        Returns the (possibly new) page if the browser was relaunched."""
        try:
            url = page.url
            content = await page.content()

            # Check if we hit a password challenge page
            is_password_page = (
                "/challenge/pwd" in url
                or "/challenge/sms" in url
                or "/challenge/iap" in url
                or ("Enter your password" in content)
                or ("Verify it's you" in content)
            )
            if is_password_page:
                logger.info("[PASSWORD_CHALLENGE] Google is asking for password/verification.")
                if progress_cb:
                    await progress_cb(75, "Google requires password/verification — opening visible browser...")
                # Find the user_id for this page
                user_id = None
                for uid, entry in self._user_contexts.items():
                    if entry["page"] == page:
                        user_id = uid
                        break
                if user_id:
                    new_page = await self._relaunch_headed(user_id)
                    try:
                        await new_page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    except Exception:
                        pass
                    if progress_cb:
                        await progress_cb(80, "Please enter password in the browser window. Waiting up to 3 minutes...")
                    for i in range(180):
                        await asyncio.sleep(1)
                        try:
                            current = new_page.url
                            if "challenge" not in current and "accounts.google.com" not in current:
                                logger.info(f"[PASSWORD_CHALLENGE] Login complete, now on: {current}")
                                break
                            cookies = await new_page.context.cookies("https://accounts.google.com")
                            has_pwd_cookie = any(c["name"] in ("SID", "SSID", "HSID") for c in cookies)
                            if has_pwd_cookie and i > 10:
                                try:
                                    await new_page.goto("https://myaccount.google.com", timeout=10000)
                                except Exception:
                                    pass
                                await asyncio.sleep(2)
                                break
                        except Exception:
                            pass
                    else:
                        logger.warning("[PASSWORD_CHALLENGE] Timed out waiting for password entry.")
                    marker = os.path.join(self._user_data_dir(user_id), ".session_active")
                    with open(marker, "w") as f:
                        f.write("active")
                    self._user_contexts[user_id]["headless"] = True
                    logger.info("[PASSWORD_CHALLENGE] Session saved. Future runs will be headless.")
                    return new_page
                return page

            # Check if we're on an account chooser page
            is_chooser = (
                "AccountChooser" in url
                or "Choose an account" in content
                or "Use your Google Account" in content
                or ("identifier" in url and "accounts.google.com" in url)
            )

            # Check if we're on a Google sign-in page (email entry)
            is_signin = (
                "signin" in url.lower()
                or "identifier" in url
                or ("accounts.google.com" in url and "Choose an account" not in content)
            )

            if is_chooser:
                logger.info("[ACOUNT_CHOOSER] Detected account chooser page, selecting account...")
                if progress_cb:
                    await progress_cb(75, "Account chooser detected, selecting account...")

                # Strategy 1: Click element with data-email attribute
                try:
                    email_el = await page.query_selector('[data-email]')
                    if email_el:
                        email = await email_el.get_attribute('data-email')
                        logger.info(f"[ACOUNT_CHOOSER] Clicking account: {email}")
                        if progress_cb:
                            await progress_cb(80, f"Clicking account: {email}")
                        await email_el.click()
                        await asyncio.sleep(4)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception:
                            pass
                        new_url = page.url
                        if "challenge" in new_url:
                            result_page = await self._handle_account_chooser(page, progress_cb)
                            if result_page:
                                return result_page
                        return page
                except Exception as e:
                    logger.debug(f"[ACOUNT_CHOOSER] data-email strategy failed: {e}")

                # Strategy 2: Click by data-identifier
                try:
                    id_el = await page.query_selector('[data-identifier]')
                    if id_el:
                        identifier = await id_el.get_attribute('data-identifier')
                        logger.info(f"[ACOUNT_CHOOSER] Clicking identifier: {identifier}")
                        if progress_cb:
                            await progress_cb(80, f"Clicking: {identifier}")
                        await id_el.click()
                        await asyncio.sleep(4)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception:
                            pass
                        new_url = page.url
                        if "challenge" in new_url:
                            result_page = await self._handle_account_chooser(page, progress_cb)
                            if result_page:
                                return result_page
                        return page
                except Exception as e:
                    logger.debug(f"[ACOUNT_CHOOSER] data-identifier strategy failed: {e}")

                # Strategy 3: Click the first list item in the account list
                try:
                    items = await page.query_selector_all('li[role="presentation"]')
                    if not items:
                        items = await page.query_selector_all('ul[role="listbox"] li')
                    if not items:
                        items = await page.query_selector_all('[data-email], [data-identifier]')
                    if items:
                        logger.info(f"[ACOUNT_CHOOSER] Found {len(items)} account entries, clicking first...")
                        if progress_cb:
                            await progress_cb(80, f"Found {len(items)} accounts, clicking...")
                        await items[0].click()
                        await asyncio.sleep(4)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception:
                            pass
                        new_url = page.url
                        if "challenge" in new_url:
                            result_page = await self._handle_account_chooser(page, progress_cb)
                            if result_page:
                                return result_page
                        return page
                except Exception as e:
                    logger.debug(f"[ACOUNT_CHOOSER] list item strategy failed: {e}")

                # Strategy 4: Click any div with role="link" inside account list
                try:
                    link_els = await page.query_selector_all('div[role="link"][data-email]')
                    if link_els:
                        await link_els[0].click()
                        await asyncio.sleep(4)
                        new_url = page.url
                        if "challenge" in new_url:
                            result_page = await self._handle_account_chooser(page, progress_cb)
                            if result_page:
                                return result_page
                        return page
                except Exception:
                    pass

                logger.warning("[ACOUNT_CHOOSER] Could not find clickable account element")
                if progress_cb:
                    await progress_cb(80, "Could not find account to click")

            elif is_signin and "accounts.google.com" in url:
                logger.info("[SIGNIN] On Google sign-in page. Waiting for user interaction.")
                if progress_cb:
                    await progress_cb(75, "On Google sign-in page...")

        except Exception as e:
            logger.warning(f"Account chooser handling error: {e}")

        return page

    async def execute(self, action: str, params: Dict[str, Any], progress_cb: Callable[[int, str], Any], user_id: str = "default") -> Dict[str, Any]:
        await progress_cb(10, f"Initializing browser session for: {action}")
        
        authorized = await permission_guard.authorize_action("browser", action, params)
        if not authorized:
            raise PermissionError(f"User denied execution of browser action: {action}")

        try:
            await self._ensure_browser(user_id)
        except Exception as e:
            logger.error(f"Browser launch failed: {e}\n{traceback.format_exc()}")
            raise RuntimeError(f"Failed to launch browser: {e}")
        await progress_cb(40, "Browser environment ready.")

        page = self._user_contexts[user_id]["page"]
        result = {}
        if action == "navigate":
            url = params["url"]
            if not _validate_url_scheme(url):
                raise ValueError(f"Blocked navigation to URL with disallowed scheme: {url}")
            await progress_cb(60, f"Navigating to URL: {url}")
            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"Navigate failed to {url}: {e}\n{traceback.format_exc()}")
                raise RuntimeError(f"Failed to navigate to {url}: {e}")
            await asyncio.sleep(3)
            current_url = page.url
            logger.info(f"[NAV] Landed on: {current_url}")
            await progress_cb(70, f"Landed on: {current_url[:80]}")

            # Handle Google account chooser / login redirects — may return a new page
            new_page = await self._handle_account_chooser(page, progress_cb)
            if new_page and new_page != page:
                page = new_page
                self._user_contexts[user_id]["page"] = page

            # Wait for final page to load
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

            final_url = page.url
            logger.info(f"[NAV] Final URL: {final_url}")
            await progress_cb(90, f"Final page: {final_url[:80]}")
            result = {"title": await page.title(), "url": final_url}
        elif action == "click":
            selector = params["selector"]
            fallback_text = params.get("fallback_text", "")
            await progress_cb(70, f"Clicking selector: {selector}")
            clicked = False
            # Try primary selector first (try each comma-separated one)
            selectors = [s.strip() for s in selector.split(",")]
            used_click_sel = None
            for sel in selectors:
                try:
                    await page.click(sel, timeout=5000)
                    clicked = True
                    used_click_sel = sel
                    await progress_cb(75, f"Clicked via selector: {sel[:60]}")
                    logger.info(f"[CLICK] Successfully clicked selector: {sel}")
                    break
                except Exception as e:
                    logger.warning(f"Click selector failed: {sel} — {e}")
                    continue
            # Try text-based click as last resort
            if not clicked and fallback_text:
                try:
                    await page.get_by_text(fallback_text, exact=True).click(timeout=5000)
                    clicked = True
                    await progress_cb(75, f"Used text-based click: '{fallback_text}'")
                except Exception:
                    pass
            # Try aria-label text match
            if not clicked and fallback_text:
                try:
                    await page.click(f"[aria-label*='{fallback_text}']", timeout=5000)
                    clicked = True
                    await progress_cb(75, f"Used aria-label click: '{fallback_text}'")
                except Exception:
                    pass
            # JS click as final attempt
            if not clicked:
                try:
                    safe_text = _sanitize_js_string(fallback_text or "Send")
                    clicked_js = await page.evaluate(f"""
                        (() => {{
                            const targetText = '{safe_text}';

                            function isEnabled(el) {{
                                if (!el) return false;
                                if (el.getAttribute('aria-disabled') === 'true') return false;
                                if (el.classList.contains('T-I-JJ')) return false; // Gmail disabled class
                                return el.offsetParent !== null && !el.disabled;
                            }}

                            // Gmail-specific Send button selectors (most specific first)
                            // NOTE: div.T-I.T-I-KE.L3 is the COMPOSE button, NOT Send — removed
                            const gmailSelectors = [
                                'div[role="button"][data-tooltip*="Send (~Ctrl"]',
                                'div[role="button"][aria-label*="Send (~Ctrl"]',
                                'div[role="button"][data-tooltip*="Send"]',
                                'div[role="button"][aria-label="Send"]',
                                'tr.btC td div[role="button"]',
                            ];
                            for (const sel of gmailSelectors) {{
                                try {{
                                    const el = document.querySelector(sel);
                                    if (isEnabled(el)) {{
                                        el.click();
                                        return true;
                                    }}
                                }} catch(e) {{}}
                            }}

                            // Generic selectors by text match
                            const selectors = [
                                'div[role="button"]', 'button', 'span[role="button"]',
                                'a[role="button"]', '[data-tooltip*="Send"]', '[aria-label*="Send"]'
                            ];
                            for (const sel of selectors) {{
                                const els = document.querySelectorAll(sel);
                                for (const el of els) {{
                                    const txt = (el.textContent || '').trim();
                                    if (txt === targetText || txt.startsWith(targetText)) {{
                                        el.click();
                                        return true;
                                    }}
                                }}
                            }}

                            // XPath fallback for text content
                            try {{
                                const xpath = `//*[text()='${{targetText}}']`;
                                const xresult = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                                if (xresult.singleNodeValue) {{
                                    xresult.singleNodeValue.click();
                                    return true;
                                }}
                            }} catch(e) {{}}

                            return false;
                        }})()
                    """)
                    if clicked_js:
                        clicked = True
                        await progress_cb(75, "Used JS fallback click on Send button")
                    else:
                        logger.warning("JS fallback click did not find any Send button")
                except Exception as e:
                    logger.warning(f"JS fallback click failed: {e}")
            if not clicked:
                raise RuntimeError(f"Could not click any element matching: {selector}")
            # Debug: screenshot after click for email-related steps
            if used_click_sel and ("Send" in (fallback_text or "") or "send" in params.get("name", "").lower()):
                try:
                    import base64
                    ss = await page.screenshot(type="png")
                    ss_b64 = base64.b64encode(ss).decode()
                    logger.info(f"[CLICK] Post-send screenshot captured ({len(ss)} bytes)")
                    await progress_cb(90, f"Post-send screenshot captured")
                except Exception as e:
                    logger.warning(f"Screenshot failed: {e}")
        elif action == "fill":
            selector = params["selector"]
            value = params["value"]
            await progress_cb(70, f"Filling field: {selector} with value")
            filled = False
            used_method = "none"
            is_contenteditable = False

            # Step 1: wait for any matching element to be visible
            selectors_to_try = [s.strip() for s in selector.split(",")]
            target_el = None
            for sel in selectors_to_try:
                try:
                    loc = page.locator(sel).first
                    await loc.wait_for(state="visible", timeout=2000)
                    target_el = loc
                    break
                except Exception:
                    continue

            if target_el is not None:
                try:
                    await target_el.click(timeout=1500)
                except Exception:
                    pass

                # Determine if the matched element is contenteditable
                is_contenteditable = False
                try:
                    meta = await asyncio.wait_for(
                        target_el.evaluate("""el => ({
                            tag: el.tagName.toLowerCase(),
                            ce: el.getAttribute('contenteditable')
                        })"""),
                        timeout=3.0,
                    )
                    is_contenteditable = meta["tag"] in ("div", "span", "td", "p") or meta["ce"] is not None
                except Exception:
                    pass

                if is_contenteditable:
                    # Gmail's Quill editor requires keyboard events to register content.
                    # Try: focus + select all + keyboard.type (most reliable for Gmail)
                    try:
                        # Click to focus the contenteditable
                        await target_el.click(timeout=3000)
                        await asyncio.sleep(0.3)
                        # Select all existing content and delete
                        await page.keyboard.press("Control+a")
                        await asyncio.sleep(0.1)
                        await page.keyboard.press("Backspace")
                        await asyncio.sleep(0.2)
                        # Type the value using keyboard (triggers proper input events)
                        await page.keyboard.type(value, delay=5)
                        filled = True
                        used_method = "keyboard_type"
                        await progress_cb(75, "Used keyboard.type for contenteditable (Gmail-compatible)")
                    except Exception as e:
                        logger.warning(f"keyboard.type contenteditable failed: {e}")

                    # Fallback: page.fill
                    if not filled:
                        for sel in selectors_to_try:
                            try:
                                await page.fill(sel, value, timeout=5000)
                                filled = True
                                used_method = "page.fill_contenteditable"
                                await progress_cb(75, "Used page.fill for contenteditable (fallback)")
                                break
                            except Exception:
                                continue

                if not filled:
                    try:
                        await page.fill(selector, value, timeout=5000)
                        filled = True
                        used_method = "page.fill"
                    except Exception:
                        pass

            # Fallback: try Playwright fill on each comma-separated selector
            if not filled:
                for sel in selectors_to_try:
                    try:
                        await page.fill(sel, value, timeout=5000)
                        filled = True
                        used_method = f"page.fill_fallback:{sel[:40]}"
                        await progress_cb(75, f"Used fallback selector: {sel}")
                        break
                    except Exception:
                        continue

            # Last resort: JS evaluate to set any visible input/contenteditable
            if not filled:
                try:
                    await asyncio.wait_for(
                        page.evaluate(f"""
                            const val = {json.dumps(value)};
                            const candidates = document.querySelectorAll(
                                'input[type="text"], input:not([type]), textarea, div[contenteditable], [role="textbox"]'
                            );
                            for (const el of candidates) {{
                                if (el.offsetParent !== null && el.offsetHeight > 0) {{
                                    el.focus();
                                    if (el.isContentEditable) {{
                                        el.textContent = val;
                                    }} else {{
                                        el.value = val;
                                    }}
                                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                                    el.dispatchEvent(new Event('change', {{bubbles: true}}));
                                    break;
                                }}
                            }}
                        """),
                        timeout=5.0,
                    )
                    filled = True
                    used_method = "js_global_fallback"
                    await progress_cb(75, "Used JS global fallback to fill element")
                except Exception:
                    pass

            # Post-fill verification: read back the value
            actual_value = ""
            if filled and target_el is not None:
                try:
                    actual_value = await asyncio.wait_for(
                        target_el.evaluate("el => el.isContentEditable ? el.textContent : el.value"),
                        timeout=3.0,
                    )
                except Exception:
                    actual_value = "contenteditable_filled" if used_method in ("js_evaluate_fill", "page.fill_contenteditable") else ""
                if actual_value:
                    logger.info(f"[FILL] Readback after fill: '{actual_value[:100]}' (method={used_method})")

            if not filled:
                raise RuntimeError(f"Could not fill any input field near selector: {selector}")

            result = {"filled": True, "method": used_method, "actual_value": actual_value[:200] if actual_value else ""}
            logger.info(f"[FILL_DONE] method={used_method} selector={selector[:60]} value_len={len(value)}")
        elif action == "press":
            key = params["key"]
            await progress_cb(70, f"Pressing key: {key}")
            await page.keyboard.press(key)
            if key.lower() == "enter":
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                await asyncio.sleep(4)
        elif action == "wait":
            seconds = params.get("seconds", 2)
            await progress_cb(70, f"Waiting {seconds} seconds...")
            await asyncio.sleep(seconds)
        elif action == "wait_for_selector":
            selector = params["selector"]
            timeout = params.get("timeout", 10)
            await progress_cb(70, f"Waiting for selector: {selector} (timeout={timeout}s)")
            found = False
            for sel in [s.strip() for s in selector.split(",")]:
                try:
                    await page.wait_for_selector(sel, timeout=timeout * 1000, state="visible")
                    found = True
                    await progress_cb(80, f"Found element: {sel}")
                    break
                except Exception:
                    continue
            if not found:
                raise RuntimeError(f"wait_for_selector: none of [{selector}] appeared within {timeout}s — element required for next steps")
            result = {"found": found, "selector": selector}
        elif action == "scrape_text":
            await progress_cb(80, "Scraping page inner text")
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=8000)
            except Exception:
                pass
            await asyncio.sleep(2)
            try:
                result = {"text": await asyncio.wait_for(page.inner_text("body"), timeout=10)}
            except Exception:
                result = {"text": await asyncio.wait_for(page.evaluate("document.body.innerText.substring(0, 15000)"), timeout=10)}
            # Enforce output size limit
            if result.get("text"):
                result["text"] = _truncate_output(result["text"], MAX_SCRAPED_TEXT_BYTES)
        elif action == "scrape_links":
            link_count = params.get("count", 5)
            domain_filter = params.get("domain", "")
            await progress_cb(80, f"Extracting up to {link_count} links from page")
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=8000)
            except Exception:
                pass
            await asyncio.sleep(3)
            try:
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(2)
            except Exception:
                pass
            domain_check = f'if (!href.includes("{domain_filter}")) continue;' if domain_filter else ''
            js_code = """
                (() => {
                    const links = [];
                    const seen = new Set();
                    const anchors = document.querySelectorAll('a[href]');
                    for (const a of anchors) {
                        const href = a.href;
                        if (!href || href === '#' || href.startsWith('javascript:')) continue;
                        if (seen.has(href)) continue;
                        DOMAIN_CHECK
                        seen.add(href);
                        let title = '';
                        // YouTube-specific: try to get video title from nearby elements
                        const container = a.closest('ytd-video-renderer, ytd-rich-item-renderer, ytd-grid-video-renderer, ytd-playlist-video-renderer');
                        if (container) {
                            const titleEl = container.querySelector('#video-title, #video-title-link, .title-and-badge .title, a#video-title, h3 a, span#title');
                            if (titleEl) {
                                title = (titleEl.getAttribute('title') || titleEl.getAttribute('aria-label') || titleEl.textContent || '').trim();
                            }
                        }
                        if (!title || title.length < 3) {
                            title = (a.getAttribute('aria-label') || a.getAttribute('title') || '').trim();
                        }
                        if (!title || title.length < 3) {
                            title = (a.textContent || '').trim().substring(0, 120);
                        }
                        if (!title || title.length < 3) continue;
                        title = title.substring(0, 120);
                        // Clean up YouTube junk from titles
                        title = title.replace(/\\s+/g, ' ').replace('Watch ', '').replace('Now playing ', '').trim();
                        if (title.length < 3) continue;
                        links.push({title: title, url: href});
                        if (links.length >= LINK_COUNT) break;
                    }
                    return JSON.stringify(links);
                })()
            """.replace('DOMAIN_CHECK', domain_check).replace('LINK_COUNT', str(link_count))
            try:
                raw = await asyncio.wait_for(page.evaluate(js_code), timeout=10)
                links = json.loads(raw) if raw else []
                result = {"links": links, "count": len(links)}
            except Exception as e:
                logger.warning(f"scrape_links failed: {e}")
                result = {"links": [], "count": 0, "error": str(e)}
        elif action == "run" or action == "summarize":
            raw_query = params.get("query", params.get("command", ""))
            if raw_query.startswith("python ") or raw_query.startswith("echo ") or any(kw in raw_query for kw in ["sh ", "bash ", "./", "ping ", "curl "]):
                raw_query = ""
            query = raw_query or "Summarize the key information from this page"
            await progress_cb(50, "Waiting for page to load...")
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=8000)
            except Exception:
                pass
            await asyncio.sleep(3)
            await progress_cb(60, "Extracting page content...")
            try:
                page_text = await asyncio.wait_for(page.inner_text("body"), timeout=15)
            except Exception:
                try:
                    page_text = await asyncio.wait_for(page.evaluate("document.body.innerText.substring(0, 15000)"), timeout=10)
                except Exception:
                    page_text = ""
            if len(page_text.strip()) < 50:
                await asyncio.sleep(3)
                try:
                    page_text = await asyncio.wait_for(page.inner_text("body"), timeout=10)
                except Exception:
                    pass
            truncated = page_text[:6000]
            await progress_cb(70, "Generating summary via LLM...")
            try:
                summary = await llm_service.generate(
                    prompt=f"Page content:\n{truncated}\n\n{query}",
                    temperature=0.3,
                )
            except Exception as e:
                logger.warning(f"LLM summarization failed: {e}")
                summary = f"Could not generate summary: {e}"
            result = {"summary": summary}
        else:
            raise ValueError(f"Unknown browser agent action: {action}")

        await progress_cb(100, f"Browser action {action} execution done.")
        return result

    async def cleanup(self):
        for uid, entry in self._user_contexts.items():
            if entry.get("context"):
                try:
                    await entry["context"].close()
                except Exception:
                    pass
        if self._playwright:
            await self._playwright.stop()


class FileAgent(BaseAgent):
    _SAFE_ACTIONS = {"find_text", "search", "read", "list"}

    ACTION_ALIASES = {
        "move_file": "move",
        "delete_file": "delete",
        "create_folder": "create_directory",
        "create_dir": "create_directory",
        "mkdir": "create_directory",
        "move_files_by_keyword": "move_matching",
        "rename_file": "rename",
        "copy_file": "copy",
        "read_file": "read",
        "write_file": "write",
        "list_files": "list",
        "search_files": "search",
        "find_files": "find_text",
    }

    def _normalize_action(self, action: str) -> str:
        return self.ACTION_ALIASES.get(action, action)

    def _resolve_path(self, raw: str) -> str:
        """Resolve a path using the robust path utilities."""
        return resolve_path(raw)

    def _validate_workspace(self, path: str) -> Optional[str]:
        ok, reason = is_safe_path(path)
        if not ok:
            return reason
        return None

    def _file_exists(self, path: str) -> bool:
        return os.path.exists(path) and os.path.isfile(path)

    def _dir_exists(self, path: str) -> bool:
        return os.path.exists(path) and os.path.isdir(path)

    def _find_file_in_allowed_roots(self, filename: str) -> Optional[str]:
        """Find a file by name in the allowed roots."""
        return find_file(filename)

    async def execute(self, action: str, params: Dict[str, Any], progress_cb: Callable[[int, str], Any], user_id: str = "default") -> Dict[str, Any]:
        action = self._normalize_action(action)
        await progress_cb(10, f"File action request: {action}")

        if action not in self._SAFE_ACTIONS:
            authorized = await permission_guard.authorize_action("file", action, params)
            if not authorized:
                raise PermissionError(f"Permission denied for file action: {action}")

        result: Dict[str, Any] = {}

        if action in ("find_text", "search"):
            query = params.get("text", params.get("query", params.get("path", "")))
            await progress_cb(50, f"Searching file index for: '{query}'")
            try:
                from bson import ObjectId
                uid = ObjectId(user_id) if user_id and user_id != "default" else ObjectId()
                raw_results = await file_indexer.search(query, uid)
                result = {
                    "success": True, "query": query,
                    "match_count": len(raw_results),
                    "matches": [{"file_name": r.get("file_name", "") if isinstance(r, dict) else r.file_name, "file_path": r.get("file_path", "") if isinstance(r, dict) else r.file_path} for r in raw_results],
                }
            except Exception as e:
                logger.warning(f"File search failed: {e}")
                result = {"success": True, "query": query, "match_count": 0, "matches": []}

        elif action == "read":
            path = self._resolve_path(params.get("path", ""))
            await progress_cb(50, f"Reading file: {path}")
            if not os.path.exists(path):
                raise FileNotFoundError(f"File not found: {path}")
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                result = {"content": f.read()}

        elif action == "write":
            path = params.get("path", "")
            filename = params.get("filename", "")
            content = params.get("content", "")
            if filename and not path:
                output_dir = os.path.join(os.path.expanduser("~"), "ACO_Output")
                os.makedirs(output_dir, exist_ok=True)
                path = os.path.join(output_dir, filename)
            elif path:
                path = self._resolve_path(path)
            else:
                raise ValueError("write action requires either 'path' or 'filename' parameter")
            block = self._validate_workspace(path)
            if block:
                raise PermissionError(block)
            await progress_cb(50, f"Writing file: {path}")
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            result = {"success": True, "path": path}

        elif action == "delete":
            path = self._resolve_path(params.get("path", ""))
            block = self._validate_workspace(path)
            if block:
                raise PermissionError(block)
            # If path doesn't exist, try to find the file by name in allowed roots
            if not os.path.exists(path):
                filename = os.path.basename(path)
                found_path = self._find_file_in_allowed_roots(filename)
                if found_path:
                    logger.info(f"File not found at exact path, found at: {found_path}")
                    path = found_path
                else:
                    raise FileNotFoundError(f"File not found: {path} (also searched in allowed roots)")
            if os.path.isdir(path):
                raise IsADirectoryError(f"Cannot delete directory '{path}' through file.delete. Use file.create_directory or terminal.")
            try:
                file_size = os.path.getsize(path)
                file_mtime = os.path.getmtime(path)
                import time
                file_mtime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_mtime))
            except OSError:
                file_size = 0
                file_mtime_str = None
            await progress_cb(70, f"Deleting file: {path}")
            os.remove(path)
            await progress_cb(85, f"Verifying deletion: {path}")
            if os.path.exists(path):
                raise RuntimeError(f"File deletion verification failed: {path} still exists after unlink()")
            result = {
                "deleted": True,
                "path": path,
                "verified": True,
                "filename": os.path.basename(path),
                "size": file_size,
                "modified": file_mtime_str,
            }

        elif action == "list":
            path = self._resolve_path(params.get("path", "")) if params.get("path") else os.path.expanduser("~")
            limit = params.get("limit", 0)
            extension = params.get("extension", params.get("ext", "")).lower()
            pattern = params.get("pattern", "").lower()
            recursive = params.get("recursive", False)
            await progress_cb(50, f"Listing directory: {path}")
            if not os.path.isdir(path):
                raise FileNotFoundError(f"Directory not found: {path}")
            entries = []
            if recursive:
                for root, dirs, files in os.walk(path):
                    for entry in dirs + files:
                        full = os.path.join(root, entry)
                        rel = os.path.relpath(full, path)
                        if extension and not entry.lower().endswith(f".{extension}"):
                            continue
                        if pattern and pattern not in entry.lower():
                            continue
                        try:
                            mtime = os.path.getmtime(full)
                        except Exception:
                            mtime = 0
                        entries.append({
                            "name": entry, "path": full, "relative_path": rel,
                            "is_dir": os.path.isdir(full),
                            "size": os.path.getsize(full) if os.path.isfile(full) else None,
                            "modified": mtime,
                        })
            else:
                for entry in os.listdir(path):
                    full = os.path.join(path, entry)
                    if extension and not entry.lower().endswith(f".{extension}"):
                        continue
                    if pattern and pattern not in entry.lower():
                        continue
                    try:
                        mtime = os.path.getmtime(full)
                    except Exception:
                        mtime = 0
                    entries.append({
                        "name": entry, "path": full,
                        "is_dir": os.path.isdir(full),
                        "size": os.path.getsize(full) if os.path.isfile(full) else None,
                        "modified": mtime,
                    })
            entries.sort(key=lambda e: e["modified"], reverse=True)
            if limit > 0:
                entries = entries[:limit]
            result = {"path": path, "entries": entries, "count": len(entries)}

        elif action == "create_directory":
            path = self._resolve_path(params.get("path", ""))
            block = self._validate_workspace(path)
            if block:
                raise PermissionError(block)
            if os.path.exists(path):
                if os.path.isdir(path):
                    result = {"success": True, "path": path, "message": "Directory already exists"}
                    return result
                raise FileExistsError(f"A file already exists at '{path}'. Cannot create directory.")
            await progress_cb(50, f"Creating directory: {path}")
            os.makedirs(path, exist_ok=True)
            result = {"success": True, "path": path, "created": True}

        elif action == "move":
            source = self._resolve_path(params.get("source", ""))
            dest = self._resolve_path(params.get("destination", ""))
            create_parent = params.get("create_parent", True)
            block_s = self._validate_workspace(source)
            if block_s:
                raise PermissionError(f"Source: {block_s}")
            block_d = self._validate_workspace(dest)
            if block_d:
                raise PermissionError(f"Destination: {block_d}")
            if not os.path.exists(source):
                raise FileNotFoundError(f"Source not found: {source}")
            if os.path.isdir(source):
                raise IsADirectoryError(f"Cannot move directory '{source}' through file.move.")
            if os.path.exists(dest) and os.path.isfile(dest):
                raise FileExistsError(f"Destination file already exists: {dest}")
            await progress_cb(50, f"Moving: {source} → {dest}")
            parent = os.path.dirname(dest)
            if parent and create_parent:
                os.makedirs(parent, exist_ok=True)
            os.rename(source, dest)
            if not os.path.exists(dest):
                raise OSError(f"Move verification failed: source absent, dest absent")
            if os.path.exists(source):
                raise OSError(f"Move verification failed: source still exists")
            result = {"success": True, "source": source, "destination": dest, "moved": True}

        elif action == "rename":
            path = self._resolve_path(params.get("path", ""))
            new_name = params.get("new_name", "").strip()
            if not new_name:
                raise ValueError("rename requires 'new_name' parameter")
            block = self._validate_workspace(path)
            if block:
                raise PermissionError(block)
            if not os.path.exists(path):
                raise FileNotFoundError(f"File not found: {path}")
            dest = os.path.join(os.path.dirname(path), new_name)
            dest = self._resolve_path(dest)
            if os.path.exists(dest):
                raise FileExistsError(f"A file named '{new_name}' already exists in the same directory")
            await progress_cb(50, f"Renaming: {os.path.basename(path)} → {new_name}")
            os.rename(path, dest)
            result = {"success": True, "old_path": path, "new_path": dest, "renamed": True}

        elif action == "copy":
            source = self._resolve_path(params.get("source", ""))
            dest = self._resolve_path(params.get("destination", ""))
            create_parent = params.get("create_parent", True)
            block_s = self._validate_workspace(source)
            if block_s:
                raise PermissionError(f"Source: {block_s}")
            block_d = self._validate_workspace(dest)
            if block_d:
                raise PermissionError(f"Destination: {block_d}")
            if not os.path.exists(source):
                raise FileNotFoundError(f"Source not found: {source}")
            if os.path.isdir(source):
                raise IsADirectoryError(f"Cannot copy directory '{source}' through file.copy.")
            if os.path.exists(dest):
                raise FileExistsError(f"Destination already exists: {dest}")
            await progress_cb(50, f"Copying: {source} → {dest}")
            parent = os.path.dirname(dest)
            if parent and create_parent:
                os.makedirs(parent, exist_ok=True)
            import shutil
            shutil.copy2(source, dest)
            if not os.path.exists(dest):
                raise OSError("Copy verification failed")
            result = {"success": True, "source": source, "destination": dest, "copied": True}

        elif action == "move_matching":
            source_dir = self._resolve_path(params.get("source_directory", ""))
            dest_dir = self._resolve_path(params.get("destination_directory", ""))
            match_type = params.get("match_type", "filename_contains")
            keyword = params.get("keyword", "")
            case_sensitive = params.get("case_sensitive", False)
            create_dest = params.get("create_destination", True)

            block_s = self._validate_workspace(source_dir)
            if block_s:
                raise PermissionError(f"Source directory: {block_s}")
            block_d = self._validate_workspace(dest_dir)
            if block_d:
                raise PermissionError(f"Destination directory: {block_d}")

            if not os.path.isdir(source_dir):
                raise FileNotFoundError(f"Source directory not found: {source_dir}")
            if match_type not in ("filename_contains", "filename_starts_with", "filename_ends_with", "extension", "exact_filename"):
                raise ValueError(f"Unsupported match_type: '{match_type}'")

            await progress_cb(20, f"Scanning {source_dir} for files matching '{keyword}' ({match_type})")

            if create_dest:
                os.makedirs(dest_dir, exist_ok=True)
            elif not os.path.isdir(dest_dir):
                raise FileNotFoundError(f"Destination directory not found: {dest_dir}")

            matched = []
            for entry in os.listdir(source_dir):
                full = os.path.join(source_dir, entry)
                if not os.path.isfile(full):
                    continue
                if self._match_file(entry, match_type, keyword, case_sensitive):
                    matched.append((entry, full))

            await progress_cb(50, f"Found {len(matched)} matching file(s)")

            moved = []
            skipped = []
            for name, src_path in matched:
                dst_path = os.path.join(dest_dir, name)
                if os.path.exists(dst_path):
                    skipped.append({"file": name, "reason": "destination already exists"})
                    continue
                try:
                    os.rename(src_path, dst_path)
                    if os.path.exists(dst_path) and not os.path.exists(src_path):
                        moved.append(name)
                    else:
                        skipped.append({"file": name, "reason": "move verification failed"})
                except Exception as e:
                    skipped.append({"file": name, "reason": str(e)})

            await progress_cb(100, f"Moved {len(moved)} file(s), skipped {len(skipped)}")
            result = {
                "success": True,
                "source_directory": source_dir,
                "destination_directory": dest_dir,
                "matched_count": len(matched),
                "moved_count": len(moved),
                "moved_files": moved,
                "skipped": skipped,
            }

        else:
            raise ValueError(f"Unknown file action: {action}")

        await progress_cb(100, f"File action '{action}' completed successfully.")
        return result



class TerminalAgent(BaseAgent):
    async def execute(self, action: str, params: Dict[str, Any], progress_cb: Callable[[int, str], Any], execution_id: str = "") -> Dict[str, Any]:
        await progress_cb(10, "Terminal shell action request.")
        
        authorized = await permission_guard.authorize_action("terminal", action, params)
        if not authorized:
            raise PermissionError("Terminal action was rejected by user policy permissions.")

        command = params["command"]

        # Block destructive commands
        block_reason = _is_terminal_command_blocked(command)
        if block_reason:
            raise PermissionError(f"Blocked dangerous terminal command: {block_reason}")

        await progress_cb(50, f"Executing terminal command: {command[:200]}")

        timeout = 60.0
        if "ping" in command.lower():
            timeout = 30.0

        loop = asyncio.get_running_loop()
        def run_proc():
            if sys.platform == "win32":
                escaped_cmd = command.replace('"', '`"')
                ps_cmd = f'powershell.exe -NoProfile -Command "{escaped_cmd}"'
                proc = subprocess.Popen(
                    ps_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            elif _needs_shell(command):
                proc = subprocess.Popen(
                    command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    preexec_fn=os.setsid,
                )
            else:
                try:
                    args = shlex.split(command, posix=False)
                    args = [a.strip('"').strip("'") for a in args]
                except ValueError:
                    args = command
                    proc = subprocess.Popen(
                        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                        preexec_fn=os.setsid,
                    )
                    try:
                        stdout, stderr = proc.communicate(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        stdout, stderr = proc.communicate()
                        raise TimeoutError(f"Command timed out after {timeout}s")
                    return proc.returncode, stdout, stderr

            register_process(execution_id, proc)
            try:
                try:
                    stdout, stderr = proc.communicate(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate()
                    raise TimeoutError(f"Command timed out after {timeout}s")
                return proc.returncode, stdout, stderr
            finally:
                unregister_process(execution_id)

        rc, stdout, stderr = await loop.run_in_executor(None, run_proc)
        
        stdout = _truncate_output(stdout or "")
        stderr = _truncate_output(stderr or "")
        output_preview = (stdout or stderr or "").strip()[:500]
        await progress_cb(90, f"Command finished (rc={rc}): {output_preview}")
        return {
            "returncode": rc,
            "stdout": stdout,
            "stderr": stderr
        }


class VisionAgent(BaseAgent):
    async def execute(self, action: str, params: Dict[str, Any], progress_cb: Callable[[int, str], Any]) -> Dict[str, Any]:
        await progress_cb(15, "Vision element mapping request.")

        authorized = await permission_guard.authorize_action("vision", action, params)
        if not authorized:
            raise PermissionError(f"User denied vision action: {action}")

        if action == "find_text":
            text = params["text"]
            await progress_cb(50, f"Searching for text: '{text}' on screen")
            coords = await vision_engine.find_element(text)
            return {"found": coords is not None, "coordinates": coords}
        elif action == "capture_elements":
            await progress_cb(50, "Parsing all visual elements from screen state")
            elements = await vision_engine.capture_and_process()
            return {"elements": elements}
        else:
            raise ValueError(f"Unknown vision action: {action}")


class AgentManager:
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {
            "desktop": DesktopAgent(),
            "browser": BrowserAgent(),
            "file": FileAgent(),
            "terminal": TerminalAgent(),
            "vision": VisionAgent()
        }

    async def execute_step(
        self, step_data: Dict[str, Any], progress_cb: Callable[[int, str], Any], user_id: str = "default", execution_id: str = ""
    ) -> Dict[str, Any]:
        """Looks up the target agent and runs the step actions."""
        agent_type = step_data.get("agent_type")
        action = step_data.get("action")
        params = step_data.get("parameters", {})

        agent = self._agents.get(agent_type)
        if not agent:
            raise ValueError(f"Unsupported agent type: {agent_type}")

        logger.info(f"AgentManager dispatching {action} to {agent_type} agent (user={user_id}).")
        if isinstance(agent, BrowserAgent):
            return await agent.execute(action, params, progress_cb, user_id=user_id)
        if isinstance(agent, FileAgent):
            return await agent.execute(action, params, progress_cb, user_id=user_id)
        if isinstance(agent, TerminalAgent):
            return await agent.execute(action, params, progress_cb, execution_id=execution_id)
        return await agent.execute(action, params, progress_cb)

    async def cleanup(self):
        """Releases long-running browser instances."""
        browser_agent = self._agents.get("browser")
        if isinstance(browser_agent, BrowserAgent):
            await browser_agent.cleanup()

# Export a single global instance of the AgentManager
agent_manager = AgentManager()
