import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    success: bool
    step_id: str = ""
    agent_type: str = ""
    action: str = ""
    confidence: float = 1.0
    message: str = ""
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class Verifier(ABC):
    @abstractmethod
    async def verify(
        self,
        step: Dict[str, Any],
        result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> VerificationResult:
        ...


class NavigateVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        url = result.get("url", "")
        title = result.get("title", "")
        if url and "error" not in url.lower() and title:
            return VerificationResult(
                success=True, message=f"Page loaded: {title[:60]}",
                diagnostics={"url": url, "title": title},
            )
        if not url:
            return VerificationResult(
                success=False, message="No URL returned from navigation",
                diagnostics={"result": result},
            )
        return VerificationResult(
            success=True, confidence=0.7, message=f"Landed on {url[:80]}",
            diagnostics={"url": url},
        )


class ClickVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        if result.get("success") is False:
            return VerificationResult(success=False, message="Click returned failure")
        return VerificationResult(success=True, confidence=0.6, message="Click executed")


class FillVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        if result.get("success") is False:
            return VerificationResult(success=False, message="Fill returned failure")
        expected = (step.get("parameters", {}) or {}).get("value", "")
        actual = result.get("actual_value", "")
        method = result.get("method", "unknown")
        # contenteditable fills skip value matching (readback hangs on React contenteditable)
        if method in ("js_textcontent", "js_evaluate_fill", "keyboard_insert", "page.fill_contenteditable", "keyboard_type") or actual == "contenteditable_filled":
            return VerificationResult(
                success=True, confidence=0.85,
                message=f"Contenteditable filled via textContent",
                diagnostics={"method": method},
            )
        if actual:
            # Normalize whitespace for comparison
            actual_norm = actual.strip().replace("\u00a0", " ").replace("\n", " ")
            expected_norm = expected.strip().replace("\u00a0", " ").replace("\n", " ")
            if expected_norm and expected_norm not in actual_norm and actual_norm not in expected_norm:
                return VerificationResult(
                    success=False, confidence=0.3,
                    message=f"Fill value mismatch: expected '{expected_norm[:60]}', got '{actual_norm[:60]}'",
                    diagnostics={"expected": expected[:200], "actual": actual[:200]},
                )
            return VerificationResult(
                success=True, confidence=0.9,
                message=f"Field filled ({method}): '{actual[:80]}'",
                diagnostics={"method": method, "actual_length": len(actual)},
            )
        if result.get("filled"):
            return VerificationResult(
                success=True, confidence=0.6,
                message=f"Fill executed ({method}), but could not read back value",
                diagnostics={"method": method},
            )
        return VerificationResult(success=True, confidence=0.5, message="Fill completed (no verification)")


class PressVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        if result.get("success") is False:
            return VerificationResult(success=False, message="Key press returned failure")
        return VerificationResult(success=True, confidence=0.5, message="Key pressed")


class WaitVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        return VerificationResult(success=True, confidence=1.0, message="Wait completed")


class WaitForSelectorVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        found = result.get("found", False)
        selector = result.get("selector", step.get("parameters", {}).get("selector", ""))
        if found:
            return VerificationResult(success=True, message=f"Element appeared: {selector[:80]}")
        return VerificationResult(success=False, confidence=0.3, message=f"Element not found: {selector[:80]}")


class ScrapeTextVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        text = result.get("text", "")
        if len(text) > 20:
            return VerificationResult(
                success=True, message=f"Extracted {len(text)} characters",
                diagnostics={"length": len(text)},
            )
        if text:
            return VerificationResult(success=True, confidence=0.5, message=f"Extracted {len(text)} chars (short)")
        return VerificationResult(success=False, message="No text extracted", diagnostics={"result": result})


class ScrapeLinksVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        count = result.get("count", 0)
        if count > 0:
            return VerificationResult(
                success=True, message=f"Extracted {count} links",
                diagnostics={"count": count},
            )
        return VerificationResult(success=False, confidence=0.3, message="No links found")


class SummarizeVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        summary = result.get("summary", "")
        if len(summary) > 20:
            return VerificationResult(
                success=True, message=f"Generated summary ({len(summary)} chars)",
                diagnostics={"length": len(summary)},
            )
        if summary:
            return VerificationResult(success=True, confidence=0.5, message="Short summary generated")
        return VerificationResult(success=False, message="No summary generated")


class FileWriteVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        path = result.get("path", "")
        if path and os.path.exists(path):
            size = os.path.getsize(path)
            return VerificationResult(
                success=True, message=f"File created: {os.path.basename(path)} ({size} bytes)",
                diagnostics={"path": path, "size": size},
            )
        if result.get("success"):
            return VerificationResult(success=True, confidence=0.8, message="File written")
        return VerificationResult(success=False, message="File not created", diagnostics={"result": result})


class FileReadVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        content = result.get("content", "")
        if content:
            return VerificationResult(success=True, message=f"Read {len(content)} characters")
        return VerificationResult(success=False, message="No content returned")


class FileListVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        count = result.get("count", 0)
        path = result.get("path", "")
        if count > 0:
            return VerificationResult(
                success=True, message=f"Listed {count} items in {os.path.basename(path) if path else 'directory'}",
                diagnostics={"count": count, "path": path},
            )
        return VerificationResult(success=True, confidence=0.7, message=f"Directory empty: {path}")


class FileDeleteVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        path = result.get("path", "")
        deleted = result.get("deleted", False)
        verified = result.get("verified", False)
        if deleted and verified and path and not os.path.exists(path):
            return VerificationResult(
                success=True, confidence=1.0,
                message=f"File deleted and verified: {path}",
                diagnostics={"path": path, "size": result.get("size"), "modified": result.get("modified")},
            )
        if deleted and path and os.path.exists(path):
            return VerificationResult(
                success=False,
                message=f"Deletion failed: {path} still exists on disk",
                diagnostics={"path": path},
            )
        if not deleted:
            return VerificationResult(
                success=False,
                message=f"Delete action did not complete: {result}",
                diagnostics={"result": result},
            )
        return VerificationResult(
            success=False,
            message=f"Deletion unverified: {path}",
            diagnostics={"path": path, "deleted": deleted, "verified": verified},
        )


class FileMoveVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        if result.get("moved") and result.get("success"):
            dest = result.get("destination", "")
            if dest and os.path.exists(dest):
                return VerificationResult(
                    success=True, confidence=1.0,
                    message=f"File moved: {os.path.basename(dest)}",
                    diagnostics={"source": result.get("source"), "destination": dest},
                )
            return VerificationResult(
                success=True, confidence=0.7,
                message="File moved (destination not verified on disk)",
            )
        return VerificationResult(
            success=False,
            message=f"Move failed: {result}",
            diagnostics={"result": result},
        )


class FileRenameVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        if result.get("renamed") and result.get("success"):
            new_path = result.get("new_path", "")
            if new_path and os.path.exists(new_path):
                return VerificationResult(
                    success=True, confidence=1.0,
                    message=f"File renamed to {os.path.basename(new_path)}",
                    diagnostics={"old_path": result.get("old_path"), "new_path": new_path},
                )
            return VerificationResult(
                success=True, confidence=0.7,
                message="File renamed (not verified on disk)",
            )
        return VerificationResult(
            success=False,
            message=f"Rename failed: {result}",
            diagnostics={"result": result},
        )


class FileCopyVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        if result.get("copied") and result.get("success"):
            dest = result.get("destination", "")
            if dest and os.path.exists(dest):
                return VerificationResult(
                    success=True, confidence=1.0,
                    message=f"File copied: {os.path.basename(dest)}",
                    diagnostics={"source": result.get("source"), "destination": dest},
                )
            return VerificationResult(
                success=True, confidence=0.7,
                message="File copied (not verified on disk)",
            )
        return VerificationResult(
            success=False,
            message=f"Copy failed: {result}",
            diagnostics={"result": result},
        )


class FileCreateDirectoryVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        path = result.get("path", "")
        if result.get("success") and path:
            if result.get("created") or result.get("message") == "Directory already exists" or os.path.isdir(path):
                return VerificationResult(
                    success=True, confidence=1.0,
                    message=f"Directory created: {path}",
                    diagnostics={"path": path},
                )
        return VerificationResult(
            success=False,
            message=f"Directory creation failed: {result}",
            diagnostics={"result": result},
        )


class FileFindTextVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        count = result.get("match_count", 0)
        query = result.get("query", "")
        if count > 0:
            return VerificationResult(
                success=True, message=f"Found {count} match(es) for '{query}'",
                diagnostics={"match_count": count, "query": query},
            )
        return VerificationResult(
            success=True, confidence=0.6,
            message=f"No matches found for '{query}' (search completed)",
            diagnostics={"match_count": 0, "query": query},
        )


class FileMoveMatchingVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        if result.get("success"):
            moved = result.get("moved_count", 0)
            matched = result.get("matched_count", 0)
            skipped = result.get("skipped", [])
            if moved > 0:
                return VerificationResult(
                    success=True, confidence=1.0,
                    message=f"Moved {moved}/{matched} files. Skipped: {len(skipped)}",
                    diagnostics={"moved": moved, "matched": matched, "skipped": len(skipped)},
                )
            if matched == 0:
                return VerificationResult(
                    success=True, confidence=0.7,
                    message="No matching files found",
                    diagnostics={"matched": 0},
                )
            return VerificationResult(
                success=True, confidence=0.8,
                message=f"0 of {matched} files moved (all skipped)",
                diagnostics={"matched": matched, "skipped": len(skipped)},
            )
        return VerificationResult(
            success=False,
            message=f"Move matching failed: {result}",
            diagnostics={"result": result},
        )


class TerminalRunVerifier(Verifier):
    async def verify(self, step: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> VerificationResult:
        rc = result.get("returncode", -1)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        if rc == 0:
            return VerificationResult(
                success=True, message=f"Exit code 0, stdout: {stdout[:100] if stdout else '(empty)'}",
                diagnostics={"returncode": rc},
            )
        return VerificationResult(
            success=False, message=f"Exit code {rc}: {stderr[:200] if stderr else stdout[:200]}",
            diagnostics={"returncode": rc, "stderr": stderr[:500], "stdout": stdout[:500]},
        )


class VerificationEngine:
    def __init__(self):
        self._verifiers: Dict[str, Verifier] = {
            ("browser", "navigate"): NavigateVerifier(),
            ("browser", "click"): ClickVerifier(),
            ("browser", "fill"): FillVerifier(),
            ("browser", "press"): PressVerifier(),
            ("browser", "wait"): WaitVerifier(),
            ("browser", "wait_for_selector"): WaitForSelectorVerifier(),
            ("browser", "scrape_text"): ScrapeTextVerifier(),
            ("browser", "scrape_links"): ScrapeLinksVerifier(),
            ("browser", "summarize"): SummarizeVerifier(),
            ("file", "write"): FileWriteVerifier(),
            ("file", "read"): FileReadVerifier(),
            ("file", "list"): FileListVerifier(),
            ("file", "delete"): FileDeleteVerifier(),
            ("file", "move"): FileMoveVerifier(),
            ("file", "rename"): FileRenameVerifier(),
            ("file", "copy"): FileCopyVerifier(),
            ("file", "create_directory"): FileCreateDirectoryVerifier(),
            ("file", "find_text"): FileFindTextVerifier(),
            ("file", "search"): FileFindTextVerifier(),
            ("file", "move_matching"): FileMoveMatchingVerifier(),
            ("terminal", "run"): TerminalRunVerifier(),
        }

    async def verify(
        self,
        step: Dict[str, Any],
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        agent_type = step.get("agent_type", "")
        action = step.get("action", "")
        step_id = step.get("step_id", "")

        verifier = self._verifiers.get((agent_type, action))
        if not verifier:
            return VerificationResult(
                success=True, confidence=0.5,
                step_id=step_id, agent_type=agent_type, action=action,
                message=f"No verifier for {agent_type}/{action} — assumed success",
            )

        try:
            vresult = await verifier.verify(step, result, context or {})
            vresult.step_id = step_id
            vresult.agent_type = agent_type
            vresult.action = action
            if not vresult.success:
                logger.warning(f"Verification FAILED for {agent_type}/{action} [{step_id}]: {vresult.message}")
            return vresult
        except Exception as e:
            logger.error(f"Verifier exception for {agent_type}/{action}: {e}")
            return VerificationResult(
                success=False, step_id=step_id, agent_type=agent_type, action=action,
                message=f"Verifier error: {e}",
                diagnostics={"error": str(e)},
            )


verification_engine = VerificationEngine()
